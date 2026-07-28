import io
import os
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
import streamlit as st

DB_PATH = "database/financeiro_v2.db"
FUSO_BR = ZoneInfo("America/Sao_Paulo")


def obter_agora_br():
    """Retorna o datetime atual no fuso horário de Brasília."""
    return datetime.now(FUSO_BR)


def inicializar_banco_leads():
    """Garante a existência da pasta e cria/atualiza a tabela no SQLite unificado."""
    if not os.path.exists("database"):
        os.makedirs("database")

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS leads_vp_auditoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa TEXT UNIQUE,
            assessor TEXT,
            valor_precificacao REAL,
            comportamento_preco TEXT,
            recorrencia_cliente TEXT,
            stage_funil TEXT DEFAULT '🎯 Lead',
            link_contrato TEXT,
            link_termo_abertura TEXT,
            link_termo_fechamento TEXT,
            tipo_boleto TEXT,
            link_boletos TEXT,
            status_nota_fiscal TEXT,
            data_auditoria TEXT,
            obs_comercial TEXT,
            obs_financeiro TEXT,
            obs_juridico TEXT,
            obs_licoes TEXT,
            observacoes_vp TEXT
        )
    """)

    # Garante a existência de novas colunas caso a tabela já existisse na versão antiga
    cursor.execute("PRAGMA table_info(leads_vp_auditoria)")
    cols_existentes = [col[1] for col in cursor.fetchall()]

    novas_colunas = {
        "stage_funil": "TEXT DEFAULT '🎯 Lead'",
        "obs_comercial": "TEXT",
        "obs_financeiro": "TEXT",
        "obs_juridico": "TEXT",
        "obs_licoes": "TEXT",
    }

    for col, def_type in novas_colunas.items():
        if col not in cols_existentes:
            cursor.execute(
                f"ALTER TABLE leads_vp_auditoria ADD COLUMN {col} {def_type}"
            )

    conn.commit()
    conn.close()


def calcular_compliance_e_risco(row):
    """Calcula a taxa de compliance documental e o nível de risco do projeto."""
    docs_obrigatorios = [
        bool(row.get("link_contrato")),
        bool(row.get("link_termo_abertura")),
        bool(row.get("link_termo_fechamento")),
        bool(row.get("link_boletos")),
        "Emitida" in str(row.get("status_nota_fiscal", "")),
    ]

    pontos = sum(docs_obrigatorios)
    taxa = (pontos / len(docs_obrigatorios)) * 100

    if taxa >= 80:
        risco_label = "🟢 BAIXO RISCO (Conforme)"
        risco_cor = "#2E7D32"
    elif taxa >= 40:
        risco_label = "🟡 MÉDIO RISCO (Atenção às Pendências)"
        risco_cor = "#F57F17"
    else:
        risco_label = "🔴 ALTO RISCO (Inconformidade Crítica)"
        risco_cor = "#C62828"

    return taxa, risco_label, risco_cor, pontos, len(docs_obrigatorios)


def gerar_dossie_executivo_pdf(row):
    """Gera um Dossiê Executivo de Auditoria e Governança corporativo em PDF."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    story = []

    styles = getSampleStyleSheet()

    color_primary = colors.HexColor("#C71585")  # Magenta Institucional
    color_dark = colors.HexColor("#1A1A1A")
    color_bg_light = colors.HexColor("#F8FAFC")

    title_style = ParagraphStyle(
        "HeaderTitle",
        parent=styles["Heading1"],
        fontSize=18,
        leading=22,
        textColor=color_primary,
        fontName="Helvetica-Bold",
        alignment=1,
    )
    subtitle_style = ParagraphStyle(
        "HeaderSubtitle",
        parent=styles["Normal"],
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#64748B"),
        alignment=1,
    )
    section_style = ParagraphStyle(
        "SectionTitle",
        parent=styles["Heading2"],
        fontSize=11,
        leading=15,
        textColor=color_primary,
        fontName="Helvetica-Bold",
        spaceBefore=12,
        spaceAfter=6,
    )
    text_bold = ParagraphStyle(
        "TextBold",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        fontName="Helvetica-Bold",
        textColor=color_dark,
    )
    text_normal = ParagraphStyle(
        "TextNormal",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
        textColor=color_dark,
    )

    taxa_comp, risco_lbl, risco_hex, pontos, total_docs = (
        calcular_compliance_e_risco(row)
    )
    agora_str = obter_agora_br().strftime("%d/%m/%Y às %H:%M")

    # -------------------------------------------------------------
    # 1. CABEÇALHO INSTITUCIONAL
    # -------------------------------------------------------------
    story.append(
        Paragraph("FARMÁCIA JR. UFMG — AUDITORIA & GOVERNANÇA", title_style)
    )
    story.append(
        Paragraph(
            f"DOSSIÊ EXECUTIVO DE PROJETO  |  Nº REGISTRO: #FJ-{row['id']:04d} "
            f" |  EMISSÃO: {agora_str}",
            subtitle_style,
        )
    )
    story.append(Spacer(1, 10))
    story.append(
        HRFlowable(
            width="100%",
            thickness=1.5,
            color=color_primary,
            spaceBefore=2,
            spaceAfter=12,
        )
    )

    # -------------------------------------------------------------
    # 2. RESUMO EXECUTIVO & SCORE DE RISCO
    # -------------------------------------------------------------
    story.append(
        Paragraph("<b>1. Resumo Executivo & Nível de Risco</b>", section_style)
    )

    dados_resumo = [
        [
            Paragraph("<b>Empresa / Lead:</b>", text_bold),
            Paragraph(str(row["empresa"]), text_normal),
            Paragraph("<b>Assessor Responsável:</b>", text_bold),
            Paragraph(str(row["assessor"]), text_normal),
        ],
        [
            Paragraph("<b>Valor Precificado:</b>", text_bold),
            Paragraph(
                f"R$ {float(row['valor_precificacao']):,.2f}", text_normal
            ),
            Paragraph("<b>Fase do Funil (CRM):</b>", text_bold),
            Paragraph(str(row.get("stage_funil", "Lead")), text_normal),
        ],
        [
            Paragraph("<b>Comportamento Preço:</b>", text_bold),
            Paragraph(str(row["comportamento_preco"]), text_normal),
            Paragraph("<b>Fidelidade / Retenção:</b>", text_bold),
            Paragraph(str(row["recorrencia_cliente"]), text_normal),
        ],
        [
            Paragraph("<b>Índice Compliance:</b>", text_bold),
            Paragraph(
                f"<b>{taxa_comp:.0f}%</b> ({pontos}/{total_docs} documentos)",
                text_normal,
            ),
            Paragraph("<b>Matriz de Risco:</b>", text_bold),
            Paragraph(
                f"<font color='{risco_hex}'><b>{risco_lbl}</b></font>",
                text_normal,
            ),
        ],
    ]

    t_resumo = Table(dados_resumo, colWidths=[110, 150, 130, 150])
    t_resumo.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F1F5F9")),
            ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#F1F5F9")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )
    story.append(t_resumo)
    story.append(Spacer(1, 12))

    # -------------------------------------------------------------
    # 3. CHECKLIST DE CONFORMIDADE DOCUMENTAL
    # -------------------------------------------------------------
    story.append(
        Paragraph(
            "<b>2. Checklist de Conformidade Documental (Compliance)</b>",
            section_style,
        )
    )

    def st_icon(condicao):
        return "✔ Conforme / Anexado" if condicao else "✖ Pendente de Envio"

    dados_docs = [
        ["Documento / Etapa Obrigatória", "Status de Verificação"],
        ["Contrato Social / Prestação de Serviço", st_icon(row["link_contrato"])],
        ["Termo de Abertura do Projeto", st_icon(row["link_termo_abertura"])],
        ["Termo de Fechamento / Entregável", st_icon(row["link_termo_fechamento"])],
        [
            f"Pasta de Boletos ({row['tipo_boleto']})",
            st_icon(row["link_boletos"]),
        ],
        ["Emissão da Nota Fiscal", str(row["status_nota_fiscal"])],
    ]

    t_docs = Table(dados_docs, colWidths=[240, 300])
    t_docs.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), color_primary),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
            ("BACKGROUND", (0, 1), (-1, -1), color_bg_light),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    story.append(t_docs)
    story.append(Spacer(1, 12))

    # -------------------------------------------------------------
    # 4. OBSERVAÇÕES E NOTAS ESTRUTURADAS DA VP
    # -------------------------------------------------------------
    story.append(
        Paragraph(
            "<b>3. Parecer Técnico e Apontamentos Estruturados</b>",
            section_style,
        )
    )

    dados_obs = [
        [
            Paragraph("<b>Estratégia Comercial:</b>", text_bold),
            Paragraph(
                row.get("obs_comercial") or "Sem observações comerciais.",
                text_normal,
            ),
        ],
        [
            Paragraph("<b>Governança Financeira:</b>", text_bold),
            Paragraph(
                row.get("obs_financeiro") or "Sem observações financeiras.",
                text_normal,
            ),
        ],
        [
            Paragraph("<b>Conformidade Jurídica:</b>", text_bold),
            Paragraph(
                row.get("obs_juridico") or "Sem apontamentos jurídicos.",
                text_normal,
            ),
        ],
        [
            Paragraph("<b>Lições Aprendidas:</b>", text_bold),
            Paragraph(
                row.get("obs_licoes") or "Nenhuma lição registrada.",
                text_normal,
            ),
        ],
    ]

    t_obs = Table(dados_obs, colWidths=[140, 400])
    t_obs.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#F8FAFC")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ])
    )
    story.append(t_obs)
    story.append(Spacer(1, 15))

    # Parecer Automático
    if taxa_comp == 100:
        parecer_auto = "<b>CONCLUSÃO:</b> Dossiê 100% auditado e aprovado. Todas as obrigações legais, contábeis e contratuais foram cumpridas satisfatoriamente."
    else:
        parecer_auto = f"<b>PARECER DE PENDÊNCIA:</b> O projeto apresenta {100 - taxa_comp:.0f}% de pendências documentais. A equipe executiva deve providenciar a regularização dos itens não anexados."

    story.append(Paragraph(parecer_auto, text_normal))
    story.append(Spacer(1, 20))

    # Campo de Assinatura Institucional
    dados_ass = [
        [
            Paragraph(
                "__________________________________________<br><b>Vice-Presidência"
                " Financeira</b><br>Farmácia Jr. UFMG",
                ParagraphStyle(
                    "Ass1", parent=text_normal, alignment=1, fontSize=8
                ),
            ),
            Paragraph(
                "__________________________________________<br><b>Assessor"
                " Responsável</b><br>Gerência de Projetos",
                ParagraphStyle(
                    "Ass2", parent=text_normal, alignment=1, fontSize=8
                ),
            ),
        ]
    ]
    t_ass = Table(dados_ass, colWidths=[270, 270])
    t_ass.setStyle(
        TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ])
    )
    story.append(t_ass)

    doc.build(story)
    return buffer.getvalue()


def renderizar_modulo_leads():
    """Renderiza a Central de CRM, Compliance e Dossiês do Módulo de Auditoria."""
    inicializar_banco_leads()

    st.markdown(
        "<h2 style='text-align: center; color: #C71585;'>🎯 CRM Executivo &"
        " Auditoria de Projetos (VP)</h2>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Gestão de ciclo de vida de projetos, controle de compliance"
        " documental e emissão de Dossiês Oficiais."
    )

    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query(
        "SELECT * FROM leads_vp_auditoria ORDER BY id DESC", conn
    )
    conn.close()

    # =======================================================================
    # 📊 CARDS DE KPIS & ESTATÍSTICAS DO CRM
    # =======================================================================
    if not df.empty:
        tot_dossies = len(df)
        nf_emitidas = len(
            df[df["status_nota_fiscal"].str.contains("Emitida", na=False)]
        )

        compliance_lista = [calcular_compliance_e_risco(r)[0] for _, r in df.iterrows()]
        taxa_media_comp = (
            sum(compliance_lista) / len(compliance_lista)
            if compliance_lista
            else 0.0
        )

        recorrentes = len(
            df[df["recorrencia_cliente"].str.contains("recorrente", na=False)]
        )
        perc_recorrentes = (recorrentes / tot_dossies) * 100 if tot_dossies > 0 else 0.0

        ticket_medio = df["valor_precificacao"].mean()
        projetos_pendentes = len([c for c in compliance_lista if c < 100])

        m1, m2, m3, m4, m5, m6 = st.columns(6)
        m1.metric("Projetos", f"{tot_dossies} un")
        m2.metric("Ticket Médio", f"R$ {ticket_medio:,.0f}")
        m3.metric("Compliance", f"{taxa_media_comp:.0f}%")
        m4.metric("Recorrência", f"{perc_recorrentes:.0f}%")
        m5.metric("NFs Emitidas", f"{nf_emitidas} un")
        m6.metric("Com Pendência", f"{projetos_pendentes} un")

        st.markdown("---")

    # =======================================================================
    # TABS: CADASTRO, ATUALIZAÇÃO EVOLUTIVA E EMISSÃO DE DOSSIÊ
    # =======================================================================
    tab_painel, tab_novo, tab_editar = st.tabs([
        "📋 Painel & Dossiês Executivos",
        "➕ Novo Lead / Projeto",
        "✏️ Atualização de Compliance & CRM",
    ])

    # -----------------------------------------------------------------------
    # TAB 1: PAINEL & EMISSÃO DE DOSSIÊS
    # -----------------------------------------------------------------------
    with tab_painel:
        if df.empty:
            st.info("Nenhum projeto registrado no sistema de auditoria.")
        else:
            c_sel1, c_sel2 = st.columns([2, 1])
            empresa_sel = c_sel1.selectbox(
                "Selecione o Projeto / Lead:",
                df["empresa"].unique(),
                key="sb_dossie_select",
            )

            row_sel = df[df["empresa"] == empresa_sel].iloc[0]
            taxa_c, risco_l, risco_hex, ptos, tot_d = (
                calcular_compliance_e_risco(row_sel)
            )

            pdf_bytes = gerar_dossie_executivo_pdf(row_sel)

            c_sel2.write("")
            c_sel2.write("")
            c_sel2.download_button(
                label=f"📥 Baixar Dossiê PDF — {empresa_sel}",
                data=pdf_bytes,
                file_name=f"Dossie_VP_{empresa_sel.replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

            st.markdown("<br>", unsafe_allow_html=True)

            # Painel de Resumo do Projeto Selecionado
            col_p1, col_p2 = st.columns([1.2, 1])

            with col_p1:
                st.markdown(f"#### 📊 Ficha do Projeto: **{empresa_sel}**")
                st.write(
                    f"👤 **Assessor Responsável:** {row_sel['assessor']}"
                )
                st.write(
                    "💰 **Valor Precificado:** R$"
                    f" {row_sel['valor_precificacao']:,.2f}"
                )
                st.write(
                    f"🎯 **Estágio Funil:** {row_sel.get('stage_funil', '🎯 Lead')}"
                )
                st.write(
                    f"🏷️ **Perfil de Preço:** {row_sel['comportamento_preco']}"
                )
                st.write(
                    f"🔄 **Fidelização:** {row_sel['recorrencia_cliente']}"
                )
                st.write(
                    f"🧾 **Nota Fiscal:** {row_sel['status_nota_fiscal']}"
                )

            with col_p2:
                st.markdown("#### 🛡️ Compliance & Matriz de Risco")
                st.markdown(f"**Índice de Documentação:** {taxa_c:.0f}%")
                st.progress(taxa_c / 100.0)

                st.markdown(
                    f"<div style='background-color: {risco_hex}15; border-left:"
                    f" 5px solid {risco_hex}; padding: 10px; border-radius:"
                    f" 6px; margin-top: 10px;'><b>Status de Risco:</b><br><span"
                    f" style='color:{risco_hex};"
                    f" font-weight:bold;'>{risco_l}</span></div>",
                    unsafe_allow_html=True,
                )

            st.markdown("---")
            st.markdown("#### 📁 Checklist de Verificação no Google Drive:")

            def render_link(nome, link):
                if link:
                    st.markdown(
                        f"🟢 **{nome}:** [Acessar Documento no"
                        f" Drive]({link})"
                    )
                else:
                    st.markdown(
                        f"🔴 **{nome}:** <span style='color:red;'>Pendente de"
                        " Anexo</span>",
                        unsafe_allow_html=True,
                    )

            col_chk1, col_chk2 = st.columns(2)
            with col_chk1:
                render_link("Contrato Assinado", row_sel["link_contrato"])
                render_link("Termo de Abertura", row_sel["link_termo_abertura"])
            with col_chk2:
                render_link(
                    "Termo de Fechamento", row_sel["link_termo_fechamento"]
                )
                render_link(
                    f"Pasta de Boletos ({row_sel['tipo_boleto']})",
                    row_sel["link_boletos"],
                )

            st.markdown("---")
            # Exclusão com confirmação
            if st.button(
                f"🗑️ Excluir Dossiê de {empresa_sel}",
                key=f"del_dos_{row_sel['id']}",
            ):
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM leads_vp_auditoria WHERE id = ?",
                    (row_sel["id"],),
                )
                conn.commit()
                conn.close()

                if "sb_dossie_select" in st.session_state:
                    del st.session_state["sb_dossie_select"]

                st.success("Dossiê removido!")
                st.rerun()

    # -----------------------------------------------------------------------
    # TAB 2: NOVO CADASTRO DE LEAD
    # -----------------------------------------------------------------------
    with tab_novo:
        st.markdown("#### ➕ Iniciar Novo Lead / Projeto no CRM")

        with st.form("form_novo_lead_crm", clear_on_submit=True):
            f1, f2 = st.columns(2)
            emp = f1.text_input("Empresa / Cliente Contratante:").strip().title()
            ass = f2.text_input("Assessor Executivo do Projeto:").strip().title()

            f3, f4, f5 = st.columns(3)
            val = f3.number_input(
                "Valor Precificado (R$):", min_value=0.0, value=1000.0
            )
            funil = f4.selectbox(
                "Fase Inicial no Funil:",
                [
                    "🎯 Lead",
                    "📄 Proposta",
                    "🤝 Contrato",
                    "⚙️ Em Execução",
                    "🏁 Finalizado",
                ],
            )
            comp = f5.selectbox(
                "Comportamento do Preço:",
                [
                    "🟢 Aceitou o valor normal de tabela",
                    "🟡 Fechou com desconto negociado",
                    "🔴 Exigiu desconto agressivo para fechar",
                ],
            )

            rec = st.selectbox(
                "Fidelização do Cliente:",
                [
                    "🆕 Primeiro serviço com a Farmácia Jr.",
                    "🔄 Cliente recorrente (Já voltou mais vezes)",
                    "📈 Grande potencial de retorno para novos escopos",
                ],
            )

            if st.form_submit_button(
                "🚀 Abrir Dossiê & Registrar no CRM", use_container_width=True
            ):
                if emp and ass:
                    agora_d = obter_agora_br().strftime("%d/%m/%Y")
                    try:
                        conn = sqlite3.connect(DB_PATH)
                        cursor = conn.cursor()
                        cursor.execute(
                            """
                            INSERT INTO leads_vp_auditoria (
                                empresa, assessor, valor_precificacao, comportamento_preco, 
                                recorrencia_cliente, stage_funil, link_contrato, link_termo_abertura, 
                                link_termo_fechamento, tipo_boleto, link_boletos, status_nota_fiscal, 
                                data_auditoria, observacoes_vp
                            ) VALUES (?, ?, ?, ?, ?, ?, '', '', '', 'Boleto Único', '', '🟡 Aguardando Emissão', ?, '')
                        """,
                            (emp, ass, val, comp, rec, funil, agora_d),
                        )
                        conn.commit()
                        conn.close()
                        st.success(f"Dossiê do projeto {emp} aberto!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error(
                            "Esta empresa já possui um Dossiê cadastrado no"
                            " sistema."
                        )
                else:
                    st.error("Preencha ao menos o nome do cliente e o assessor.")

    # -----------------------------------------------------------------------
    # TAB 3: ATUALIZAÇÃO EVOLUTIVA & ANEXOS
    # -----------------------------------------------------------------------
    with tab_editar:
        if df.empty:
            st.info("Nenhum projeto cadastrado para editar.")
        else:
            emp_edit = st.selectbox(
                "Selecione o Projeto para Atualizar:",
                df["empresa"].unique(),
                key="sb_edit_lead",
            )
            r_e = df[df["empresa"] == emp_edit].iloc[0]

            with st.form("form_edicao_crm"):
                st.caption(f"Editando informações de **{emp_edit}**")

                e1, e2, e3 = st.columns(3)
                v_funil = e1.selectbox(
                    "Estágio Atual do Projeto:",
                    [
                        "🎯 Lead",
                        "📄 Proposta",
                        "🤝 Contrato",
                        "⚙️ Em Execução",
                        "🏁 Finalizado",
                        "❌ Cancelado",
                    ],
                    index=[
                        "🎯 Lead",
                        "📄 Proposta",
                        "🤝 Contrato",
                        "⚙️ Em Execução",
                        "🏁 Finalizado",
                        "❌ Cancelado",
                    ].index(r_e.get("stage_funil", "🎯 Lead")),
                )

                idx_bol = (
                    [
                        "Boleto Único",
                        "Múltiplos Boletos (Parcelado)",
                    ].index(r_e["tipo_boleto"])
                    if r_e["tipo_boleto"]
                    in ["Boleto Único", "Múltiplos Boletos (Parcelado)"]
                    else 0
                )
                v_bol = e2.selectbox(
                    "Modelo de Faturamento:",
                    ["Boleto Único", "Múltiplos Boletos (Parcelado)"],
                    index=idx_bol,
                )

                idx_nf = (
                    [
                        "🟢 Emitida e Entregue",
                        "🟡 Aguardando Emissão",
                        "⚪ Não se aplica",
                    ].index(r_e["status_nota_fiscal"])
                    if r_e["status_nota_fiscal"]
                    in [
                        "🟢 Emitida e Entregue",
                        "🟡 Aguardando Emissão",
                        "⚪ Não se aplica",
                    ]
                    else 1
                )
                v_nf = e3.selectbox(
                    "Status da Nota Fiscal:",
                    [
                        "🟢 Emitida e Entregue",
                        "🟡 Aguardando Emissão",
                        "⚪ Não se aplica",
                    ],
                    index=idx_nf,
                )

                st.markdown("##### 🔗 Links dos Documentos no Google Drive:")
                l_cont = st.text_input(
                    "Link do Contrato Assinado:", value=r_e["link_contrato"]
                )
                l_abert = st.text_input(
                    "Link do Termo de Abertura:", value=r_e["link_termo_abertura"]
                )
                l_fech = st.text_input(
                    "Link do Termo de Fechamento:",
                    value=r_e["link_termo_fechamento"],
                )
                l_boletos = st.text_input(
                    "Link da Pasta de Boletos:", value=r_e["link_boletos"]
                )

                st.markdown("##### 📝 Apontamentos Estruturados da VP:")
                obs_com = st.text_input(
                    "Estratégia Comercial:",
                    value=r_e.get("obs_comercial") or "",
                )
                obs_fin = st.text_input(
                    "Governança Financeira:",
                    value=r_e.get("obs_financeiro") or "",
                )
                obs_jur = st.text_input(
                    "Conformidade Jurídica:",
                    value=r_e.get("obs_juridico") or "",
                )
                obs_lic = st.text_input(
                    "Lições Aprendidas:", value=r_e.get("obs_licoes") or ""
                )

                if st.form_submit_button(
                    "💾 Salvar Atualizações do Dossiê", use_container_width=True
                ):
                    conn = sqlite3.connect(DB_PATH)
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        UPDATE leads_vp_auditoria 
                        SET stage_funil=?, tipo_boleto=?, status_nota_fiscal=?, 
                            link_contrato=?, link_termo_abertura=?, link_termo_fechamento=?, link_boletos=?,
                            obs_comercial=?, obs_financeiro=?, obs_juridico=?, obs_licoes=?
                        WHERE empresa=?
                    """,
                        (
                            v_funil,
                            v_bol,
                            v_nf,
                            l_cont,
                            l_abert,
                            l_fech,
                            l_boletos,
                            obs_com,
                            obs_fin,
                            obs_jur,
                            obs_lic,
                            emp_edit,
                        ),
                    )
                    conn.commit()
                    conn.close()

                    st.success("Dossiê e CRM atualizados com sucesso!")
                    st.rerun()
