import os
import sqlite3
import hashlib
import streamlit as st

# 1. Configuração da página (deve ser o primeiro comando Streamlit)
st.set_page_config(
    page_title="Plataforma VP — Farmácia Jr.",
    page_icon="🦩",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 2. Configuração do Gemini em cache de recurso (só carrega se houver chave)
@st.cache_resource
def setup_gemini():
    api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return False
    import google.generativeai as genai
    os.environ["GEMINI_API_KEY"] = api_key
    genai.configure(api_key=api_key)
    return True

setup_gemini()

# 2b. Conexão SQLite global otimizada e cacheada na memória
@st.cache_resource
def get_connection():
    return sqlite3.connect("database/financeiro_v2.db", check_same_thread=False)

# Função local de verificação de credenciais (suporta hash SHA-256 e texto plano)
def verificar_credenciais_app(email, senha):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT nome, senha, primeiro_login, departamento FROM usuarios WHERE email = ?", (email,))
    user = cursor.fetchone()
    
    if not user:
        return {"sucesso": False, "mensagem": "E-mail não cadastrado no sistema."}
    
    nome, senha_db, primeiro_login, departamento = user
    senha_hash_digitada = hashlib.sha256(senha.encode("utf-8")).hexdigest()
    
    if senha == senha_db or senha_hash_digitada == senha_db:
        return {
            "sucesso": True,
            "nome": nome,
            "primeiro_login": primeiro_login,
            "departamento": departamento or "Geral"
        }
    else:
        return {"sucesso": False, "mensagem": "Senha incorreta. Tente novamente."}

# 3. Estilo CSS Cacheado para renderização instantânea
@st.cache_data
def aplicar_estilo_ui():
    return """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <style>
        html, body, [data-testid="stAppViewContainer"] {
            background-color: #FFF5F7 !important;
            color: #2D2D2D !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #E75480 0%, #C71585 100%) !important;
            box-shadow: 3px 0 10px rgba(0,0,0,0.05);
        }
        [data-testid="stSidebar"] *, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span, [data-testid="stSidebar"] p {
            color: #FFFFFF !important;
            font-weight: 500 !important;
        }
        [data-testid="stSidebar"] div[role="radiogroup"] > label {
            background-color: rgba(255, 255, 255, 0.15) !important;
            padding: 8px 12px !important;
            border-radius: 8px !important;
            margin-bottom: 4px !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
        }
        [data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] {
            background-color: #FFFFFF !important;
        }
        [data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] span {
            color: #C71585 !important;
            font-weight: bold !important;
        }
        div[data-baseweb="input"] > div {
            background-color: #FFFFFF !important;
            border: 1.5px solid #FFB6C1 !important;
            border-radius: 8px !important;
        }
        div[data-baseweb="input"] input {
            color: #333333 !important;
            background-color: #FFFFFF !important;
            -webkit-text-fill-color: #333333 !important;
        }
        div.stButton > button {
            background: linear-gradient(90deg, #FF69B4 0%, #E75480 100%) !important;
            color: #FFFFFF !important;
            border-radius: 8px !important;
            border: none !important;
            font-weight: 600 !important;
            padding: 8px 20px !important;
            width: 100% !important;
        }
        h1, h2, h3 {
            color: #C71585 !important;
            font-weight: 700 !important;
        }
    </style>
    """

st.markdown(aplicar_estilo_ui(), unsafe_allow_html=True)

# Inicialização rápida das variáveis de sessão
if "logado" not in st.session_state:
    st.session_state.logado = False
if "email_usuario" not in st.session_state:
    st.session_state.email_usuario = ""
if "nome_usuario" not in st.session_state:
    st.session_state.nome_usuario = ""
if "primeiro_login" not in st.session_state:
    st.session_state.primeiro_login = 1
if "departamento_usuario" not in st.session_state:
    st.session_state.departamento_usuario = "Geral"

# =======================================================================
# FLUXO DE TELA 1: LOGIN
# =======================================================================
if not st.session_state.logado:
    from database.conexao_db import inicializar_banco_dados
    inicializar_banco_dados()

    # --- FORÇAR CORREÇÃO DA SENHA PADRÃO NO BANCO ---
    try:
        conn_fix = get_connection()
        cur_fix = conn_fix.cursor()
        hash_padrao = hashlib.sha256("123456".encode("utf-8")).hexdigest()
        cur_fix.execute("""
            UPDATE usuarios 
            SET senha = ?, primeiro_login = 0 
            WHERE email IN ('vice-presidencia@farmaciajr.com', 'presidencia@farmaciajr.com')
        """, (hash_padrao,))
        conn_fix.commit()
    except Exception:
        pass
    # ------------------------------------------------

    _, col2, _ = st.columns([1, 2, 1])
    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("<h1 style='text-align: center;'>🦩 Plataforma VP</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #666;'>Farmácia Jr. — Gestão Financeira & Operacional</p>", unsafe_allow_html=True)
        st.markdown("---")

        email_input = st.text_input("E-mail Institucional:", placeholder="seu-email@farmaciajr.com")
        senha_input = st.text_input("Senha:", type="password", placeholder="••••••••")

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Acessar Plataforma"):
            if email_input and senha_input:
                email_ajustado = email_input.strip().lower()
                checagem = verificar_credenciais_app(email_ajustado, senha_input)

                if checagem["sucesso"]:
                    st.session_state.logado = True
                    st.session_state.email_usuario = email_ajustado
                    st.session_state.nome_usuario = checagem["nome"]
                    st.session_state.primeiro_login = checagem["primeiro_login"]
                    st.session_state.departamento_usuario = checagem["departamento"]
                    st.rerun()
                else:
                    st.error(checagem["mensagem"])
            else:
                st.error("Por favor, preencha o e-mail e a senha.")

# =======================================================================
# FLUXO DE TELA 2: TROCA DE SENHA OBRIGATÓRIA (PRIMEIRO ACESSO)
# =======================================================================
elif st.session_state.logado and st.session_state.primeiro_login == 1:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT primeiro_login FROM usuarios WHERE email = ?", (st.session_state.email_usuario,))
    resultado = cursor.fetchone()

    if resultado and resultado[0] == 1:
        from modulos.telas_equipe import renderizar_tela_troca_senha
        renderizar_tela_troca_senha(st.session_state.email_usuario)
    else:
        st.session_state.primeiro_login = 0
        st.rerun()

# =======================================================================
# FLUXO DE TELA 3: PAINEL PRINCIPAL COM LAZY LOADING
# =======================================================================
else:
    st.sidebar.markdown("<h2 style='color: #FFFFFF !important;'>🦩 Setor VP</h2>", unsafe_allow_html=True)
    st.sidebar.markdown(f"<p style='color: #FFFFFF !important;'><b>Olá, {st.session_state.nome_usuario}!</b></p>", unsafe_allow_html=True)
    st.sidebar.markdown(f"<small style='color: #FFE4E1 !important;'>Setor: {st.session_state.departamento_usuario}</small>", unsafe_allow_html=True)
    st.sidebar.markdown("<hr style='border-color: rgba(255,255,255,0.2);'>", unsafe_allow_html=True)

    opcoes_menu = ["Totem de Vendas Express", "Planejamento de Eventos"]

    if st.session_state.departamento_usuario in ["VP", "Presidência"] or st.session_state.email_usuario in ["vice-presidencia@farmaciajr.com", "presidencia@farmaciajr.com"]:
        opcoes_menu = [
            "Dashboard Geral",
            "Fluxo de Caixa",
            "Planejamento de Eventos",
            "Contratos e Demandas Internas",
            "Pipeline de Leads",
            "Calculadora de Precificação",
            "Totem de Vendas Express",
            "Gerenciar Equipe",
        ]

    menu = st.sidebar.radio("Navegação:", opcoes_menu)

    st.sidebar.markdown("<hr style='border-color: rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
    if st.sidebar.button("🚪 Encerrar Sessão"):
        st.session_state.logado = False
        st.session_state.email_usuario = ""
        st.session_state.nome_usuario = ""
        st.session_state.primeiro_login = 1
        st.session_state.departamento_usuario = "Geral"
        st.rerun()

    # --- ROTEAMENTO INTELIGENTE (Carrega estritamente o módulo da aba selecionada) ---
    if menu == "Dashboard Geral":
        from modulos.dashboard import renderizar_dashboard_geral
        renderizar_dashboard_geral()

    elif menu == "Calculadora de Precificação":
        from modulos.precificacao import renderizar_aba_precificacao
        renderizar_aba_precificacao()

    elif menu == "Fluxo de Caixa":
        from modulos.fluxo_caixa import renderizar_aba_fluxo_caixa
        renderizar_aba_fluxo_caixa()

    elif menu == "Gerenciar Equipe":
        from modulos.telas_equipe import renderizar_gerenciamento_equipe
        renderizar_gerenciamento_equipe(st.session_state.email_usuario)

    elif menu == "Planejamento de Eventos":
        from modulos.eventos_grandes import renderizar_gestao_eventos
        renderizar_gestao_eventos()

    elif menu == "Contratos e Demandas Internas":
        from modulos.gestao_interna import renderizar_gestao_interna
        renderizar_gestao_interna()

    elif menu == "Pipeline de Leads":
        from modulos.leads import renderizar_modulo_leads
        renderizar_modulo_leads()

    elif menu == "Totem de Vendas Express":
        from modulos.totem import renderizar_totem
        renderizar_totem()
