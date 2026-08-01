import io
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import psycopg2
import streamlit as st

from modulos.fluxo_caixa import salvar_lancamento
from database.conexao_db import get_connection

FUSO_BR = ZoneInfo("America/Sao_Paulo")


def obter_agora_br():
    """Retorna o datetime atual no fuso horário de Brasília."""
    return datetime.now(FUSO_BR)


def obter_cor_evento(evento_nome):
    ev_upper = evento_nome.upper()
    if "DDA" in ev_upper:
        return "#C71585", "#FDF2F8"
    elif "SEFARM" in ev_upper:
        return "#008080", "#F0FDF4"
    elif "SIMCOM" in ev_upper:
        return "#8A2BE2", "#FAF5FF"
    elif "JOFARM" in ev_upper:
        return "#1E90FF", "#EFF6FF"
    else:
        return "#FF1493", "#FFF0F5"


def gerar_excel_didatico(
    evento,
    ing_totais,
    bruto,
    liquido,
    custos_pagos,
    custos_orcados,
    patrocinios,
    lucro,
    break_even,
    df_c,
    df_p,
):
    buffer = io.BytesIO()

    cor_primaria, cor_fundo_suave = obter_cor_evento(evento)
    receita_total = liquido + patrocinios
    total_custos = custos_pagos + custos_orcados
    roi = ((lucro / total_custos) * 100) if total_custos > 0 else 0.0

    agora = obter_agora_br()

    if lucro > 0:
        parecer_texto = (
            f"🟢 PROJETO SUPERAVITÁRIO: O evento apresentou desempenho excelente, gerando R$ {lucro:,.2f} de lucro líquido "
            f"com margem de retorno (ROI) de {roi:.1f}%."
        )
    elif lucro == 0:
        parecer_texto = "🟡 PONTO DE EQUILÍBRIO: O evento cobriu exatamente suas despesas operacionais, sem lucro ou prejuízo acumulado."
    else:
        parecer_texto = (
            f"🔴 ATENÇÃO - DEFICITÁRIO: O evento registrou déficit de R$ {abs(lucro):,.2f}. Recomenda-se reforçar a captação de patrocínios "
            f"ou rever os custos operacionais orçados."
        )

    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        workbook = writer.book

        fmt_capa_titulo = workbook.add_format({
            "bold": True, "font_name": "Arial", "font_size": 18,
            "font_color": "#FFFFFF", "fg_color": cor_primaria,
            "align": "center", "valign": "vcenter",
        })

        fmt_capa_sub = workbook.add_format({
            "italic": True, "font_name": "Arial", "font_size": 10,
            "font_color": "#FFFFFF", "fg_color": cor_primaria,
            "align": "center", "valign": "vcenter",
        })

        fmt_kpi_card_titulo = workbook.add_format({
            "bold": True, "font_name": "Arial", "font_size": 9,
            "font_color": "#555555", "fg_color": cor_fundo_suave,
            "align": "center", "valign": "vcenter",
            "border": 1, "border_color": cor_primaria,
        })

        fmt_kpi_card_valor = workbook.add_format({
            "bold": True, "font_name": "Arial", "font_size": 14,
            "font_color": cor_primaria, "fg_color": "#FFFFFF",
            "num_format": "R$ #,##0.00", "align": "center", "valign": "vcenter",
            "border": 1, "border_color": cor_primaria,
        })

        fmt_kpi_lucro_positivo = workbook.add_format({
            "bold": True, "font_name": "Arial", "font_size": 14,
            "font_color": "#2E7D32", "fg_color": "#E8F5E9",
            "num_format": "R$ #,##0.00", "align": "center", "valign": "vcenter",
            "border": 1, "border_color": "#2E7D32",
        })

        fmt_kpi_lucro_negativo = workbook.add_format({
            "bold": True, "font_name": "Arial", "font_size": 14,
            "font_color": "#C62828", "fg_color": "#FFEBEE",
            "num_format": "R$ #,##0.00", "align": "center", "valign": "vcenter",
            "border": 1, "border_color": "#C62828",
        })

        fmt_secao_titulo = workbook.add_format({
            "bold": True, "font_name": "Arial", "font_size": 11,
            "font_color": cor_primaria, "bottom": 2, "bottom_color": cor_primaria,
        })

        fmt_tabela_cabecalho = workbook.add_format({
            "bold": True, "font_name": "Arial", "font_size": 10,
            "font_color": "#FFFFFF", "fg_color": cor_primaria,
            "align": "center", "valign": "vcenter", "border": 1, "border_color": "#D3D3D3",
        })

        fmt_celula = workbook.add_format({
            "font_name": "Arial", "font_size": 9, "align": "left", "valign": "vcenter",
            "border": 1, "border_color": "#E0E0E0",
        })

        fmt_celula_zebra = workbook.add_format({
            "font_name": "Arial", "font_size": 9, "align": "left", "valign": "vcenter",
            "border": 1, "border_color": "#E0E0E0", "bg_color": "#F9FAFB",
        })

        fmt_moeda = workbook.add_format({
            "font_name": "Arial", "font_size": 9, "num_format": "R$ #,##0.00",
            "align": "right", "valign": "vcenter", "border": 1, "border_color": "#E0E0E0",
        })

        fmt_moeda_zebra = workbook.add_format({
            "font_name": "Arial", "font_size": 9, "num_format": "R$ #,##0.00",
            "align": "right", "valign": "vcenter", "border": 1, "border_color": "#E0E0E0",
            "bg_color": "#F9FAFB",
        })

        fmt_parecer = workbook.add_format({
            "font_name": "Arial", "font_size": 9.5, "text_wrap": True,
            "valign": "vcenter", "fg_color": "#F8FAFC", "border": 1, "border_color": "#CBD5E1",
        })

        fmt_rodape = workbook.add_format({
            "font_name": "Arial", "font_size": 8.5, "italic": True,
            "font_color": "#64748B", "align": "center", "valign": "vcenter",
        })

        ws_dash = workbook.add_worksheet("📊 Dashboard Executivo")
        ws_dash.hide_gridlines(2)
        ws_dash.set_landscape()
        ws_dash.set_paper(9)

        ws_dash.merge_range("B2:H3", f"FARMÁCIA JR. — RELATÓRIO EXECUTIVO", fmt_capa_titulo)
        ws_dash.merge_range("B4:H4", f"Projeto: {evento}  |  Gerado em {agora.strftime('%d/%m/%Y às %H:%M')}", fmt_capa_sub)

        ws_dash.write("B6", "📌 INDICADORES CHAVE DE DESEMPENHO (KPIs)", fmt_secao_titulo)

        kpis = [
            ("Faturamento Bruto", bruto, fmt_kpi_card_valor, "B", "C"),
            ("Receita Líquida + Patrocínios", receita_total, fmt_kpi_card_valor, "D", "E"),
            ("Custos Operacionais Totais", total_custos, fmt_kpi_card_valor, "F", "G"),
        ]

        for titulo, valor, fmt_v, c1, c2 in kpis:
            ws_dash.merge_range(f"{c1}7:{c2}7", titulo.upper(), fmt_kpi_card_titulo)
            ws_dash.merge_range(f"{c1}8:{c2}8", valor, fmt_v)

        ws_dash.merge_range("H7:H7", "LUCRO LÍQUIDO", fmt_kpi_card_titulo)
        fmt_lucro_usa = fmt_kpi_lucro_positivo if lucro >= 0 else fmt_kpi_lucro_negativo
        ws_dash.write("H8", lucro, fmt_lucro_usa)

        ws_dash.write("B11", "📊 COMPOSIÇÃO FINANCEIRA DO PROJETO", fmt_secao_titulo)

        ws_dash.write("B13", "Categoria", fmt_tabela_cabecalho)
        ws_dash.write("C13", "Valor (R$)", fmt_tabela_cabecalho)

        dados_grafico = [
            ("Ingressos / Balcão", liquido),
            ("Patrocínios", patrocinios),
            ("Custos Pagos", custos_pagos),
            ("Custos Orçados", custos_orcados),
            ("Lucro Líquido", lucro if lucro > 0 else 0),
        ]

        for i, (rotulo, val) in enumerate(dados_grafico):
            ws_dash.write(13 + i, 1, rotulo, fmt_celula)
            ws_dash.write(13 + i, 2, val, fmt_moeda)

        chart = workbook.add_chart({"type": "column"})
        chart.add_series({
            "name": "Valores R$",
            "categories": "='📊 Dashboard Executivo'!$B$14:$B$18",
            "values": "='📊 Dashboard Executivo'!$C$14:$C$18",
            "fill": {"color": cor_primaria},
            "data_labels": {"value": True, "num_format": "R$ #,##0"},
        })
        chart.set_title({"name": "Distribuição de Receitas e Custos (R$)"})
        chart.set_legend({"none": True})
        chart.set_size({"width": 460, "height": 220})
        ws_dash.insert_chart("D11", chart)

        ws_dash.write("B20", "💬 PARECER DE DESEMPENHO FINANCEIRO", fmt_secao_titulo)
        ws_dash.merge_range("B21:H22", parecer_texto, fmt_parecer)

        ws_dash.write("B24", f"• Ponto de Equilíbrio (Break-Even): {break_even}", fmt_celula)
        ws_dash.write("E24", f"• Ingressos/Copos Vendidos: {ing_totais} un", fmt_celula)
        ws_dash.write("G24", f"• Retorno s/ Investimento (ROI): {roi:.1f}%", fmt_celula)

        ws_dash.merge_range("B26:H26", "Farmácia Jr. UFMG — Gestão Financeira e Estratégica de Projetos", fmt_rodape)

        ws_dash.set_column("A:A", 3)
        ws_dash.set_column("B:H", 18)

        df_c_export = df_c.copy()
        if not df_c_export.empty and "evento" in df_c_export.columns:
            df_c_export = df_c_export.drop(columns=["evento", "id"], errors="ignore")
            df_c_export = df_c_export.rename(
                columns={"data": "Data", "item": "Insumo / Item", "valor": "Valor (R$)", "status": "Status"}
            )
        else:
            df_c_export = pd.DataFrame([{"Data": "-", "Insumo / Item": "Nenhum custo registrado", "Valor (R$)": 0.0, "Status": "-"}])

        ws_custos = workbook.add_worksheet("💸 Custos Operacionais")
        ws_custos.set_landscape()

        for col_num, value in enumerate(df_c_export.columns):
            ws_custos.write(0, col_num, value, fmt_tabela_cabecalho)

        for row_num in range(len(df_c_export)):
            zebra = row_num % 2 == 1
            f_txt = fmt_celula_zebra if zebra else fmt_celula
            f_moeda = fmt_moeda_zebra if zebra else fmt_moeda

            for col_num, col_name in enumerate(df_c_export.columns):
                val = df_c_export.iloc[row_num, col_num]
                if "Valor" in str(col_name):
                    ws_custos.write_number(row_num + 1, col_num, float(val or 0.0), f_moeda)
                else:
                    ws_custos.write(row_num + 1, col_num, str(val if val is not None else ""), f_txt)

        for col_num, col_name in enumerate(df_c_export.columns):
            max_len = max((df_c_export[col_name].astype(str).map(len).max() if not df_c_export.empty else 0), len(col_name)) + 6
            ws_custos.set_column(col_num, col_num, min(max_len, 45))
        ws_custos.freeze_panes(1, 0)

        df_p_export = df_p.copy()
        if not df_p_export.empty and "evento" in df_p_export.columns:
            df_p_export = df_p_export.drop(columns=["evento", "id"], errors="ignore")
            df_p_export = df_p_export.rename(
                columns={"data": "Data", "empresa": "Parceiro / Empresa", "valor": "Valor (R$)"}
            )
        else:
            df_p_export = pd.DataFrame([{"Data": "-", "Parceiro / Empresa": "Nenhum patrocínio registrado", "Valor (R$)": 0.0}])

        ws_pat = workbook.add_worksheet("🤝 Patrocínios")
        ws_pat.set_landscape()

        for col_num, value in enumerate(df_p_export.columns):
            ws_pat.write(0, col_num, value, fmt_tabela_cabecalho)

        for row_num in range(len(df_p_export)):
            zebra = row_num % 2 == 1
            f_txt = fmt_celula_zebra if zebra else fmt_celula
            f_moeda = fmt_moeda_zebra if zebra else fmt_moeda

            for col_num, col_name in enumerate(df_p_export.columns):
                val = df_p_export.iloc[row_num, col_num]
                if "Valor" in str(col_name):
                    ws_pat.write_number(row_num + 1, col_num, float(val or 0.0), f_moeda)
                else:
                    ws_pat.write(row_num + 1, col_num, str(val if val is not None else ""), f_txt)

        for col_num, col_name in enumerate(df_p_export.columns):
            max_len = max((df_p_export[col_name].astype(str).map(len).max() if not df_p_export.empty else 0), len(col_name)) + 6
            ws_pat.set_column(col_num, col_num, min(max_len, 45))
        ws_pat.freeze_panes(1, 0)

    return buffer.getvalue()


def renderizar_gestao_eventos():

    st.markdown(
        "<h2 style='text-align: center; color: #FF1493;'>🔬 Planejamento"
        " Estratégico de Eventos — Farmácia Jr.</h2>",
        unsafe_allow_html=True,
    )

    lista_meses = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
    ]

    conn = get_connection()
    df_lista_ev = pd.read_sql_query(
        "SELECT nome FROM cadastro_eventos ORDER BY id ASC", conn
    )
    conn.close()

    lista_opcoes = ["-- Selecione --"] + df_lista_ev["nome"].tolist()

    c_ev1, c_ev2 = st.columns([3, 1])
    evento_selecionado = c_ev1.selectbox(
        "Selecione o Evento para Planejamento/Gestão:", lista_opcoes
    )

    with c_ev2:
        st.write("")
        st.write("")
        with st.popover("➕ Criar Novo Evento"):
            novo_nome_ev = (
                st.text_input("Nome do Novo Evento/Curso:").strip().upper()
            )
            if st.button("Cadastrar Evento"):
                if novo_nome_ev:
                    try:
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO cadastro_eventos (nome) VALUES (?)",
                            (novo_nome_ev,),
                        )
                        conn.commit()
                        conn.close()
                        st.success(f"Evento {novo_nome_ev} criado com sucesso!")
                        st.rerun()
                    except psycopg2.IntegrityError:
                        st.error("Este evento já está cadastrado.")
                else:
                    st.warning("Digite um nome válido.")

    if evento_selecionado != "-- Selecione --":
        is_dda = "DDA" in evento_selecionado
        tag_evento = evento_selecionado.split(" ")[0]

        conn = get_connection()
        df_sympla = pd.read_sql_query(
            "SELECT * FROM sympla_consolidado WHERE evento = ?",
            conn,
            params=(evento_selecionado,),
        )
        df_custos = pd.read_sql_query(
            "SELECT * FROM custos_eventos WHERE evento = ?",
            conn,
            params=(evento_selecionado,),
        )
        df_patrocinios = pd.read_sql_query(
            "SELECT * FROM patrocinios_eventos WHERE evento = ?",
            conn,
            params=(evento_selecionado,),
        )

        if is_dda:
            df_vendas_totem = pd.read_sql_query(
                "SELECT valor_bruto, valor_liquido FROM fluxo_caixa_geral"
                " WHERE categoria = 'Serviço Prestado' AND descricao LIKE '%Açaí%'",
                conn,
            )
            bruto_calculado = (
                df_vendas_totem["valor_bruto"].sum()
                if not df_vendas_totem.empty
                else 0.0
            )
            liquido_calculado = (
                df_vendas_totem["valor_liquido"].sum()
                if not df_vendas_totem.empty
                else 0.0
            )
            ingressos_totais = len(df_vendas_totem)
            taxa_sympla_perc = 1.99
            meta_ing = (
                df_sympla["meta_ingressos"].iloc[0]
                if not df_sympla.empty
                else 200
            )
        else:
            bruto_calculado = (
                df_sympla["faturamento_bruto"].iloc[0]
                if not df_sympla.empty
                else 0.0
            )
            taxa_sympla_perc = (
                df_sympla["taxa_porcentagem"].iloc[0]
                if not df_sympla.empty
                else 10.0
            )
            liquido_calculado = bruto_calculado * (1 - (taxa_sympla_perc / 100))
            ingressos_totais = (
                df_sympla["ingressos_vendidos"].iloc[0]
                if not df_sympla.empty
                else 0
            )
            meta_ing = (
                df_sympla["meta_ingressos"].iloc[0]
                if not df_sympla.empty
                else 100
            )

        conn.close()

        custos_pagos = (
            df_custos[df_custos["status"] == "🟢 Pago"]["valor"].sum()
            if not df_custos.empty
            else 0.0
        )
        custos_orcados = (
            df_custos[df_custos["status"] == "🟡 Orçado (Previsão)"]["valor"].sum()
            if not df_custos.empty
            else 0.0
        )
        total_custos = custos_pagos + custos_orcados

        total_patrocinios = (
            df_patrocinios["valor"].sum() if not df_patrocinios.empty else 0.0
        )

        receita_total = liquido_calculado + total_patrocinios
        lucro_liquido = receita_total - total_custos
        margem_lucro = (
            (lucro_liquido / receita_total * 100) if receita_total > 0 else 0.0
        )

        preco_medio = (
            (bruto_calculado / ingressos_totais) * (1 - (taxa_sympla_perc / 100))
            if ingressos_totais > 0
            else 0.0
        )
        custo_aberto = total_custos - total_patrocinios

        if custo_aberto <= 0:
            txt_break_even = "Bateu! Patrocínios pagaram tudo."
            cor_be = "#E8F5E9"
            txt_visual_be = "🚀 Custos Pagos por Patrocínio!"
        elif preco_medio == 0:
            txt_break_even = "Sem dados de venda."
            cor_be = "#FFF3E0"
            txt_visual_be = "⏳ Aguardando primeiras vendas..."
        else:
            qtd_necessaria = int(custo_aberto / preco_medio) + (
                1 if (custo_aberto % preco_medio) > 0 else 0
            )
            faltam = qtd_necessaria - ingressos_totais
            if faltam > 0:
                txt_break_even = f"Faltam {faltam} un"
                cor_be = "#FFEBEE"
                txt_visual_be = (
                    f"🎯 Faltam vender {faltam} copos/ingressos para cobrir os custos totais"
                    if is_dda
                    else f"🎯 Faltam vender {faltam} ingressos para lucrar"
                )
            else:
                txt_break_even = "Alcançado!"
                cor_be = "#E8F5E9"
                txt_visual_be = (
                    "🟢 Ponto de Equilíbrio Alcançado! O evento já dá lucro."
                )

        tab_dashboard, tab_sympla, tab_custos, tab_patrocinio, tab_simulador = (
            st.tabs([
                "📊 Resumo Executivo",
                "🎟️ Painel de Vendas" if is_dda else "🎟️ Painel Sympla",
                "💸 Custos Operacionais",
                "🤝 Captação Comercial",
                "🧮 Simulador de Preços",
            ])
        )

        with tab_dashboard:
            st.markdown(f"### 📋 Painel de Desempenho — {tag_evento}")

            if meta_ing > 0:
                progresso = min(float(ingressos_totais) / meta_ing, 1.0)
                label_meta = (
                    f"Vendas Totem: **{ingressos_totais}** de **{meta_ing}** copos"
                    if is_dda
                    else f"Vendas Sympla: **{ingressos_totais}** de **{meta_ing}** ingressos"
                )
                st.markdown(f"{label_meta} ({progresso*100:.1f}%)")
                st.progress(progresso)
            st.markdown("<br>", unsafe_allow_html=True)

            st.markdown(
                f"""
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 20px;">
                <div style="background-color: #FFF0F5; border-left: 5px solid #FF1493; padding: 12px; border-radius: 8px;">
                    <span style="color: #666; font-size: 12px; font-weight: bold;">💰 FATURAMENTO BRUTO</span>
                    <h3 style="color: #FF1493; margin: 3px 0 0 0;">R$ {bruto_calculado:.2f}</h3>
                </div>
                <div style="background-color: #F0F8FF; border-left: 5px solid #1E90FF; padding: 12px; border-radius: 8px;">
                    <span style="color: #666; font-size: 12px; font-weight: bold;">📥 RECEITA LÍQUIDA + PATROCÍNIOS</span>
                    <h3 style="color: #1E90FF; margin: 3px 0 0 0;">R$ {receita_total:.2f}</h3>
                </div>
                <div style="background-color: #F5F5F5; border-left: 5px solid #6c757d; padding: 12px; border-radius: 8px;">
                    <span style="color: #666; font-size: 12px; font-weight: bold;">💸 CUSTOS (PAGOS / ORÇADOS)</span>
                    <h3 style="color: #6c757d; margin: 3px 0 0 0;">R$ {total_custos:.2f}</h3>
                    <span style="color: #888; font-size: 10px;">R$ {custos_pagos:.2f} pagos | R$ {custos_orcados:.2f} a vencer</span>
                </div>
                <div style="background-color: {'#E8F5E9' if lucro_liquido >= 0 else '#FFEBEE'}; border-left: 5px solid {'#2E7D32' if lucro_liquido >= 0 else '#C62828'}; padding: 12px; border-radius: 8px;">
                    <span style="color: #666; font-size: 12px; font-weight: bold;">🎯 LUCRO LÍQUIDO FINAL</span>
                    <h3 style="color: {'#2E7D32' if lucro_liquido >= 0 else '#C62828'}; margin: 3px 0 0 0;">R$ {lucro_liquido:.2f}</h3>
                    <span style="color: #666; font-size: 10px; font-weight: bold;">Margem: {margem_lucro:.1f}%</span>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

            st.markdown(
                f"""
            <div style="background-color: {cor_be}; padding: 12px; border-radius: 8px; text-align: center; font-size: 14px; font-weight: bold; color: #333; margin-bottom: 20px;">
                {txt_visual_be}
            </div>
            """,
                unsafe_allow_html=True,
            )

            if not df_custos.empty:
                st.markdown("#### 📊 Divisão dos Custos por Item")
                fig_custos = px.pie(
                    df_custos,
                    values="valor",
                    names="item",
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Pastel,
                )
                fig_custos.update_layout(margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig_custos, use_container_width=True)

            st.markdown("---")
            dados_excel = gerar_excel_didatico(
                evento_selecionado,
                ingressos_totais,
                bruto_calculado,
                liquido_calculado,
                custos_pagos,
                custos_orcados,
                total_patrocinios,
                lucro_liquido,
                txt_break_even,
                df_custos,
                df_patrocinios,
            )

            st.download_button(
                label="📥 Exportar Relatório Executivo em Excel (.xlsx)",
                data=dados_excel,
                file_name=f"Relatorio_Executivo_{tag_evento.lower()}_{obter_agora_br().strftime('%Y-%m-%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        with tab_sympla:
            if is_dda:
                st.markdown("### 📊 Metas de Vendas do DDA")
                st.info(
                    "💡 O Faturamento e a quantidade de copos vendidos são calculados de forma AUTOMÁTICA e em tempo real via Totem de Vendas Express!"
                )
                with st.form("form_dda_meta"):
                    meta_v = st.number_input(
                        "Definir Meta de Copos para o Evento:",
                        min_value=1,
                        value=int(meta_ing),
                    )
                    if st.form_submit_button("Atualizar Meta do DDA"):
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            INSERT INTO sympla_consolidado (evento, ingressos_vendidos, faturamento_bruto, taxa_porcentagem, meta_ingressos)
                            VALUES (?, ?, ?, ?, ?)
                            ON CONFLICT (evento) DO UPDATE SET
                                ingressos_vendidos = EXCLUDED.ingressos_vendidos,
                                faturamento_bruto = EXCLUDED.faturamento_bruto,
                                taxa_porcentagem = EXCLUDED.taxa_porcentagem,
                                meta_ingressos = EXCLUDED.meta_ingressos
                        """,
                            (
                                evento_selecionado,
                                ingressos_totais,
                                bruto_calculado,
                                taxa_sympla_perc,
                                meta_v,
                            ),
                        )
                        conn.commit()
                        conn.close()
                        st.success("Meta do DDA salva com sucesso!")
                        st.rerun()
            else:
                st.markdown("### Configurações de Lotes do Sympla")
                with st.form("form_sympla_dados"):
                    col_s1, col_s2 = st.columns(2)
                    ing_v = col_s1.number_input(
                        "Ingressos Vendidos no Painel:",
                        min_value=0,
                        value=int(ingressos_totais),
                    )
                    meta_v = col_s2.number_input(
                        "Meta Total de Ingressos do Evento:",
                        min_value=1,
                        value=int(meta_ing),
                    )

                    col_s3, col_s4 = st.columns(2)
                    fat_b = col_s3.number_input(
                        "Faturamento Bruto Acumulado (R$):",
                        min_value=0.0,
                        value=float(bruto_calculado),
                    )
                    taxa_s = col_s4.number_input(
                        "Taxa de Serviço Sympla (%):",
                        min_value=0.0,
                        value=float(taxa_sympla_perc),
                    )

                    if st.form_submit_button("Guardar Configuração Sympla"):
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            INSERT INTO sympla_consolidado (evento, ingressos_vendidos, faturamento_bruto, taxa_porcentagem, meta_ingressos)
                            VALUES (?, ?, ?, ?, ?)
                            ON CONFLICT (evento) DO UPDATE SET
                                ingressos_vendidos = EXCLUDED.ingressos_vendidos,
                                faturamento_bruto = EXCLUDED.faturamento_bruto,
                                taxa_porcentagem = EXCLUDED.taxa_porcentagem,
                                meta_ingressos = EXCLUDED.meta_ingressos
                        """,
                            (
                                evento_selecionado,
                                ing_v,
                                fat_b,
                                taxa_s,
                                meta_v,
                            ),
                        )
                        conn.commit()
                        conn.close()
                        st.success("Dados do Sympla salvos!")
                        st.rerun()

        with tab_custos:
            st.markdown("### Orçamento e Custos de Infraestrutura")

            with st.expander("➕ Adicionar Novo Gasto / Cotação"):
                desc_c = st.text_input("Fornecedor / Insumo:").strip()
                val_c = st.number_input("Custo do Item (R$):", min_value=0.0)
                dep_c = st.selectbox(
                    "Diretoria Executora:",
                    ["PROJETOS", "IMAGEM", "AR", "VP", "PRESIDÊNCIA", "NEGÓCIOS"],
                    key="dep_c",
                )
                status_c = st.selectbox(
                    "Status Financeiro:", ["🟢 Pago", "🟡 Orçado (Previsão)"]
                )

                if st.button("Gravar Linha de Custo"):
                    if desc_c and val_c > 0:
                        agora = obter_agora_br()
                        hoje = agora.strftime("%Y-%m-%d")
                        mes_nome = lista_meses[agora.month - 1]
                        desc_completa = f"Gasto {tag_evento}: {desc_c}"

                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO custos_eventos (evento, item, valor, data, status) VALUES (?, ?, ?, ?, ?)",
                            (
                                evento_selecionado,
                                desc_c,
                                val_c,
                                hoje,
                                status_c,
                            ),
                        )
                        conn.commit()
                        conn.close()

                        if status_c == "🟢 Pago":
                            salvar_lancamento(
                                mes_nome,
                                hoje,
                                dep_c,
                                "Despesa",
                                "Eventos",
                                desc_completa,
                                val_c,
                                0.0,
                                val_c,
                                "Banco do Brasil",
                                "🟢 Pago",
                                "🟢 Emitida",
                                "❌ Não enviado",
                            )
                        st.success("Custo gravado com sucesso!")
                        st.rerun()

            st.markdown("#### Planilha de Despesas Ativas")
            if df_custos.empty:
                st.info("Nenhum custo lançado.")
            else:
                for idx, row in df_custos.iterrows():
                    col_t1, col_t2, col_t3, col_t4 = st.columns([3, 1, 1, 1])
                    status_exibido = (
                        row["status"]
                        if "status" in row and row["status"]
                        else "🟢 Pago"
                    )
                    col_t1.write(f"📅 {row['data']} | **{row['item']}** ({status_exibido})")
                    col_t2.write(f"R$ {row['valor']:.2f}")

                    if col_t3.button("🗑️ Excluir", key=f"del_c_{row['id']}"):
                        desc_para_remover = f"Gasto {tag_evento}: {row['item']}"
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            "DELETE FROM custos_eventos WHERE id = ?",
                            (row["id"],),
                        )
                        cursor.execute(
                            "DELETE FROM fluxo_caixa_geral WHERE descricao = ? AND valor_bruto = ?",
                            (desc_para_remover, row["valor"]),
                        )
                        conn.commit()
                        conn.close()
                        st.success("Custo excluído!")
                        st.rerun()

        with tab_patrocinio:
            st.markdown("### Arrecadação Comercial Externa")

            with st.expander("➕ Adicionar Entrada de Patrocinador Comercial"):
                emp_p = st.text_input("Nome do Parceiro / Laboratório:").strip()
                val_p = st.number_input("Valor Fechado (R$):", min_value=0.0)
                dep_p = st.selectbox(
                    "Diretoria que Captou:",
                    ["NEGÓCIOS", "IMAGEM", "AR", "VP", "PRESIDÊNCIA", "PROJETOS"],
                    key="dep_p",
                )

                if st.button("Gravar Entrada de Patrocínio"):
                    if emp_p and val_p > 0:
                        agora = obter_agora_br()
                        hoje = agora.strftime("%Y-%m-%d")
                        mes_nome = lista_meses[agora.month - 1]
                        desc_completa = f"Patrocínio {tag_evento}: {emp_p}"

                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO patrocinios_eventos (evento, empresa, valor, data) VALUES (?, ?, ?, ?)",
                            (evento_selecionado, emp_p, val_p, hoje),
                        )
                        conn.commit()
                        conn.close()

                        salvar_lancamento(
                            mes_nome,
                            hoje,
                            dep_p,
                            "Receita",
                            "Serviço Prestado",
                            desc_completa,
                            val_p,
                            0.0,
                            val_p,
                            "Banco do Brasil",
                            "🟢 Pago",
                            "🟢 Emitida",
                            "❌ Não enviado",
                        )
                        st.success("Patrocínio gravado e sincronizado no Fluxo de Caixa Geral!")
                        st.rerun()

            st.markdown("#### Histórico de Captações Ativas")
            if df_patrocinios.empty:
                st.info("Nenhum aporte comercial registrado.")
            else:
                for idx, row in df_patrocinios.iterrows():
                    col_p1, col_p2, col_p3 = st.columns([3, 1, 1])
                    col_p1.write(f"📅 {row['data']} | **{row['empresa']}**")
                    col_p2.write(f"R$ {row['valor']:.2f}")
                    if col_p3.button("🗑️ Excluir", key=f"del_p_{row['id']}"):
                        desc_para_remover = f"Patrocínio {tag_evento}: {row['empresa']}"
                        conn = get_connection()
                        cursor = conn.cursor()
                        cursor.execute(
                            "DELETE FROM patrocinios_eventos WHERE id = ?",
                            (row["id"],),
                        )
                        cursor.execute(
                            "DELETE FROM fluxo_caixa_geral WHERE descricao = ? AND valor_bruto = ?",
                            (desc_para_remover, row["valor"]),
                        )
                        conn.commit()
                        conn.close()
                        st.success("Patrocínio excluído!")
                        st.rerun()

        with tab_simulador:
            st.markdown("### 🧮 Calculadora de Lotes e Precificação de Ingressos")
            st.caption(
                "Simule cenários antes de abrir o evento no Sympla ou balcão para garantir a margem de lucro desejada."
            )

            c_sim1, c_sim2 = st.columns(2)
            custo_base_sim = c_sim1.number_input(
                "Custo Total Estimado (R$):",
                value=float(total_custos) if total_custos > 0 else 1000.0,
            )
            patrocinio_sim = c_sim2.number_input(
                "Patrocínios Previstos (R$):", value=float(total_patrocinios)
            )

            c_sim3, c_sim4 = st.columns(2)
            meta_pessoas_sim = c_sim3.number_input(
                "Meta de Participantes (Pessoas):", min_value=1, value=100
            )
            margem_alvo_sim = c_sim4.number_input(
                "Margem de Lucro Desejada (%):", min_value=0.0, value=20.0
            )

            custo_liquido_sim = max(0.0, custo_base_sim - patrocinio_sim)
            receita_necessaria = custo_liquido_sim * (1 + (margem_alvo_sim / 100))

            taxa_simpla = 0.10 if not is_dda else 0.0
            preco_sugerido_bruto = (receita_necessaria / meta_pessoas_sim) / (1 - taxa_simpla)

            st.markdown("---")
            st.markdown("#### 💡 Resultado da Simulação Comercial:")

            res1, res2, res3 = st.columns(3)
            res1.metric(
                "Custo Fixo por Pessoa",
                f"R$ {(custo_liquido_sim / meta_pessoas_sim):.2f}",
            )
            res2.metric(
                "Preço Mínimo (Break-even)",
                f"R$ {((custo_liquido_sim / meta_pessoas_sim) / (1 - taxa_simpla)):.2f}",
            )
            res3.metric(
                "Preço Sugerido (Com Lucro)",
                f"R$ {preco_sugerido_bruto:.2f}",
            )

            st.info(f"""
            📌 **Estratégia Recomendada para os Lotes:**
            * **Lote Promo / Lote 1:** R$ {(preco_sugerido_bruto * 0.85):.2f} *(Para acelerar o caixa no início)*
            * **Lote 2 (Padrão):** R$ {preco_sugerido_bruto:.2f}
            * **Lote 3 (Últimos dias):** R$ {(preco_sugerido_bruto * 1.15):.2f}
            """)
