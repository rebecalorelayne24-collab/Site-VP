import sqlite3
import os

def inicializar_banco_dados():
    caminho_db = 'database/financeiro_farmaciajr.db'
    
    # Garante que a pasta 'database' exista
    if not os.path.exists('database'):
        os.makedirs('database')
        
    # Se o banco antigo existir, verifica se a coluna 'senha' está presente
    # Caso a coluna não exista (banco antigo desatualizado), remove o arquivo para recriar do zero
    if os.path.exists(caminho_db):
        try:
            conn_test = sqlite3.connect(caminho_db)
            cursor_test = conn_test.cursor()
            cursor_test.execute("SELECT senha, departamento FROM usuarios LIMIT 1")
            conn_test.close()
        except sqlite3.OperationalError:
            if 'conn_test' in locals():
                conn_test.close()
            os.remove(caminho_db)  # Deleta o arquivo antigo incompatível

    # Conecta e cria o banco novo atualizado
    conn = sqlite3.connect(caminho_db)
    cursor = conn.cursor()
    
    # 1. Criar Tabela de Usuários Atualizada
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
    
    # 2. Cadastrar Diretorias Executivas com primeiro_login = 0 (Acesso direto)
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
