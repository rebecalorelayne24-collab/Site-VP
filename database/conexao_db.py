import sqlite3

def inicializar_banco_dados():
    conn = sqlite3.connect('banco_financeiro.db')
    cursor = conn.cursor()
    
    # 1. Cria a tabela de usuarios se nao existir
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            nome TEXT,
            cargo TEXT,
            status TEXT DEFAULT 'Ativo'
        )
    ''')
    
    # 2. Insere os e-mails autorizados para liberacao de acesso
    cursor.execute('''
        INSERT OR IGNORE INTO usuarios (email, nome, cargo, status)
        VALUES ('admin@farmaciajr.com', 'Administrador', 'Vice-Presidência', 'Ativo')
    ''')
    
    cursor.execute('''
        INSERT OR IGNORE INTO usuarios (email, nome, cargo, status)
        VALUES ('vicepresidencia@farmaciajr.com', 'Vice Presidência', 'Vice-Presidência', 'Ativo')
    ''')
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    inicializar_banco_dados()
