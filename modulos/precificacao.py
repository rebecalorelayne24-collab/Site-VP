import io
import json
import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import docx
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from google import genai
import pandas as pd
from pypdf import PdfReader
import streamlit as st

FUSO_BR = ZoneInfo("America/Sao_Paulo")

# Tabela oficial de preços base da Farmácia Jr. atualizada
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
    """Calcula a data final pulando sábados e domingos automaticamente."""
    data_atual = data_inicial
    dias_contados = 0
    while dias_contados < dias_uteis:
        data_atual += timedelta(days=1)
        if data_atual.weekday() < 5:  # Segunda a sexta-feira
            dias_contados += 1
    return data_atual


def extrair_valor_por_regex(texto):
    """Procura padrões de valores em R$ no texto do PDF sem gastar cota de IA."""
    padroes = [
        r"(?:total|valor total|total a pagar|subtotal|valor geral|valor)[\s\:\=]*r\$\s*([\d\.\,]+)",
        r"r\$\s*([\d\.\,]+)",
    ]
    for padrao in padroes:
        matches = re.findall(padrao, texto, re.IGNORECASE)
        for match in matches:
            val_str = match.strip()
            if "," in val_str and "." in val_str:
                val_str = val_str.replace(".", "").replace(",", ".")
            elif "," in val_str:
                val_str = val_str.replace(",", ".")
            try:
                val_num = float(val_str)
                if val_num > 0:
                    return val_num
            except ValueError:
                continue
    return None


def extrair_valor_pdf_com_ia(arquivo_pdf):
    """Extrai o valor bruto do PDF usando primeiro Regex (grátis) e Gemini (se necessário)."""
    try:
        # 1. Tenta extração direta via PyPDF + Regex primeiro (Sem gasto de API)
        arquivo_pdf.seek(0)
        reader = PdfReader(arquivo_pdf)
        texto_completo = ""
        for page in reader.pages:
            t = page.extract_text()
            if t:
                texto_completo += t + "\n"

        texto_limpo = texto_completo.strip()

        if len(texto_limpo) > 10:
            val_regex = extrair_valor_por_regex(texto_limpo)
            if val_regex and val_regex > 0:
                return val_regex

        # 2. Se o Regex não achou, consulta a IA via Gemini API
        api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get(
            "GEMINI_API_KEY"
        )
        if api_key:
            api_key = str(api_key).strip().strip('"').strip("'")

        if not api_key:
            st.warning("⚠️ API Key do Gemini não configurada nos Secrets.")
            return None

        client = genai.Client(api_key=api_key)

        prompt = """
        Você é a inteligência financeira da Farmácia Jr. (UFMG). 
        Analise o texto do orçamento do laboratório e extraia o VALOR TOTAL BRUTO do serviço.
        Retorne ESTRITAMENTE um JSON no seguinte formato:
        {"valor_total": 0.00}
        """

        # Usa o modelo padrão mais leve para economizar cota de RPT
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=f"{prompt}\n\nTexto do PDF:\n{texto_limpo}",
        )

        resp_txt = (
            response.text.strip().replace("```json", "").replace("```", "")
        )
        dados_ia = json.loads(resp_txt)
        return float(dados_ia.get("valor_total", 0.0))

    except Exception as e:
        erro_str = str(e)
        if "429" in erro_str or "RESOURCE_EXHAUSTED" in erro_str:
            st.warning(
                "⏳ Limite de requisições por minuto da IA atingido. "
                "Aguarde cerca de 1 minuto ou preencha o valor manualmente no campo abaixo."
            )
        else:
            st.error(f"Não foi possível ler o valor automaticamente: {e}")
        return None


def obter_texto_parcelamento(servico, valor_total):
    """Aplica as regras da planilha e calcula o valor matemático de cada parcela."""
    if servico == "Revisão Bibliográfica":
        return "Consulte o diretor"

    num_parcelas = 1
    texto_especial = None

    if servico == "Rotulagem Nutricional":
        if valor_total < 200:
            num_parcelas = 1
        elif valor_total < 600:
            num_parcelas = 2
        elif 600 <= valor_total < 800:
            num_parcelas = 3
        elif 800 <= valor_total <= 1000:
            num_parcelas = 4
        else:
            texto_especial = "Consulte o diretor"

    elif servico == "Tabela Nutricional":
        if valor_total < 200:
            num_parcelas = 1
        elif valor_total < 600:
            num_parcelas = 2
        elif 600 <= valor_total < 800:
            num_parcelas = 3
        elif 800 <= valor_total <= 1000:
            num_parcelas = 4
        else:
            texto_especial = (
                "Parcelamento Especial (Olhar com Presidência/Diretoria)"
            )

    if texto_especial:
        return texto_especial

    if num_parcelas == 1:
        return f"À vista (R$ {valor_total:,.2f})"
    else:
        valor_da_parcela = valor_total / num_parcelas
        return f"{num_parcelas} parcelas de R$ {valor_da_parcela:,.2f}"


def gerar_docx_proposta(dados):
    """Gera o documento Word (.docx) seguindo o modelo da Farmácia Jr."""
    doc = docx.Document()

    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)

    style = doc.styles["Normal"]
    font = style.font
    font.name = "Arial"
    font.size = Pt(11)

    agora = obter_agora_br()
    data_validade = calcular_data_final_uteis(agora, 15).strftime("%d/%m/%Y")

    p_val = doc.add_paragraph()
    p_val.add_run(f"Validade precificação: {data_validade}").font.size = Pt(10)

    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run_tit = p_tit.add_run(f"\nPrecificação – {dados['nome_lead']}")
    run_tit.bold = True
    run_tit.size = Pt(14)

    p_sub = doc.add_paragraph()
    p_sub.add_run(f"{dados['nome_servico'].upper()}").bold = True

    if dados["tipo_servico"] == "Serviço Autoral (Farmácia Jr.)":
        doc.add_paragraph().add_run("1° opção – Precificação cheia").bold = True

        table1 = doc.add_table(rows=2, cols=4)
        table1.style = "Table Grid"
        hdr = table1.rows[0].cells
        hdr[0].text, hdr[1].text, hdr[2].text, hdr[3].text = (
            "Serviços",
            "Valor unitário",
            "Quantidade proposta",
            "Total",
        )

        row1 = table1.rows[1].cells
        row1[0].text = dados["nome_servico"]
        row1[1].text = f"R$ {dados['valor_base']:.2f}"
        row1[2].text = str(dados["quantidade"])
        row1[3].text = f"R$ {dados['total_cheio']:.2f}"

        doc.add_paragraph(
            f"\nPrazo de execução: {dados['prazo']} dias úteis (Previsão de"
            f" entrega: {dados['data_entrega_autoral']})"
        )
        doc.add_paragraph(
            f"Formas de pagamento: {dados['parcelas_cheio']}"
        )

        doc.add_paragraph().add_run(
            f"\n2° opção – desconto de acordo [{dados['motivo_desconto']}]"
        ).bold = True

        table2 = doc.add_table(rows=2, cols=4)
        table2.style = "Table Grid"
        hdr2 = table2.rows[0].cells
        hdr2[0].text, hdr2[1].text, hdr2[2].text, hdr2[3].text = (
            "Serviços",
            "Valor unitário",
            "Quantidade proposta",
            "Total",
        )

        row2 = table2.rows[1].cells
        row2[0].text = dados["nome_servico"]
        row2[1].text = f"R$ {dados['unitario_desconto']:.2f}"
        row2[2].text = str(dados["quantidade"])
        row2[3].text = f"R$ {dados['total_desconto']:.2f}"

        doc.add_paragraph(
            f"\nPrazo de execução: {dados['prazo']} dias úteis (Previsão de"
            f" entrega: {dados['data_entrega_autoral']})"
        )
        doc.add_paragraph(
            f"Formas de pagamento: {dados['parcelas_desconto']}"
        )

    else:
        doc.add_paragraph().add_run("1° opção – Precificação cheia").bold = True

        table3 = doc.add_table(rows=2, cols=4)
        table3.style = "Table Grid"
        hdr3 = table3.rows[0].cells
        hdr3[0].text, hdr3[1].text, hdr3[2].text, hdr3[3].text = (
            "Serviços",
            "Valor unitário",
            "Quantidade proposta",
            "Total",
        )

        row3 = table3.rows[1].cells
        row3[0].text = dados["nome_servico"]
        row3[1].text = f"R$ {dados['total_terceirizado']:.2f}"
        row3[2].text = "1"
        row3[3].text = f"R$ {dados['total_terceirizado']:.2f}"

        doc.add_paragraph(
            f"\nPrazo de execução: {dados['prazo_terceirizado']} dias (Incluso"
            " prazo de segurança da EJ. Previsão:"
            f" {dados['data_entrega_terc']})"
        )
        doc.add_paragraph(
            f"Formas de pagamento: {dados['parcelas_terceirizado']}"
        )

        p_param = doc.add_paragraph()
        p_param.add_run("Parâmetros analisados:\n").bold = True
        p_param.add_run(dados["parametros"])

        p_met = doc.add_paragraph()
        p_met.add_run("\nMetodologia:\n").bold = True
        p_met.add_run(dados["metodologia"])

        doc.add_paragraph(f"\nValor da coleta: {dados['txt_coleta']}")

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer


def renderizar_aba_precificacao():
    st.title("🦩 Calculadora de Precificação Comercial Inteligente")

    st.markdown(
        """
        <div style="background-color: #FFF0F5; padding: 15px; border-left: 5px solid #FF69B4; border-radius: 4px; margin-bottom: 20px;">
            <span style="color: #FF1493; font-weight: bold;">⚠️ DIRETRIZ INTERNA DA VICE-PRESIDÊNCIA:</span><br>
            O prazo de entrega de uma precificação de um <b>serviço autoral</b> para negócios é de no máximo <b>2 dias úteis</b>.<br>
            Já em caso de <b>serviço laboratorial (terceirizado)</b> não podemos exceder o prazo máximo de <b>5 dias úteis</b> para envio ao lead.
        </div>
    """,
        unsafe_allow_html=True,
    )

    nome_lead = st.text_input(
        "Nome do Lead / Empresa:", placeholder="Ex: Mika Doces Artesanais"
    )
    tipo_servico = st.selectbox(
        "Modalidade do Serviço:",
        [
            "Serviço Autoral (Farmácia Jr.)",
            "Serviço Terceirizado (Laboratório)",
        ],
    )

    dados_calculados = {}
    agora = obter_agora_br()

    if tipo_servico == "Serviço Autoral (Farmácia Jr.)":
        col1, col2 = st.columns(2)
        with col1:
            nome_servico = st.selectbox(
                "Serviço Autoral:", list(PRECOS_AUTORAIS.keys())
            )
            valor_base = PRECOS_AUTORAIS[nome_servico]
            st.info(
                f"💰 Valor de tabela fixado pelo setor: **R$ {valor_base:,.2f}**"
            )
            quantidade = st.number_input(
                "Quantidade (Nº de Rótulos / Tabelas / Produtos):",
                min_value=1,
                value=1,
            )
        with col2:
            if nome_servico == "Rotulagem Nutricional":
                prazo = quantidade * 10 if quantidade <= 1 else quantidade * 6
            elif nome_servico == "Tabela Nutricional":
                prazo = quantidade * 7 if quantidade <= 1 else quantidade * 4
            elif nome_servico == "Revisão Bibliográfica":
                prazo = quantidade * 60
            else:
                prazo = quantidade * 5

            st.info(f"📅 Prazo de execução calculado: **{prazo} dias úteis**")

            total_cheio = valor_base * quantidade
            parcelas_cheio = obter_texto_parcelamento(
                nome_servico, total_cheio
            )
            st.info(f"💳 Condição de Pagamento (Cheio): **{parcelas_cheio}**")

        data_entrega = calcular_data_final_uteis(agora, prazo).strftime(
            "%d/%m/%Y"
        )

        st.markdown(
            "<h4 style='color: #FF1493;'>🔍 Seleção de Descontos (Limite Máximo"
            " de 15%)</h4>",
            unsafe_allow_html=True,
        )

        c1, c2, c3 = st.columns(3)
        desc_me = c1.checkbox("Microempreendedor com CNPJ (2.5%)")
        desc_nova = c1.checkbox("Empresa nova no mercado (2.5%)")
        desc_antigo = c1.checkbox("Cliente antigo da EJ (5.0%)")
        desc_novo_cli = c2.checkbox("Primeira compra / Novo cliente (1.25%)")
        desc_mulher = c2.checkbox("Liderança feminina / Mulheres (1.75%)")
        desc_combo = c2.checkbox("Combo / Mais de um serviço (5.0%)")
        desc_qtd = c3.checkbox("Quantidade progressiva de produtos (5.0%)")
        desc_indica = c3.checkbox("Lead por indicação de cliente (5.0%)")
        desc_ufmg = c3.checkbox("Ex-aluno ou familiar UFMG (2.5%)")

        soma_descontos = 0
        motivos = []
        if desc_me:
            soma_descontos += 2.5
            motivos.append("Microempreendedor")
        if desc_nova:
            soma_descontos += 2.5
            motivos.append("Empresa Nova")
        if desc_antigo:
            soma_descontos += 5.0
            motivos.append("Cliente Antigo")
        if desc_novo_cli:
            soma_descontos += 1.25
            motivos.append("Novo Cliente")
        if desc_mulher:
            soma_descontos += 1.75
            motivos.append("Líderes Mulheres")
        if desc_combo:
            soma_descontos += 5.0
            motivos.append("Mais de um Serviço")
        if desc_qtd:
            soma_descontos += 5.0
            motivos.append("Quantidade de Produto")
        if desc_indica:
            soma_descontos += 5.0
            motivos.append("Indicação")
        if desc_ufmg:
            soma_descontos += 2.5
            motivos.append("Ex-aluno UFMG")

        desconto_final_pct = min(soma_descontos, 15.0)
        motivo_txt = (
            ", ".join(motivos) if motivos else "Critérios de elegibilidade"
        )

        total_desconto = total_cheio * (1 - (desconto_final_pct / 100))
        unitario_desconto = total_desconto / quantidade

        parcelas_desconto = obter_texto_parcelamento(
            nome_servico, total_desconto
        )

        st.markdown(
            f"**Soma dos descontos:** {soma_descontos:.2f}% | **Desconto real"
            " aplicado (Limite de 15%):** <span style='color:#FF1493;"
            f" font-weight:bold;'>{desconto_final_pct:.2f}%</span>",
            unsafe_allow_html=True,
        )

        st.markdown("---")
        card1, card2 = st.columns(2)
        card1.metric(
            "Opção 1: Preço Cheio",
            f"R$ {total_cheio:,.2f}",
            f"{parcelas_cheio}",
        )
        card2.metric(
            "Opção 2: Preço com Desconto",
            f"R$ {total_desconto:,.2f}",
            f"{parcelas_desconto}",
        )

        dados_calculados = {
            "nome_lead": nome_lead,
            "tipo_servico": tipo_servico,
            "nome_servico": nome_servico,
            "valor_base": valor_base,
            "quantidade": quantidade,
            "total_cheio": total_cheio,
            "prazo": prazo,
            "data_entrega_autoral": data_entrega,
            "parcelas_cheio": parcelas_cheio,
            "parcelas_desconto": parcelas_desconto,
            "motivo_desconto": motivo_txt,
            "unitario_desconto": unitario_desconto,
            "total_desconto": total_desconto,
        }

    else:
        # --- CENÁRIO TERCEIRIZADO ---
        st.markdown(
            "<h4 style='color: #FF1493;'>📂 Upload do Orçamento do"
            " Laboratório</h4>",
            unsafe_allow_html=True,
        )
        arquivo_pdf = st.file_uploader(
            "Arraste o arquivo PDF do laboratório parceiro aqui:",
            type=["pdf"],
            key="file_pdf_lab",
        )

        val_auto_detectado = 0.0

        if arquivo_pdf is not None:
            with st.spinner("🤖 Processando arquivo de orçamento..."):
                val_extraido = extrair_valor_pdf_com_ia(arquivo_pdf)
                if val_extraido is not None and val_extraido > 0:
                    val_auto_detectado = val_extraido
                    st.success(
                        "✅ Sucesso! Valor do laboratório identificado: **R$"
                        f" {val_auto_detectado:,.2f}**"
                    )

        orcamento_lab = st.number_input(
            "Valor do Orçamento do Laboratório (R$):",
            min_value=0.0,
            value=float(val_auto_detectado),
            step=50.0,
        )

        col1, col2 = st.columns(2)
        with col1:
            nome_servico = st.text_input(
                "Nome do Serviço Laboratorial:",
                value="Análise Microbiológica de Água",
            )
        with col2:
            prazo_lab = st.number_input(
                "Prazo original dado pelo laboratório (em dias corridos):",
                min_value=1,
                value=7,
            )
            coleta_opcao = st.radio(
                "Serviço de Coleta:",
                [
                    "Não oferecido (Amostra por conta do cliente)",
                    "Oferecido pela Farmácia Jr.",
                ],
            )
            valor_coleta = (
                st.number_input(
                    "Valor da Coleta (R$):", min_value=0.0, value=0.0
                )
                if "Oferecido" in coleta_opcao
                else 0.0
            )

        parametros = st.text_area(
            "Parâmetros analisados:",
            value=(
                "Presença/Ausência de bactérias do grupo Coliformes Totais e"
                " Termotolerantes (E. coli)."
            ),
        )
        metodologia = st.text_area(
            "Metodologia aplicada:",
            value=(
                "Contagem de bactérias heterotróficas conforme padrões"
                " laboratoriais."
            ),
        )

        # Matemática da planilha: = B4 + 110 + 0.18*(B4 + 110)
        margem_fixa_setor = 110.00
        subtotal_terc = orcamento_lab + margem_fixa_setor
        taxas_de_nota = subtotal_terc * 0.18
        total_terceirizado = subtotal_terc + taxas_de_nota

        prazo_final_terc = int(round(prazo_lab + 20, 0))
        data_entrega_terc = (agora + timedelta(days=prazo_final_terc)).strftime(
            "%d/%m/%Y"
        )

        parcelas_terceirizado = obter_texto_parcelamento(
            "Tabela Nutricional", total_terceirizado
        )

        txt_coleta = (
            f"R$ {valor_coleta:,.2f}"
            if "Oferecido" in coleta_opcao
            else (
                "não é oferecido o serviço de coleta ficando a critério do"
                " cliente a disponibilização da amostra."
            )
        )

        st.markdown("---")
        st.metric(
            "Opção Única Terceirizada (Cálculo Automático)",
            f"R$ {total_terceirizado:,.2f}",
            f"Prazo com segurança: {prazo_final_terc} dias corridos",
        )
        st.info(
            "💳 Condição de Pagamento Calculada:"
            f" **{parcelas_terceirizado}**"
        )
        st.info(
            "📅 Previsão exata de entrega para o cliente final:"
            f" **{data_entrega_terc}**"
        )

        dados_calculados = {
            "nome_lead": nome_lead,
            "tipo_servico": tipo_servico,
            "nome_servico": nome_servico,
            "total_terceirizado": total_terceirizado,
            "prazo_terceirizado": prazo_final_terc,
            "data_entrega_terc": data_entrega_terc,
            "parametros": parametros,
            "metodologia": metodologia,
            "txt_coleta": txt_coleta,
            "parcelas_terceirizado": parcelas_terceirizado,
        }

    if nome_lead:
        st.markdown("---")
        arquivo_word = gerar_docx_proposta(dados_calculados)
        st.download_button(
            label=(
                "📥 Gerar e Baixar Documento de Precificação Oficial (.docx)"
            ),
            data=arquivo_word,
            file_name=f"Precificação - {nome_lead}.docx",
            mime=(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            ),
            use_container_width=True,
        )
    else:
        st.warning(
            "⚠️ Insira o nome do Lead no início da página para habilitar a"
            " geração do documento Word."
        )
