import io
import json
import os
import sqlite3
from datetime import datetime

import google.generativeai as genai
import pandas as pd
from pypdf import PdfReader
import streamlit as st

# Caminho unificado do banco de dados
DB_PATH = "database/financeiro_v2.db"


def garantir_colunas_documentacao():
    """Garante de forma absoluta que todas as colunas do fluxo de caixa existam no banco."""
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
    """Salva um lançamento completo no banco de dados."""
    garantir_colunas_documentacao()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO fluxo_caixa_geral (mes, data, departamento, tipo, categoria, descricao, valor_bruto, taxa, valor_liquido, conta_origem, status_pagamento, nota_fiscal, status_onvio)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    """Envia o texto do extrato para o Gemini mapear os dados em JSON garantido."""
    api_key = st.secrets.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY")

    if not api_key:
        st.error("⚠️ Chave GEMINI_API_KEY não encontrada nos Secrets do Streamlit Cloud.")
        return []

    if not texto_pdf or len(texto_pdf.strip()) < 10:
        st.warning("⚠️ O PDF parece estar sem texto editável (pode ser uma imagem digitalizada).")
        return []

    try:
        genai.configure(api_key=api_key)

        prompt = f"""
        Você é um assistente financeiro sênior da Farmácia Jr. (UFMG).
        Analise o texto deste extrato bancário e extraia TODOS os lançamentos válidos de entrada e saída.
        Ignore linhas de saldos, saques sem descrição, rendimentos informativos ou tarifas zeradas.

        Para cada lançamento válido, retorne obrigatoriamente uma lista de objetos JSON contendo:
        - data: formato YYYY-MM-DD (Se não tiver o ano no texto, assuma o ano atual de {datetime.now().year})
        - tipo: "Receita" (para PIX recebidos, depósitos, créditos) ou "Despesa" (para PIX enviados, pagamentos, boletos, tarifas)
        - descricao: descrição limpa da transação
        - valor_bruto: valor numérico float positivo (ex: 150.50)

        Exemplo de resposta esperada:
        [
            {{"data": "2026-03-15", "tipo": "Receita", "descricao": "PIX RECEBIDO - JOAO SILVA", "valor_bruto": 150.00}},
            {{"data": "2026-03-16", "tipo": "Despesa", "descricao": "COMPRA DE JALECOS", "valor_bruto": 450.50}}
        ]

        Texto do extrato:
        {texto_pdf}
        """

        # Configuração que força a resposta em JSON nativo
        try:
            model = genai.GenerativeModel(
                "gemini-2.5-flash",
                generation_config={"response_mime_type": "application/json"}
            )
            response = model.generate_content(prompt)
            resposta_texto = response.text.strip()
        except Exception:
            # Fallback caso a versão da lib não suporte o parâmetro de mime_type
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content(prompt)
            resposta_texto = response.text.strip()

        # Limpeza caso o modelo inclua formatação Markdown extra
        if "```" in resposta_texto:
            resposta_texto = resposta_texto.split("```")[1]
            if resposta_texto.startswith("json"):
                resposta_texto = resposta_texto[4:]

        dados = json.loads(resposta_texto.strip())
        return dados if isinstance(dados, list) else []

    except json.JSONDecodeError as e:
        st.error(f"Erro ao converter a resposta da IA em lista financeira: {e}")
        return []
    except Exception as e:
        st.error(f"Erro no processamento da IA: {e}")
        return []


def gerar_excel_estilizado(df_export):
    """Gera um arquivo Excel estilizado profissionalmente com as cores da Farmácia Jr."""
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
    cols_existentes = [
        c for c in colunas_renomeadas.keys() if c in df_formatado.columns
    ]
    df_formatado = df_formatado[cols_existentes].rename(
        columns=colunas_renomeadas
    )

    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df_formatado.to_excel(writer, index=False, sheet_name="Fluxo_de_Caixa")

        workbook = writer.book
        worksheet = writer.sheets["Fluxo_de_Caixa"]

        fmt_cabecalho = workbook.add_format({
            "bold": True,
            "text_wrap": True,
            "valign": "vcenter",
            "align": "center",
            "fg_color": "#FF1493",
            "font_color": "#FFFFFF",
            "font_name": "Arial",
            "font_size": 10,
            "border": 1,
            "border_color": "#D3D3D3",
        })

        fmt_celula = workbook.add_format({
            "font_name": "Arial",
            "font_size": 9,
            "align": "left",
            "valign": "vcenter",
            "border": 1,
            "border_color": "#E0E0E0",
        })

        fmt_moeda = workbook.add_format({
            "font_name": "Arial",
            "font_size": 9,
            "num_format": "R$ #,##0.00",
            "align": "right",
            "valign": "vcenter",
            "border": 1,
            "border_color": "#E0E0E0",
        })

        fmt_data = workbook.add_format({
            "font_name": "Arial",
            "font_size": 9,
            "align": "center",
            "valign": "vcenter",
            "border": 1,
            "border_color": "#E0E0E0",
        })

        for col_num, value in enumerate(df_formatado.columns):
            worksheet.write(0, col_num, value, fmt_cabecalho)

        for row_num in range(len(df_formatado)):
            for col_num, col_name in enumerate(df_formatado.columns):
                val = df_formatado.iloc[row_num, col_num]
                if "Valor" in col_name or "Taxa" in col_name:
                    worksheet.write_number(
                        row_num + 1, col_num, float(val or 0.0), fmt_moeda
                    )
                elif "Data" in col_name:
                    worksheet.write(row_num + 1, col_num, str(val or ""), fmt_data)
                else:
                    worksheet.write(row_num + 1, col_num, str(val or ""), fmt_celula)

        for col_num, col_name in enumerate(df_formatado.columns):
            max_len = (
                max(
                    (
                        df_formatado[col_name].astype(str).map(len).max()
                        if not df_formatado.empty
                        else 0
                    ),
                    len(col_name),
                )
                + 4
            )
            worksheet.set_column(col_num, col_num, min(max_len, 45))

        worksheet.freeze_panes(1, 0)

    return buffer.getvalue()


def renderizar_aba_fluxo_caixa():
    """Exibe o painel de fluxo de caixa, filtros, IA e exportação."""
    garantir_colunas_documentacao()

    st.markdown(
        "<h2 style='text-align: center; color: #C71585;'>📊 Fluxo de Caixa"
        " Geral — Farmácia Jr.</h2>",
        unsafe_allow_html=True,
    )
    st.write(
        "Gerencie os registros financeiros de forma manual ou faça o upload"
        " automatizado de extratos lidos por IA."
    )

    lista_meses = [
        "Janeiro",
        "Fevereiro",
        "Março",
        "Abril",
        "Maio",
        "Junho",
        "Julho",
        "Agosto",
        "Setembro",
        "Outubro",
        "Novembro",
        "Dezembro",
    ]

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT * FROM fluxo_caixa_geral ORDER BY data DESC, id DESC", conn
    )
    conn.close()

    aba_manual, aba_pdf = st.tabs(
        ["➕ Registro Manual", "🤖 Importar por IA (PDF)"]
    )

    with aba_manual:
        with st.expander("Abrir Formulário de Operação Manual"):
            data = st.date_input("Data do Lançamento", value=datetime.now())
            depto = st.selectbox(
                "Departamento",
                ["VP", "IMAGEM", "AR", "PRESIDÊNCIA", "PROJETOS", "NEGÓCIOS"],
            )
            tipo = st.selectbox("Tipo", ["Receita", "Despesa"])
            cat = st.selectbox(
                "Categoria",
                ["Serviço Prestado", "ADM: Operacional", "Marketing", "Eventos"],
            )
            desc = st.text_input("Descrição")
            v_bruto = st.number_input("Valor Bruto (R$)", min_value=0.0)
            v_taxa = st.number_input("Taxas (R$)", min_value=0.0, value=0.0)
            v_liq = v_bruto - v_taxa
            conta = st.selectbox(
                "Conta de Origem", ["Banco do Brasil", "PicPay", "Caixa"]
            )
            pagamento = st.selectbox(
                "Status do Pagamento", ["🟢 Pago", "🟡 Pendente"]
            )
            nf = st.selectbox(
                "Nota Fiscal",
                ["🟢 Emitida", "🟡 Aguardando Emissão", "⚪ Não se aplica"],
            )
            onvio = st.selectbox("Status na Onvio", ["❌ Não enviado", "Enviado"])

            if st.button("Confirmar Lançamento Manual"):
                if not desc:
                    st.error("Por favor, digite uma descrição para a movimentação.")
                else:
                    mes_nome = lista_meses[data.month - 1]
                    salvar_lancamento(
                        mes_nome,
                        data.strftime("%Y-%m-%d"),
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
                    )
                    st.success("Lançamento manual salvo!")
                    st.rerun()

    with aba_pdf:
        st.markdown("#### 🤖 Leitura Cognitiva de Extratos com Gemini")
        st.caption(
            "Faça o upload do PDF. O Gemini lerá linha por linha de forma"
            " inteligente, mapeando os valores automaticamente."
        )

        arquivo_pdf = st.file_uploader(
            "Escolha o arquivo do Extrato (.pdf)",
            type=["pdf"],
            key="uploader_ia_fluxo",
        )
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
                    st.write(
                        f"📋 **{len(lancamentos_ia)} lançamentos mapeados com sucesso pela IA:**"
                    )

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
                            "categoria": (
                                "ADM: Operacional"
                                if item.get("tipo") == "Despesa"
                                else "Serviço Prestado"
                            ),
                            "descricao": item.get("descricao", "Lançamento sem nome"),
                            "valor_bruto": float(item.get("valor_bruto", 0.0)),
                            "taxa": 0.0,
                            "valor_liquido": float(item.get("valor_bruto", 0.0)),
                            "conta_origem": "Banco do Brasil",
                            "status_pagamento": "🟢 Pago",
                            "nota_fiscal": "⚪ Não se aplica",
                            "status_onvio": "❌ Não enviado",
                        })

                    df_previa = pd.DataFrame(dados_finais)
                    st.dataframe(
                        df_previa[["data", "tipo", "descricao", "valor_bruto"]],
                        use_container_width=True,
                    )

                    if st.button(
                        "📥 Aprovar e Injetar Transações da IA", type="primary"
                    ):
                        for lancamento in dados_finais:
                            salvar_lancamento(
                                lancamento["mes"],
                                lancamento["data"],
                                lancamento["departamento"],
                                lancamento["tipo"],
                                lancamento["categoria"],
                                lancamento["descricao"],
                                lancamento["valor_bruto"],
                                lancamento["taxa"],
                                lancamento["valor_liquido"],
                                lancamento["conta_origem"],
                                lancamento["status_pagamento"],
                                lancamento["nota_fiscal"],
                                lancamento["status_onvio"],
                            )
                        st.success(
                            "Extrato conciliado pela IA e salvo no banco de dados!"
                        )
                        st.rerun()
                else:
                    st.warning(
                        "A IA não encontrou lançamentos válidos no texto do extrato."
                    )
            else:
                st.error("Não foi possível extrair nenhum texto desse PDF. Se for uma imagem digitalizada, tente exportar o extrato original em PDF do seu banco.")

    st.markdown("---")

    if not df.empty:
        receitas_pagas = df[
            (df["tipo"] == "Receita")
            & (df["status_pagamento"].str.contains("Pago", na=False))
        ]["valor_liquido"].sum()
        despesas_pagas = df[
            (df["tipo"] == "Despesa")
            & (df["status_pagamento"].str.contains("Pago", na=False))
        ]["valor_liquido"].sum()
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
        filtro_depto = c_f2.selectbox(
            "Filtrar por Diretoria:",
            ["Todas", "IMAGEM", "AR", "VP", "PRESIDÊNCIA", "PROJETOS", "NEGÓCIOS"],
        )
        filtro_status = c_f3.selectbox(
            "Filtrar por Pagamento:", ["Todos", "🟢 Pago", "🟡 Pendente"]
        )

        df_filtrado = df.copy()
        if filtro_mes != "Todos":
            df_filtrado = df_filtrado[df_filtrado["mes"] == filtro_mes]
        if filtro_depto != "Todas":
            df_filtrado = df_filtrado[df_filtrado["departamento"] == filtro_depto]
        if filtro_status != "Todos":
            status_busca = "Pendente" if "Pendente" in filtro_status else "Pago"
            df_filtrado = df_filtrado[
                df_filtrado["status_pagamento"].str.contains(status_busca, na=False)
            ]

        excel_estilizado_bytes = gerar_excel_estilizado(df_filtrado)

        st.download_button(
            label="📊 Baixar Relatório Consolidado em Excel (.xlsx)",
            data=excel_estilizado_bytes,
            file_name=(
                "Planilha_Fluxo_Caixa_FarmaciaJr_"
                f"{datetime.now().strftime('%Y-%m-%d')}.xlsx"
            ),
            mime=(
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            use_container_width=True,
        )

        st.markdown(
            f"#### 📄 Lançamentos Encontrados ({len(df_filtrado)} registros)"
        )
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
                col_l2.caption(
                    f"📁 Setor: {row['departamento']} | Categoria: {row['categoria']} |"
                    f" Conta: {row['conta_origem']}"
                )

                col_l3.write(f"💸 **Líq:** R$ {row['valor_liquido']:.2f}")
                col_l3.caption(
                    f"Status: {row['status_pagamento']} | NF: {row['nota_fiscal']}"
                )

                if col_l4.button(
                    "🗑️", key=f"del_fluxo_{row['id']}", help="Excluir lançamento"
                ):
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute(
                        "DELETE FROM fluxo_caixa_geral WHERE id = ?", (row["id"],)
                    )
                    conn.commit()
                    conn.close()
                    st.success("Removido!")
                    st.rerun()
            st.markdown(
                "<hr style='margin: 4px 0; border: 0.5px solid #F8F8F8;'>",
                unsafe_allow_html=True,
            )
    else:
        st.info("A tabela de fluxo de caixa está limpa no momento.")
