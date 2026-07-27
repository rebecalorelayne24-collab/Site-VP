import sqlite3

def inicializar_banco_dados():
    conn = sqlite3.connect('banco_financeiro.db')
    cursor = conn.cursor()
    
    # Cria a tabela garantindo as colunas de email e senha
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            nome TEXT,
            cargo TEXT,
            status TEXT DEFAULT 'Ativo'
        )
    ''')
    
    # Cadastra o usuário admin com a senha '123456'
    cursor.execute('''
        INSERT OR REPLACE INTO usuarios (email, senha, nome, cargo, status)
        VALUES ('admin@farmaciajr.com', '123456', 'Administrador', 'Vice-Presidência', 'Ativo')
    ''')
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    inicializar_banco_dados()
