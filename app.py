import os
import sqlite3
from datetime import datetime
import streamlit as st
import google.generativeai as genai

# --- CONFIGURAÇÃO SEGURA DA API DO GEMINI ---
api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")

if api_key:
    os.environ["GEMINI_API_KEY"] = api_key
    genai.configure(api_key=api_key)

# --- IMPORTAÇÕES DOS MÓDULOS INTERNOS ---
from database.conexao_db import inicializar_banco_dados
from modulos.dashboard import renderizar_dashboard_geral
from modulos.equipe import verificar_credenciais
from modulos.eventos_grandes import renderizar_gestao_eventos
from modulos.fluxo_caixa import renderizar_aba_fluxo_caixa, salvar_lancamento
from modulos.gestao_interna import renderizar_gestao_interna
from modulos.leads import renderizar_modulo_leads
from modulos.precificacao import renderizar_aba_precificacao
from modulos.telas_equipe import (
    renderizar_gerenciamento_equipe,
    renderizar_tela_troca_senha,
)
from modulos.totem import renderizar_totem

# Garante a inicialização do banco de dados
inicializar_banco_dados()

st.set_page_config(
    page_title="Plataforma VP — Farmácia Jr.",
    page_icon="🦩",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- DESIGN SYSTEM EXCLUSIVO (UI/UX AJUSTADO & CONTRASTE PERFEITO) ---
st.markdown(
    """
    <style>
        /* 1. CONFIGURAÇÃO GERAL DA PÁGINA */
        html, body, [data-testid="stAppViewContainer"] {
            background-color: #F8F9FA !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif !important;
            color: #212529 !important;
        }

        /* 2. BARRA LATERAL (SIDEBAR ELEGANTE) */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #4A122E 0%, #2D0B1C 100%) !important;
            border-right: 1px solid #E9ECEF !important;
            box-shadow: 2px 0 12px rgba(0,0,0,0.05);
        }

        /* Textos e títulos da Sidebar */
        [data-testid="stSidebar"] *, 
        [data-testid="stSidebar"] label, 
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] p {
            color: #F8F9FA !important;
            font-size: 0.95rem !important;
        }

        /* Itens de navegação da Sidebar */
        [data-testid="stSidebar"] div[role="radiogroup"] > label {
            background-color: rgba(255, 255, 255, 0.05) !important;
            padding: 10px 14px !important;
            border-radius: 8px !important;
            margin-bottom: 6px !important;
            transition: all 0.2s ease-in-out !important;
            border: 1px solid rgba(255, 255, 255, 0.1) !important;
        }

        [data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
            background-color: rgba(255, 255, 255, 0.15) !important;
            transform: translateX(4px);
        }

        /* Item do menu selecionado */
        [data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] {
            background: linear-gradient(90deg, #E6007E 0%, #C71585 100%) !important;
            font-weight: bold !important;
            border: none !important;
            box-shadow: 0 4px 10px rgba(230, 0, 126, 0.3) !important;
        }

        /* 3. CAMPOS DE ENTRADA (CORREÇÃO DE FUNDO BRANCO E TEXTO ESCURO) */
        div[data-baseweb="input"] {
            background-color: #FFFFFF !important;
            border-radius: 8px !important;
        }

        div[data-baseweb="input"] > div {
            background-color: #FFFFFF !important;
            border: 1.5px solid #CED4DA !important;
            border-radius: 8px !important;
            color: #212529 !important;
        }

        div[data-baseweb="input"] input {
            color: #212529 !important;
            background-color: #FFFFFF !important;
            -webkit-text-fill-color: #212529 !important;
        }

        div[data-baseweb="input"] > div:focus-within {
            border-color: #E6007E !important;
            box-shadow: 0 0 0 3px rgba(230, 0, 126, 0.15) !important;
        }

        /* 4. BOTÕES PRINCIPAIS */
        div.stButton > button {
            background: linear-gradient(90deg, #E6007E 0%, #C71585 100%) !important;
            color: #FFFFFF !important;
            border-radius: 8px !important;
            border: none !important;
            font-weight: 600 !important;
            padding: 10px 24px !important;
            box-shadow: 0 4px 12px rgba(230, 0, 126, 0.25) !important;
            transition: all 0.2s ease-in-out !important;
            width: 100% !important;
        }

        div.stButton > button:hover {
            background: linear-gradient(90deg, #D00072 0%, #B01075 100%) !important;
            box-shadow: 0 6px 16px rgba(230, 0, 126, 0.35) !important;
            transform: translateY(-1px);
        }

        /* 5. TÍTULOS DA TELA PRINCIPAL */
        h1, h2, h3 {
            color: #2D0B1C !important;
            font-weight: 700 !important;
            letter-spacing: -0.5px !important;
        }

        .stCaption {
            color: #6C757D !important;
        }

        /* Abas superiors (Tabs) */
        button[data-baseweb="tab"] {
            color: #495057 !important;
            font-weight: 600 !important;
        }
        button[aria-selected="true"] {
            color: #E6007E !important;
            border-bottom-color: #E6007E !important;
        }
    </style>
""",
    unsafe_allow_html=True,
)

# Inicializa as variáveis de sessão
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
# --- TELA 1: LOGIN AMIGÁVEL E CLEAN ---
# =======================================================================
if not st.session_state.logado:
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown(
            "<h1 style='text-align: center;'>🦩 Plataforma VP</h1>",
            unsafe_allow_html=True,
        )
        st.markdown(
            "<p style='text-align: center; color: #6C757D;'>Farmácia Jr. —"
            " Gestão Financeira & Operacional</p>",
            unsafe_allow_html=True,
        )
        st.markdown("---")

        email_input = st.text_input(
            "E-mail Institucional:", placeholder="seu-email@farmaciajr.com"
        )
        senha_input = st.text_input(
            "Senha:", type="password", placeholder="••••••••"
        )

        st.markdown("<br>", unsafe_allow_html=True)
        botao_login = st.button("Acessar Plataforma")

        if botao_login:
            if email_input and senha_input:
                email_ajustado = email_input.strip().lower()
                checagem = verificar_credenciais(email_ajustado, senha_input)

                if checagem["sucesso"]:
                    st.session_state.logado = True
                    st.session_state.email_usuario = email_ajustado
                    st.session_state.nome_usuario = checagem["nome"]
                    st.session_state.primeiro_login = checagem["primeiro_login"]
                    st.session_state.departamento_usuario = checagem.get(
                        "departamento", "Geral"
                    )
                    st.rerun()
                else:
                    st.error(checagem["mensagem"])
            else:
                st.error(
                    "Por favor, informe seu e-mail e sua senha para entrar."
                )

# =======================================================================
# --- TELA 2: TROCA DE SENHA (PRIMEIRO ACESSO) ---
# =======================================================================
elif st.session_state.logado and st.session_state.primeiro_login == 1:
    conn = sqlite3.connect("database/financeiro_v2.db")
    cursor = conn.cursor()
    cursor.execute(
        "SELECT primeiro_login FROM usuarios WHERE email = ?",
        (st.session_state.email_usuario,),
    )
    resultado = cursor.fetchone()
    conn.close()

    status_atual = resultado[0] if resultado else 0

    if status_atual == 1:
        renderizar_tela_troca_senha(st.session_state.email_usuario)
    else:
        st.session_state.primeiro_login = 0
        st.rerun()

# =======================================================================
# --- TELA 3: PAINEL PRINCIPAL DA PLATAFORMA ---
# =======================================================================
else:
    # Sidebar Superior
    st.sidebar.markdown(
        "<h2 style='color: #FFFFFF; margin-bottom: 0px;'>🦩 Setor VP</h2>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        "<p style='color: #E6007E !important; font-weight: bold;'>Olá,"
        f" {st.session_state.nome_usuario}!</p>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        "<small style='color: #ADB5BD;'>Setor:"
        f" {st.session_state.departamento_usuario}</small>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        "<hr style='border-color: rgba(255,255,255,0.1);'>",
        unsafe_allow_html=True,
    )

    # Opções do Menu
    opcoes_menu = ["Totem de Vendas Express", "Planejamento de Eventos"]

    if st.session_state.departamento_usuario in [
        "VP",
        "Presidência",
    ] or st.session_state.email_usuario in [
        "vice-presidencia@farmaciajr.com",
        "presidencia@farmaciajr.com",
    ]:
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

    st.sidebar.markdown(
        "<hr style='border-color: rgba(255,255,255,0.1);'>",
        unsafe_allow_html=True,
    )
    if st.sidebar.button("🚪 Encerrar Sessão"):
        st.session_state.logado = False
        st.session_state.email_usuario = ""
        st.session_state.nome_usuario = ""
        st.session_state.primeiro_login = 1
        st.session_state.departamento_usuario = "Geral"
        st.rerun()

    # Roteamento de Páginas
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
