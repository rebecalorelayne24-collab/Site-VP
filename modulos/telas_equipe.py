import base64
from datetime import datetime
import io
import re
import pandas as pd
import psycopg2
import streamlit as st
from werkzeug.security import check_password_hash, generate_password_hash
from database.conexao_db import get_connection

CORES_DIRETORIAS = {
    "VP": "#FF69B4",
    "IMAGEM": "#8A2BE2",
    "PROJETOS": "#1E90FF",
    "NEGÓCIOS": "#2E8B57",
    "AR": "#FF8C00",
    "PRESIDÊNCIA": "#DAA520",
}


def converter_imagem_para_base64(imagem_arquivo):
    if imagem_arquivo is not None:
        return base64.b64encode(imagem_arquivo.read()).decode("utf-8")
    return ""


def renderizar_tela_troca_senha(email_usuario):
    """Módulo obrigatório de primeiro acesso utilizando o hash seguro do Werkzeug."""
    st.markdown(
        "<h3 style='color: #FF1493; text-align: center;'>🔒 Primeiro Acesso — Atualize sua Senha</h3>",
        unsafe_allow_html=True,
    )
    st.write("Por motivos de segurança da EJ, altere a senha padrão antes de acessar a plataforma.")

    with st.form("form_troca_senha"):
        nova_senha = st.text_input("Digite sua Nova Senha:", type="password")
        confirma_senha = st.text_input("Confirme a Nova Senha:", type="password")

        if st.form_submit_button("🔒 Salvar Nova Senha Criptografada e Entrar"):
            if len(nova_senha) < 6:
                st.error("A senha deve ter pelo menos 6 caracteres.")
            elif nova_senha != confirma_senha:
                st.error("As senhas digitadas não coincidem.")
            else:
                senha_hash = generate_password_hash(nova_senha)
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE usuarios 
                    SET senha = ?, primeiro_login = 0 
                    WHERE email = ?
                """,
                    (senha_hash, email_usuario),
                )
                conn.commit()
                conn.close()

                st.success("Senha atualizada e criptografada com sucesso!")
                st.session_state.primeiro_login = 0
                st.rerun()


def renderizar_gerenciamento_equipe(email_logado):

    st.markdown(
        "<h2 style='color: #FF1493;'>👥 Gestão de Pessoas & RH – Farmácia Jr.</h2>",
        unsafe_allow_html=True,
    )

    conn = get_connection()
    df_users = pd.read_sql_query("SELECT * FROM usuarios", conn)
    conn.close()

    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    tot_membros = len(df_users)
    tot_diretores = len(df_users[df_users["cargo"].str.contains("Diretor", case=False, na=False)])
    tot_assessores = len(df_users[df_users["cargo"].str.contains("Assessor", case=False, na=False)])
    tot_ativos = len(df_users[df_users["status"] == "Ativo"])

    m1.metric("👥 Total de Membros", tot_membros)
    m2.metric("🏅 Diretores e VPs", tot_diretores)
    m3.metric("🎓 Assessores", tot_assessores)
    m4.metric("🟢 Membros Ativos", tot_ativos)

    tab_equipe, tab_meu_perfil, tab_cadastrar = st.tabs(
        ["📋 Organograma & Equipe", "✨ Meu Perfil & Acesso", "➕ Cadastrar Novo Membro"]
    )

    with tab_equipe:
        c_busca, c_filtro_dept, c_filtro_status = st.columns([2, 1, 1])
        with c_busca:
            termo_busca = st.text_input("🔍 Pesquisar por nome, e-mail ou matrícula:", placeholder="Ex: Rebeca, UFMG...").strip().lower()
        with c_filtro_dept:
            filtro_dept = st.selectbox("📂 Diretoria:", ["Todas", "VP", "PROJETOS", "NEGÓCIOS", "IMAGEM", "AR", "PRESIDÊNCIA"])
        with c_filtro_status:
            filtro_status = st.selectbox("📌 Status:", ["Todos", "Ativo", "Afastado", "Desligado", "Ex-membro"])

        df_filtrado = df_users.copy()
        if termo_busca:
            df_filtrado = df_filtrado[
                df_filtrado["nome"].str.lower().str.contains(termo_busca, na=False)
                | df_filtrado["email"].str.lower().str.contains(termo_busca, na=False)
                | df_filtrado["matricula"].str.lower().str.contains(termo_busca, na=False)
            ]
        if filtro_dept != "Todas":
            df_filtrado = df_filtrado[df_filtrado["departamento"] == filtro_dept]
        if filtro_status != "Todos":
            df_filtrado = df_filtrado[df_filtrado["status"] == filtro_status]

        st.markdown(f"##### Exibindo {len(df_filtrado)} membro(s)")

        if df_filtrado.empty:
            st.info("Nenhum membro encontrado com os filtros selecionados.")
        else:
            for _, row in df_filtrado.iterrows():
                cor_borda = CORES_DIRETORIAS.get(row["departamento"], "#FF1493")
                status_icon = "🟢" if row["status"] == "Ativo" else ("🟡" if row["status"] == "Afastado" else "🔴")

                if row["foto_base64"]:
                    img_html = f"<img src='data:image/png;base64,{row['foto_base64']}' style='width:70px; height:70px; border-radius:50%; object-fit: cover; border: 2px solid {cor_borda}; margin-right: 15px;'>"
                else:
                    img_html = f"<div style='width:70px; height:70px; border-radius:50%; background-color:#FFF0F5; display:flex; align-items:center; justify-content:center; font-size:32px; border: 2px solid {cor_borda}; margin-right:15px;'>👤</div>"

                tel_clean = re.sub(r"\D", "", str(row["telefone"]))
                link_wa = f"https://wa.me/55{tel_clean}" if len(tel_clean) >= 10 else "#"

                col_card, col_acao = st.columns([4, 1.2])

                with col_card:
                    st.markdown(
                        f"""
                    <div style="display: flex; align-items: center; background-color: #FFFFFF; padding: 15px; border-radius: 10px; border-left: 6px solid {cor_borda}; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 10px;">
                        {img_html}
                        <div>
                            <h4 style="margin:0; color:#333;">{row['nome']} {status_icon} <span style="font-size:12px; color:#888;">({row['status']})</span></h4>
                            <p style="margin:3px 0; font-size:13px; color:#555;">
                                🏅 <b>{row['cargo']}</b> | 📂 <b>{row['departamento']}</b> | 🆔 Matrícula: {row['matricula'] or 'N/I'}
                            </p>
                            <p style="margin:0; font-size:12px; color:#777;">
                                ✉️ {row['email']} | 📱 <a href="{link_wa}" target="_blank" style="color:#2E8B57; text-decoration:none;"><b>WhatsApp</b></a> | 📅 Entrada: {row['data_entrada'] or 'N/I'}
                            </p>
                        </div>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                with col_acao:
                    st.write("")
                    if row["email"] == email_logado:
                        st.caption("✨ Seu Perfil")
                    else:
                        with st.popover("🗑️ Opções", use_container_width=True):
                            st.warning(f"Ação permanente para **{row['nome']}**:")
                            if st.button("Confirmar Exclusão", key=f"conf_del_{row['id']}", type="primary", use_container_width=True):
                                conn = get_connection()
                                cursor = conn.cursor()
                                cursor.execute("DELETE FROM usuarios WHERE id = ?", (row["id"],))
                                conn.commit()
                                conn.close()
                                st.success("Membro removido do sistema!")
                                st.rerun()

    with tab_meu_perfil:
        meu_perfil = df_users[df_users["email"] == email_logado]
        if not meu_perfil.empty:
            dados_eu = meu_perfil.iloc[0]
            st.markdown(f"#### 👤 Perfil do Membro: **{dados_eu['nome']}**")

            with st.form("form_auto_perfil"):
                c1, c2 = st.columns(2)
                with c1:
                    novo_nome = st.text_input("Nome Completo:", value=dados_eu["nome"])
                    novo_tel = st.text_input("Telefone / WhatsApp:", value=dados_eu["telefone"], placeholder="(31) 99999-9999")
                    novo_linkedin = st.text_input("Perfil do LinkedIn (URL):", value=dados_eu["linkedin"])
                with c2:
                    nova_matr = st.text_input("Matrícula UFMG:", value=dados_eu["matricula"])
                    novo_insta = st.text_input("Instagram (@usuário):", value=dados_eu["instagram"])
                    nova_foto = st.file_uploader("Atualizar Foto de Perfil:", type=["png", "jpg", "jpeg"])

                st.markdown("---")
                st.markdown("##### 🔒 Alteração de Senha")
                senha_atual_input = st.text_input("Senha Atual (necessária para alterar):", type="password")
                nova_senha_input = st.text_input("Nova Senha:", type="password")

                if st.form_submit_button("💾 Salvar Alterações do Perfil"):
                    conn = get_connection()
                    cursor = conn.cursor()

                    foto_str = dados_eu["foto_base64"]
                    if nova_foto:
                        foto_str = converter_imagem_para_base64(nova_foto)

                    if nova_senha_input:
                        if check_password_hash(dados_eu["senha"], senha_atual_input) or dados_eu["senha"] == senha_atual_input:
                            hash_nova = generate_password_hash(nova_senha_input)
                            cursor.execute(
                                """
                                UPDATE usuarios 
                                SET nome=?, telefone=?, linkedin=?, instagram=?, matricula=?, foto_base64=?, senha=?
                                WHERE email=?
                            """,
                                (novo_nome, novo_tel, novo_linkedin, novo_insta, nova_matr, foto_str, hash_nova, email_logado),
                            )
                            st.success("Perfil e senha atualizados com sucesso!")
                        else:
                            st.error("A senha atual digitada está incorreta.")
                    else:
                        cursor.execute(
                            """
                            UPDATE usuarios 
                            SET nome=?, telefone=?, linkedin=?, instagram=?, matricula=?, foto_base64=?
                            WHERE email=?
                        """,
                            (novo_nome, novo_tel, novo_linkedin, novo_insta, nova_matr, foto_str, email_logado),
                        )
                        st.success("Dados do perfil atualizados com sucesso!")

                    conn.commit()
                    conn.close()
                    st.rerun()

    with tab_cadastrar:
        st.markdown("#### ➕ Cadastrar Novo Acesso / Membro da Farmácia Jr.")
        with st.form("form_novo_membro_rh", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                nome_c = st.text_input("Nome Completo:*").strip().title()
                email_c = st.text_input("E-mail Institucional ou Pessoal:*").strip().lower()
                dept_c = st.selectbox("Diretoria/Setor Executivo:", ["VP", "PROJETOS", "NEGÓCIOS", "IMAGEM", "AR", "PRESIDÊNCIA"])
                cargo_c = st.selectbox("Função na EJ:", ["Assessor(a)", "Diretor(a)", "Vice-Diretor(a)", "Conselheiro(a)"])
                tel_c = st.text_input("Telefone com DDD:", placeholder="(31) 99999-9999")
            with col2:
                matr_c = st.text_input("Matrícula UFMG:")
                status_c = st.selectbox("Status Inicial:", ["Ativo", "Afastado", "Desligado", "Ex-membro"])
                perm_c = st.selectbox("Nível de Permissão:", ["Membro", "Diretoria", "Administrador"])
                data_ent_c = st.date_input("Data de Entrada na EJ:", value=datetime.now()).strftime("%d/%m/%Y")
                foto_c = st.file_uploader("Foto de Perfil:", type=["png", "jpg", "jpeg"])

            if st.form_submit_button("🚀 Finalizar Cadastro com Criptografia"):
                if nome_c and email_c:
                    senha_padrao_hash = generate_password_hash("farmaciajr123")
                    foto_str = converter_imagem_para_base64(foto_c)

                    conn = get_connection()
                    cursor = conn.cursor()
                    try:
                        cursor.execute(
                            """
                            INSERT INTO usuarios (
                                nome, email, senha, departamento, primeiro_login, 
                                cargo, foto_base64, telefone, status, permissoes, 
                                matricula, data_entrada
                            )
                            VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?)
                        """,
                            (
                                nome_c,
                                email_c,
                                senha_padrao_hash,
                                dept_c,
                                cargo_c,
                                foto_str,
                                tel_c,
                                status_c,
                                perm_c,
                                matr_c,
                                data_ent_c,
                            ),
                        )
                        conn.commit()
                        st.success(f"Membro **{nome_c}** cadastrado(a) com sucesso! A senha inicial padrão é 'farmaciajr123'.")
                        st.rerun()
                    except psycopg2.IntegrityError:
                        st.error("Este e-mail já está cadastrado no banco da EJ.")
                    finally:
                        conn.close()
                else:
                    st.error("Preencha ao menos o Nome e E-mail para efetuar o cadastro.")
