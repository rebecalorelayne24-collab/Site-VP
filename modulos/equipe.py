import sqlite3
import hashlib

# Função de hash compatível com hashlib (caso esteja usando sha256)
def gerar_hash_senha(senha_texto):
    return hashlib.sha256(senha_texto.encode("utf-8")).hexdigest()

conn = sqlite3.connect("database/financeiro_v2.db")
cursor = conn.cursor()

# Substitua pelo e-mail que você está tentando usar para entrar
email_alvo = "vice-presidencia@farmaciajr.com" 

# Reseta a senha para 'farmaciajr123' e força o primeiro login
nova_senha_hash = gerar_hash_senha("farmaciajr123")

cursor.execute("""
    UPDATE usuarios 
    SET senha = ?, primeiro_login = 1 
    WHERE email = ?
""", (nova_senha_hash, email_alvo))

conn.commit()
conn.close()
print(f"Senha do usuário {email_alvo} resetada para 'farmaciajr123' com sucesso!")
