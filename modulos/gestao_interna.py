import os
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from modulos.fluxo_caixa import salvar_lancamento

DB_PATH = "database/financeiro_v2.db"
FUSO_BR = ZoneInfo("America/Sao_Paulo")


def obter_agora_br():
    """Retorna a data e hora atuais no fuso horário de Brasília."""
    return datetime.now(FUSO_BR)


def inicializar_banco_contratos_assessores():
    """Garante a existência da pasta e de todas as tabelas necessárias no SQLite."""
    if not os.path.exists("database"):
        os.makedirs("database")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Tabela de Usuários / Assessores / Trainees
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            email TEXT,
            departamento TEXT,
            cargo TEXT DEFAULT 'Assessor'
        )
    """)

    # Tabela de Contratos Comerciais
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contratos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT NOT NULL,
            servico TEXT,
            departamento TEXT,
            assessor_responsavel TEXT,
            valor_total REAL,
            parcelas INTEGER,
            data_assinatura TEXT,
            status TEXT DEFAULT '🟢 Ativo'
        )
    """)

    # Tabela de Demandas e Solicitações de Assessores
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS demandas_assessores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            assessor TEXT NOT NULL,
            departamento TEXT,
            tipo_demanda TEXT,
            descricao TEXT,
            valor REAL,
            data_solicitacao TEXT,
            status TEXT DEFAULT '🟡 Em Análise'
        )
    """)

    conn.commit()
    conn.close()


def renderizar_gestao_interna():
    """Renderiza a página de Contratos de Clientes e Demandas dos Assessores."""
    inicializar_banco_contratos_assessores()

    st.markdown(
        "<h2 style='text-align: center; color: #C71585;'>📑 Gestão de"
        " Contratos & Demandas dos Assessores</h2>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Acompanhe o fechamento de contratos por assessores e gerencie"
        " solicitações de verba, reembolsos e compras da equipe."
    )

    lista_deptos = ["VP", "IMAGEM", "AR", "PRESIDÊNCIA", "PROJETOS", "NEGÓCIOS"]
    lista_meses = [
        "Janeiro",
        "Fevereiro",
        "Março",
        "Abril",
        "Maio",
        "Junho",
        "Julho",
        "Agosto",
        "Setembro",
        "Outubro",
        "Novembro",
        "Dezembro",
    ]

    # Carrega lista de assessores do banco de forma segura
    try:
        conn = sqlite3.connect(DB_PATH)
        df_membros = pd.read_sql_query(
            "SELECT nome FROM usuarios ORDER BY nome ASC", conn
        )
        conn.close()
        lista_assessores = (
            df_membros["nome"].tolist()
            if not df_membros.empty
            else ["Nenhum assessor cadastrado"]
        )
    except Exception:
        lista_assessores = ["Nenhum assessor cadastrado"]

    aba_contratos, aba_demandas, aba_equipe = st.tabs([
        "📜 Contratos de Clientes",
        "📥 Demandas dos Assessores",
        "👤 Cadastro de Assessores",
    ])

    # =======================================================================
    # ABA 1: CONTRATOS FECHADOS POR ASSESSORES
    # =======================================================================
    with aba_contratos:
        st.markdown("### 📜 Gestão de Contratos e Serviços Fechados")

        with st.expander("➕ Registrar Novo Contrato / Serviço"):
            c1, c2, c3 = st.columns(3)
            cliente = c1.text_input("Empresa / Cliente Contratante:").strip()
            servico = c2.text_input("Serviço Contratado:").strip()
            depto = c3.selectbox(
                "Diretoria do Projeto:", lista_deptos, key="cad_dep_contrato"
            )

            c4, c5, c6 = st.columns(3)
            assessor_resp = c4.selectbox(
                "Assessor Responsável:", lista_assessores, key="cad_ass_contrato"
            )
            val_total = c5.number_input(
                "Valor Total do Contrato (R$):", min_value=0.0
            )
            parcelas = c6.number_input("Nº de Parcelas:", min_value=1, value=1)

            if st.button("💾 Registrar Contrato", use_container_width=True):
                if cliente and servico and val_total > 0:
                    agora = obter_agora_br()
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO contratos (cliente, servico, departamento, assessor_responsavel, valor_total, parcelas, data_assinatura, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, '🟢 Ativo')
                    """,
                        (
                            cliente,
                            servico,
                            depto,
                            assessor_resp,
                            val_total,
                            parcelas,
                            agora.strftime("%Y-%m-%d"),
                        ),
                    )
                    conn.commit()
                    conn.close()

                    # Sincronização automática da 1ª parcela no Fluxo de Caixa
                    val_parcela = val_total / parcelas
                    mes_nome = lista_meses[agora.month - 1]
                    salvar_lancamento(
                        mes_nome,
                        agora.strftime("%Y-%m-%d"),
                        depto,
                        "Receita",
                        "Serviço Prestado",
                        f"Contrato {cliente} ({assessor_resp}) - Parcela 1/{parcelas}",
                        val_parcela,
                        0.0,
                        val_parcela,
                        "Banco do Brasil",
                        "🟢 Pago",
                        "🟡 Aguardando Emissão",
                        "❌ Não enviado",
                    )

                    st.success(
                        f"Contrato com {cliente} registrado com sucesso e"
                        " 1ª parcela integrada ao Caixa!"
                    )
                    st.rerun()
                else:
                    st.error(
                        "Preencha o cliente, o serviço e um valor maior que R$"
                        " 0,00."
                    )

        st.markdown("---")

        try:
            conn = sqlite3.connect(DB_PATH)
            df_contratos = pd.read_sql_query(
                "SELECT * FROM contratos ORDER BY id DESC", conn
            )
            conn.close()
        except Exception:
            df_contratos = pd.DataFrame()

        if not df_contratos.empty:
            tot_contratos = df_contratos["valor_total"].sum()
            c_m1, c_m2 = st.columns(2)
            c_m1.metric("Faturamento em Contratos", f"R$ {tot_contratos:,.2f}")
            c_m2.metric("Contratos Ativos", f"{len(df_contratos)} projetos")

            st.markdown("#### 📋 Contratos Cadastrados")
            for idx, row in df_contratos.iterrows():
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    col1.write(f"🤝 **{row['cliente']}** — *{row['servico']}*")
                    col1.caption(
                        f"📁 Diretoria: {row['departamento']} | Assessor:"
                        f" {row['assessor_responsavel']} | Assinado em:"
                        f" {row['data_assinatura']}"
                    )

                    col2.write(f"💰 **R$ {row['valor_total']:.2f}**")
                    col2.caption(
                        f"{row['parcelas']}x de R$"
                        f" {(row['valor_total'] / row['parcelas']):.2f}"
                    )

                    col3.write(f"Status: **{row['status']}**")

                    if col4.button(
                        "🗑️",
                        key=f"del_contrato_{row['id']}",
                        help="Excluir contrato",
                    ):
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute(
                            "DELETE FROM contratos WHERE id = ?", (row["id"],)
                        )
                        conn.commit()
                        conn.close()
                        st.success("Removido!")
                        st.rerun()
                st.markdown(
                    "<hr style='margin: 4px 0; border: 0.5px solid #F8F8F8;'>",
                    unsafe_allow_html=True,
                )
        else:
            st.info("Nenhum contrato cadastrado até o momento.")

    # =======================================================================
    # ABA 2: DEMANDAS E SOLICITAÇÕES DOS ASSESSORES
    # =======================================================================
    with aba_demandas:
        st.markdown("### 📥 Solicitações Financeiras de Assessores e Trainees")
        st.caption(
            "Envio de solicitações de reembolsos, verbas operacionais ou"
            " materiais de projeto para aprovação."
        )

        with st.expander("➕ Nova Demanda / Solicitação de Verba"):
            d1, d2, d3 = st.columns(3)
            assessor_dem = d1.selectbox(
                "Assessor Solicitante:",
                lista_assessores,
                key="cad_ass_demanda",
            )
            depto_dem = d2.selectbox(
                "Diretoria:", lista_deptos, key="cad_dep_demanda"
            )
            tipo_dem = d3.selectbox(
                "Tipo de Solicitação:",
                [
                    "Reembolso de Despesa",
                    "Compra de Material",
                    "Verba para Evento",
                    "Outros",
                ],
            )

            d4, d5 = st.columns([3, 1])
            desc_dem = d4.text_input(
                "Descrição / Justificativa do Gastos:"
            ).strip()
            val_dem = d5.number_input("Valor Solicitado (R$):", min_value=0.0)

            if st.button("📨 Enviar Solicitação para a VP", use_container_width=True):
                if desc_dem and val_dem > 0:
                    agora = obter_agora_br()
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO demandas_assessores (assessor, departamento, tipo_demanda, descricao, valor, data_solicitacao, status)
                        VALUES (?, ?, ?, ?, ?, ?, '🟡 Em Análise')
                    """,
                        (
                            assessor_dem,
                            depto_dem,
                            tipo_dem,
                            desc_dem,
                            val_dem,
                            agora.strftime("%Y-%m-%d"),
                        ),
                    )
                    conn.commit()
                    conn.close()
                    st.success("Demanda registrada com sucesso!")
                    st.rerun()
                else:
                    st.error("Informe a descrição/justificativa e o valor.")

        st.markdown("---")

        try:
            conn = sqlite3.connect(DB_PATH)
            df_demandas = pd.read_sql_query(
                "SELECT * FROM demandas_assessores ORDER BY id DESC", conn
            )
            conn.close()
        except Exception:
            df_demandas = pd.DataFrame()

        if not df_demandas.empty:
            st.markdown("#### 📋 Pedidos de Assessores")

            for idx, row in df_demandas.iterrows():
                with st.container():
                    col_d1, col_d2, col_d3, col_d4 = st.columns([3, 2, 2, 1])

                    col_d1.write(
                        f"👤 **{row['assessor']}** ({row['departamento']}) —"
                        f" *{row['tipo_demanda']}*"
                    )
                    col_d1.caption(
                        f"📝 {row['descricao']} | Data: {row['data_solicitacao']}"
                    )

                    col_d2.write(f"💸 **R$ {row['valor']:.2f}**")
                    col_d3.write(f"Status: **{row['status']}**")

                    if "Em Análise" in str(row["status"]):
                        if col_d4.button(
                            "🟢 Aprovar", key=f"aprov_dem_{row['id']}"
                        ):
                            agora = obter_agora_br()
                            mes_nome = lista_meses[agora.month - 1]

                            conn = sqlite3.connect(DB_PATH)
                            cursor = conn.cursor()
                            cursor.execute(
                                "UPDATE demandas_assessores SET status = '🟢"
                                " Aprovado' WHERE id = ?",
                                (row["id"],),
                            )
                            conn.commit()
                            conn.close()

                            # Lança a despesa aprovada no Fluxo de Caixa
                            salvar_lancamento(
                                mes_nome,
                                agora.strftime("%Y-%m-%d"),
                                row["departamento"],
                                "Despesa",
                                "ADM: Operacional",
                                f"Demanda ({row['assessor']}):"
                                f" {row['descricao']}",
                                row["valor"],
                                0.0,
                                row["valor"],
                                "Banco do Brasil",
                                "🟢 Pago",
                                "⚪ Não se aplica",
                                "❌ Não enviado",
                            )
                            st.success(
                                "Demanda aprovada e lançada no Fluxo de Caixa!"
                            )
                            st.rerun()
                    else:
                        if col_d4.button(
                            "🗑️", key=f"del_dem_{row['id']}", help="Excluir"
                        ):
                            conn = sqlite3.connect(DB_PATH)
                            cursor = conn.cursor()
                            cursor.execute(
                                "DELETE FROM demandas_assessores WHERE id = ?",
                                (row["id"],),
                            )
                            conn.commit()
                            conn.close()
                            st.success("Removido!")
                            st.rerun()

                st.markdown(
                    "<hr style='margin: 4px 0; border: 0.5px solid #F8F8F8;'>",
                    unsafe_allow_html=True,
                )
        else:
            st.info("Nenhuma demanda de assessor registrada até o momento.")

    # =======================================================================
    # ABA 3: CADASTRO DE ASSESSORES / EQUIPE
    # =======================================================================
    with aba_equipe:
        st.markdown("### 👤 Equipe de Assessores & Trainees")

        with st.expander("➕ Cadastrar Novo Assessor / Trainee"):
            e1, e2, e3 = st.columns(3)
            nome_a = e1.text_input("Nome do Assessor/Trainee:").strip()
            email_a = e2.text_input("E-mail:").strip()
            dep_a = e3.selectbox(
                "Diretoria:", lista_deptos, key="cad_dep_assessor"
            )

            cargo_a = st.selectbox("Cargo:", ["Assessor", "Trainee", "Director / VP"])

            if st.button("💾 Salvar Cadastro na Equipe", use_container_width=True):
                if nome_a:
                    try:
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO usuarios (nome, email, departamento, cargo) VALUES (?, ?, ?, ?)",
                            (nome_a, email_a, dep_a, cargo_a),
                        )
                        conn.commit()
                        conn.close()
                        st.success(f"{cargo_a} {nome_a} cadastrado(a) com sucesso!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Este nome já está cadastrado na equipe.")
                else:
                    st.warning("Preencha ao menos o nome.")

        st.markdown("---")

        try:
            conn = sqlite3.connect(DB_PATH)
            df_membros_tab = pd.read_sql_query(
                "SELECT id, nome, departamento, cargo, email FROM usuarios ORDER BY nome ASC",
                conn,
            )
            conn.close()
        except Exception:
            df_membros_tab = pd.DataFrame()

        if not df_membros_tab.empty:
            st.markdown(f"#### 📋 Membros Ativos ({len(df_membros_tab)} cadastrados)")
            st.dataframe(
                df_membros_tab[["nome", "cargo", "departamento", "email"]],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("Nenhum assessor cadastrado até o momento.")
            
