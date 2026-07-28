import streamlit as st
import sqlite3
from datetime import datetime

# --- IMPORTAÇÕES DOS MÓDULOS INTERNOS ---
from modulos.precificacao import renderizar_aba_precificacao
from modulos.fluxo_caixa import renderizar_aba_fluxo_caixa, salvar_lancamento
from database.conexao_db import inicializar_banco_dados
from modulos.equipe import verificar_credenciais
from modulos.telas_equipe import renderizar_tela_troca_senha, renderizar_gerenciamento_equipe
from modulos.totem import renderizar_totem  
from modulos.eventos_grandes import renderizar_gestao_eventos  
from modulos.gestao_interna import renderizar_gestao_interna  
from modulos.dashboard import renderizar_dashboard_geral        
from modulos.leads import renderizar_modulo_leads

# Garante que o banco de dados e as tabelas principais existam ao iniciar
inicializar_banco_dados()

st.set_page_config(page_title="Plataforma VP — Farmácia Jr.", page_icon="🦩", layout="wide")

# --- CUSTOMIZAÇÃO VISUAL: IDENTIDADE DA VP COM CONTRASTE PERFEITO ---
st.markdown("""
    <style>
        /* Define o fundo de toda a aplicação como claro/branco */
        .stApp {
            background-color: #FAFAFA !important;
            color: #333333 !important;
        }

        /* Menu lateral (Sidebar): Tom rosa vibrante elegante para dar leitura perfeita */
        [data-testid="stSidebar"] {
            background-color: #FFF0F5 !important;
            border-right: 2px solid #FFB6C1 !important;
        }

        /* Força a cor dos textos e labels do menu lateral para escuro/legível */
        [data-testid="stSidebar"] *, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span {
            color: #4A154B !important;
            font-weight: 600 !important;
        }

        /* Cor dos botões principais */
        div.stButton > button:first-child {
            background-color: #FF69B4 !important;
            color: white !important;
            border-radius: 8px !important;
            border: none !important;
            font-weight: bold !important;
        }
        div.stButton > button:first-child:hover {
            background-color: #FF1493 !important;
            color: white !important;
        }

        /* Customização dos links e títulos */
        h1, h2, h3, h4 {
            color: #C71585 !important;
        }

        /* Customização das abas superiores (Tabs) */
        button[data-baseweb="tab"] {
            color: #555555 !important;
            font-weight: bold !important;
        }
        button[aria-selected="true"] {
            color: #FF1493 !important;
            border-bottom-color: #FF1493 !important;
        }
    </style>
""", unsafe_allow_html=True)

# Inicializa as variáveis de controle de sessão do Streamlit
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
# --- FLUXO DE TELA 1: SE NÃO ESTIVER LOGADO ---
# =======================================================================
if not st.session_state.logado:
    st.title("🦩 Login - Plataforma Financeira da Farmácia Jr.")
    st.caption("Qualquer membro com e-mail @farmaciajr.com possui auto-cadastro liberado no primeiro acesso.")
    
    with st.container():
        email_input = st.text_input("E-mail Institucional:")
        senha_input = st.text_input("Senha:", type="password")
        botao_login = st.button("Entrar no Sistema")
        
        if botao_login:
            if email_input and senha_input:
                email_ajustado = email_input.strip().lower()
                checagem = verificar_credenciais(email_ajustado, senha_input)
                
                if checagem["sucesso"]:
                    st.session_state.logado = True
                    st.session_state.email_usuario = email_ajustado
                    st.session_state.nome_usuario = checagem["nome"]
                    st.session_state.primeiro_login = checagem["primeiro_login"]
                    st.session_state.departamento_usuario = checagem.get("departamento", "Geral")
                    st.rerun()
                else:
                    st.error(checagem["mensagem"])
            else:
                st.error("Por favor, preencha todos os campos para fazer o login.")

# =======================================================================
# --- FLUXO DE TELA 2: PRIMEIRO ACESSO OBRIGATÓRIO (TROCA DE SENHA) ---
# =======================================================================
elif st.session_state.logado and st.session_state.primeiro_login == 1:
    conn = sqlite3.connect('database/financeiro_v2.db')
    cursor = conn.cursor()
    cursor.execute("SELECT primeiro_login FROM usuarios WHERE email = ?", (st.session_state.email_usuario,))
    status_atual = cursor.fetchone()[0]
    conn.close()
    
    if status_atual == 1:
        renderizar_tela_troca_senha(st.session_state.email_usuario)
    else:
        st.session_state.primeiro_login = 0
        st.rerun()

# =======================================================================
# --- FLUXO DE TELA 3: HOME PRINCIPAL COM MENU DINÂMICO PROTEGIDO ---
# =======================================================================
else:
    st.sidebar.markdown("<h2 style='color: #FF1493;'>🦩 Setor VP</h2>", unsafe_allow_html=True)
    st.sidebar.title(f"Olá, {st.session_state.nome_usuario}!")
    st.sidebar.markdown(f"**Setor:** {st.session_state.departamento_usuario}")
    st.sidebar.markdown("---")
    
    # Menu básico reduzido para membros comuns
    opcoes_menu = ["Totem de Vendas Express", "Planejamento de Eventos"]
    
    # Menu executivo completo liberado para VP e Presidência
    if st.session_state.departamento_usuario in ["VP", "Presidência"] or st.session_state.email_usuario in ["vice-presidencia@farmaciajr.com", "presidencia@farmaciajr.com"]:
        opcoes_menu = [
            "Dashboard Geral", 
            "Fluxo de Caixa", 
            "Planejamento de Eventos", 
            "Contratos e Demandas Internas", 
            "Pipeline de Leads",
            "Calculadora de Precificação", 
            "Totem de Vendas Express", 
            "Gerenciar Equipe"
        ]

    menu = st.sidebar.radio("Navegar por Funções:", opcoes_menu)

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 Sair / Logout"):
        st.session_state.logado = False
        st.session_state.email_usuario = ""
        st.session_state.nome_usuario = ""
        st.session_state.primeiro_login = 1
        st.session_state.departamento_usuario = "Geral"
        st.rerun()

    # --- CONTROLADOR ESTRUTURADO DE EXIBIÇÃO DE PÁGINAS ---
    if menu == "Dashboard Geral":
        renderizar_dashboard_geral()
        
    elif menu == "Calculadora de Precificação":
        renderizar_aba_precificacao()
        
    elif menu == "Fluxo de Caixa":
        renderizar_aba_fluxo_caixa()
        
    elif menu == "Gerenciar Equipe":
        renderizar_gerenciamento_equipe(st.session_state.email_usuario)
        
    elif menu == "Planejamento de Eventos":
        renderizar_gestao_eventos()
        
    elif menu == "Contratos e Demandas Internas":
        renderizar_gestao_interna()
        
    elif menu == "Pipeline de Leads":
        renderizar_modulo_leads()
        
    elif menu == "Totem de Vendas Express":
        renderizar_totem()
