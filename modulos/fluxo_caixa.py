import io
import json
import os
import sqlite3
from datetime import datetime

import google.generativeai as genai
import pandas as pd
from pypdf import PdfReader
import streamlit as st

from modulos.estilo import (
    INK, MIST, VERDANT, CORAL, SAGE, CLOUD, BORDER, SLATE,
    injetar_estilos, page_header, section_header, metric_card, pill, formatar_moeda,
)

DB_PATH = "database/financeiro_v2.db"


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
    """Retorna os bancos padrão somados aos bancos já existentes no banco de dados."""
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
    """Insere um novo lançamento único no fluxo de caixa."""
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
    """Insere múltiplos lançamentos instantaneamente em lote."""
    if not lista_lancamentos:
        return

    garantir_colunas_documentacao()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    dados_tuple = [
        (
            l["mes"],
            l["data"],
            l["departamento"],
            l["tipo"],
            l["categoria"],
            l["descricao"],
            l["valor_bruto"],
            l["taxa"],
            l["valor_liquido"],
            l["conta_origem"],
            l["status_pagamento"],
            l["nota_fiscal"],
            l["status_onvio"],
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
    """Lê o extrato em alta velocidade utilizando modelos leves e configurados."""
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
        - tipo: "Receita" (entradas/+) ou "Despesa" (saídas/-)
        - valor_bruto: float positivo
        - banco: Nome da instituição bancária
        - Ignore saldos e rodapés.

        Texto do extrato:
        {texto_pdf}
        """

        modelos_rapidos = [
            "gemini-1.5-flash-8b",
            "gemini-2.0-flash",
            "gemini-flash-latest",
        ]

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
        st.error(f"Erro no processamento rápido da IA: {e}")
        return []


def gerar_excel_estilizado(df_export):
    """Gera o arquivo Excel formatado para download."""
    buffer = io.BytesIO()

    colunas_renomeadas = {
        "id": "ID",
        "mes": "Mês",
        "data": "Data",
        "departamento": "Diretoria",
        "tipo": "Tipo",
        "categoria": "Categoria",
        "descricao": "Descrição da Operação",
        "valor_bruto": "Valor Bruto",
        "taxa": "Taxas",
        "valor_liquido": "Valor Líquido",
        "conta_origem": "Conta Bancária",
        "status_pagamento": "Status Pagamento",
        "nota_fiscal": "Nota Fiscal",
        "status_onvio": "Status Contábil",
    }

    df_formatado = df_export.copy()
    cols_existentes = [c for c in colunas_renomeadas.keys() if c in df_formatado.columns]
    df_formatado = df_formatado[cols_existentes].rename(columns=colunas_renomeadas)
    n_linhas = len(df_formatado)
    n_cols = len(df_formatado.columns)
    linha_titulo, linha_cabecalho = 0, 2
    primeira_linha_dados = linha_cabecalho + 1

    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df_formatado.to_excel(
            writer, index=False, sheet_name="Fluxo_de_Caixa", startrow=linha_cabecalho
        )

        workbook = writer.book
        worksheet = writer.sheets["Fluxo_de_Caixa"]

        cor_receita_bg, cor_receita_fg = "#E5F3EC", "#186B45"
        cor_despesa_bg, cor_despesa_fg = "#FCEAE4", "#B94A2C"
        cor_zebra = "#F4F9F7"

        fmt_titulo = workbook.add_format({
            "bold": True, "font_name": "Arial", "font_size": 14,
            "font_color": INK, "valign": "vcenter",
        })
        fmt_subtitulo = workbook.add_format({
            "font_name": "Arial", "font_size": 9, "font_color": "#5B7A72", "valign": "vcenter",
        })
        fmt_cabecalho = workbook.add_format({
            "bold": True, "text_wrap": True, "valign": "vcenter", "align": "center",
            "fg_color": INK, "font_color": "#FFFFFF", "font_name": "Arial", "font_size": 10,
            "border": 1, "border_color": INK,
        })

        def _fmt_celula(zebra=False):
            return workbook.add_format({
                "font_name": "Arial", "font_size": 9, "align": "left", "valign": "vcenter",
                "border": 1, "border_color": "#E0E0E0",
                "bg_color": cor_zebra if zebra else "#FFFFFF",
            })

        def _fmt_moeda(zebra=False):
            return workbook.add_format({
                "font_name": "Arial", "font_size": 9, "num_format": "R$ #,##0.00;[RED]-R$ #,##0.00",
                "align": "right", "valign": "vcenter",
                "border": 1, "border_color": "#E0E0E0",
                "bg_color": cor_zebra if zebra else "#FFFFFF",
            })

        def _fmt_data(zebra=False):
            return workbook.add_format({
                "font_name": "Arial", "font_size": 9, "align": "center", "valign": "vcenter",
                "border": 1, "border_color": "#E0E0E0",
                "bg_color": cor_zebra if zebra else "#FFFFFF",
            })

        def _fmt_tipo(receita, zebra=False):
            return workbook.add_format({
                "font_name": "Arial", "font_size": 9, "bold": True, "align": "center", "valign": "vcenter",
                "border": 1, "border_color": "#E0E0E0",
                "bg_color": cor_receita_bg if receita else cor_despesa_bg,
                "font_color": cor_receita_fg if receita else cor_despesa_fg,
            })

        fmt_total_label = workbook.add_format({
            "bold": True, "font_name": "Arial", "font_size": 9.5, "font_color": "#FFFFFF",
            "fg_color": INK, "align": "right", "valign": "vcenter", "border": 1, "border_color": INK,
        })
        fmt_total_valor = workbook.add_format({
            "bold": True, "font_name": "Arial", "font_size": 9.5, "font_color": "#FFFFFF",
            "fg_color": INK, "num_format": "R$ #,##0.00", "align": "right", "valign": "vcenter",
            "border": 1, "border_color": INK,
        })

        worksheet.merge_range(linha_titulo, 0, linha_titulo, max(n_cols - 1, 1), "", fmt_titulo)
        worksheet.write(linha_titulo, 0, "🦩 Fluxo de Caixa — Farmácia Jr.", fmt_titulo)
        worksheet.merge_range(linha_titulo + 1, 0, linha_titulo + 1, max(n_cols - 1, 1), "", fmt_subtitulo)
        worksheet.write(
            linha_titulo + 1, 0,
            f"Exportado em {datetime.now().strftime('%d/%m/%Y')} · {n_linhas} lançamento(s)",
            fmt_subtitulo,
        )

        for col_num, value in enumerate(df_formatado.columns):
            worksheet.write(linha_cabecalho, col_num, value, fmt_cabecalho)

        for row_num in range(n_linhas):
            zebra = row_num % 2 == 1
            linha_planilha = primeira_linha_dados + row_num
            eh_receita = str(df_formatado.iloc[row_num].get("Tipo", "")).strip().lower() == "receita"

            for col_num, col_name in enumerate(df_formatado.columns):
                val = df_formatado.iloc[row_num, col_num]
                if "Valor" in col_name or "Taxa" in col_name:
                    worksheet.write_number(
                        linha_planilha, col_num, float(val or 0.0), _fmt_moeda(zebra)
                    )
                elif col_name == "Data":
                    worksheet.write(linha_planilha, col_num, str(val or ""), _fmt_data(zebra))
                elif col_name == "Tipo":
                    worksheet.write(linha_planilha, col_num, str(val or ""), _fmt_tipo(eh_receita, zebra))
                else:
                    worksheet.write(linha_planilha, col_num, str(val or ""), _fmt_celula(zebra))

        linha_total = primeira_linha_dados + n_linhas
        col_letras = {i: chr(65 + i) for i in range(26)}
        worksheet.merge_range(
            linha_total, 0, linha_total, n_cols - 2 if n_cols > 1 else 0, "TOTAL", fmt_total_label
        )
        for col_num, col_name in enumerate(df_formatado.columns):
            if col_name in ("Valor Bruto", "Taxas", "Valor Líquido") and n_linhas > 0:
                letra = col_letras.get(col_num, None)
                if letra:
                    inicio = f"{letra}{primeira_linha_dados + 1}"
                    fim = f"{letra}{primeira_linha_dados + n_linhas}"
                    worksheet.write_formula(
                        linha_total, col_num, f"=SUM({inicio}:{fim})", fmt_total_valor
                    )

        for col_num, col_name in enumerate(df_formatado.columns):
            max_len = max(
                (df_formatado[col_name].astype(str).map(len).max() if not df_formatado.empty else 0),
                len(col_name),
            ) + 4
            worksheet.set_column(col_num, col_num, min(max_len, 45))

        if n_linhas > 0:
            worksheet.autofilter(linha_cabecalho, 0, linha_cabecalho + n_linhas, n_cols - 1)
        worksheet.freeze_panes(primeira_linha_dados, 0)
        worksheet.hide_gridlines(2)

    return buffer.getvalue()


def renderizar_aba_fluxo_caixa():
    """Renderiza a interface do Fluxo de Caixa no Streamlit."""
    injetar_estilos()
    garantir_colunas_documentacao()

    page_header("💳", "Fluxo de Caixa", "Gerencie os registros financeiros de forma manual ou por IA")

    lista_meses = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"
    ]

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM fluxo_caixa_geral ORDER BY data DESC, id DESC", conn)
    conn.close()

    opcoes_bancos = obter_lista_bancos(df)

    aba_manual, aba_pdf = st.tabs(["➕ Registro Manual", "🤖 Importar por IA (PDF)"])

    with aba_manual:
        with st.expander("Abrir formulário de operação manual"):
            data = st.date_input("Data do Lançamento", value=datetime.now())
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
                    st.success(f"Lançamento manual salvo na conta '{conta_final_manual.strip()}'!")
                    st.rerun()

    with aba_pdf:
        section_header("Automação", "Leitura cognitiva de extratos com Gemini")
        st.caption("Faça o upload do PDF. O Gemini detectará o banco, datas e valores automaticamente.")

        arquivo_pdf = st.file_uploader("Escolha o arquivo do Extrato (.pdf)", type=["pdf"], key="uploader_ia_fluxo")
        if arquivo_pdf is not None:
            with st.spinner("🤖 Extraindo texto do documento..."):
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
                with st.spinner("🧠 O Gemini está interpretando as transações..."):
                    lancamentos_ia = ler_extrato_com_gemini(texto_bruto)

                if lancamentos_ia:
                    st.write(f"📋 **{len(lancamentos_ia)} lançamentos mapeados pela IA:**")

                    banco_detectado = lancamentos_ia[0].get("banco", "PicPay") if lancamentos_ia else "PicPay"

                    c_b1, c_b2 = st.columns([2, 2])
                    idx_default = 0
                    for i, op in enumerate(opcoes_bancos):
                        if str(banco_detectado).lower() in op.lower():
                            idx_default = i
                            break

                    conta_sel_pdf = c_b1.selectbox(
                        "🏦 Selecione/Confirme a Conta Bancária:",
                        opcoes_bancos, index=idx_default, key="sb_pdf_banco"
                    )

                    if conta_sel_pdf == "➕ Adicionar Novo Banco...":
                        conta_final_pdf = c_b2.text_input("Digite o nome do novo banco:", key="txt_novo_banco_pdf")
                    else:
                        conta_final_pdf = conta_sel_pdf

                    dados_finais = []
                    for item in lancamentos_ia:
                        try:
                            dt_obj = datetime.strptime(item["data"], "%Y-%m-%d")
                            mes_calculado = lista_meses[dt_obj.month - 1]
                        except Exception:
                            mes_calculado = "Janeiro"

                        dados_finais.append({
                            "mes": mes_calculado,
                            "data": item.get("data", datetime.now().strftime("%Y-%m-%d")),
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
                    st.dataframe(
                        df_previa[["data", "tipo", "descricao", "valor_bruto", "conta_origem"]],
                        use_container_width=True,
                    )

                    if st.button("📥 Aprovar e Injetar Transações da IA", type="primary"):
                        if not conta_final_pdf or conta_final_pdf == "➕ Adicionar Novo Banco...":
                            st.error("Por favor, digite o nome do novo banco antes de injetar.")
                        else:
                            with st.spinner("⚡ Salvando em lote instantaneamente..."):
                                salvar_lancamentos_em_lote(dados_finais)
                            st.success(f"Lançamentos salvos com sucesso na conta '{conta_final_pdf.strip()}'!")
                            st.rerun()
                else:
                    st.warning("A IA não encontrou lançamentos válidos no texto do extrato.")
            else:
                st.error("Não foi possível extrair texto do PDF.")

    st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
    st.markdown('<div class="fj-divider"></div>', unsafe_allow_html=True)

    if not df.empty:
        receitas_pagas = df[(df["tipo"] == "Receita") & (df["status_pagamento"].str.contains("Pago", na=False))]["valor_liquido"].sum()
        despesas_pagas = df[(df["tipo"] == "Despesa") & (df["status_pagamento"].str.contains("Pago", na=False))]["valor_liquido"].sum()
        saldo_real = receitas_pagas - despesas_pagas
        cor_saldo = VERDANT if saldo_real >= 0 else CORAL

        m1, m2, m3 = st.columns(3)
        metric_card(
            m1, "Receitas (líq.)", "📥", f"{VERDANT}22",
            formatar_moeda(receitas_pagas),
            f"linear-gradient(90deg, {VERDANT}, {SAGE})",
        )
        metric_card(
            m2, "Despesas acumuladas", "📤", f"{CORAL}22",
            formatar_moeda(despesas_pagas),
            f"linear-gradient(90deg, {CORAL}, #F2A38B)",
        )
        metric_card(
            m3, "Saldo atual", "⚖️", f"{cor_saldo}22",
            formatar_moeda(saldo_real),
            f"linear-gradient(90deg, {cor_saldo}, {SAGE})",
        )

        st.markdown("<div style='height:22px;'></div>", unsafe_allow_html=True)

        section_header("Consultas", "Filtros e exportação")
        st.markdown('<div class="fj-filter-bar">', unsafe_allow_html=True)
        c_f1, c_f2, c_f3 = st.columns(3)
        filtro_mes = c_f1.selectbox("Mês", ["Todos"] + lista_meses)
        filtro_depto = c_f2.selectbox("Diretoria", ["Todas", "IMAGEM", "AR", "VP", "PRESIDÊNCIA", "PROJETOS", "NEGÓCIOS"])
        filtro_status = c_f3.selectbox("Pagamento", ["Todos", "🟢 Pago", "🟡 Pendente"])
        st.markdown('</div>', unsafe_allow_html=True)

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
            label="📊 Baixar relatório consolidado em Excel (.xlsx)",
            data=excel_estilizado_bytes,
            file_name=f"Planilha_Fluxo_Caixa_FarmaciaJr_{datetime.now().strftime('%Y-%m-%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
        section_header("Registros", f"{len(df_filtrado)} lançamentos encontrados")

        for idx, row in df_filtrado.iterrows():
            cor_tipo = VERDANT if row["tipo"] == "Receita" else CORAL
            status_ok = "Pago" in str(row["status_pagamento"])

            # Formatação sem quebras de linha/espaços extras para não estourar o Markdown
            pill_html = pill(row["status_pagamento"], VERDANT if status_ok else "#C9A227") + pill(row["nota_fiscal"], SLATE)
            date_pill_html = f'<div class="fj-date-pill" style="background:{cor_tipo}18; color:{cor_tipo};">{row["data"][5:]}<br>{row["tipo"][:3].upper()}</div>'
            desc_html = f'<div class="fj-desc">{row["descricao"]}</div>'
            meta_html = f'<div class="fj-meta">📁 {row["departamento"]} · {row["categoria"]} · {row["conta_origem"]}</div>'
            val_html = f'<div class="fj-value">R$ {row["valor_liquido"]:.2f}</div>'

            st.markdown('<div class="fj-list-row">', unsafe_allow_html=True)
            col_l1, col_l2, col_l3, col_l4 = st.columns([1, 4, 2, 1])

            col_l1.markdown(date_pill_html, unsafe_allow_html=True)
            col_l2.markdown(desc_html, unsafe_allow_html=True)
            col_l2.markdown(meta_html, unsafe_allow_html=True)
            col_l3.markdown(val_html, unsafe_allow_html=True)
            col_l3.markdown(pill_html, unsafe_allow_html=True)

            if col_l4.button("🗑️", key=f"del_fluxo_{row['id']}", help="Excluir lançamento"):
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM fluxo_caixa_geral WHERE id = ?", (row["id"],))
                conn.commit()
                conn.close()
                st.success("Removido!")
                st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)
    else:
        empty_html = (
            f'<div class="fj-chart-card" style="text-align:center; padding:36px 20px;">'
            f'<div style="font-size:28px;">🧫</div>'
            f'<p style="font-family:\'Space Grotesk\',sans-serif; font-weight:600; color:{INK}; margin:10px 0 4px 0;">'
            f'A tabela de fluxo de caixa está limpa no momento</p>'
            f'<p style="font-family:\'Inter\',sans-serif; font-size:13px; color:{SLATE}; margin:0;">'
            f'Lance um registro manual ou importe um extrato por IA para começar.</p></div>'
        )
        st.markdown(empty_html, unsafe_allow_html=True)
