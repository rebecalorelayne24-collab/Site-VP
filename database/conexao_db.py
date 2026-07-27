import sqlite3
import os

def inicializar_banco_dados():
    # Garante que a pasta 'database' exista
    if not os.path.exists('database'):
        os.makedirs('database')
        
    # Usamos um novo nome de arquivo para forçar a criação limpa na nuvem
    caminho_db = 'database/financeiro_vp.db'
    
    conn = sqlite3.connect(caminho_db)
    cursor = conn.cursor()
    
    # 1. Cria a Tabela de Usuários com a estrutura completa
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
    
    # 2. Inserção das contas com acesso direto ao menu da VP
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
