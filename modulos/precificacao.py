import io
import json
import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
import google.generativeai as genai
import pandas as pd
from pypdf import PdfReader
import streamlit as st

FUSO_BR = ZoneInfo("America/Sao_Paulo")

# Tabela oficial de preços base da Farmácia Jr.
PRECOS_AUTORAIS = {
    "Rotulagem Nutricional": 130.00,
    "Tabela Nutricional": 90.00,
    "Revisão Bibliográfica": 1100.00,
    "Formulação Cosmética": 250.00,
}


def obter_agora_br():
    """Retorna a data e hora atuais no fuso horário de Brasília."""
    return datetime.now(FUSO_BR)


def calcular_data_final_uteis(data_inicial, dias_uteis):
    """Calcula a data final desconsiderando sábados e domingos."""
    data_atual = data_inicial
    dias_contados = 0
    while dias_contados < dias_uteis:
        data_atual += timedelta(days=1)
        if data_atual.weekday() < 5:  # Segunda a sexta-feira
            dias_contados += 1
    return data_atual


def extrair_valor_pdf_com_ia(arquivo_pdf):
    """Lê o PDF do orçamento do laboratório e usa Gemini para extrair o valor bruto de forma estável."""
    try:
        # Busca a API Key do Streamlit Secrets ou do ambiente do sistema
        api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get(
            "GEMINI_API_KEY"
        )
        if api_key:
            api_key = str(api_key).strip().strip('"').strip("'")

        if not api_key:
            st.error(
                "API Key do Gemini não configurada. Adicione 'GEMINI_API_KEY'"
                " nos secrets."
            )
            return None

        # Configuração da biblioteca google.generativeai
        genai.configure(api_key=api_key)

        arquivo_pdf.seek(0)
        bytes_pdf = arquivo_pdf.read()

        arquivo_pdf.seek(0)
        reader = PdfReader(arquivo_pdf)
        texto_completo = ""
        for page in reader.pages:
            texto_extraido = page.extract_text()
            if texto_extraido:
                texto_completo += texto_extraido + "\n"

        prompt = """
        Você é um auditor financeiro experiente da Farmácia Jr. (UFMG).
        Sua ÚNICA missão é analisar o documento de orçamento/proposta de laboratório anexo e identificar o VALOR TOTAL BRUTO FINAL a ser pago pelo serviço.

        INSTRUÇÕES DE PRECISÃO:
        1. Procure pela seção de Totais: 'VALOR TOTAL', 'TOTAL DO ORÇAMENTO', 'TOTAL GERAL', 'TOTAL A PAGAR', 'VALOR FINAL' ou o somatório do final do documento.
        2. IGNORE valores unitários, taxas por amostra individual, descontos condicionais ou subtotais parciais.
        3. IGNORE datas, CNPJs, CEPs, números de proposta ou telefones.
        4. Retorne ESTRITAMENTE um JSON no seguinte formato:
        {"valor_total": 0.00}
        """

        modelos_testar = [
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-flash-latest",
        ]
        resposta_texto = None

        conteudo_input = [
            prompt,
            {"mime_type": "application/pdf", "data": bytes_pdf},
        ]

        for m in modelos_testar:
            try:
                model = genai.GenerativeModel(m)
                res = model.generate_content(
                    conteudo_input,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.0
                    ),
                )
                if res and res.text:
                    resposta_texto = res.text.strip()
                    break
            except Exception:
                continue

        if not resposta_texto and len(texto_completo.strip()) > 5:
            prompt_txt = f"{prompt}\n\nTexto do Orçamento:\n{texto_completo}"
            for m in modelos_testar:
                try:
                    model = genai.GenerativeModel(m)
                    res = model.generate_content(
                        prompt_txt,
                        generation_config=genai.types.GenerationConfig(
                            temperature=0.0
                        ),
                    )
                    if res and res.text:
                        resposta_texto = res.text.strip()
                        break
                except Exception:
                    continue

        if not resposta_texto:
            return None

        # Limpeza de formatação Markdown JSON
        if "```" in resposta_texto:
            partes = resposta_texto.split("
