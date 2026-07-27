import sqlite3

def inicializar_banco_dados():
    """Garante a criação de todas as tabelas necessárias no banco de dados unificado"""
    conn = sqlite3.connect('database/financeiro_farmaciajr.db')
    cursor = conn.cursor()
    
    # [Tabelas antigas de utilizadores/fluxo de caixa que já tinhas mantêm-se aqui]
    # ...

    # TABELA: Fila de Comandas para a montagem do Açaí
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comandas_dda (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            horario TEXT,
            produto TEXT,
            adicionais TEXT,
            status TEXT
        )
    ''')

    # Insere o seu e-mail garantindo acesso de Vice-Presidência/Admin
cursor.execute("""
    INSERT OR REPLACE INTO usuarios (email, nome, cargo, status)
    VALUES ('vice-presidencia@farmaciajr.com', 'Administrador', 'Vice-Presidência', 'Ativo')
""")
conn.commit()

    # NOVA TABELA: Controle de Empréstimos e Devoluções de Jalecos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emprestimos_jaleco (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data_hora TEXT,
            cliente_nome TEXT,
            cliente_telefone TEXT,
            membro_responsavel TEXT,
            status_pagamento TEXT,
            status_devolucao TEXT
        )
    ''')

    # Tabela de Usuários/Membros com a estrutura definitiva exigida pelo app.py e equipe.py
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            email TEXT UNIQUE,
            senha TEXT DEFAULT 'farmaciajr123',
            departamento TEXT DEFAULT 'Geral',
            primeiro_login INTEGER DEFAULT 1,
            cargo TEXT DEFAULT 'Assessor(a)',
            foto_base64 TEXT DEFAULT ''
        )
    ''')

    # SCRIPT DE COMPLIANCE: Se o banco já existia, garante que nenhuma coluna nova ficou de fora
    colunas_usuarios = [
        ("nome", "TEXT"),
        ("email", "TEXT UNIQUE"),
        ("senha", "TEXT DEFAULT 'farmaciajr123'"),
        ("departamento", "TEXT DEFAULT 'Geral'"),
        ("primeiro_login", "INTEGER DEFAULT 1"),
        ("cargo", "TEXT DEFAULT 'Assessor(a)'"),
        ("foto_base64", "TEXT DEFAULT ''")
    ]
    
    for coluna, tipo in colunas_usuarios:
        try:
            cursor.execute(f"ALTER TABLE usuarios ADD COLUMN {coluna} {tipo}")
        except sqlite3.OperationalError:
            pass # A coluna já existe, ignora e vai para a próxima
    
    conn.commit()
    conn.close()
    print("Banco de dados da Farmácia Jr. configurado com sucesso!")
