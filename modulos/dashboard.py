import os
import sqlite3
import pandas as pd
import plotly.express as px
import streamlit as st

# Banco de dados padronizado com o Fluxo de Caixa
DB_PATH = "database/financeiro_v2.db"

# =======================================================================
# 🎨 TOKENS DE DESIGN
# =======================================================================
INK = "#0B3D3A"        # texto principal / títulos
MIST = "#F4F9F7"        # fundo suave
VERDANT = "#1F8F5B"      # receitas / positivo
CORAL = "#E8623F"       # despesas / negativo
SAGE = "#8FBFA8"        # apoio / secundário
CLOUD = "#FFFFFF"       # fundo dos cards
BORDER = "#E2ECE8"      # bordas sutis
SLATE = "#5B7A72"       # texto secundário / labels


def garantir_tabela_existente():
    """Garante a criação do banco e da tabela antes de qualquer leitura."""
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


def injetar_estilos():
    """Injeta o sistema de design (fontes, cards, headers) uma única vez."""
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@500;600&display=swap');

        /* -------- Header principal -------- */
        .fj-header {{
            display: flex;
            align-items: center;
            gap: 14px;
            margin-bottom: 2px;
        }}
        .fj-header-icon {{
            width: 46px; height: 46px;
            border-radius: 14px;
            background: linear-gradient(135deg, {VERDANT}, {INK});
            display: flex; align-items: center; justify-content: center;
            font-size: 22px;
            flex-shrink: 0;
        }}
        .fj-header-title {{
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 700;
            font-size: 26px;
            color: {INK};
            margin: 0;
            line-height: 1.1;
        }}
        .fj-header-caption {{
            font-family: 'Inter', sans-serif;
            font-size: 13px;
            color: {SLATE};
            margin-top: 2px;
        }}
        .fj-divider {{
            height: 3px;
            border-radius: 3px;
            background: linear-gradient(90deg, {VERDANT} 0%, {SAGE} 45%, {CORAL} 100%);
            margin: 18px 0 22px 0;
            opacity: 0.85;
        }}

        /* -------- Eyebrow de seção -------- */
        .fj-eyebrow {{
            font-family: 'IBM Plex Mono', monospace;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.10em;
            text-transform: uppercase;
            color: {SAGE};
            margin-bottom: 2px;
        }}
        .fj-section-title {{
            font-family: 'Space Grotesk', sans-serif;
            font-size: 18px;
            font-weight: 600;
            color: {INK};
            margin: 0 0 14px 0;
        }}

        /* -------- Metric cards -------- */
        .fj-card {{
            background: {CLOUD};
            border-radius: 16px;
            border: 1px solid {BORDER};
            padding: 20px 22px 18px 22px;
            position: relative;
            overflow: hidden;
            box-shadow: 0 2px 10px rgba(11,61,58,0.05);
            transition: transform .18s ease, box-shadow .18s ease;
            height: 128px;
        }}
        .fj-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 10px 26px rgba(11,61,58,0.10);
        }}
        .fj-card::before {{
            content: "";
            position: absolute;
            top: 0; left: 0; right: 0;
            height: 4px;
        }}
        .fj-card-label {{
            font-family: 'Inter', sans-serif;
            font-size: 11.5px;
            font-weight: 600;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            color: {SLATE};
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .fj-icon-badge {{
            width: 26px; height: 26px;
            border-radius: 8px;
            display: flex; align-items: center; justify-content: center;
            font-size: 13px;
            flex-shrink: 0;
        }}
        .fj-card-value {{
            font-family: 'Space Grotesk', sans-serif;
            font-size: 26px;
            font-weight: 700;
            color: {INK};
            margin-top: 10px;
            letter-spacing: -0.01em;
        }}
        .fj-card-sub {{
            font-family: 'IBM Plex Mono', monospace;
            font-size: 11.5px;
            font-weight: 600;
            margin-top: 6px;
        }}

        /* -------- Chart cards -------- */
        .fj-chart-card {{
            background: {CLOUD};
            border-radius: 16px;
            border: 1px solid {BORDER};
            padding: 18px 20px 6px 20px;
            box-shadow: 0 2px 10px rgba(11,61,58,0.05);
        }}

        /* -------- Filter bar -------- */
        .fj-filter-bar {{
            background: {MIST};
            border: 1px solid {BORDER};
            border-radius: 14px;
            padding: 14px 18px 4px 18px;
            margin-bottom: 18px;
        }}

        /* Ajustes finos em widgets nativos do Streamlit dentro das seções */
        div[data-testid="stSelectbox"] label, div[data-testid="stRadio"] label {{
            font-family: 'Inter', sans-serif !important;
            font-weight: 600 !important;
            color: {INK} !important;
            font-size: 13px !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def metric_card(col, label, icon, icon_bg, value_str, accent_gradient, sub_text=None, sub_color=None):
    """Renderiza um card de métrica no estilo do sistema de design."""
    sub_html = ""
    if sub_text:
        sub_html = f'<div class="fj-card-sub" style="color:{sub_color};">{sub_text}</div>'

    col.markdown(
        f"""
        <div class="fj-card" style="--tw: 0;">
            <div style="position:absolute; top:0; left:0; right:0; height:4px; background:{accent_gradient};"></div>
            <div class="fj-card-label">
                <span class="fj-icon-badge" style="background:{icon_bg};">{icon}</span>
                {label}
            </div>
            <div class="fj-card-value">{value_str}</div>
            {sub_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def renderizar_dashboard_geral():
    injetar_estilos()

    # -------------------------------------------------------------
    # Header
    # -------------------------------------------------------------
    st.markdown(
        f"""
        <div class="fj-header">
            <div class="fj-header-icon">🦩</div>
            <div>
                <p class="fj-header-title">Painel Financeiro</p>
                <p class="fj-header-caption">Visão consolidada da saúde financeira, origem de receitas e saídas por diretoria</p>
            </div>
        </div>
        <div class="fj-divider"></div>
        """,
        unsafe_allow_html=True,
    )

    # 1. Garante a existência do banco/tabela antes da leitura
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
        st.markdown(
            f"""
            <div class="fj-chart-card" style="text-align:center; padding:36px 20px;">
                <div style="font-size:28px;">🧫</div>
                <p style="font-family:'Space Grotesk',sans-serif; font-weight:600; color:{INK}; margin:10px 0 4px 0;">
                    Ainda não há lançamentos
                </p>
                <p style="font-family:'Inter',sans-serif; font-size:13px; color:{SLATE}; margin:0;">
                    O painel será gerado automaticamente assim que os primeiros registros forem lançados no Fluxo de Caixa.
                </p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        return

    # Tratamento de Tipos com Fallback de Segurança
    df["valor_liquido"] = pd.to_numeric(df["valor_liquido"], errors="coerce").fillna(0.0)
    df["data"] = pd.to_datetime(df["data"], errors="coerce")

    if "status_pagamento" not in df.columns:
        df["status_pagamento"] = "🟢 Pago"
    if "departamento" not in df.columns:
        df["departamento"] = "GERAL"
    if "categoria" not in df.columns:
        df["categoria"] = "Sem Categoria"

    # -------------------------------------------------------------
    # Filtros
    # -------------------------------------------------------------
    meses_ordem = [
        "Todos", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]

    st.markdown('<div class="fj-filter-bar">', unsafe_allow_html=True)
    col_f1, col_f2 = st.columns(2)
    filtro_mes = col_f1.selectbox("🗓️ Mês de referência", meses_ordem)
    filtro_status = col_f2.radio(
        "💰 Regime de caixa",
        ["Apenas confirmados (pagos)", "Todos (incluir pendentes)"],
        horizontal=True,
    )
    st.markdown('</div>', unsafe_allow_html=True)

    df_filtrado = df.copy()
    if filtro_mes != "Todos":
        df_filtrado = df_filtrado[df_filtrado["mes"] == filtro_mes]

    if filtro_status == "Apenas confirmados (pagos)":
        df_filtrado = df_filtrado[df_filtrado["status_pagamento"].str.contains("Pago", na=False)]

    # -------------------------------------------------------------
    # Métricas
    # -------------------------------------------------------------
    receitas = df_filtrado[df_filtrado["tipo"] == "Receita"]["valor_liquido"].sum()
    despesas = df_filtrado[df_filtrado["tipo"] == "Despesa"]["valor_liquido"].sum()
    saldo = receitas - despesas
    margem = (saldo / receitas * 100) if receitas > 0 else 0.0

    cor_saldo = VERDANT if saldo >= 0 else CORAL
    gradiente_saldo = f"linear-gradient(90deg, {cor_saldo}, {SAGE})"

    m1, m2, m3 = st.columns(3)

    metric_card(
        m1, "Faturamento", "📥", f"{VERDANT}22",
        formatar_moeda(receitas),
        f"linear-gradient(90deg, {VERDANT}, {SAGE})",
    )
    metric_card(
        m2, "Despesas acumuladas", "📤", f"{CORAL}22",
        formatar_moeda(despesas),
        f"linear-gradient(90deg, {CORAL}, #F2A38B)",
    )
    metric_card(
        m3, "Saldo em caixa", "⚖️", f"{cor_saldo}22",
        formatar_moeda(saldo),
        gradiente_saldo,
        sub_text=f"{margem:.1f}% margem operacional",
        sub_color=cor_saldo,
    )

    st.markdown("<div style='height:22px;'></div>", unsafe_allow_html=True)

    # Estilo global dos gráficos, alinhado à paleta do sistema
    estilo_layout_grafico = dict(
        margin=dict(l=10, r=10, t=10, b=10),
        font=dict(color=INK, size=12, family="Inter, sans-serif"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(font=dict(color=INK, size=11)),
        xaxis=dict(tickfont=dict(color=INK), title_font=dict(color=INK)),
        yaxis=dict(tickfont=dict(color=INK), title_font=dict(color=INK)),
    )

    # -------------------------------------------------------------
    # Evolução mensal + Pizza
    # -------------------------------------------------------------
    col_esq, col_dir = st.columns(2)

    with col_esq:
        st.markdown('<div class="fj-eyebrow">Tendência</div>', unsafe_allow_html=True)
        st.markdown('<p class="fj-section-title">Evolução mensal</p>', unsafe_allow_html=True)
        st.markdown('<div class="fj-chart-card">', unsafe_allow_html=True)

        df_mensal = df_filtrado.groupby(["mes", "tipo"])["valor_liquido"].sum().reset_index()
        df_mensal["mes"] = pd.Categorical(df_mensal["mes"], categories=meses_ordem[1:], ordered=True)
        df_mensal = df_mensal.sort_values("mes")

        if not df_mensal.empty:
            fig_evolucao = px.line(
                df_mensal, x="mes", y="valor_liquido", color="tipo",
                color_discrete_map={"Receita": VERDANT, "Despesa": CORAL},
                markers=True,
                labels={"valor_liquido": "Valor (R$)", "mes": "Mês", "tipo": "Tipo"},
            )
            fig_evolucao.update_traces(line=dict(width=3), marker=dict(size=7))
            fig_evolucao.update_layout(**estilo_layout_grafico, legend_title_text="")
            st.plotly_chart(fig_evolucao, use_container_width=True)
        else:
            st.caption("Sem dados suficientes para o período selecionado.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_dir:
        st.markdown('<div class="fj-eyebrow">Composição</div>', unsafe_allow_html=True)
        st.markdown('<p class="fj-section-title">Fontes de receita</p>', unsafe_allow_html=True)
        st.markdown('<div class="fj-chart-card">', unsafe_allow_html=True)

        df_rec = df_filtrado[df_filtrado["tipo"] == "Receita"]
        if not df_rec.empty:
            fig_pizza = px.pie(
                df_rec, values="valor_liquido", names="categoria",
                color_discrete_sequence=[VERDANT, SAGE, "#C9E4D6", INK, "#4FAE7A", "#B7DCC6"],
                hole=0.55,
            )
            fig_pizza.update_traces(
                textposition="outside",
                textinfo="percent+label",
                textfont=dict(color=INK, size=12, family="Inter, sans-serif"),
                outsidetextfont=dict(color=INK, size=12, family="Inter, sans-serif"),
                marker=dict(line=dict(color=CLOUD, width=2)),
            )
            fig_pizza.update_layout(**estilo_layout_grafico, showlegend=False)
            st.plotly_chart(fig_pizza, use_container_width=True)
        else:
            st.caption("Nenhuma receita registrada no filtro selecionado.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:22px;'></div>", unsafe_allow_html=True)

    # -------------------------------------------------------------
    # Despesas por diretoria
    # -------------------------------------------------------------
    st.markdown('<div class="fj-eyebrow">Distribuição</div>', unsafe_allow_html=True)
    st.markdown('<p class="fj-section-title">Despesas por diretoria</p>', unsafe_allow_html=True)
    st.markdown('<div class="fj-chart-card">', unsafe_allow_html=True)

    df_desp = df_filtrado[df_filtrado["tipo"] == "Despesa"]

    if not df_desp.empty:
        fig_barras = px.bar(
            df_desp, x="departamento", y="valor_liquido", color="categoria",
            barmode="stack",
            color_discrete_sequence=[CORAL, "#F2A38B", INK, SAGE, "#8C4E3B", "#D9C6A5"],
            labels={
                "valor_liquido": "Total gasto (R$)",
                "departamento": "Diretoria",
                "categoria": "Categoria",
            },
        )
        fig_barras.update_layout(**estilo_layout_grafico)
        st.plotly_chart(fig_barras, use_container_width=True)
    else:
        st.caption("Nenhuma despesa registrada para exibir o gráfico de barras.")
    st.markdown('</div>', unsafe_allow_html=True)
