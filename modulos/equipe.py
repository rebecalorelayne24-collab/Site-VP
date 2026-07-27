import sqlite3

def inicializar_tabela_usuarios():
    """Garante que a tabela de usuários exista e cria o login inicial do Admin da VP se estiver vazia."""
    try:
        conn = sqlite3.connect('database/financeiro_farmaciajr.db')
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                nome TEXT NOT NULL,
                senha TEXT NOT NULL,
                departamento TEXT NOT NULL,
                primeiro_login INTEGER DEFAULT 1
            )
        ''')
        
        # Verifica se já existe algum usuário cadastrado
        cursor.execute("SELECT COUNT(*) FROM usuarios")
        total = cursor.fetchone()[0]
        
        # Se for o primeiro acesso ao sistema zerado, cria a conta mestra da VP
        if total == 0:
            cursor.execute('''
                INSERT INTO usuarios (email, nome, senha, departamento, primeiro_login)
                VALUES (?, ?, ?, ?, 0)
            ''', ('admin@farmaciajr.com.br', 'Vice-Presidência Admin', 'FarmaciaJr2026', 'VP'))
            conn.commit()
            
        conn.close()
    except Exception as e:
        print(f"Erro ao inicializar tabela de usuários: {e}")

def verificar_credenciais(email, senha):
    """
    Busca o usuário no banco de dados e valida se a senha está correta.
    Retorna um dicionário com o status do login e os dados da sessão.
    """
    # Garante que a tabela existe antes de fazer a consulta
    inicializar_tabela_usuarios()
    
    email_limpo = email.strip().lower()
    
    try:
        conn = sqlite3.connect('database/financeiro_farmaciajr.db')
        cursor = conn.cursor()
        
        # Busca o usuário pelo e-mail ajustado
        cursor.execute("""
            SELECT nome, primeiro_login, departamento, senha 
            FROM usuarios 
            WHERE LOWER(email) = ?
        """, (email_limpo,))
        
        usuario = cursor.fetchone()
        conn.close()
        
        # 1. Se não encontrou o e-mail no banco
        if not usuario:
            return {
                "sucesso": False,
                "mensagem": "❌ Usuário não cadastrado. Solicite o acesso à Vice-Presidência."
            }
        
        nome, primeiro_login, departamento, senha_banco = usuario
        
        # 2. Se a senha digitada estiver correta
        if senha == senha_banco:
            return {
                "sucesso": True,
                "nome": nome,
                "primeiro_login": bool(primeiro_login),
                "departamento": departamento,
                "mensagem": "🟢 Login efetuado com sucesso!"
            }
        # 3. Se errar a senha
        else:
            return {
                "sucesso": False,
                "mensagem": "❌ Senha incorreta. Tente novamente ou solicite o reset da conta."
            }
            
    except Exception as e:
        return {
            "sucesso": False,
            "mensagem": f"⚠️ Erro ao conectar ao banco de autenticação: {e}"
        }