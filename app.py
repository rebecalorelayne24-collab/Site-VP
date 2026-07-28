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

# Garante a inicialização do banco de dados unificado
inicializar_banco_dados()

st.set_page_config(
    page_title="Plataforma VP — Farmácia Jr.",
    page_icon="🦩",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- DESIGN SYSTEM: ROSA PASTEL SOFT + BARRA LATERAL ROSA COM TEXTO BRANCO ---
st.markdown(
    """
    <style>
        /* 1. FUNDO DA PÁGINA CLARO E REPOUSANTE */
        html, body, [data-testid="stAppViewContainer"] {
            background-color: #FFF5F7 !important;
            color: #2D2D2D !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        }

        /* 2. BARRA LATERAL (SIDEBAR): ROSA VIBRANTE E ELEGANTE */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #E75480 0%, #C71585 100%) !important;
            border-right: none !important;
            box-shadow: 3px 0 10px rgba(0,0,0,0.05);
        }

        /* Textos e Rótulos da Sidebar em BRANCO PURO */
        [data-testid="stSidebar"] *, 
        [data-testid="stSidebar"] label, 
        [data-testid="stSidebar"] span,
        [data-testid="stSidebar"] p {
            color: #FFFFFF !important;
            font-weight: 500 !important;
        }

        /* Itens de Navegação do Menu */
        [data-testid="stSidebar"] div[role="radiogroup"] > label {
            background-color: rgba(255, 255, 255, 0.15) !important;
            padding: 10px 14px !important;
            border-radius: 10px !important;
            margin-bottom: 6px !important;
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            transition: all 0.2s ease-in-out !important;
        }

        [data-testid="stSidebar"] div[role="radiogroup"] > label:hover {
            background-color: rgba(255, 255, 255, 0.25) !important;
        }

        /* Item Selecionado no Menu (Destaque em Branco) */
        [data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] {
            background-color: #FFFFFF !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1) !important;
            border: none !important;
        }

        [data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] span {
            color: #C71585 !important;
            font-weight: bold !important;
        }

        /* 3. CAIXAS DE ENTRADA (INPUTS DE LOGIN COM FUNDO BRANCO LIMPO) */
        div[data-baseweb="input"] {
            background-color: #FFFFFF !important;
            border-radius: 10px !important;
        }

        div[data-baseweb="input"] > div {
            background-color: #FFFFFF !important;
            border: 1.5px solid #FFB6C1 !important;
            border-radius: 10px !important;
        }

        div[data-baseweb="input"] input {
            color: #333333 !important;
            background-color: #FFFFFF !important;
            -webkit-text-fill-color: #333333 !important;
        }

        div[data-baseweb="input"] > div:focus-within {
            border-color: #E75480 !important;
            box-shadow: 0 0 0 3px rgba(231, 84, 128, 0.2) !important;
        }

        /* 4. BOTÕES PRINCIPAIS */
        div.stButton > button {
            background: linear-gradient(90deg, #FF69B4 0%, #E75480 100%) !important;
            color: #FFFFFF !important;
            border-radius: 10px !important;
            border: none !important;
            font-weight: 600 !important;
            padding: 10px 24px !important;
            box-shadow: 0 4px 10px rgba(231, 84, 128, 0.25) !important;
            width: 100% !important;
        }

        div.stButton > button:hover {
            background: linear-gradient(90deg, #E75480 0%, #C71585 100%) !important;
        }

        /* 5. TÍTULOS */
        h1, h2, h3 {
            color: #C71585 !important;
            font-weight: 700 !important;
        }

        /* Abas Superiores (Tabs) */
        button[data-baseweb="tab"] {
            color: #555555 !important;
            font-weight: 600 !important;
        }
        button[aria-selected="true"] {
            color: #E75480 !important;
            border-bottom-color: #E75480 !important;
        }
    </style>
""",
    unsafe_allow_html=True,
)

# Inicialização das Variáveis de Sessão
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
# --- TELA 1: LOGIN AMIGÁVEL ---
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
            "<p style='text-align: center; color: #666;'>Farmácia Jr. — Gestão Financeira & Operacional</p>",
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
                st.error("Por favor, preencha o e-mail e a senha para entrar.")

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
# --- TELA 3: PAINEL PRINCIPAL ---
# =======================================================================
else:
    st.sidebar.markdown(
        "<h2 style='color: #FFFFFF !important; margin-bottom: 0px;'>🦩 Setor VP</h2>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        f"<p style='color: #FFFFFF !important;'><b>Olá, {st.session_state.nome_usuario}!</b></p>",
        unsafe_allow_html=True,
    )
    st.sidebar.markdown(
        f"<small style='color: #FFE4E1 !important;'>Setor: {st.session_state.departamento_usuario}</small>",
        unsafe_allow_html=True,
    )
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
