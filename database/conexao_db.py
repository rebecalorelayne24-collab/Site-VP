import sqlite3
import os

def inicializar_banco_dados():
    # Garante que a pasta 'database' exista
    if not os.path.exists('database'):
        os.makedirs('database')
        
    caminho_db = 'database/financeiro_vp.db'
    conn = sqlite3.connect(caminho_db)
    cursor = conn.cursor()
    
    # 1. Tabela de Usuários
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            nome TEXT NOT NULL,
            departamento TEXT DEFAULT 'Geral',
            primeiro_login INTEGER DEFAULT 0,
            status TEXT DEFAULT 'Ativo'
        )
    ''')
    
    # 2. Tabela do Fluxo de Caixa Geral
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fluxo_caixa_geral (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mes TEXT,
            data TEXT,
            departamento TEXT,
            tipo TEXT,
            categoria TEXT,
            descricao TEXT,
            valor_bruto REAL,
            taxa REAL,
            valor_liquido REAL,
            conta_origem TEXT,
            status_pagamento TEXT,
            nota_fiscal TEXT,
            status_envio TEXT,
            comprovante TEXT,
            conta TEXT
        )
    ''')

    # 3. Tabela de Eventos
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_evento TEXT,
            data_evento TEXT,
            orcamento_previsto REAL,
            custo_real REAL,
            status TEXT
        )
    ''')

    # 4. Tabela de Leads
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT,
            empresa TEXT,
            email TEXT,
            telefone TEXT,
            status TEXT,
            valor_estimado REAL
        )
    ''')
    
    # Inserção das contas administradoras
    usuarios_iniciais = [
        ('vice-presidencia@farmaciajr.com', '123456', 'Vice-Presidência', 'VP', 0, 'Ativo'),
        ('presidencia@farmaciajr.com', '123456', 'Presidência', 'Presidência', 0, 'Ativo')
    ]
    
    for email, senha, nome, departamento, primeiro_login, status in usuarios_iniciais:
        cursor.execute('''
            INSERT OR REPLACE INTO usuarios (email, senha, nome, departamento, primeiro_login, status)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (email.strip().lower(), senha, nome, departamento, primeiro_login, status))
        
    conn.commit()
    conn.close()

if __name__ == '__main__':
    inicializar_banco_dados()
