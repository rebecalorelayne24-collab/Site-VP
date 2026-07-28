import os
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

# Banco de dados padronizado com o Fluxo de Caixa
DB_PATH = "database/financeiro_v2.db"


def garantir_tabela_existente():
    """Garante a criação do banco e da tabela antes da tentativa de leitura."""
    if not os.path.exists("database"):
        os.makedirs("database")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fluxo_caixa_geral (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mes TEXT,
            data TEXT,
            departamento TEXT,
            tipo TEXT,
            categoria TEXT,
            descricao TEXT,
            valor_bruto REAL,
            taxa REAL,
            valor_liquido REAL,
            conta_origem TEXT,
            status_pagamento TEXT,
            nota_fiscal TEXT,
            status_onvio TEXT
        )
    """)
    conn.commit()
    conn.close()


def renderizar_dashboard_geral():
    st.markdown(
        "<h2 style='text-align: center; color: #FF1493;'>📊 Dashboard Estratégico — Farmácia Jr.</h2>",
        unsafe_allow_html=True,
    )
    st.caption("Visão consolidada da saúde financeira, origem de receitas e saídas por diretoria.")

    # 1. Garante que a tabela existe antes de tentar ler
    garantir_tabela_existente()

    # 2. Carregamento Seguro dos Dados
    try:
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query("SELECT * FROM fluxo_caixa_geral", conn)
        conn.close()
    except Exception as e:
        st.error(f"Erro ao acessar o banco de dados: {e}")
        return

    if df.empty:
        st.info("ℹ️ O Dashboard será gerado assim que os primeiros lançamentos forem registrados no Fluxo de Caixa.")
        return

    # Tratamento de Tipos com Fallback de Segurança
    df["valor_liquido"] = pd.to_numeric(df["valor_liquido"], errors="coerce").fillna(0.0)
    df["data"] = pd.to_datetime(df["data"], errors="coerce")

    # Garantia de existência de colunas essenciais
    if "status_pagamento" not in df.columns:
        df["status_pagamento"] = "🟢 Pago"
    if "departamento" not in df.columns:
        df["departamento"] = "GERAL"
    if "categoria" not in df.columns:
        df["categoria"] = "Sem Categoria"

    # =======================================================================
    # 🎛️ FILTROS ESTRATÉGICOS (MÊS E STATUS)
    # =======================================================================
    meses_ordem = [
        "Todos", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]

    col_f1, col_f2 = st.columns(2)
    filtro_mes = col_f1.selectbox("🗓️ Filtrar por Mês de Referência:", meses_ordem)
    filtro_status = col_f2.radio(
        "💰 Regime de Caixa:",
        ["Apenas Confirmados (Pagos)", "Todos (Incluir Pendentes)"],
        horizontal=True,
    )

    # Aplicação dos Filtros
    df_filtrado = df.copy()
    if filtro_mes != "Todos":
        df_filtrado = df_filtrado[df_filtrado["mes"] == filtro_mes]

    if filtro_status == "Apenas Confirmados (Pagos)":
        df_filtrado = df_filtrado[df_filtrado["status_pagamento"].str.contains("Pago", na=False)]

    st.markdown("---")

    # =======================================================================
    # 1. MÉTRICAS CHAVE (CARDS EXECUTIVOS)
    # =======================================================================
    receitas = df_filtrado[df_filtrado["tipo"] == "Receita"]["valor_liquido"].sum()
    despesas = df_filtrado[df_filtrado["tipo"] == "Despesa"]["valor_liquido"].sum()
    saldo = receitas - despesas
    margem = (saldo / receitas * 100) if receitas > 0 else 0.0

    m1, m2, m3 = st.columns(3)
    m1.metric("📥 Faturamento (Receitas)", f"R$ {receitas:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    m2.metric("📤 Despesas Acumuladas", f"R$ {despesas:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    m3.metric(
        "⚖️ Saldo em Caixa",
        f"R$ {saldo:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        delta=f"{margem:.1f}% Margem Operacional",
        delta_color="normal" if saldo >= 0 else "inverse",
    )

    st.markdown("---")

    # =======================================================================
    # 2. GRÁFICOS: EVOLUÇÃO E PIZZA DE CATEGORIAS
    # =======================================================================
    col_esq, col_dir = st.columns(2)

    with col_esq:
        st.markdown("#### 📈 Evolução Mensal (Receitas vs Despesas)")
        df_mensal = df_filtrado.groupby(["mes", "tipo"])["valor_liquido"].sum().reset_index()

        # Ordenação Cronológica Estrita
        df_mensal["mes"] = pd.Categorical(df_mensal["mes"], categories=meses_ordem[1:], ordered=True)
        df_mensal = df_mensal.sort_values("mes")

        if not df_mensal.empty:
            fig_evolucao = px.line(
                df_mensal,
                x="mes",
                y="valor_liquido",
                color="tipo",
                color_discrete_map={"Receita": "#2E7D32", "Despesa": "#C62828"},
                markers=True,
                template="plotly_white",
                labels={"valor_liquido": "Valor (R$)", "mes": "Mês", "tipo": "Tipo"},
            )
            fig_evolucao.update_layout(margin=dict(l=20, r=20, t=20, b=20), legend_title_text="")
            st.plotly_chart(fig_evolucao, use_container_width=True)
        else:
            st.caption("Sem dados suficientes para o período selecionado.")

    with col_dir:
        st.markdown("#### 🍕 Fontes de Receita por Categoria")
        df_rec = df_filtrado[df_filtrado["tipo"] == "Receita"]
        if not df_rec.empty:
            fig_pizza = px.pie(
                df_rec,
                values="valor_liquido",
                names="categoria",
                color_discrete_sequence=px.colors.qualitative.Pastel,
                hole=0.4,
            )
            fig_pizza.update_layout(margin=dict(l=20, r=20, t=20, b=20))
            st.plotly_chart(fig_pizza, use_container_width=True)
        else:
            st.caption("Nenhuma receita registrada no filtro selecionado.")

    st.markdown("---")

    # =======================================================================
    # 3. GRÁFICOS: DESPESAS POR DIRETORIA
    # =======================================================================
    st.markdown("#### 🏢 Distribuição de Despesas por Diretoria")
    df_desp = df_filtrado[df_filtrado["tipo"] == "Despesa"]

    if not df_desp.empty:
        fig_barras = px.bar(
            df_desp,
            x="departamento",
            y="valor_liquido",
            color="categoria",
            barmode="stack",
            color_discrete_sequence=px.colors.qualitative.Safe,
            template="plotly_white",
            labels={
                "valor_liquido": "Total Gasto (R$)",
                "departamento": "Diretoria",
                "categoria": "Categoria",
            },
        )
        fig_barras.update_layout(margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_barras, use_container_width=True)
    else:
        st.caption("Nenhuma despesa registrada para exibir o gráfico de barras.")
