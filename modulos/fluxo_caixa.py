import io
import json
import os
import sqlite3
from datetime import datetime

import google.generativeai as genai
import pandas as pd
from pypdf import PdfReader
import streamlit as st

DB_PATH = "database/financeiro_v2.db"


def garantir_colunas_documentacao():
    """Garante a existência da tabela fluxo_caixa_geral no banco de dados."""
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


def salvar_lancamento(
    mes,
    data,
    depto,
    tipo,
    cat,
    desc,
    v_bruto,
    v_taxa,
    v_liq,
    conta,
    pagamento,
    nf,
    onvio,
):
    """Insere um novo lançamento no fluxo de caixa."""
    garantir_colunas_documentacao()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO fluxo_caixa_geral (
            mes, data, departamento, tipo, categoria, descricao, 
            valor_bruto, taxa, valor_liquido, conta_origem, 
            status_pagamento, nota_fiscal, status_onvio
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            mes,
            data,
            depto,
            tipo,
            cat,
            desc,
            v_bruto,
            v_taxa,
            v_liq,
            conta,
            pagamento,
            nf,
            onvio,
        ),
    )
    conn.commit()
    conn.close()


def ler_extrato_com_gemini(texto_pdf):
    """Realiza a leitura do extrato em texto com fallbacks para os modelos ativos."""
    api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")

    if not api_key:
        st.error("⚠️ Chave GEMINI_API_KEY não encontrada nos Secrets do Streamlit Cloud.")
        return []

    if not texto_pdf or len(texto_pdf.strip()) < 10:
        st.warning("⚠️ O PDF parece estar sem texto editável.")
        return []

    try:
        genai.configure(api_key=api_key)

        prompt = f"""
        Você é um assistente financeiro da Farmácia Jr. (UFMG).
        Analise o texto deste extrato bancário e extraia TODOS os lançamentos válidos de entrada e saída.
        Ignore linhas de saldos ou rendimentos informativos.

        Retorne obrigatoriamente uma lista JSON no formato puro:
        [
            {{"data": "2026-03-15", "tipo": "Receita", "descricao": "PIX RECEBIDO - JOAO SILVA", "valor_bruto": 150.00}},
            {{"data": "2026-03-16", "tipo": "Despesa", "descricao": "COMPRA DE JALECOS", "valor_bruto": 450.50}}
        ]

        Regras:
        - data: YYYY-MM-DD
        - tipo: "Receita" ou "Despesa"
        - valor_bruto: número float positivo

        Texto do extrato:
        {texto_pdf}
        """

        # Modelos com identificadores de versão suportados no SDK atual
        modelos_validos = [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash-latest",
            "gemini-1.5-flash-002"
        ]

        resposta_texto = None
        ultimo_erro = None

        for m in modelos_validos:
            try:
                model = genai.GenerativeModel(m)
                res = model.generate_content(prompt)
                if res and res.text:
                    resposta_texto = res.text.strip()
                    break
            except Exception as err:
                ultimo_erro = err
                continue

        if not resposta_texto:
            st.error(f"⚠️ Erro ao comunicar com a API do Gemini: {ultimo_erro}")
            return []

        if "```" in resposta_texto:
            partes = resposta_texto.split("
