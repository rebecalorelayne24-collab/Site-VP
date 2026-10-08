"""
Conexão com o Postgres (Supabase) para a Plataforma VP.

Velocidade: abrir uma conexão nova a cada consulta é caro (handshake de
rede + TLS + login), principalmente com o servidor longe. Aqui as conexões
ficam num "pool" criado uma única vez (st.cache_resource) e são reaproveitadas.
Para o resto do código nada muda: conn.close() agora devolve a conexão ao pool
em vez de fechá-la, e os "?" continuam sendo traduzidos para "%s".
"""

import time

import psycopg2
import psycopg2.pool
import streamlit as st

_ULTIMO_USO = {}          # id(conexão) -> timestamp do último uso
_OCIOSO_MAX_SEG = 30      # acima disso, testa a conexão antes de usar


class _CompatCursor:
    """Encapsula um cursor psycopg2 e traduz '?' -> '%s' nas queries."""

    def __init__(self, real_cursor):
        self._cursor = real_cursor

    @staticmethod
    def _traduzir(query):
        return query.replace("?", "%s")

    def execute(self, query, params=None):
        q = self._traduzir(query)
        if params is None:
            return self._cursor.execute(q)
        return self._cursor.execute(q, params)

    def executemany(self, query, seq_params):
        return self._cursor.executemany(self._traduzir(query), seq_params)

    def __getattr__(self, item):
        return getattr(self._cursor, item)

    def __iter__(self):
        return iter(self._cursor)


class _CompatConnection:
    """Conexão do pool; close() devolve ao pool em vez de encerrar."""

    def __init__(self, real_conn, pool):
        self._conn = real_conn
        self._pool = pool
        self._devolvida = False

    def cursor(self, *args, **kwargs):
        return _CompatCursor(self._conn.cursor(*args, **kwargs))

    def close(self):
        if self._devolvida:
            return
        self._devolvida = True
        try:
            if not self._conn.closed:
                self._conn.rollback()  # limpa transação pendente (commit já foi feito antes)
                _ULTIMO_USO[id(self._conn)] = time.time()
                self._pool.putconn(self._conn)
            else:
                self._pool.putconn(self._conn, close=True)
        except Exception:
            try:
                self._pool.putconn(self._conn, close=True)
            except Exception:
                pass

    def __getattr__(self, item):
        return getattr(self._conn, item)


def _obter_credenciais():
    if "SUPABASE_DB_URL" in st.secrets:
        return {"dsn": st.secrets["SUPABASE_DB_URL"]}
    return {
        "host": st.secrets["SUPABASE_DB_HOST"],
        "port": st.secrets.get("SUPABASE_DB_PORT", "5432"),
        "dbname": st.secrets.get("SUPABASE_DB_NAME", "postgres"),
        "user": st.secrets["SUPABASE_DB_USER"],
        "password": st.secrets["SUPABASE_DB_PASSWORD"],
    }


@st.cache_resource
def _obter_pool():
    creds = _obter_credenciais()
    extras = dict(keepalives=1, keepalives_idle=30, keepalives_interval=10, keepalives_count=3)
    if "dsn" in creds:
        return psycopg2.pool.ThreadedConnectionPool(1, 5, creds["dsn"], **extras)
    return psycopg2.pool.ThreadedConnectionPool(1, 5, **creds, **extras)


def _conexao_viva(conn):
    """Se ficou parada um tempo, confirma que o servidor ainda responde."""
    if conn.closed:
        return False
    parada = time.time() - _ULTIMO_USO.get(id(conn), 0)
    if parada < _OCIOSO_MAX_SEG:
        return True
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.rollback()
        return True
    except Exception:
        return False


def get_connection():
    pool = _obter_pool()
    for _ in range(3):
        conn = pool.getconn()
        if _conexao_viva(conn):
            return _CompatConnection(conn, pool)
        pool.putconn(conn, close=True)
    return _CompatConnection(pool.getconn(), pool)
 
    return _CompatConnection(pool.getconn(), pool)
