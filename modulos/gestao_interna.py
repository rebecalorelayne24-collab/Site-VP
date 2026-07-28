import os
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

DB_PATH = "database/financeiro_v2.db"
FUSO_BR = ZoneInfo("America/Sao_Paulo")


def obter_agora_br():
    """Retorna o datetime atual no fuso horário de Brasília."""
    return datetime.now(FUSO_BR)


def inicializar_banco_gestao_interna():
    """Garante a existência da pasta e de todas as tabelas necessárias no SQLite."""
    if not os.path.exists("database"):
        os.makedirs("database")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Tabela de Usuários / Membros (Corrige o DatabaseError do Pandas)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            email TEXT,
            departamento TEXT,
            cargo TEXT DEFAULT 'Membro'
        )
    """)

    # Tabela de Tarefas / Gestão Interna
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tarefas_internas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titulo TEXT NOT NULL,
            responsavel TEXT,
            departamento TEXT,
            prioridade TEXT,
            data_limite TEXT,
            status TEXT DEFAULT '🟡 Em Andamento'
        )
    """)

    conn.commit()
    conn.close()


def renderizar_gestao_interna():
    """Função chamada na linha 216 do app.py."""
    inicializar_banco_gestao_interna()

    st.markdown(
        "<h2 style='text-align: center; color: #C71585;'>📋 Gestão Interna & Equipe — Farmácia Jr.</h2>",
        unsafe_allow_html=True,
    )
    st.write("Acompanhe os membros da equipe, atribuição de tarefas e pendências internas da diretoria.")

    lista_deptos = ["VP", "IMAGEM", "AR", "PRESIDÊNCIA", "PROJETOS", "NEGÓCIOS"]

    aba_membros, aba_tarefas = st.tabs(["👤 Membros & Equipe", "📌 Quadro de Tarefas"])

    # =======================================================================
    # ABA 1: USUÁRIOS E MEMBROS
    # =======================================================================
    with aba_membros:
        st.markdown("### 👤 Cadastro de Membros")

        with st.expander("➕ Cadastrar Novo Membro"):
            c1, c2, c3 = st.columns(3)
            nome_m = c1.text_input("Nome Completo:").strip()
            email_m = c2.text_input("E-mail Institucional:").strip()
            dep_m = c3.selectbox("Diretoria:", lista_deptos, key="dep_membro_cad")

            if st.button("💾 Cadastrar Membro", use_container_width=True):
                if nome_m:
                    try:
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO usuarios (nome, email, departamento) VALUES (?, ?, ?)",
                            (nome_m, email_m, dep_m),
                        )
                        conn.commit()
                        conn.close()
                        st.success(f"Membro {nome_m} cadastrado com sucesso!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Este membro já está cadastrado.")
                else:
                    st.warning("Preencha ao menos o nome do membro.")

        st.markdown("---")

        # Leitura Segura de Usuários
        try:
            conn = sqlite3.connect(DB_PATH)
            df_membros = pd.read_sql_query("SELECT id, nome, email, departamento, cargo FROM usuarios ORDER BY nome ASC", conn)
            conn.close()
        except Exception:
            df_membros = pd.DataFrame(columns=["id", "nome", "email", "departamento", "cargo"])

        if not df_membros.empty:
            st.markdown(f"#### 📋 Membros Ativos ({len(df_membros)} cadastrados)")
            st.dataframe(df_membros[["nome", "departamento", "email", "cargo"]], use_container_width=True, hide_index=True)
        else:
            st.info("Nenhum membro cadastrado na base ainda.")

    # =======================================================================
    # ABA 2: QUADRO DE TAREFAS
    # =======================================================================
    with aba_tarefas:
        st.markdown("### 📌 Controle de Tarefas Internas")

        # Lista de membros atualizada para o selectbox
        lista_membros_opcoes = df_membros["nome"].tolist() if not df_membros.empty else ["Nenhum membro cadastrado"]

        with st.expander("➕ Nova Tarefa / Demanda"):
            t1, t2, t3 = st.columns(3)
            titulo_t = t1.text_input("Título da Tarefa:").strip()
            resp_t = t2.selectbox("Membro Responsável:", lista_membros_opcoes)
            dep_t = t3.selectbox("Diretoria:", lista_deptos, key="dep_tarefa_cad")

            t4, t5 = st.columns(2)
            prio_t = t4.selectbox("Prioridade:", ["🔴 Alta", "🟡 Média", "🟢 Baixa"])
            dt_limite = t5.date_input("Data Limite:", value=obter_agora_br())

            if st.button("📌 Criar Tarefa", use_container_width=True):
                if titulo_t and resp_t != "Nenhum membro cadastrado":
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO tarefas_internas (titulo, responsavel, departamento, prioridade, data_limite, status)
                        VALUES (?, ?, ?, ?, ?, '🟡 Em Andamento')
                    """,
                        (titulo_t, resp_t, dep_t, prio_t, dt_limite.strftime("%Y-%m-%d")),
                    )
                    conn.commit()
                    conn.close()
                    st.success("Tarefa registrada!")
                    st.rerun()
                else:
                    st.error("Insira o título da tarefa e selecione um responsável válido.")

        st.markdown("---")

        try:
            conn = sqlite3.connect(DB_PATH)
            df_tarefas = pd.read_sql_query("SELECT * FROM tarefas_internas ORDER BY id DESC", conn)
            conn.close()
        except Exception:
            df_tarefas = pd.DataFrame()

        if not df_tarefas.empty:
            st.markdown("#### 📋 Painel de Tarefas")
            for idx, row in df_tarefas.iterrows():
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    col1.write(f"📌 **{row['titulo']}**")
                    col1.caption(f"👤 Responsável: {row['responsavel']} ({row['departamento']}) | Até: {row['data_limite']}")

                    col2.write(f"Prioridade: {row['prioridade']}")
                    col3.write(f"Status: **{row['status']}**")

                    if "Em Andamento" in str(row["status"]):
                        if col4.button("🟢 Concluir", key=f"conc_tar_{row['id']}"):
                            conn = sqlite3.connect(DB_PATH)
                            cursor = conn.cursor()
                            cursor.execute("UPDATE tarefas_internas SET status = '🟢 Concluída' WHERE id = ?", (row["id"],))
                            conn.commit()
                            conn.close()
                            st.success("Concluída!")
                            st.rerun()
                    else:
                        if col4.button("🗑️", key=f"del_tar_{row['id']}"):
                            conn = sqlite3.connect(DB_PATH)
                            cursor = conn.cursor()
                            cursor.execute("DELETE FROM tarefas_internas WHERE id = ?", (row["id"],))
                            conn.commit()
                            conn.close()
                            st.success("Excluída!")
                            st.rerun()
                st.markdown("<hr style='margin: 4px 0; border: 0.5px solid #F8F8F8;'>", unsafe_allow_html=True)
        else:
            st.info("Nenhuma tarefa registrada no momento.")
