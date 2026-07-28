import sqlite3

# Caminho unificado do banco de dados da aplicação
DB_PATH = 'database/financeiro_v2.db'

def verificar_credenciais(email, senha):
    """
    Verifica se o e-mail e a senha correspondem a um usuário cadastrado e ativo.
    """
    email_limpo = email.strip().lower()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT nome, primeiro_login, departamento, status, senha 
            FROM usuarios 
            WHERE LOWER(email) = ?
        """, (email_limpo,))
        usuario = cursor.fetchone()
    except sqlite3.OperationalError as e:
        conn.close()
        return {"sucesso": False, "mensagem": f"Erro de estrutura no banco de dados: {e}"}
    
    conn.close()
    
    if usuario:
        nome, primeiro_login, departamento, status, senha_banco = usuario
        
        if status != 'Ativo':
            return {"sucesso": False, "mensagem": "Usuário inativo. Solicite o acesso à Vice-Presidência."}
            
        if senha == senha_banco:
            return {
                "sucesso": True,
                "nome": nome,
                "primeiro_login": primeiro_login,
                "departamento": departamento
            }
        else:
            return {"sucesso": False, "mensagem": "Senha incorreta. Tente novamente."}
    else:
        return {"sucesso": False, "mensagem": "Usuário não cadastrado. Solicite o acesso à Vice-Presidência."}
