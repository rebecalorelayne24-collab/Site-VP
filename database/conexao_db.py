import sqlite3
import os

def inicializar_banco_dados():
    # Garante que a pasta 'database' exista no ambiente
    if not os.path.exists('database'):
        os.makedirs('database')
        
    conn = sqlite3.connect('database/financeiro_farmaciajr.db')
    cursor = conn.cursor()
    
    # Remove a tabela antiga incompativel (caso ela nao tenha a coluna senha)
    # e cria a nova tabela com a estrutura correta
    try:
        cursor.execute("SELECT senha FROM usuarios LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("DROP TABLE IF EXISTS usuarios")

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
    
    # Inserir/Atualizar os acessos das Diretorias Executivas
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
