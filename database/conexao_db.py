import sqlite3

def inicializar_banco_dados():
    conn = sqlite3.connect('banco_financeiro.db')
    cursor = conn.cursor()
    
    # 1. Cria a tabela de usuarios caso nao exista
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            nome TEXT,
            cargo TEXT,
            status TEXT DEFAULT 'Ativo'
        )
    ''')
    
    # 2. Insere/Atualiza os e-mails liberados para acesso imediato
    usuarios_iniciais = [
        ('rebeca@farmaciajr.com', 'Rebeca', 'Vice-Presidência', 'Ativo'),
        ('admin@farmaciajr.com', 'Administrador', 'Vice-Presidência', 'Ativo')
    ]
    
    for email, nome, cargo, status in usuarios_iniciais:
        cursor.execute('''
            INSERT OR REPLACE INTO usuarios (email, nome, cargo, status)
            VALUES (?, ?, ?, ?)
        ''', (email.strip().lower(), nome, cargo, status))
        
    conn.commit()
    conn.close()

if __name__ == '__main__':
    inicializar_banco_dados()
