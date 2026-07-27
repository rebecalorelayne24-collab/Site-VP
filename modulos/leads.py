import streamlit as st
import sqlite3
import pandas as pd
import io
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

def inicializar_banco_leads():
    conn = sqlite3.connect('database/financeiro_farmaciajr.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads_vp_auditoria (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa TEXT UNIQUE,
            assessor TEXT,
            valor_precificacao REAL,
            comportamento_preco TEXT,
            recorrencia_cliente TEXT,
            link_contrato TEXT,
            link_termo_abertura TEXT,
            link_termo_fechamento TEXT,
            tipo_boleto TEXT,
            link_boletos TEXT,
            status_nota_fiscal TEXT,
            data_auditoria TEXT,
            observacoes_vp TEXT
        )
    ''')
    conn.commit()
    conn.close()

def gerar_ata_auditoria_pdf(row):
    """Gera um PDF executivo oficial em formato de Ata de Auditoria do Projeto para a VP"""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], fontSize=18, leading=22, textColor=colors.HexColor('#FF1493'), alignment=1)
    section_style = ParagraphStyle('SectionStyle', parent=styles['Heading2'], fontSize=12, leading=16, textColor=colors.HexColor('#333'), spaceBefore=10, spaceAfter=5)
    text_style = ParagraphStyle('TextStyle', parent=styles['Normal'], fontSize=10, leading=14)
    
    story.append(Paragraph("🦩 ATA DE AUDITORIA E FECHAMENTO DE PROJETO — VP", title_style))
    story.append(Spacer(1, 15))
    
    dados_comerciais = [
        ["Empresa / Lead:", row['empresa'], "Assessor Responsável:", row['assessor']],
        ["Valor Precificado:", f"R$ {row['valor_precificacao']:.2f}", "Data de Registro:", row['data_auditoria']],
        ["Perfil do Preço:", row['comportamento_preco'], "Fidelidade / Retenção:", row['recorrencia_cliente']]
    ]
    t1 = Table(dados_comerciais, colWidths=[110, 150, 120, 150])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#FFF0F5')),
        ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#FFF0F5')),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
    ]))
    
    story.append(Paragraph("<b>1. Identificação Estratégica & Comercial</b>", section_style))
    story.append(t1)
    story.append(Spacer(1, 15))
    
    def formatar_link(link):
        return "Conforme / Anexado" if link else "❌ Pendente de Envio"

    dados_documentos = [
        ["Documento / Processo", "Status / Verificação"],
        ["Contrato Assinado", formatar_link(row['link_contrato'])],
        ["Termo de Abertura", formatar_link(row['link_termo_abertura'])],
        ["Termo de Fechamento", formatar_link(row['link_termo_fechamento'])],
        [f"Boletos ({row['tipo_boleto']})", formatar_link(row['link_boletos'])],
        ["Nota Fiscal", row['status_nota_fiscal']]
    ]
    t2 = Table(dados_documentos, colWidths=[200, 330])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#FF69B4')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#FAFAFA')),
        ('FONTSIZE', (0,0), (-1,-1), 9),
    ]))
    
    story.append(Paragraph("<b>2. Conformidade de Processos e Documentação (Compliance VP)</b>", section_style))
    story.append(t2)
    story.append(Spacer(1, 15))
    
    story.append(Paragraph("<b>3. Parecer e Notas de Acompanhamento da VP</b>", section_style))
    story.append(Paragraph(row['observacoes_vp'] if row['observacoes_vp'] else "Nenhuma observação cadastrada.", text_style))
    
    doc.build(story)
    return buffer.getvalue()

def renderizar_modulo_leads():
    inicializar_banco_leads()
    st.markdown("<h2 style='text-align: center; color: #FF1493;'>🎯 CRM & Auditoria de Projetos (VP)</h2>", unsafe_allow_html=True)
    st.caption("Cadastre o Lead inicial e vá preenchendo os documentos e os termos conforme o projeto avançar.")
    
    # Carrega dados atualizados do banco
    conn = sqlite3.connect('database/financeiro_farmaciajr.db')
    df = pd.read_sql_query("SELECT * FROM leads_vp_auditoria ORDER BY id DESC", conn)
    conn.close()

    # 📊 Card de Resumo de Compliance
    if not df.empty:
        total_dossies = len(df)
        dossies_completos = len(df[(df['link_contrato'] != '') & (df['status_nota_fiscal'].str.contains('Emitida', na=False))])
        taxa_compliance = (dossies_completos / total_dossies) * 100
        
        c_kpi1, c_kpi2, c_kpi3 = st.columns(3)
        c_kpi1.metric("Total de Dossiês", f"{total_dossies} projetos")
        c_kpi2.metric("Projetos com NF Emitida", f"{len(df[df['status_nota_fiscal'].str.contains('Emitida', na=False)])} un")
        c_kpi3.metric("Índice de Compliance Documental", f"{taxa_compliance:.0f}%")
        st.markdown("---")

    col_esquerda, col_direita = st.columns([1, 1])
    
    # =======================================================================
    # BLOCO 1: NOVO CADASTRO
    # =======================================================================
    with col_esquerda:
        st.markdown("#### ➕ Iniciar Novo Lead / Projeto")
        with st.form("form_novo_lead", clear_on_submit=True):
            empresa = st.text_input("Nome da Empresa / Lead:").strip().title()
            assessor = st.text_input("Assessor Executivo do Projeto:").strip().title()
            v_precificacao = st.number_input("Valor da Precificação Original (R$):", min_value=0.0)
            
            comp_preco = st.selectbox("Comportamento do Preço Inicial:", [
                "🟢 Aceitou o valor normal de tabela", 
                "🟡 Fechou com desconto negociado", 
                "🔴 Exigiu desconto agressivo para fechar"
            ])
            recorrencia = st.selectbox("Fidelização / Histórico:", [
                "🆕 Primeiro serviço com a Farmácia Jr.",
                "🔄 Cliente recorrente (Já voltou mais vezes)",
                "📈 Grande potencial de retorno para novos escopos"
            ])
            
            if st.form_submit_button("🚀 Abrir Dossiê do Lead"):
                if empresa and assessor:
                    hoje = datetime.now().strftime("%d/%m/%Y")
                    try:
                        conn = sqlite3.connect('database/financeiro_farmaciajr.db')
                        cursor = conn.cursor()
                        cursor.execute('''
                            INSERT INTO leads_vp_auditoria (empresa, assessor, valor_precificacao, comportamento_preco, recorrencia_cliente, link_contrato, link_termo_abertura, link_termo_fechamento, tipo_boleto, link_boletos, status_nota_fiscal, data_auditoria, observacoes_vp)
                            VALUES (?, ?, ?, ?, ?, '', '', '', 'Boleto Único', '', '🟡 Aguardando Emissão', ?, '')
                        ''', (empresa, assessor, v_precificacao, comp_preco, recorrencia, hoje))
                        conn.commit()
                        conn.close()
                        st.success(f"Dossiê de {empresa} criado com sucesso!")
                        st.rerun()
                    except sqlite3.IntegrityError:
                        st.error("Essa empresa já possui um Dossiê aberto! Use o painel ao lado para editar.")
                else:
                    st.error("Preencha o nome da empresa e o assessor para criar.")

        # =======================================================================
        # BLOCO 2: EDIÇÃO EVOLUTIVA
        # =======================================================================
        st.markdown("---")
        if not df.empty:
            st.markdown("#### ✏️ Atualizar Progresso do Dossiê")
            empresa_editar = st.selectbox("Selecione o Lead para anexar documentos:", df['empresa'].unique(), key="sb_edit")
            row_edit = df[df['empresa'] == empresa_editar].iloc[0]
            
            with st.form("form_edicao_evolutiva"):
                st.caption(f"Editando documentos de: **{empresa_editar}**")
                
                l_contrato = st.text_input("Link do Contrato Assinado:", value=row_edit['link_contrato'])
                l_abertura = st.text_input("Link do Termo de Abertura:", value=row_edit['link_termo_abertura'])
                l_fechamento = st.text_input("Link do Termo de Fechamento:", value=row_edit['link_termo_fechamento'])
                
                idx_tipo_bol = ["Boleto Único", "Múltiplos Boletos (Parcelado)"].index(row_edit['tipo_boleto']) if row_edit['tipo_boleto'] in ["Boleto Único", "Múltiplos Boletos (Parcelado)"] else 0
                t_boleto = st.selectbox("Modelo do Faturamento:", ["Boleto Único", "Múltiplos Boletos (Parcelado)"], index=idx_tipo_bol)
                l_boletos = st.text_input("Link da Pasta de Boletos:", value=row_edit['link_boletos'])
                
                idx_nf = ["🟢 Emitida e Entregue", "🟡 Aguardando Emissão", "⚪ Não se aplica"].index(row_edit['status_nota_fiscal']) if row_edit['status_nota_fiscal'] in ["🟢 Emitida e Entregue", "🟡 Aguardando Emissão", "⚪ Não se aplica"] else 1
                status_nf = st.selectbox("Status da Emissão da Nota Fiscal:", ["🟢 Emitida e Entregue", "🟡 Aguardando Emissão", "⚪ Não se aplica"], index=idx_nf)
                
                obs_vp = st.text_area("Notas e Anotações da VP sobre o Cliente:", value=row_edit['observacoes_vp'])
                
                if st.form_submit_button("🔄 Salvar Alterações / Anexos"):
                    conn = sqlite3.connect('database/financeiro_farmaciajr.db')
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE leads_vp_auditoria 
                        SET link_contrato=?, link_termo_abertura=?, link_termo_fechamento=?, tipo_boleto=?, link_boletos=?, status_nota_fiscal=?, observacoes_vp=?
                        WHERE empresa=?
                    ''', (l_contrato, l_abertura, l_fechamento, t_boleto, l_boletos, status_nf, obs_vp, empresa_editar))
                    conn.commit()
                    conn.close()
                    st.success("Documentação atualizada com sucesso!")
                    st.rerun()

    # =======================================================================
    # BLOCO 3: EMISSÃO DE ATA & EXCLUSÃO LIMPA
    # =======================================================================
    with col_direita:
        st.markdown("#### 📄 Dossiês Prontos & Emissão de Ata")
        if df.empty:
            st.info("Nenhum dossiê de projeto auditado até o momento.")
        else:
            empresas_auditadas = df['empresa'].unique()
            empresa_selecionada = st.selectbox("Selecione o Projeto para Visualizar/Imprimir:", empresas_auditadas, key="sb_print")
            
            row_selecionada = df[df['empresa'] == empresa_selecionada].iloc[0]
            
            pdf_bytes = gerar_ata_auditoria_pdf(row_selecionada)
            st.download_button(
                label=f"📥 Emitir Dossiê Consolidado em PDF — {empresa_selecionada}",
                data=pdf_bytes,
                file_name=f"Dossie_VP_{empresa_selecionada.replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True
            )
            
            st.markdown("---")
            st.markdown(f"**🔬 Painel Checklist de Compliance — {empresa_selecionada}**")
            
            def exibir_status_doc(nome_doc, link):
                if link:
                    st.markdown(f"✅ **{nome_doc}:** [Acessar Documento no Drive]({link})")
                else:
                    st.markdown(f"❌ **{nome_doc}:** <span style='color:red;'>Pendente de Envio</span>", unsafe_allow_html=True)
            
            st.write(f"👤 **Assessor Responsável:** {row_selecionada['assessor']}")
            st.write(f"💰 **Ticket Estimado:** R$ {row_selecionada['valor_precificacao']:.2f}")
            st.write(f"📊 **Margem:** {row_selecionada['comportamento_preco']}")
            st.write(f"🧾 **Nota Fiscal:** {row_selecionada['status_nota_fiscal']}")
            
            st.markdown("#### 📁 Checklist de Verificação:")
            exibir_status_doc("Contrato Assinado", row_selecionada['link_contrato'])
            exibir_status_doc("Termo de Abertura", row_selecionada['link_termo_abertura'])
            exibir_status_doc("Termo de Fechamento", row_selecionada['link_termo_fechamento'])
            exibir_status_doc(f"Boletos ({row_selecionada['tipo_boleto']})", row_selecionada['link_boletos'])
            
            if row_selecionada['observacoes_vp']:
                st.info(f"**Notas da VP:** {row_selecionada['observacoes_vp']}")
                
            st.markdown("---")
            
            # 🗑️ BOTÃO DE EXCLUSÃO COM LIMPEZA DE SESSÃO
            id_para_deletar = int(row_selecionada['id'])
            
            if st.button("🗑️ Deletar Dossiê por Completo", key=f"btn_del_dossie_{id_para_deletar}", use_container_width=True, type="secondary"):
                conn = sqlite3.connect('database/financeiro_farmaciajr.db')
                cursor = conn.cursor()
                cursor.execute("DELETE FROM leads_vp_auditoria WHERE id = ?", (id_para_deletar,))
                conn.commit()
                conn.close()
                
                # Limpa as chaves das selectboxes salvas na memória para evitar travamento na re-renderização
                if 'sb_print' in st.session_state:
                    del st.session_state['sb_print']
                if 'sb_edit' in st.session_state:
                    del st.session_state['sb_edit']
                    
                st.success("Dossiê excluído do banco de dados com sucesso!")
                st.rerun()