import io
import os
import sqlite3
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from modulos.fluxo_caixa import salvar_lancamento

DB_PATH = "database/financeiro_v2.db"


def inicializar_banco_eventos():
    """Garante a existência do diretório e de todas as tabelas necessárias no SQLite."""
    if not os.path.exists("database"):
        os.makedirs("database")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Tabela de Lista de Eventos (Permite adicionar dinamicamente)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS cadastro_eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL
        )
    """)

    # Inserção de eventos padrão se estiver vazia
    cursor.execute("SELECT COUNT(*) FROM cadastro_eventos")
    if cursor.fetchone()[0] == 0:
        eventos_padrao = [
            ("DDA (Dia do Açaí)",),
            ("SIMCOM (Simpósio de Cosméticos)",),
            ("JOFARM (Jornada Farmacêutica)",),
            ("SEFARM (Simpósio de Farmácia)",),
        ]
        cursor.executemany(
            "INSERT INTO cadastro_eventos (nome) VALUES (?)", eventos_padrao
        )

    # Tabela de Custos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custos_eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evento TEXT,
            item TEXT,
            valor REAL,
            data TEXT,
            status TEXT DEFAULT '🟢 Pago'
        )
    """)

    # Garantir coluna status em custos
    cursor.execute("PRAGMA table_info(custos_eventos)")
    colunas_custos = [col[1] for col in cursor.fetchall()]
    if "status" not in colunas_custos:
        cursor.execute(
            "ALTER TABLE custos_eventos ADD COLUMN status TEXT DEFAULT '🟢 Pago'"
        )

    # Tabela de Patrocínios
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patrocinios_eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            evento TEXT,
            empresa TEXT,
            valor REAL,
            data TEXT
        )
    """)

    # Tabela Sympla
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sympla_consolidado (
            evento TEXT PRIMARY KEY,
            ingressos_vendidos INTEGER,
            faturamento_bruto REAL,
            taxa_porcentagem REAL,
            meta_ingressos INTEGER
        )
    """)

    # Tabela do Fluxo de Caixa Geral (garante que consultas ao DDA não falhem)
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
    """Gera o relatório em Excel do Evento com a mesma identidade e layout estilizado do Fluxo de Caixa."""
    buffer = io.BytesIO()

    is_dda = "DDA" in evento
    label_vendas = (
        "Vendas Totem (Balcão)" if is_dda else "Ingressos Vendidos (Sympla)"
    )
    label_bruto = (
        "Faturamento Bruto Balcão" if is_dda else "Faturamento Bruto (Sympla)"
    )
    label_liq = (
        "Faturamento Líquido (Sem Taxa)"
        if is_dda
        else "Faturamento Líquido (Sympla)"
    )

    resumo_data = {
        "Indicador Financeiro": [
            label_vendas,
            label_bruto,
            label_liq,
            "Aporte de Patrocínios",
            "Receita Total Realizada",
            "Custos Operacionais Pagos",
            "Custos Orçados (Previsão)",
            "LUCRO LÍQUIDO DO PROJETO",
            "Ponto de Equilíbrio (Break-Even)",
        ],
        "Valor / Métrica": [
            f"{ing_totais} un",
            bruto,
            liquido,
            patrocinios,
            liquido + patrocinios,
            custos_pagos,
            custos_orcados,
            lucro,
            break_even,
        ],
    }
    df_resumo = pd.DataFrame(resumo_data)

    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        # 1. ABA RESUMO EXECUTIVO
        df_resumo.to_excel(writer, sheet_name="Resumo Executivo", index=False)

        # 2. ABA CUSTOS
        df_c_export = df_c.copy()
        if not df_c_export.empty and "evento" in df_c_export.columns:
            df_c_export = df_c_export.drop(columns=["evento", "id"], errors="ignore")
            df_c_export = df_c_export.rename(
                columns={"data": "Data", "item": "Insumo / Item", "valor": "Valor (R$)", "status": "Status"}
            )
        else:
            df_c_export = pd.DataFrame([{"Aviso": "Nenhum custo registrado"}])
        df_c_export.to_excel(writer, sheet_name="Detalhamento de Custos", index=False)

        # 3. ABA PATROCÍNIOS
        df_p_export = df_p.copy()
        if not df_p_export.empty and "evento" in df_p_export.columns:
            df_p_export = df_p_export.drop(columns=["evento", "id"], errors="ignore")
            df_p_export = df_p_export.rename(
                columns={"data": "Data", "empresa": "Parceiro / Empresa", "valor": "Valor (R$)"}
            )
        else:
            df_p_export = pd.DataFrame([{"Aviso": "Nenhum patrocínio registrado"}])
        df_p_export.to_excel(writer, sheet_name="Patrocínios Captados", index=False)

        workbook = writer.book

        # Estilos padronizados (Iguaizinhos ao Fluxo de Caixa)
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

        # Estilizar cada aba criada
        for sheet_name, df_aba in [
            ("Resumo Executivo", df_resumo),
            ("Detalhamento de Custos", df_c_export),
            ("Patrocínios Captados", df_p_export),
        ]:
            worksheet = writer.sheets[sheet_name]

            # Escrever Cabeçalho
            for col_num, value in enumerate(df_aba.columns):
                worksheet.write(0, col_num, value, fmt_cabecalho)

            # Escrever Dados
            for row_num in range(len(df_aba)):
                for col_num, col_name in enumerate(df_aba.columns):
                    val = df_aba.iloc[row_num, col_num]
                    if isinstance(val, (int, float)) and ("Valor" in str(col_name) or sheet_name == "Resumo Executivo"):
                        worksheet.write_number(row_num + 1, col_num, float(val), fmt_moeda)
                    else:
                        worksheet.write(row_num + 1, col_num, str(val if val is not None else ""), fmt_celula)

            # Auto-ajuste de largura de colunas
            for col_num, col_name in enumerate(df_aba.columns):
                max_len = max(
                    (df_aba[col_name].astype(str).map(len).max() if not df_aba.empty else 0),
                    len(col_name),
                ) + 5
                worksheet.set_column(col_num, col_num, min(max_len, 45))

            worksheet.freeze_panes(1, 0)

    return buffer.getvalue()


def renderizar_gestao_eventos():
    inicializar_banco_eventos()

    st.markdown(
        "<h2 style='text-align: center; color: #FF1493;'>🔬 Planejamento"
        " Estratégico de Eventos — Farmácia Jr.</h2>",
        unsafe_allow_html=True,
    )

    lista_meses = [
        "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
        "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
    ]

    # 1. Carregar lista dinâmica de eventos
    conn = sqlite3.connect(DB_PATH)
    df_lista_ev = pd.read_sql_query(
        "SELECT nome FROM cadastro_eventos ORDER BY id ASC", conn
    )
    conn.close()

    lista_opcoes = ["-- Selecione --"] + df_lista_ev["nome"].tolist()

    c_ev1, c_ev2 = st.columns([3, 1])
    evento_selecionado = c_ev1.selectbox(
        "Selecione o Evento para Planejamento/Gestão:", lista_opcoes
    )

    # ➕ Criar Novo Evento Dinamicamente
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
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute(
                            "INSERT INTO cadastro_eventos (nome) VALUES (?)",
                            (novo_nome_ev,),
                        )
                        conn.commit()
                        conn.close()
                        st.success(f"Evento {novo_nome_ev} criado com sucesso!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Este evento já está cadastrado.")
                else:
                    st.warning("Digite um nome válido.")

    if evento_selecionado != "-- Selecione --":
        is_dda = "DDA" in evento_selecionado
        tag_evento = evento_selecionado.split(" ")[0]

        conn = sqlite3.connect(DB_PATH)
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

        # Separação de Custos Pagos vs Orçados
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

        # Break-Even
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

        # =======================================================================
        # ABA 1: RESUMO EXEC COM GRÁFICOS VISUAIS
        # =======================================================================
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
                label="📥 Exportar Dados para Planilha Oficial Executiva (.xlsx)",
                data=dados_excel,
                file_name=f"planejamento_{tag_evento.lower()}_{datetime.now().strftime('%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )

        # =======================================================================
        # ABA 2: VENDAS / SYMPLA
        # =======================================================================
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
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            INSERT OR REPLACE INTO sympla_consolidado (evento, ingressos_vendidos, faturamento_bruto, taxa_porcentagem, meta_ingressos)
                            VALUES (?, ?, ?, ?, ?)
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
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            INSERT OR REPLACE INTO sympla_consolidado (evento, ingressos_vendidos, faturamento_bruto, taxa_porcentagem, meta_ingressos)
                            VALUES (?, ?, ?, ?, ?)
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

        # =======================================================================
        # ABA 3: CUSTOS OPERACIONAIS (COM STATUS PAGO VS ORÇADO)
        # =======================================================================
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
                        dt_atual = datetime.now()
                        hoje = dt_atual.strftime("%Y-%m-%d")
                        mes_nome = lista_meses[dt_atual.month - 1]
                        desc_completa = f"Gasto {tag_evento}: {desc_c}"

                        conn = sqlite3.connect(DB_PATH)
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
                        conn = sqlite3.connect(DB_PATH)
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

        # =======================================================================
        # ABA 4: PATROCÍNIOS
        # =======================================================================
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
                        dt_atual = datetime.now()
                        hoje = dt_atual.strftime("%Y-%m-%d")
                        mes_nome = lista_meses[dt_atual.month - 1]
                        desc_completa = f"Patrocínio {tag_evento}: {emp_p}"

                        conn = sqlite3.connect(DB_PATH)
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
                        conn = sqlite3.connect(DB_PATH)
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

        # =======================================================================
        # 🧮 SIMULADOR DE INGRESSOS E LOTES
        # =======================================================================
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
