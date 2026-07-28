"""
Sistema de design compartilhado da Plataforma VP — Farmácia Jr.
Importe deste módulo em qualquer página para manter a identidade visual consistente.
"""
import streamlit as st

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


@st.cache_data
def _css():
    return f"""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@500;600&display=swap');

    /* -------- Header de página -------- */
    .fj-header {{
        display: flex; align-items: center; gap: 14px; margin-bottom: 2px;
    }}
    .fj-header-icon {{
        width: 46px; height: 46px; border-radius: 14px;
        background: linear-gradient(135deg, {VERDANT}, {INK});
        display: flex; align-items: center; justify-content: center;
        font-size: 22px; flex-shrink: 0;
    }}
    .fj-header-title {{
        font-family: 'Space Grotesk', sans-serif; font-weight: 700;
        font-size: 26px; color: {INK}; margin: 0; line-height: 1.1;
    }}
    .fj-header-caption {{
        font-family: 'Inter', sans-serif; font-size: 13px; color: {SLATE}; margin-top: 2px;
    }}
    .fj-divider {{
        height: 3px; border-radius: 3px;
        background: linear-gradient(90deg, {VERDANT} 0%, {SAGE} 45%, {CORAL} 100%);
        margin: 18px 0 22px 0; opacity: 0.85;
    }}

    /* -------- Eyebrow / título de seção -------- */
    .fj-eyebrow {{
        font-family: 'IBM Plex Mono', monospace; font-size: 11px; font-weight: 600;
        letter-spacing: 0.10em; text-transform: uppercase; color: {SAGE}; margin-bottom: 2px;
    }}
    .fj-section-title {{
        font-family: 'Space Grotesk', sans-serif; font-size: 18px; font-weight: 600;
        color: {INK}; margin: 0 0 14px 0;
    }}

    /* -------- Metric cards -------- */
    .fj-card {{
        background: {CLOUD}; border-radius: 16px; border: 1px solid {BORDER};
        padding: 20px 22px 18px 22px; position: relative; overflow: hidden;
        box-shadow: 0 2px 10px rgba(11,61,58,0.05);
        transition: transform .18s ease, box-shadow .18s ease; height: 128px;
    }}
    .fj-card:hover {{ transform: translateY(-2px); box-shadow: 0 10px 26px rgba(11,61,58,0.10); }}
    .fj-card-label {{
        font-family: 'Inter', sans-serif; font-size: 11.5px; font-weight: 600;
        letter-spacing: 0.06em; text-transform: uppercase; color: {SLATE};
        display: flex; align-items: center; gap: 8px;
    }}
    .fj-icon-badge {{
        width: 26px; height: 26px; border-radius: 8px;
        display: flex; align-items: center; justify-content: center;
        font-size: 13px; flex-shrink: 0;
    }}
    .fj-card-value {{
        font-family: 'Space Grotesk', sans-serif; font-size: 26px; font-weight: 700;
        color: {INK}; margin-top: 10px; letter-spacing: -0.01em;
    }}
    .fj-card-sub {{
        font-family: 'IBM Plex Mono', monospace; font-size: 11.5px; font-weight: 600; margin-top: 6px;
    }}

    /* -------- Chart / content cards -------- */
    .fj-chart-card {{
        background: {CLOUD}; border-radius: 16px; border: 1px solid {BORDER};
        padding: 18px 20px 6px 20px; box-shadow: 0 2px 10px rgba(11,61,58,0.05);
    }}

    /* -------- Filter bar -------- */
    .fj-filter-bar {{
        background: {MIST}; border: 1px solid {BORDER}; border-radius: 14px;
        padding: 14px 18px 4px 18px; margin-bottom: 18px;
    }}

    /* -------- List rows (lançamentos) -------- */
    .fj-list-row {{
        background: {CLOUD}; border: 1px solid {BORDER}; border-radius: 12px;
        padding: 12px 16px; margin-bottom: 8px;
        transition: box-shadow .15s ease, border-color .15s ease;
    }}
    .fj-list-row:hover {{ box-shadow: 0 4px 14px rgba(11,61,58,0.08); border-color: {SAGE}; }}
    .fj-date-pill {{
        border-radius: 10px; text-align: center; padding: 6px 4px;
        font-family: 'IBM Plex Mono', monospace; font-weight: 600; font-size: 11px;
        line-height: 1.4;
    }}
    .fj-pill {{
        display: inline-block; border-radius: 999px; padding: 2px 10px;
        font-family: 'Inter', sans-serif; font-size: 11px; font-weight: 600;
        margin-right: 4px;
    }}
    .fj-desc {{
        font-family: 'Inter', sans-serif; font-weight: 600; color: {INK}; font-size: 14px;
    }}
    .fj-meta {{
        font-family: 'Inter', sans-serif; font-size: 11.5px; color: {SLATE};
    }}
    .fj-value {{
        font-family: 'IBM Plex Mono', monospace; font-weight: 600; font-size: 14px; color: {INK};
    }}

    /* Ajustes finos em widgets nativos do Streamlit */
    div[data-testid="stSelectbox"] label, div[data-testid="stRadio"] label,
    div[data-testid="stTextInput"] label, div[data-testid="stNumberInput"] label,
    div[data-testid="stDateInput"] label {{
        font-family: 'Inter', sans-serif !important; font-weight: 600 !important;
        color: {INK} !important; font-size: 13px !important;
    }}
    </style>
    """


def injetar_estilos():
    """Injeta o sistema de design uma vez por página."""
    st.markdown(_css(), unsafe_allow_html=True)


def page_header(icon, title, caption):
    """Cabeçalho padrão de página com ícone, título e divisor gradiente."""
    st.markdown(
        f"""
        <div class="fj-header">
            <div class="fj-header-icon">{icon}</div>
            <div>
                <p class="fj-header-title">{title}</p>
                <p class="fj-header-caption">{caption}</p>
            </div>
        </div>
        <div class="fj-divider"></div>
        """,
        unsafe_allow_html=True,
    )


def section_header(eyebrow, title):
    """Eyebrow + título de seção, no padrão do sistema de design."""
    st.markdown(f'<div class="fj-eyebrow">{eyebrow}</div>', unsafe_allow_html=True)
    st.markdown(f'<p class="fj-section-title">{title}</p>', unsafe_allow_html=True)


def metric_card(col, label, icon, icon_bg, value_str, accent_gradient, sub_text=None, sub_color=None):
    """Renderiza um card de métrica no estilo do sistema de design."""
    sub_html = ""
    if sub_text:
        sub_html = f'<div class="fj-card-sub" style="color:{sub_color};">{sub_text}</div>'

    col.markdown(
        f"""
        <div class="fj-card">
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


def pill(text, color):
    """Pequeno badge arredondado (ex: status de pagamento, nota fiscal)."""
    return f'<span class="fj-pill" style="background:{color}22; color:{color};">{text}</span>'


def formatar_moeda(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
