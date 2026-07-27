import sqlite3
import os

def inicializar_banco_dados():
    # Garante que a pasta 'database' exista no ambiente
    if not os.path.exists('database'):
        os.makedirs('database')
        
    # Conecta ao arquivo do banco de dados exato esperado pelo app.py
    conn = sqlite3.connect('database/financeiro_farmaciajr.db')
    cursor = conn.cursor()
    
    # 1. Criar Tabela de Usuários com todas as colunas necessárias
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
    
    # 2. Inserir ou atualizar os acessos das Diretorias Executivas
    # (Define primeiro_login = 0 para pular a tela de troca de senha e ir direto ao painel)
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
