import hashlib
from database.conexao_db import get_connection

def verificar_credenciais(email, senha):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT nome, senha, primeiro_login, departamento FROM usuarios WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    
    if not user:
        return {"sucesso": False, "mensagem": "E-mail não cadastrado no sistema."}
    
    nome, senha_db, primeiro_login, departamento = user
    senha_hash_digitada = hashlib.sha256(senha.encode("utf-8")).hexdigest()
    
    if senha == senha_db or senha_hash_digitada == senha_db:
        return {
            "sucesso": True,
            "nome": nome,
            "primeiro_login": primeiro_login,
            "departamento": departamento
        }
    else:
        return {"sucesso": False, "mensagem": "Senha incorreta. Tente novamente."}
