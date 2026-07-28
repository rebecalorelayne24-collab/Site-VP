import io
import json
import os
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

import google.generativeai as genai
import pandas as pd
from pypdf import PdfReader
import streamlit as st

DB_PATH = "database/financeiro_v2.db"
FUSO_BR = ZoneInfo("America/Sao_Paulo")


def obter_agora_br():
    """Retorna o datetime atual no fuso horário oficial de Brasília."""
    return datetime.now(FUSO_BR)


def garantir_colunas_documentacao():
    """Garante a existência da tabela e adiciona colunas faltantes dinamicamente."""
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

    cursor.execute("PRAGMA table_info(fluxo_caixa_geral)")
    colunas_existentes = [coluna[1] for coluna in cursor.fetchall()]

    colunas_necessarias = {
        "mes": "TEXT",
        "data": "TEXT",
        "departamento": "TEXT",
        "tipo": "TEXT",
        "categoria": "TEXT",
        "descricao": "TEXT",
        "valor_bruto": "REAL",
        "taxa": "REAL",
        "valor_liquido": "REAL",
        "conta_origem": "TEXT",
        "status_pagamento": "TEXT",
        "nota_fiscal": "TEXT",
        "status_onvio": "TEXT",
    }

    for coluna, tipo_dado in colunas_necessarias.items():
        if coluna not in colunas_existentes:
            cursor.execute(
                f"ALTER TABLE fluxo_caixa_geral ADD COLUMN {coluna} {tipo_dado}"
            )

    conn.commit()
    conn.close()


def obter_lista_bancos(df):
    """Retorna os bancos padrão somados aos cadastrados no banco de dados."""
    bancos_padrao = ["PicPay", "Banco do Brasil", "Caixa", "Itaú", "Nubank", "Cora", "Banco BTG"]
    if not df.empty and "conta_origem" in df.columns:
        bancos_existentes = [b for b in df["conta_origem"].dropna().unique() if b]
        for b in bancos_existentes:
            if b not in bancos_padrao:
                bancos_padrao.append(b)
    bancos_padrao.append("➕ Adicionar Novo Banco...")
    return bancos_padrao


def salvar_lancamento(
    mes, data, depto, tipo, cat, desc, v_bruto, v_taxa, v_liq, conta, pagamento, nf, onvio
):
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
        (mes, data, depto, tipo, cat, desc, v_bruto, v_taxa, v_liq, conta, pagamento, nf, onvio),
    )
    conn.commit()
    conn.close()


def salvar_lancamentos_em_lote(lista_lancamentos):
    if not lista_lancamentos:
        return

    garantir_colunas_documentacao()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    dados_tuple = [
        (
            l["mes"], l["data"], l["departamento"], l["tipo"], l["categoria"], l["descricao"],
            l["valor_bruto"], l["taxa"], l["valor_liquido"], l["conta_origem"], l["status_pagamento"],
            l["nota_fiscal"], l["status_onvio"]
        )
        for l in lista_lancamentos
    ]

    cursor.executemany(
        """
        INSERT INTO fluxo_caixa_geral (
            mes, data, departamento, tipo, categoria, descricao, 
            valor_bruto, taxa, valor_liquido, conta_origem, 
            status_pagamento, nota_fiscal, status_onvio
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        dados_tuple,
    )

    conn.commit()
    conn.close()


def ler_extrato_com_gemini(texto_pdf):
    api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if api_key:
        api_key = str(api_key).strip().strip('"').strip("'")

    if not api_key or not texto_pdf or len(texto_pdf.strip()) < 10:
        return []

    try:
        genai.configure(api_key=api_key)

        prompt = f"""
        Extraia todas as transações deste extrato bancário.
        Retorne estritamente um array JSON puro no seguinte formato:
        [
            {{"data": "2026-06-30", "tipo": "Receita", "descricao": "PIX RECEBIDO - NOME", "valor_bruto": 2.00, "banco": "PicPay"}}
        ]
        Regras:
        - data: YYYY-MM-DD
        - tipo: "Receita" ou "Despesa"
        - valor_bruto: float positivo
        - banco: Nome da instituição bancária

        Texto do extrato:
        {texto_pdf}
        """

        modelos_rapidos = ["gemini-1.5-flash-8b", "gemini-2.0-flash", "gemini-flash-latest"]
        generation_config = genai.types.GenerationConfig(temperature=0.0)

        resposta_texto = None
        for m in modelos_rapidos:
            try:
                model = genai.GenerativeModel(m)
                res = model.generate_content(prompt, generation_config=generation_config)
                if res and res.text:
                    resposta_texto = res.text.strip()
                    break
            except Exception:
                continue

        if not resposta_texto:
            return []

        if "```" in resposta_texto:
            partes = resposta_texto.split("```")
            for parte in partes:
                parte_limpa = parte.strip()
                if parte_limpa.startswith("json"):
                    parte_limpa = parte_limpa[4:].strip()
                if parte_limpa.startswith("[") and parte_limpa.endswith("]"):
                    resposta_texto = parte_limpa
                    break

        dados = json.loads(resposta_texto.strip())
        return dados if isinstance(dados, list) else []

    except Exception as e:
        st.error(f"Erro na IA: {e}")
        return []


def gerar_excel_estilizado(df_export):
    """Gera um Relatório Financeiro Executivo no Excel com destaques em Verde (Receitas) e Vermelho (Despesas)."""
    buffer = io.BytesIO()

    # Cálculos prévios para o Dashboard
    df_calc = df_export.copy()
    if not df_calc.empty:
        df_calc["valor_liquido"] = pd.to_numeric(df_calc["valor_liquido"], errors="coerce").fillna(0.0)
        tot_receitas = df_calc[df_calc["tipo"] == "Receita"]["valor_liquido"].sum()
        tot_despesas = df_calc[df_calc["tipo"] == "Despesa"]["valor_liquido"].sum()
        saldo_liquido = tot_receitas - tot_despesas
        qtd_lancamentos = len(df_calc)
        ticket_medio = (tot_receitas / len(df_calc[df_calc["tipo"] == "Receita"])) if len(df_calc[df_calc["tipo"] == "Receita"]) > 0 else 0.0
        margem_op = (saldo_liquido / tot_receitas * 100) if tot_receitas > 0 else 0.0
    else:
        tot_receitas = tot_despesas = saldo_liquido = ticket_medio = margem_op = 0.0
        qtd_lancamentos = 0

    agora = obter_agora_br()

    # Análise Financeira Automática
    if saldo_liquido > 0:
        analise_texto = f"🟢 SAÚDE FINANCEIRA EXCELENTE: A operação registra saldo positivo de R$ {saldo_liquido:,.2f} com margem operacional de {margem_op:.1f}%. A receita é suficiente para cobrir 100% dos custos operacionais."
    elif saldo_liquido == 0:
        analise_texto = "🟡 ATENÇÃO - BREAK-EVEN OPERACIONAL: O faturamento total emparelhou exatamente com os custos do período. Recomenda-se acompanhamento rigoroso."
    else:
        analise_texto = f"🔴 ALERTA DE DÉFICIT OPERACIONAL: As despesas superaram as receitas do período em R$ {abs(saldo_liquido):,.2f}. Recomenda-se contenção de despesas administrativas imediata."

    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        workbook = writer.book

        # -------------------------------------------------------------
        # 🎨 PALETA E ESTILOS PROFISSIONAIS
        # -------------------------------------------------------------
        COR_PRIMARIA = "#FF1493"      # Rosa/Magenta Farmácia Jr.
        COR_FUNDO_CAB = "#C71585"     # Magenta Escuro
        COR_VERDE_BG = "#E8F5E9"      # Verde Receita Suave
        COR_VERDE_TXT = "#2E7D32"     # Verde Texto
        COR_VERMELHO_BG = "#FFEBEE"   # Vermelho Despesa Suave
        COR_VERMELHO_TXT = "#C62828"  # Vermelho Texto

        fmt_capa_titulo = workbook.add_format({
            "bold": True, "font_name": "Arial", "font_size": 18,
            "font_color": "#FFFFFF", "fg_color": COR_FUNDO_CAB,
            "align": "center", "valign": "vcenter",
        })

        fmt_capa_sub = workbook.add_format({
            "italic": True, "font_name": "Arial", "font_size": 10,
            "font_color": "#FFFFFF", "fg_color": COR_FUNDO_CAB,
            "align": "center", "valign": "vcenter",
        })

        fmt_kpi_titulo = workbook.add_format({
            "bold": True, "font_name": "Arial", "font_size": 9,
            "font_color": "#555555", "fg_color": "#F3F4F6",
            "align": "center", "valign": "vcenter",
            "border": 1, "border_color": "#D1D5DB",
        })

        fmt_kpi_rec = workbook.add_format({
            "bold": True, "font_name": "Arial", "font_size": 13,
            "font_color": COR_VERDE_TXT, "fg_color": COR_VERDE_BG,
            "num_format": "R$ #,##0.00", "align": "center", "valign": "vcenter",
            "border": 1, "border_color": COR_VERDE_TXT,
        })

        fmt_kpi_desp = workbook.add_format({
            "bold": True, "font_name": "Arial", "font_size": 13,
            "font_color": COR_VERMELHO_TXT, "fg_color": COR_VERMELHO_BG,
            "num_format": "R$ #,##0.00", "align": "center", "valign": "vcenter",
            "border": 1, "border_color": COR_VERMELHO_TXT,
        })

        fmt_kpi_saldo = workbook.add_format({
            "bold": True, "font_name": "Arial", "font_size": 13,
            "font_color": COR_VERDE_TXT if saldo_liquido >= 0 else COR_VERMELHO_TXT,
            "fg_color": COR_VERDE_BG if saldo_liquido >= 0 else COR_VERMELHO_BG,
            "num_format": "R$ #,##0.00", "align": "center", "valign": "vcenter",
            "border": 1, "border_color": COR_VERDE_TXT if saldo_liquido >= 0 else COR_VERMELHO_TXT,
        })

        fmt_kpi_num = workbook.add_format({
            "bold": True, "font_name": "Arial", "font_size": 13,
            "font_color": "#1F2937", "fg_color": "#FFFFFF",
            "align": "center", "valign": "vcenter",
            "border": 1, "border_color": "#D1D5DB",
        })

        fmt_secao_titulo = workbook.add_format({
            "bold": True, "font_name": "Arial", "font_size": 11,
            "font_color": COR_FUNDO_CAB, "bottom": 2, "bottom_color": COR_FUNDO_CAB,
        })

        fmt_cabecalho = workbook.add_format({
            "bold": True, "text_wrap": True, "valign": "vcenter", "align": "center",
            "fg_color": COR_PRIMARIA, "font_color": "#FFFFFF", "font_name": "Arial", "font_size": 10,
            "border": 1, "border_color": "#D3D3D3",
        })

        fmt_celula = workbook.add_format({
            "font_name": "Arial", "font_size": 9, "align": "left", "valign": "vcenter",
            "border": 1, "border_color": "#E0E0E0",
        })

        fmt_celula_zebra = workbook.add_format({
            "font_name": "Arial", "font_size": 9, "align": "left", "valign": "vcenter",
            "border": 1, "border_color": "#E0E0E0", "bg_color": "#F9FAFB",
        })

        # Estilos específicos para destacar Receita e Despesa
        fmt_tipo_receita = workbook.add_format({
            "bold": True, "font_name": "Arial", "font_size": 9,
            "font_color": COR_VERDE_TXT, "fg_color": COR_VERDE_BG,
            "align": "center", "valign": "vcenter", "border": 1, "border_color": "#C8E6C9",
        })

        fmt_tipo_despesa = workbook.add_format({
            "bold": True, "font_name": "Arial", "font_size": 9,
            "font_color": COR_VERMELHO_TXT, "fg_color": COR_VERMELHO_BG,
            "align": "center", "valign": "vcenter", "border": 1, "border_color": "#FFCDD2",
        })

        fmt_moeda_receita = workbook.add_format({
            "bold": True, "font_name": "Arial", "font_size": 9, "num_format": "R$ #,##0.00",
            "font_color": COR_VERDE_TXT, "align": "right", "valign": "vcenter",
            "border": 1, "border_color": "#E0E0E0",
        })

        fmt_moeda_despesa = workbook.add_format({
            "bold": True, "font_name": "Arial", "font_size": 9, "num_format": "R$ #,##0.00",
            "font_color": COR_VERMELHO_TXT, "align": "right", "valign": "vcenter",
            "border": 1, "border_color": "#E0E0E0",
        })

        fmt_analise = workbook.add_format({
            "font_name": "Arial", "font_size": 9.5, "text_wrap": True,
            "valign": "vcenter", "fg_color": "#F8FAFC", "border": 1, "border_color": "#CBD5E1",
        })

        fmt_rodape = workbook.add_format({
            "font_name": "Arial", "font_size": 8.5, "italic": True,
            "font_color": "#64748B", "align": "center", "valign": "vcenter",
        })

        # =============================================================
        # 1. ABA DASHBOARD EXECUTIVO
        # =============================================================
        ws_dash = workbook.add_worksheet("📊 Dashboard Executivo")
        ws_dash.hide_gridlines(2)
        ws_dash.set_landscape()
        ws_dash.set_paper(9)

        if os.path.exists("assets/logo.png"):
            ws_dash.insert_image("B2", "assets/logo.png", {"x_scale": 0.20, "y_scale": 0.20})

        ws_dash.merge_range("C2:H3", "RELATÓRIO FINANCEIRO GERENCIAL — FARMÁCIA JR.", fmt_capa_titulo)
        ws_dash.merge_range("C4:H4", f"UFMG · Vice-Presidência Financeira  |  Gerado em {agora.strftime('%d/%m/%Y às %H:%M')}", fmt_capa_sub)

        ws_dash.write("B6", "📌 INDICADORES CHAVE DA OPERAÇÃO", fmt_secao_titulo)

        ws_dash.merge_range("B7:C7", "FATURAMENTO (RECEITAS)", fmt_kpi_titulo)
        ws_dash.merge_range("B8:C8", tot_receitas, fmt_kpi_rec)

        ws_dash.merge_range("D7:E7", "DESPESAS ACUMULADAS", fmt_kpi_titulo)
        ws_dash.merge_range("D8:E8", tot_despesas, fmt_kpi_desp)

        ws_dash.merge_range("F7:G7", "SALDO OPERACIONAL", fmt_kpi_titulo)
        ws_dash.merge_range("F8:G8", saldo_liquido, fmt_kpi_saldo)

        ws_dash.write("H7", "TICKET MÉDIO REC.", fmt_kpi_titulo)
        ws_dash.write("H8", ticket_medio, fmt_kpi_rec)

        ws_dash.write("I7", "TOTAL REGISTROS", fmt_kpi_titulo)
        ws_dash.write("I8", f"{qtd_lancamentos} un", fmt_kpi_num)

        ws_dash.write("B11", "📊 RESUMO DE CAIXA MENSAL", fmt_secao_titulo)
        ws_dash.write("B13", "Métrica", fmt_cabecalho)
        ws_dash.write("C13", "Valor (R$)", fmt_cabecalho)

        ws_dash.write("B14", "Entradas (Receitas)", fmt_celula)
        ws_dash.write("C14", tot_receitas, fmt_moeda_receita)

        ws_dash.write("B15", "Saídas (Despesas)", fmt_celula)
        ws_dash.write("C15", tot_despesas, fmt_moeda_despesa)

        ws_dash.write("B16", "Resultado Líquido", fmt_celula)
        ws_dash.write("C16", saldo_liquido, fmt_moeda_receita if saldo_liquido >= 0 else fmt_moeda_despesa)

        chart_resumo = workbook.add_chart({"type": "column"})
        chart_resumo.add_series({
            "name": "Consolidado R$",
            "categories": "='📊 Dashboard Executivo'!$B$14:$B$15",
            "values": "='📊 Dashboard Executivo'!$C$14:$C$15",
            "fill": {"color": COR_PRIMARIA},
            "data_labels": {"value": True, "num_format": "R$ #,##0"},
        })
        chart_resumo.set_title({"name": "Comparativo Entradas vs Saídas (R$)"})
        chart_resumo.set_legend({"none": True})
        chart_resumo.set_size({"width": 460, "height": 220})
        ws_dash.insert_chart("D11", chart_resumo)

        ws_dash.write("B20", "💬 ANÁLISE TÉCNICA E PARECER FINANCEIRO", fmt_secao_titulo)
        ws_dash.merge_range("B21:I22", analise_texto, fmt_analise)

        ws_dash.merge_range("B25:I25", "Farmácia Jr. UFMG — Documento Financeiro Oficial e Confidencial", fmt_rodape)

        ws_dash.set_column("A:A", 3)
        ws_dash.set_column("B:I", 17)

        # =============================================================
        # 2. ABA RESUMO POR DEPARTAMENTO
        # =============================================================
        ws_depto = workbook.add_worksheet("🏢 Resumo por Diretoria")
        ws_depto.set_landscape()

        if not df_calc.empty:
            df_depto = df_calc.groupby(["departamento", "tipo"])["valor_liquido"].sum().unstack(fill_value=0.0).reset_index()
            if "Receita" not in df_depto.columns:
                df_depto["Receita"] = 0.0
            if "Despesa" not in df_depto.columns:
                df_depto["Despesa"] = 0.0
            df_depto["Saldo Líquido"] = df_depto["Receita"] - df_depto["Despesa"]
            df_depto = df_depto.rename(columns={"departamento": "Diretoria"})
        else:
            df_depto = pd.DataFrame(columns=["Diretoria", "Receita", "Despesa", "Saldo Líquido"])

        for col_num, val in enumerate(df_depto.columns):
            ws_depto.write(0, col_num, val, fmt_cabecalho)

        for row_num in range(len(df_depto)):
            zebra = row_num % 2 == 1
            f_txt = fmt_celula_zebra if zebra else fmt_celula

            for col_num, col_name in enumerate(df_depto.columns):
                v = df_depto.iloc[row_num, col_num]
                if col_name == "Diretoria":
                    ws_depto.write(row_num + 1, col_num, str(v), f_txt)
                elif col_name == "Receita":
                    ws_depto.write_number(row_num + 1, col_num, float(v), fmt_moeda_receita)
                elif col_name == "Despesa":
                    ws_depto.write_number(row_num + 1, col_num, float(v), fmt_moeda_despesa)
                else:
                    fmt_s = fmt_moeda_receita if float(v) >= 0 else fmt_moeda_despesa
                    ws_depto.write_number(row_num + 1, col_num, float(v), fmt_s)

        if not df_depto.empty:
            chart_depto = workbook.add_chart({"type": "bar", "subtype": "group"})
            chart_depto.add_series({
                "name": "Receita",
                "categories": f"='🏢 Resumo por Diretoria'!$A$2:$A${len(df_depto)+1}",
                "values": f"='🏢 Resumo por Diretoria'!$B$2:$B${len(df_depto)+1}",
                "fill": {"color": COR_VERDE_TXT},
            })
            chart_depto.add_series({
                "name": "Despesa",
                "categories": f"='🏢 Resumo por Diretoria'!$A$2:$A${len(df_depto)+1}",
                "values": f"='🏢 Resumo por Diretoria'!$C$2:$C${len(df_depto)+1}",
                "fill": {"color": COR_VERMELHO_TXT},
            })
            chart_depto.set_title({"name": "Desempenho Financeiro por Diretoria (R$)"})
            chart_depto.set_size({"width": 550, "height": 280})
            ws_depto.insert_chart("E2", chart_depto)

        for col_num, col_name in enumerate(df_depto.columns):
            max_len = max((df_depto[col_name].astype(str).map(len).max() if not df_depto.empty else 0), len(col_name)) + 6
            ws_depto.set_column(col_num, col_num, min(max_len, 35))
        ws_depto.freeze_panes(1, 1)

        # =============================================================
        # 3. ABA BASE DE DADOS COMPLETA (TIPO & VALORES EM CORES)
        # =============================================================
        colunas_renomeadas = {
            "id": "ID", "mes": "Mês", "data": "Data", "departamento": "Diretoria", "tipo": "Tipo",
            "categoria": "Categoria", "descricao": "Descrição da Operação", "valor_bruto": "Valor Bruto",
            "taxa": "Taxas", "valor_liquido": "Valor Líquido", "conta_origem": "Conta Bancária",
            "status_pagamento": "Status Pagamento", "nota_fiscal": "Nota Fiscal", "status_onvio": "Status Contábil",
        }

        df_formatado = df_export.copy()
        cols_existentes = [c for c in colunas_renomeadas.keys() if c in df_formatado.columns]
        df_formatado = df_formatado[cols_existentes].rename(columns=colunas_renomeadas)

        ws_base = workbook.add_worksheet("💰 Base Fluxo de Caixa")
        ws_base.set_landscape()

        for col_num, value in enumerate(df_formatado.columns):
            ws_base.write(0, col_num, value, fmt_cabecalho)

        for row_num in range(len(df_formatado)):
            zebra = row_num % 2 == 1
            tipo_linha = str(df_formatado.iloc[row_num].get("Tipo", "")).strip().lower()
            eh_receita = "receita" in tipo_linha

            for col_num, col_name in enumerate(df_formatado.columns):
                val = df_formatado.iloc[row_num, col_num]

                if col_name == "Tipo":
                    # Coluna Tipo destacada em Verde ou Vermelho
                    fmt_t = fmt_tipo_receita if eh_receita else fmt_tipo_despesa
                    ws_base.write(row_num + 1, col_num, str(val or ""), fmt_t)
                elif "Valor" in col_name or "Taxa" in col_name:
                    # Valores em Verde (Receita) ou Vermelho (Despesa)
                    fmt_m = fmt_moeda_receita if eh_receita else fmt_moeda_despesa
                    ws_base.write_number(row_num + 1, col_num, float(val or 0.0), fmt_m)
                else:
                    f_txt = fmt_celula_zebra if zebra else fmt_celula
                    ws_base.write(row_num + 1, col_num, str(val or ""), f_txt)

        for col_num, col_name in enumerate(df_formatado.columns):
            max_len = max(
                (df_formatado[col_name].astype(str).map(len).max() if not df_formatado.empty else 0),
                len(col_name),
            ) + 4
            ws_base.set_column(col_num, col_num, min(max_len, 45))

        if not df_formatado.empty:
            ws_base.autofilter(0, 0, len(df_formatado), len(df_formatado.columns) - 1)
        ws_base.freeze_panes(1, 1)

    return buffer.getvalue()


def renderizar_aba_fluxo_caixa():
    garantir_colunas_documentacao()

    st.markdown(
        "<h2 style='text-align: center; color: #C71585;'>📊 Fluxo de Caixa Geral — Farmácia Jr.</h2>",
        unsafe_allow_html=True,
    )
    st.write("Gerencie os registros financeiros de forma manual ou por IA.")

    lista_meses = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM fluxo_caixa_geral ORDER BY data DESC, id DESC", conn)
    conn.close()

    opcoes_bancos = obter_lista_bancos(df)

    aba_manual, aba_pdf = st.tabs(["➕ Registro Manual", "⚡ Importar por IA (PDF)"])

    with aba_manual:
        with st.expander("Abrir Formulário de Operação Manual"):
            agora = obter_agora_br()
            data = st.date_input("Data do Lançamento", value=agora)
            depto = st.selectbox("Departamento", ["VP", "IMAGEM", "AR", "PRESIDÊNCIA", "PROJETOS", "NEGÓCIOS"])
            tipo = st.selectbox("Tipo", ["Receita", "Despesa"])
            cat = st.selectbox("Categoria", ["Serviço Prestado", "ADM: Operacional", "Marketing", "Eventos"])
            desc = st.text_input("Descrição")
            v_bruto = st.number_input("Valor Bruto (R$)", min_value=0.0)
            v_taxa = st.number_input("Taxas (R$)", min_value=0.0, value=0.0)
            v_liq = v_bruto - v_taxa

            conta_sel_manual = st.selectbox("Conta de Origem", opcoes_bancos, key="sb_manual_banco")
            if conta_sel_manual == "➕ Adicionar Novo Banco...":
                conta_final_manual = st.text_input("Digite o nome do novo banco:", key="txt_novo_banco_manual")
            else:
                conta_final_manual = conta_sel_manual

            pagamento = st.selectbox("Status do Pagamento", ["🟢 Pago", "🟡 Pendente"])
            nf = st.selectbox("Nota Fiscal", ["🟢 Emitida", "🟡 Aguardando Emissão", "⚪ Não se aplica"])
            onvio = st.selectbox("Status na Onvio", ["❌ Não enviado", "Enviado"])

            if st.button("Confirmar Lançamento Manual"):
                if not desc:
                    st.error("Por favor, digite uma descrição para a movimentação.")
                elif not conta_final_manual or conta_final_manual == "➕ Adicionar Novo Banco...":
                    st.error("Por favor, informe um nome de banco válido.")
                else:
                    mes_nome = lista_meses[data.month - 1]
                    salvar_lancamento(
                        mes_nome, data.strftime("%Y-%m-%d"), depto, tipo, cat,
                        desc, v_bruto, v_taxa, v_liq, conta_final_manual.strip(), pagamento, nf, onvio
                    )
                    st.success("Lançamento manual salvo!")
                    st.rerun()

    with aba_pdf:
        st.markdown("#### ⚡ Leitura Cognitiva de Extratos com Gemini")
        st.caption("Faça o upload do PDF. O Gemini detectará o banco, datas e valores automaticamente.")

        arquivo_pdf = st.file_uploader("Escolha o arquivo do Extrato (.pdf)", type=["pdf"], key="uploader_ia_fluxo")
        if arquivo_pdf is not None:
            with st.spinner("⚡ Lendo extrato em alta velocidade..."):
                try:
                    reader = PdfReader(arquivo_pdf)
                    texto_bruto = ""
                    for page in reader.pages:
                        texto_extraido = page.extract_text()
                        if texto_extraido:
                            texto_bruto += texto_extraido + "\n"
                except Exception as e:
                    st.error(f"Erro ao ler arquivo PDF: {e}")
                    texto_bruto = ""

            if texto_bruto:
                lancamentos_ia = ler_extrato_com_gemini(texto_bruto)

                if lancamentos_ia:
                    st.write(f"📋 **{len(lancamentos_ia)} lançamentos mapeados:**")

                    banco_detectado = lancamentos_ia[0].get("banco", "PicPay") if lancamentos_ia else "PicPay"

                    c_b1, c_b2 = st.columns([2, 2])
                    idx_default = 0
                    for i, op in enumerate(opcoes_bancos):
                        if str(banco_detectado).lower() in op.lower():
                            idx_default = i
                            break

                    conta_sel_pdf = c_b1.selectbox(
                        "🏦 Selecione/Confirme a Conta Bancária:", opcoes_bancos, index=idx_default, key="sb_pdf_banco"
                    )

                    if conta_sel_pdf == "➕ Adicionar Novo Banco...":
                        conta_final_pdf = c_b2.text_input("Digite o nome do novo banco:", key="txt_novo_banco_pdf")
                    else:
                        conta_final_pdf = conta_sel_pdf

                    agora = obter_agora_br()
                    dados_finais = []
                    for item in lancamentos_ia:
                        try:
                            dt_obj = datetime.strptime(item["data"], "%Y-%m-%d")
                            mes_calculado = lista_meses[dt_obj.month - 1]
                        except Exception:
                            mes_calculado = lista_meses[agora.month - 1]

                        dados_finais.append({
                            "mes": mes_calculado,
                            "data": item.get("data", agora.strftime("%Y-%m-%d")),
                            "departamento": "GERAL",
                            "tipo": item.get("tipo", "Despesa"),
                            "categoria": "ADM: Operacional" if item.get("tipo") == "Despesa" else "Serviço Prestado",
                            "descricao": item.get("descricao", "Lançamento sem nome"),
                            "valor_bruto": float(item.get("valor_bruto", 0.0)),
                            "taxa": 0.0,
                            "valor_liquido": float(item.get("valor_bruto", 0.0)),
                            "conta_origem": conta_final_pdf.strip() if conta_final_pdf else "PicPay",
                            "status_pagamento": "🟢 Pago",
                            "nota_fiscal": "⚪ Não se aplica",
                            "status_onvio": "❌ Não enviado",
                        })

                    df_previa = pd.DataFrame(dados_finais)
                    st.dataframe(df_previa[["data", "tipo", "descricao", "valor_bruto", "conta_origem"]], use_container_width=True)

                    if st.button("📥 Aprovar e Injetar Transações", type="primary"):
                        if not conta_final_pdf or conta_final_pdf == "➕ Adicionar Novo Banco...":
                            st.error("Por favor, digite o nome do novo banco antes de injetar.")
                        else:
                            with st.spinner("⚡ Salvando em lote instantaneamente..."):
                                salvar_lancamentos_em_lote(dados_finais)
                            st.success("Lançamentos salvos no banco de dados!")
                            st.rerun()
                else:
                    st.warning("Não foram encontrados lançamentos válidos no extrato.")
            else:
                st.error("Não foi possível extrair texto do PDF.")

    st.markdown("---")

    if not df.empty:
        receitas_pagas = df[(df["tipo"] == "Receita") & (df["status_pagamento"].str.contains("Pago", na=False))]["valor_liquido"].sum()
        despesas_pagas = df[(df["tipo"] == "Despesa") & (df["status_pagamento"].str.contains("Pago", na=False))]["valor_liquido"].sum()
        saldo_real = receitas_pagas - despesas_pagas
        cor_saldo_txt = "#2E7D32" if saldo_real >= 0 else "#C62828"

        st.markdown(
            f"""
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 15px; margin-bottom: 25px;">
                <div style="background-color: #EBF7EE; border-left: 5px solid #2E7D32; padding: 12px; border-radius: 6px;">
                    <span style="color: #555; font-size: 12px; font-weight: bold;">📥 RECEITAS (LÍQ)</span>
                    <h3 style="color: #2E7D32; margin: 2px 0 0 0;">R$ {receitas_pagas:.2f}</h3>
                </div>
                <div style="background-color: #FDF2F2; border-left: 5px solid #C62828; padding: 12px; border-radius: 6px;">
                    <span style="color: #555; font-size: 12px; font-weight: bold;">📤 DESPESAS ACUMULADAS</span>
                    <h3 style="color: #C62828; margin: 2px 0 0 0;">R$ {despesas_pagas:.2f}</h3>
                </div>
                <div style="background-color: {'#E8F5E9' if saldo_real >= 0 else '#FFEBEE'}; border-left: 5px solid {cor_saldo_txt}; padding: 12px; border-radius: 6px;">
                    <span style="color: #555; font-size: 12px; font-weight: bold;">⚖️ SALDO ATUAL</span>
                    <h3 style="color: {cor_saldo_txt}; margin: 2px 0 0 0;">R$ {saldo_real:.2f}</h3>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### 🔍 Consultas e Exportação")
        c_f1, c_f2, c_f3 = st.columns(3)
        filtro_mes = c_f1.selectbox("Filtrar por Mês:", ["Todos"] + lista_meses)
        filtro_depto = c_f2.selectbox("Filtrar por Diretoria:", ["Todas", "IMAGEM", "AR", "VP", "PRESIDÊNCIA", "PROJETOS", "NEGÓCIOS"])
        filtro_status = c_f3.selectbox("Filtrar por Pagamento:", ["Todos", "🟢 Pago", "🟡 Pendente"])

        df_filtrado = df.copy()
        if filtro_mes != "Todos":
            df_filtrado = df_filtrado[df_filtrado["mes"] == filtro_mes]
        if filtro_depto != "Todas":
            df_filtrado = df_filtrado[df_filtrado["departamento"] == filtro_depto]
        if filtro_status != "Todos":
            status_busca = "Pendente" if "Pendente" in filtro_status else "Pago"
            df_filtrado = df_filtrado[df_filtrado["status_pagamento"].str.contains(status_busca, na=False)]

        excel_estilizado_bytes = gerar_excel_estilizado(df_filtrado)

        st.download_button(
            label="📊 Baixar Relatório Executivo Consolidado (.xlsx)",
            data=excel_estilizado_bytes,
            file_name=f"Relatorio_Financeiro_FarmaciaJr_{obter_agora_br().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        st.markdown(f"#### 📄 Lançamentos Encontrados ({len(df_filtrado)} registros)")
        for idx, row in df_filtrado.iterrows():
            with st.container():
                col_l1, col_l2, col_l3, col_l4 = st.columns([1, 4, 2, 1])
                cor_tipo = "#E8F5E9" if row["tipo"] == "Receita" else "#FFEBEE"
                txt_tipo_cor = "#2E7D32" if row["tipo"] == "Receita" else "#C62828"

                col_l1.markdown(
                    f"""
                    <div style="background-color: {cor_tipo}; color: {txt_tipo_cor}; text-align: center; border-radius: 4px; padding: 4px; font-weight: bold; font-size: 12px;">
                        {row['data'][5:]}<br>{row['tipo'][:3].upper()}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                col_l2.write(f"**{row['descricao']}**")
                col_l2.caption(f"📁 Setor: {row['departamento']} | Categoria: {row['categoria']} | Conta: {row['conta_origem']}")

                col_l3.write(f"💸 **Líq:** R$ {row['valor_liquido']:.2f}")
                col_l3.caption(f"Status: {row['status_pagamento']} | NF: {row['nota_fiscal']}")

                if col_l4.button("🗑️", key=f"del_fluxo_{row['id']}", help="Excluir lançamento"):
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM fluxo_caixa_geral WHERE id = ?", (row["id"],))
                    conn.commit()
                    conn.close()
                    st.success("Removido!")
                    st.rerun()
            st.markdown("<hr style='margin: 4px 0; border: 0.5px solid #F8F8F8;'>", unsafe_allow_html=True)
    else:
        st.info("A tabela de fluxo de caixa está limpa no momento.")
