import os
import sqlite3
import urllib.parse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import streamlit as st

from modulos.fluxo_caixa import salvar_lancamento

DB_PATH = "database/financeiro_v2.db"
FUSO_BR = ZoneInfo("America/Sao_Paulo")


def obter_agora_br():
    """Retorna o datetime atual no fuso horário oficial de Brasília."""
    return datetime.now(FUSO_BR)


def inicializar_banco_gestao():
    """Garante a existência do diretório e de todas as tabelas no SQLite."""
    if not os.path.exists("database"):
        os.makedirs("database")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Tabela de Contratos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contratos_ej (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente TEXT,
            projeto TEXT,
            valor_total REAL,
            parcelas_totais INTEGER,
            parcelas_pagas INTEGER,
            vencimento TEXT,
            link_drive TEXT,
            status_boleto TEXT
        )
    """)

    # Tabela de Tarefas dos Assessores
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tarefas_assessores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tarefa TEXT,
            assessor_nome TEXT,
            diretoria TEXT,
            prazo TEXT,
            status TEXT
        )
    """)

    # Tabela de Usuários / Membros (evita o erro do Pandas ao buscar assessores)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            email TEXT,
            departamento TEXT,
            cargo TEXT DEFAULT 'Membro'
        )
    """)

    # Tabela de Fluxo de Caixa Geral (garante que buscas não falhem)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fluxo_caixa_geral (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mes TEXT, data TEXT, departamento TEXT, tipo TEXT,
            categoria TEXT, descricao TEXT, valor_bruto REAL, taxa REAL,
            valor_liquido REAL, conta_origem TEXT, status_pagamento TEXT,
            nota_fiscal TEXT, status_onvio TEXT
        )
    """)

    conn.commit()
    conn.close()


def converter_data_segura(str_data):
    """Converte strings de data em datetime aceitando múltiplos formatos com segurança."""
    if not str_data:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(str_data.strip(), fmt)
        except ValueError:
            pass
    return None


def renderizar_gestao_interna():
    inicializar_banco_gestao()
    lista_meses = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]
    hoje_dt = obter_agora_br().replace(tzinfo=None)

    st.markdown(
        "<h2 style='text-align: center; color: #FF1493;'>💼 Central de Negócios & Gestão Interna</h2>",
        unsafe_allow_html=True,
    )

    tab_contratos, tab_tarefas = st.tabs([
        "🤝 Controle de Contratos & Boletos",
        "📋 Distribuição de Tarefas (Kanban)"
    ])

    # =======================================================================
    # 1. TELA: CONTROLE DE CONTRATOS & RECEBÍVEIS
    # =======================================================================
    with tab_contratos:
        st.markdown("### 📜 Gestão de Contratos e Inteligência de Recebíveis")
        conn = sqlite3.connect(DB_PATH)
        df_con = pd.read_sql_query("SELECT * FROM contratos_ej ORDER BY id DESC", conn)
        conn.close()

        previsao_90_dias = 0.0
        total_atrasado = 0.0
        status_contagem = {"🟢 Finalizado": 0, "🟡 A Receber": 0, "🔴 Em Atraso": 0}

        if not df_con.empty:
            for idx, row in df_con.iterrows():
                val_parcela = (
                    row["valor_total"] / row["parcelas_totais"]
                    if row["parcelas_totais"] > 0
                    else row["valor_total"]
                )
                venc_dt = converter_data_segura(row["vencimento"])

                if row["parcelas_pagas"] >= row["parcelas_totais"]:
                    status_contagem["🟢 Finalizado"] += 1
                elif venc_dt and venc_dt < hoje_dt:
                    status_contagem["🔴 Em Atraso"] += 1
                    total_atrasado += val_parcela
                else:
                    status_contagem["🟡 A Receber"] += 1
                    if venc_dt and hoje_dt <= venc_dt <= (hoje_dt + timedelta(days=90)):
                        previsao_90_dias += val_parcela

        # Cards Executivos
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            st.markdown(
                f"""
            <div style="background-color: #E0F7FA; border-left: 5px solid #00838F; padding: 15px; border-radius: 8px;">
                <span style="color: #444; font-size: 13px; font-weight: bold;">🔮 PREVISÃO DE RECEITA (90 DIAS)</span>
                <h2 style="color: #00838F; margin: 5px 0 0 0; font-size: 24px;">R$ {previsao_90_dias:.2f}</h2>
                <span style="color: #666; font-size: 11px;">Boletos a vencer nos próximos 3 meses</span>
            </div>
            """,
                unsafe_allow_html=True,
            )

        with col_c2:
            st.markdown(
                f"""
            <div style="background-color: {'#FFF3E0' if total_atrasado == 0 else '#FFEBEE'}; border-left: 5px solid {'#E65100' if total_atrasado == 0 else '#C62828'}; padding: 15px; border-radius: 8px;">
                <span style="color: #444; font-size: 13px; font-weight: bold;">⚠️ ÍNDICE DE INADIMPLÊNCIA ATUAL</span>
                <h2 style="color: {'#E65100' if total_atrasado == 0 else '#C62828'}; margin: 5px 0 0 0; font-size: 24px;">R$ {total_atrasado:.2f}</h2>
                <span style="color: #666; font-size: 11px;">{'Nenhum boleto em atraso na EJ' if total_atrasado == 0 else 'Valores com vencimento ultrapassado'}</span>
            </div>
            """,
                unsafe_allow_html=True,
            )

        st.markdown("<br>", unsafe_allow_html=True)

        # Calculadora & Gerador de Parcelas Integrado no Formulário
        with st.expander("➕ Cadastrar Novo Contrato Fechado"):
            with st.form("form_contrato", clear_on_submit=True):
                c1, c2 = st.columns(2)
                cli = c1.text_input("Nome do Cliente / Empresa:").strip().title()
                proj = c2.text_input("Nome do Projeto:").strip()

                c3, c4, c5 = st.columns(3)
                v_tot = c3.number_input("Valor Total (R$):", min_value=0.0)
                parc_t = c4.number_input("Total Parcelas:", min_value=1, value=1)
                parc_p = c5.number_input("Parcelas Quitadas Inicialmente:", min_value=0, value=0)

                c6, c7 = st.columns(2)
                venc = c6.text_input(
                    "Próximo Vencimento (DD/MM/AAAA):",
                    value=hoje_dt.strftime("%d/%m/%Y"),
                )
                link = c7.text_input("Link da Pasta de Anexos (Drive):")

                if st.form_submit_button("💾 Salvar Contrato"):
                    if cli and proj and v_tot > 0:
                        status_bol = (
                            "🟢 Finalizado"
                            if parc_p >= parc_t
                            else "🟡 Aguardando Compensação"
                        )
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            INSERT INTO contratos_ej (cliente, projeto, valor_total, parcelas_totais, parcelas_pagas, vencimento, link_drive, status_boleto)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                            (cli, proj, v_tot, parc_t, parc_p, venc, link, status_bol),
                        )
                        conn.commit()
                        conn.close()
                        st.success("Contrato registrado com sucesso!")
                        st.rerun()

        # Listagem Visual de Contratos
        if not df_con.empty:
            st.markdown("#### 📄 Contratos Ativos & Histórico")
            for idx, row in df_con.iterrows():
                status_atual = row["status_boleto"]
                if row["parcelas_pagas"] < row["parcelas_totais"]:
                    venc_dt = converter_data_segura(row["vencimento"])
                    if venc_dt and venc_dt < hoje_dt:
                        status_atual = "🔴 Em Atraso"
                    else:
                        status_atual = "🟡 A Receber"

                cor_status = (
                    "#E8F5E9"
                    if "🟢" in status_atual or "Finalizado" in status_atual
                    else ("#FFEBEE" if "🔴" in status_atual else "#FFF3E0")
                )
                txt_status = (
                    "#2E7D32"
                    if "🟢" in status_atual or "Finalizado" in status_atual
                    else ("#C62828" if "🔴" in status_atual else "#E65100")
                )

                st.markdown(
                    f"""
                <div style="background-color: #FAFAFA; border-left: 5px solid {txt_status}; padding: 12px; border-radius: 6px; margin-bottom: 10px;">
                    <span style="float: right; background-color: {cor_status}; color: {txt_status}; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: bold;">{status_atual}</span>
                    <h4 style="margin: 0; color: #333;">🤝 {row['cliente']} — <span style="font-size: 14px; color: #666;">{row['projeto']}</span></h4>
                    <p style="margin: 5px 0 0 0; font-size: 14px;">💰 <b>Total:</b> R$ {row['valor_total']:.2f} | 📊 <b>Boletos:</b> {row['parcelas_pagas']}/{row['parcelas_totais']} | 📅 <b>Vencimento:</b> {row['vencimento']}</p>
                </div>
                """,
                    unsafe_allow_html=True,
                )

                col_b1, col_b2, col_b3 = st.columns([2, 2, 1])
                if row["link_drive"]:
                    col_b1.link_button("📂 Abrir Pasta", row["link_drive"], use_container_width=True)
                else:
                    col_b1.caption("⚪ Sem link anexado.")

                if row["parcelas_pagas"] < row["parcelas_totais"]:
                    v_parcela = row["valor_total"] / row["parcelas_totais"]
                    if col_b2.button(
                        f"Confirmar Parcela (R$ {v_parcela:.2f})",
                        key=f"p_prc_{row['id']}",
                        use_container_width=True,
                    ):
                        n_p = row["parcelas_pagas"] + 1
                        n_s = (
                            "🟢 Finalizado"
                            if n_p == row["parcelas_totais"]
                            else "🟡 Aguardando Compensação"
                        )

                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE contratos_ej SET parcelas_pagas = ?,"
                            " status_boleto = ? WHERE id = ?",
                            (n_p, n_s, row["id"]),
                        )
                        conn.commit()
                        conn.close()

                        salvar_lancamento(
                            lista_meses[hoje_dt.month - 1],
                            hoje_dt.strftime("%Y-%m-%d"),
                            "NEGÓCIOS",
                            "Receita",
                            "Serviço Prestado",
                            f"Parc {n_p}/{row['parcelas_totais']} Contrato:"
                            f" {row['cliente']}",
                            v_parcela,
                            0.0,
                            v_parcela,
                            "Banco do Brasil",
                            "🟢 Pago",
                            "🟢 Emitida",
                            "❌ Não enviado",
                        )
                        st.success("Boleto liquidado e receita registrada no Fluxo de Caixa!")
                        st.rerun()

                if col_b3.button("🗑️ Deletar", key=f"dl_cn_{row['id']}", use_container_width=True):
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM contratos_ej WHERE id = ?", (row["id"],))
                    conn.commit()
                    conn.close()
                    st.success("Contrato removido!")
                    st.rerun()

    # =======================================================================
    # 2. TELA: QUADRO KANBAN DE DEMANDAS COM FILTRO POR DIRETORIA
    # =======================================================================
    with tab_tarefas:
        st.markdown("### 📋 Painel Didático de Distribuição de Demandas")

        try:
            conn = sqlite3.connect(DB_PATH)
            df_membros = pd.read_sql_query("SELECT nome FROM usuarios ORDER BY nome ASC", conn)
            conn.close()
            lista_nomes_membros = (
                df_membros["nome"].tolist()
                if not df_membros.empty
                else ["Nenhum membro cadastrado"]
            )
        except Exception:
            lista_nomes_membros = ["Nenhum membro cadastrado"]

        with st.expander("➕ Delegar Nova Tarefa para Assessor"):
            with st.form("form_tarefa"):
                tar = st.text_input("Descrição da Demanda (O que precisa ser feito?):").strip()
                ass_selecionado = st.selectbox("Selecione o Assessor Responsável:", lista_nomes_membros)
                dir_resp = st.selectbox(
                    "Diretoria da Demanda:",
                    ["VP", "PROJETOS", "NEGÓCIOS", "IMAGEM", "AR", "PRESIDÊNCIA"],
                )
                prz = st.text_input("Prazo de Entrega (Ex: Até Sexta 18h):", value="Até sexta-feira")

                if st.form_submit_button("🚀 Enviar para o Painel"):
                    if tar and ass_selecionado != "Nenhum membro cadastrado":
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            INSERT INTO tarefas_assessores (tarefa, assessor_nome, diretoria, prazo, status)
                            VALUES (?, ?, ?, ?, '🟡 A Fazer')
                        """,
                            (tar, ass_selecionado, dir_resp, prz),
                        )
                        conn.commit()
                        conn.close()
                        st.success(f"Tarefa delegada para {ass_selecionado}!")
                        st.rerun()

        # Carrega tarefas do banco
        conn = sqlite3.connect(DB_PATH)
        df_tar = pd.read_sql_query("SELECT * FROM tarefas_assessores", conn)
        conn.close()

        st.markdown("---")

        # Filtro de Busca por Diretoria no Kanban
        col_filtro_k1, _ = st.columns([2, 2])
        filtro_dir_kanban = col_filtro_k1.selectbox(
            "🔍 Filtrar Demandas por Diretoria:",
            ["Todas", "VP", "PROJETOS", "NEGÓCIOS", "IMAGEM", "AR", "PRESIDÊNCIA"],
        )

        df_tar_filtrado = df_tar.copy()
        if not df_tar_filtrado.empty and filtro_dir_kanban != "Todas":
            df_tar_filtrado = df_tar_filtrado[df_tar_filtrado["diretoria"] == filtro_dir_kanban]

        col_todo, col_doing, col_done = st.columns(3)

        with col_todo:
            st.markdown("#### 🟡 A Fazer")
            df_todo = (
                df_tar_filtrado[df_tar_filtrado["status"] == "🟡 A Fazer"]
                if not df_tar_filtrado.empty
                else pd.DataFrame()
            )
            if df_todo.empty:
                st.caption("Nenhuma tarefa pendente.")
            else:
                for _, r in df_todo.iterrows():
                    texto_whats = (
                        f"Olá, *{r['assessor_nome']}*! Você recebeu uma nova"
                        " demanda na plataforma da Farmácia Jr.\n\n📋"
                        f" *Tarefa:* {r['tarefa']}\n📁 *Setor:*"
                        f" {r['diretoria']}\n📅 *Prazo:* {r['prazo']}\n\nPor"
                        " favor, acesse o site e altere o status ao iniciar!"
                    )
                    texto_codificado = urllib.parse.quote(texto_whats)
                    link_whatsapp = f"https://wa.me/?text={texto_codificado}"

                    st.markdown(
                        f"""
                    <div style='background-color: #FFF9E6; border-left: 4px solid #FFA000; padding: 10px; border-radius: 5px; margin-bottom: 5px;'>
                        <b>{r['tarefa']}</b><br>
                        <small>👤 Assessor: {r['assessor_nome']} ({r['diretoria']})<br>📅 Prazo: {r['prazo']}</small>
                    </div>
                    """,
                        unsafe_allow_html=True,
                    )

                    c_btn1, c_btn2 = st.columns(2)
                    if c_btn1.button(
                        "⏩ Iniciar", key=f"st_{r['id']}", use_container_width=True
                    ):
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE tarefas_assessores SET status = '🔵"
                            " Executando' WHERE id = ?",
                            (r["id"],),
                        )
                        conn.commit()
                        conn.close()
                        st.rerun()

                    c_btn2.link_button(
                        "💬 Notificar", link_whatsapp, use_container_width=True
                    )

        with col_doing:
            st.markdown("#### 🔵 Em Andamento")
            df_doing = (
                df_tar_filtrado[df_tar_filtrado["status"] == "🔵 Executando"]
                if not df_tar_filtrado.empty
                else pd.DataFrame()
            )
            if df_doing.empty:
                st.caption("Nenhuma tarefa em andamento.")
            else:
                for _, r in df_doing.iterrows():
                    st.markdown(
                        "<div style='background-color: #E3F2FD; border-left: 4px"
                        " solid #1976D2; padding: 10px; border-radius: 5px;"
                        f" margin-bottom: 5px;'><b>{r['tarefa']}</b><br><small>👤"
                        f" Assessor: {r['assessor_nome']}"
                        f" ({r['diretoria']})<br>📅 Prazo:"
                        f" {r['prazo']}</small></div>",
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "✅ Concluir", key=f"dn_{r['id']}", use_container_width=True
                    ):
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute(
                            "UPDATE tarefas_assessores SET status = '🟢"
                            " Concluído' WHERE id = ?",
                            (r["id"],),
                        )
                        conn.commit()
                        conn.close()
                        st.rerun()

        with col_done:
            st.markdown("#### 🟢 Concluído")
            df_done = (
                df_tar_filtrado[df_tar_filtrado["status"] == "🟢 Concluído"]
                if not df_tar_filtrado.empty
                else pd.DataFrame()
            )
            if df_done.empty:
                st.caption("Nenhuma tarefa concluída.")
            else:
                for _, r in df_done.iterrows():
                    st.markdown(
                        "<div style='background-color: #E8F5E9; border-left: 4px"
                        " solid #388E3C; padding: 10px; border-radius: 5px;"
                        " margin-bottom: 5px; text-decoration: line-through;"
                        f" color: #777;'><b>{r['tarefa']}</b><br><small>👤"
                        f" Concluído por: {r['assessor_nome']}</small></div>",
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "🗑️ Limpar", key=f"cl_{r['id']}", use_container_width=True
                    ):
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute(
                            "DELETE FROM tarefas_assessores WHERE id = ?",
                            (r["id"],),
                        )
                        conn.commit()
                        conn.close()
                        st.rerun()
