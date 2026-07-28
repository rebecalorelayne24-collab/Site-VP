import os
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

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


def aplicar_estilos_customizados():
    """Aplica CSS com paleta de cores elegante, neutra e harmoniosa."""
    st.markdown(
        """
        <style>
        /* Estilização dos Cards Expositivos com cores suaves */
        .card-metrica {
            background-color: #FFFFFF;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.04);
            border: 1px solid #F0F0F0;
            text-align: center;
        }
        .card-metrica span {
            font-size: 12px;
            font-weight: 700;
            color: #6B7280;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        .card-metrica h3 {
            margin: 8px 0 4px 0;
            font-size: 26px;
            font-weight: 800;
        }
        .card-metrica p {
            margin: 0;
            font-size: 13px;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def renderizar_dashboard_geral():
    aplicar_estilos_customizados()

    st.markdown(
        "<h2 style='text-align: center; color: #C71585; font-weight: 800;'>📊 Dashboard Estratégico — Farmácia Jr.</h2>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align: center; color: #6B7280; font-size: 14px; margin-bottom: 25px;'>Visão consolidada da saúde financeira, origem de receitas e saídas por diretoria.</p>",
        unsafe_allow_html=True,
    )

    garantir_tabela_existente()

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

    # Tratamento de Tipos
    df["valor_liquido"] = pd.to_numeric(df["valor_liquido"], errors="coerce").fillna(0.0)
    df["data"] = pd.to_datetime(df["data"], errors="coerce")

    if "status_pagamento" not in df.columns:
        df["status_pagamento"] = "🟢 Pago"
    if "departamento" not in df.columns:
        df["departamento"] = "GERAL"
    if "categoria" not in df.columns:
        df["categoria"] = "Sem Categoria"

    # =======================================================================
    # 🎛️ FILTROS
    # =======================================================================
    meses_ordem = [
        "Todos", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]

    c_f1, c_f2 = st.columns([1, 1])
    filtro_mes = c_f1.selectbox("🗓️ Mês de Referência:", meses_ordem)
    filtro_status = c_f2.radio(
        "💰 Regime de Caixa:",
        ["Apenas Confirmados (Pagos)", "Todos (Incluir Pendentes)"],
        horizontal=True,
    )

    df_filtrado = df.copy()
    if filtro_mes != "Todos":
        df_filtrado = df_filtrado[df_filtrado["mes"] == filtro_mes]

    if filtro_status == "Apenas Confirmados (Pagos)":
        df_filtrado = df_filtrado[df_filtrado["status_pagamento"].str.contains("Pago", na=False)]

    st.markdown("<br>", unsafe_allow_html=True)

    # =======================================================================
    # 1. CARDS DE MÉTRICAS (CORES SUAVES)
    # =======================================================================
    receitas = df_filtrado[df_filtrado["tipo"] == "Receita"]["valor_liquido"].sum()
    despesas = df_filtrado[df_filtrado["tipo"] == "Despesa"]["valor_liquido"].sum()
    saldo = receitas - despesas
    margem = (saldo / receitas * 100) if receitas > 0 else 0.0

    m1, m2, m3 = st.columns(3)

    # Card Receitas (Verde Emerald)
    m1.markdown(
        f"""
        <div class="card-metrica" style="border-top: 4px solid #10B981;">
            <span>📥 Faturamento (Receitas)</span>
            <h3 style="color: #059669;">R$ {receitas:,.2f}</h3>
        </div>
        """.replace(",", "X").replace(".", ",").replace("X", "."),
        unsafe_allow_html=True,
    )

    # Card Despesas (Vermelho Suave)
    m2.markdown(
        f"""
        <div class="card-metrica" style="border-top: 4px solid #EF4444;">
            <span>📤 Despesas Acumuladas</span>
            <h3 style="color: #DC2626;">R$ {despesas:,.2f}</h3>
        </div>
        """.replace(",", "X").replace(".", ",").replace("X", "."),
        unsafe_allow_html=True,
    )

    # Card Saldo (Verde ou Vermelho dinâmico)
    cor_borda = "#10B981" if saldo >= 0 else "#EF4444"
    cor_texto = "#059669" if saldo >= 0 else "#DC2626"
    m3.markdown(
        f"""
        <div class="card-metrica" style="border-top: 4px solid {cor_borda};">
            <span>⚖️ Saldo em Caixa</span>
            <h3 style="color: {cor_texto};">R$ {saldo:,.2f}</h3>
            <p style="color: {cor_texto};">Margem Operacional: {margem:.1f}%</p>
        </div>
        """.replace(",", "X").replace(".", ",").replace("X", "."),
        unsafe_allow_html=True,
    )

    st.markdown("<br><hr style='border: 0.5px solid #E5E7EB;'><br>", unsafe_allow_html=True)

    # =======================================================================
    # 2. GRÁFICOS: EVOLUÇÃO E PIZZA (PALETAS HARMONIZADAS)
    # =======================================================================
    col_esq, col_dir = st.columns(2)

    # Paleta corporativa moderna para categorias (Tom Rosa, Azul, Roxo, Verde Água, Amarelo Suave)
    paleta_categorias = ["#EC4899", "#3B82F6", "#8B5CF6", "#14B8A6", "#F59E0B", "#6366F1", "#10B981"]

    with col_esq:
        st.markdown("<h4 style='color: #374151;'>📈 Evolução Mensal (Receitas vs Despesas)</h4>", unsafe_allow_html=True)
        df_mensal = df_filtrado.groupby(["mes", "tipo"])["valor_liquido"].sum().reset_index()

        df_mensal["mes"] = pd.Categorical(df_mensal["mes"], categories=meses_ordem[1:], ordered=True)
        df_mensal = df_mensal.sort_values("mes")

        if not df_mensal.empty:
            fig_evolucao = px.line(
                df_mensal,
                x="mes",
                y="valor_liquido",
                color="tipo",
                color_discrete_map={"Receita": "#10B981", "Despesa": "#EF4444"},
                markers=True,
                template="plotly_white",
                labels={"valor_liquido": "Valor (R$)", "mes": "Mês", "tipo": "Tipo"},
            )
            fig_evolucao.update_layout(
                margin=dict(l=10, r=10, t=30, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_evolucao, use_container_width=True)
        else:
            st.caption("Sem dados suficientes para o período selecionado.")

    with col_dir:
        st.markdown("<h4 style='color: #374151;'>🍕 Fontes de Receita por Categoria</h4>", unsafe_allow_html=True)
        df_rec = df_filtrado[df_filtrado["tipo"] == "Receita"]
        if not df_rec.empty:
            fig_pizza = px.pie(
                df_rec,
                values="valor_liquido",
                names="categoria",
                color_discrete_sequence=paleta_categorias,
                hole=0.45,
            )
            fig_pizza.update_layout(
                margin=dict(l=10, r=10, t=30, b=10),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_pizza, use_container_width=True)
        else:
            st.caption("Nenhuma receita registrada no filtro selecionado.")

    st.markdown("<br><hr style='border: 0.5px solid #E5E7EB;'><br>", unsafe_allow_html=True)

    # =======================================================================
    # 3. GRÁFICO: BARRAS POR DIRETORIA
    # =======================================================================
    st.markdown("<h4 style='color: #374151;'>🏢 Distribuição de Despesas por Diretoria</h4>", unsafe_allow_html=True)
    df_desp = df_filtrado[df_filtrado["tipo"] == "Despesa"]

    if not df_desp.empty:
        fig_barras = px.bar(
            df_desp,
            x="departamento",
            y="valor_liquido",
            color="categoria",
            barmode="stack",
            color_discrete_sequence=paleta_categorias,
            template="plotly_white",
            labels={
                "valor_liquido": "Total Gasto (R$)",
                "departamento": "Diretoria",
                "categoria": "Categoria",
            },
        )
        fig_barras.update_layout(
            margin=dict(l=10, r=10, t=30, b=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_barras, use_container_width=True)
    else:
        st.caption("Nenhuma despesa registrada para exibir o gráfico de barras.")
        st.caption("Nenhuma despesa registrada para exibir o gráfico de barras.")
