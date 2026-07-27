import streamlit as st
import sqlite3
import pandas as pd
import base64

def converter_imagem_para_base64(imagem_arquivo):
    """Converte a imagem enviada para uma string de texto Base64 para salvar no banco"""
    if imagem_arquivo is not None:
        return base64.b64encode(imagem_arquivo.read()).decode('utf-8')
    return ""

def renderizar_tela_troca_senha(email_usuario):
    """Módulo obrigatório de primeiro acesso para segurança do assessor"""
    st.markdown("<h3 style='color: #FF1493; text-align: center;'>🔒 Primeiro Acesso - Atualize sua Senha</h3>", unsafe_allow_html=True)
    st.write("Por motivos de segurança da EJ, altere a senha padrão antes de acessar o painel financeiro.")
    
    with st.form("form_troca_senha"):
        nova_senha = st.text_input("Digite sua Nova Senha:", type="password")
        confirma_senha = st.text_input("Confirme a Nova Senha:", type="password")
        
        if st.form_submit_button("Atualizar Senha e Entrar"):
            if len(nova_senha) < 6:
                st.error("A senha deve ter pelo menos 6 caracteres.")
            elif nova_senha != confirma_senha:
                st.error("As senhas digitadas não coincidem.")
            else:
                conn = sqlite3.connect('database/financeiro_farmaciajr.db')
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE usuarios 
                    SET senha = ?, primeiro_login = 0 
                    WHERE email = ?
                """, (nova_senha, email_usuario))
                conn.commit()
                conn.close()
                
                st.success("Senha atualizada com sucesso!")
                st.session_state.primeiro_login = 0
                st.rerun()

def renderizar_gerenciamento_equipe(email_logado):
    """Painel de controle de RH e Organograma com fotos, cargos e correção de e-mails errados"""
    st.markdown("<h3 style='color: #FF1493;'>👥 Gerenciamento de Membros da EJ</h3>", unsafe_allow_html=True)
    st.caption("Cadastre novos membros ou remova registros antigos/incorretos instantaneamente.")
    
    # Criação das novas colunas de cargo e foto caso elas ainda não existam no SQLite
    conn = sqlite3.connect('database/financeiro_farmaciajr.db')
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN cargo TEXT DEFAULT 'Assessor(a)'")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE usuarios ADD COLUMN foto_base64 TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()

    # Form de cadastro de novos assessores/diretores
    with st.expander("➕ Cadastrar Novo Membro (Assessores e Diretores)"):
        with st.form("form_novo_usuario", clear_on_submit=True):
            nome = st.text_input("Nome Completo:").strip().title()
            email = st.text_input("E-mail (Institucional ou Pessoal das Diretoras):").strip().lower()
            depto = st.selectbox("Diretoria/Setor Executivo:", ["VP", "PROJETOS", "NEGÓCIOS", "IMAGEM", "AR", "PRESIDÊNCIA"])
            cargo = st.selectbox("Função / Cargo na EJ:", ["Assessor(a)", "Diretor(a)", "Vice-Diretor(a)"])
            foto_upload = st.file_uploader("Foto de Perfil (PNG/JPG):", type=["png", "jpg", "jpeg"])
            
            if st.form_submit_button("🚀 Finalizar Cadastro de Acesso"):
                if nome and email:
                    foto_string = converter_imagem_para_base64(foto_upload)
                    
                    conn = sqlite3.connect('database/financeiro_farmaciajr.db')
                    cursor = conn.cursor()
                    try:
                        cursor.execute('''
                            INSERT INTO usuarios (nome, email, senha, departamento, primeiro_login, cargo, foto_base64)
                            VALUES (?, ?, 'farmaciajr123', ?, 1, ?, ?)
                        ''', (nome, email, depto, cargo, foto_string))
                        conn.commit()
                        st.success(f"{cargo} {nome} cadastrado(a) com sucesso!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Este e-mail já está cadastrado no sistema.")
                    finally:
                        conn.close()
                else:
                    st.error("Por favor, preencha o nome e o e-mail completo para liberar o acesso.")

    # Listagem visual do time com as fotos e botão de exclusão/correção rápida
    st.markdown("#### 📋 Membros Ativos & Gestão de Acessos")
    conn = sqlite3.connect('database/financeiro_farmaciajr.db')
    df_users = pd.read_sql_query("SELECT id, nome, email, departamento, cargo, foto_base64 FROM usuarios", conn)
    conn.close()

    if df_users.empty:
        st.info("Nenhum membro cadastrado até o momento.")
    else:
        for _, row in df_users.iterrows():
            if row['foto_base64']:
                img_html = f"<img src='data:image/png;base64,{row['foto_base64']}' style='width:60px; height:60px; border-radius:50%; object-fit: cover; margin-right: 15px;'>"
            else:
                img_html = "<div style='width:60px; height:60px; border-radius:50%; background-color:#FFFFF0; display:flex; align-items:center; justify-content:center; font-size:30px; margin-right:15px; border: 1px solid #ddd;'>👤</div>"

            # Colunas para separar o Card Visual do Botão de Ação
            col_card, col_acao = st.columns([4, 2])
            
            with col_card:
                st.markdown(f"""
                <div style="display: flex; align-items: center; background-color: #FAFAFA; padding: 12px; border-radius: 8px; border-left: 4px solid #FF69B4; height: 85px;">
                    {img_html}
                    <div>
                        <h4 style="margin:0; color:#333;">{row['nome']}</h4>
                        <p style="margin:2px 0 0 0; font-size:13px; color:#666;">
                            🏅 <b>{row['cargo']}</b> | 📂 Diretoria: {row['departamento']} | ✉️ {row['email']}
                        </p>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col_acao:
                st.write("")  # Espaçador vertical para alinhar com o card
                if row['email'] == email_logado:
                    st.caption("✨ Seu Perfil Atual")
                else:
                    # Botão para corrigir e-mails errados ou remover quem saiu da EJ
                    if st.button("🗑️ Apagar / Corrigir", key=f"del_usr_{row['id']}", use_container_width=True):
                        conn = sqlite3.connect('database/financeiro_farmaciajr.db')
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM usuarios WHERE id = ?", (row['id'],))
                        conn.commit()
                        conn.close()
                        st.success("Cadastro removido com sucesso!")
                        st.rerun()