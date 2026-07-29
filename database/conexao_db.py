import os
import sqlite3

DB_PATH = "database/financeiro_v2.db"


def inicializar_banco_dados():
    if not os.path.exists("database"):
        os.makedirs("database")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Tabela de Usuários Completa
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            nome TEXT NOT NULL,
            departamento TEXT DEFAULT 'Geral',
            cargo TEXT DEFAULT 'Membro',
            foto_base64 TEXT,
            primeiro_login INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Ativo'
        )
    """
    )

    # Garantir colunas caso a tabela já tenha sido criada sem elas
    colunas_desejadas = [
        ("cargo", "TEXT DEFAULT 'Membro'"),
        ("foto_base64", "TEXT"),
    ]
    for col, tipo in colunas_desejadas:
        try:
            cursor.execute(f"ALTER TABLE usuarios ADD COLUMN {col} {tipo}")
        except sqlite3.OperationalError:
            pass  # Coluna já existe

    # Tabela de Fluxo de Caixa
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS fluxo_caixa_geral (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mes TEXT, data TEXT, departamento TEXT, tipo TEXT,
            categoria TEXT, descricao TEXT, valor_bruto REAL,
            taxa REAL, valor_liquido REAL, conta_origem TEXT,
            status_pagamento TEXT, nota_fiscal TEXT, status_envio TEXT,
            comprovante TEXT, conta TEXT
        )
    """
    )

    # Inserção segura de diretores (utiliza INSERT OR IGNORE para não sobrescrever dados salvos)
    usuarios_iniciais = [
        (
            "vice-presidencia@farmaciajr.com",
            "123456",
            "Vice-Presidência",
            "VP",
            "Diretor(a)",
            0,
            "Ativo",
        ),
        (
            "presidencia@farmaciajr.com",
            "123456",
            "Presidência",
            "Presidência",
            "Diretor(a)",
            0,
            "Ativo",
        ),
    ]

    for (
        email,
        senha,
        nome,
        dep,
        cargo,
        p_login,
        status,
    ) in usuarios_iniciais:
        cursor.execute(
            """
            INSERT OR IGNORE INTO usuarios (email, senha, nome, departamento, cargo, primeiro_login, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (email.strip().lower(), senha, nome, dep, cargo, p_login, status),
        )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    inicializar_banco_dados()
