"""
Módulo central de conexão com o banco de dados da Plataforma VP.

Antes, cada tela abria sua própria conexão SQLite local
(sqlite3.connect(...)), o que fazia os dados sumirem sempre que o
Streamlit Cloud reiniciava o container (sistema de arquivos efêmero).

Agora, get_connection() devolve uma conexão Postgres (Supabase), que é
persistente. Para não precisar reescrever as ~190 queries que usam "?"
como placeholder (sintaxe do SQLite), a conexão retornada é envolvida
num "compat layer" que traduz automaticamente "?" para "%s" (sintaxe do
Postgres/psycopg2) antes de executar. Ou seja: o resto do código do app
continua escrevendo cursor.execute("... WHERE id = ?", (id,)) igual a
antes, sem precisar tocar em cada uma das telas.
"""

import streamlit as st
import psycopg2
import psycopg2.extras


class _CompatCursor:
    """Encapsula um cursor psycopg2 e traduz '?' -> '%s' nas queries."""

    def __init__(self, real_cursor):
        self._cursor = real_cursor

    @staticmethod
    def _traduzir(query):
        # Os placeholders '?' do SQLite viram '%s' do Postgres.
        # (Não há nenhum '?' literal dentro de strings SQL no projeto,
        # apenas usados como placeholder — checado manualmente.)
        return query.replace("?", "%s")

    def execute(self, query, params=None):
        query_traduzida = self._traduzir(query)
        if params is None:
            return self._cursor.execute(query_traduzida)
        return self._cursor.execute(query_traduzida, params)

    def executemany(self, query, seq_params):
        query_traduzida = self._traduzir(query)
        return self._cursor.executemany(query_traduzida, seq_params)

    def __getattr__(self, item):
        # Repassa tudo mais (fetchone, fetchall, rowcount, description, etc.)
        return getattr(self._cursor, item)

    def __iter__(self):
        return iter(self._cursor)


class _CompatConnection:
    """Encapsula a conexão psycopg2 para devolver cursores compatíveis."""

    def __init__(self, real_conn):
        self._conn = real_conn

    def cursor(self, *args, **kwargs):
        return _CompatCursor(self._conn.cursor(*args, **kwargs))

    def __getattr__(self, item):
        # Repassa commit, close, rollback, etc. direto para a conexão real.
        return getattr(self._conn, item)


def _obter_credenciais():
    """Lê a connection string do Supabase a partir do st.secrets."""
    if "SUPABASE_DB_URL" in st.secrets:
        return {"dsn": st.secrets["SUPABASE_DB_URL"]}

    # Alternativa: credenciais separadas em vez de uma URL única.
    return {
        "host": st.secrets["SUPABASE_DB_HOST"],
        "port": st.secrets.get("SUPABASE_DB_PORT", "5432"),
        "dbname": st.secrets.get("SUPABASE_DB_NAME", "postgres"),
        "user": st.secrets["SUPABASE_DB_USER"],
        "password": st.secrets["SUPABASE_DB_PASSWORD"],
    }


def get_connection():
    """
    Devolve uma conexão Postgres (Supabase), compatível com o padrão de
    uso `conn.cursor()...execute("...?...")` usado em todo o restante
    do projeto.
    """
    creds = _obter_credenciais()
    if "dsn" in creds:
        conn = psycopg2.connect(creds["dsn"])
    else:
        conn = psycopg2.connect(**creds)
    return _CompatConnection(conn)
