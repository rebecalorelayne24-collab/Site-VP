import streamlit as st
import sqlite3
import pandas as pd
import io
import os
from datetime import datetime
from modulos.fluxo_caixa import salvar_lancamento

def garantir_tabelas_totem():
    """Garante que a pasta database e as tabelas operacionais do balcão existam no banco"""
    os.makedirs('database', exist_ok=True)
    conn = None
    try:
        conn = sqlite3.connect('database/financeiro_farmaciajr.db')
        cursor = conn.cursor()
        
        # Tabela de Fluxo de Caixa Próprio do Balcão
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS caixa_balcao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_hora TEXT,
                tipo_servico TEXT,
                descricao TEXT,
                cliente TEXT,
                valor REAL,
                diretoria TEXT,
                status_pagamento TEXT
            )
        ''')
        
        # Tabela de Controle de Empréstimo de Jalecos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS emprestimos_jaleco (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_hora TEXT,
                cliente_nome TEXT,
                cliente_telefone TEXT,
                membro_responsavel TEXT,
                status_pagamento TEXT,
                status_devolucao TEXT DEFAULT '🟡 Com o Aluno'
            )
        ''')
        
        # Tabela de Histórico de Vendas do DDA (Açaí/Sundae)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vendas_dda (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_hora TEXT,
                produto TEXT,
                cliente_nome TEXT,
                valor REAL,
                diretoria TEXT
            )
        ''')
        
        # Tabela de Vendas de Souvenirs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vendas_souvenirs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_hora TEXT,
                item TEXT,
                cliente_nome TEXT,
                valor REAL,
                diretoria TEXT
            )
        ''')
        
        # Tabela de Impressões e Xerox
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS registro_impressoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_hora TEXT,
                cliente_nome TEXT,
                paginas INTEGER,
                valor REAL,
                diretoria TEXT
            )
        ''')
        
        conn.commit()
    except Exception as e:
        st.error(f"Erro ao inicializar o banco de dados do Totem: {e}")
    finally:
        if conn:
            conn.close()

def renderizar_totem():
    garantir_tabelas_totem()
    
    st.markdown("<h2 style='text-align: center; color: #FF1493;'>🍦 Central de Sincronização & Caixa do Balcão</h2>", unsafe_allow_html=True)
    st.caption("Gerenciamento isolado das receitas de balcão (Açaí, Jalecos, Souvenirs e Impressões) e sincronização com o sistema geral.")

    lista_meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

    tab_caixa_proprio, tab_importar, tab_dda, tab_jalecos, tab_souvenirs, tab_impressoes = st.tabs([
        "📊 Caixa do Balcão",
        "📥 Importar Relatório Offline", 
        "🍧 Histórico DDA (Açaí)",
        "🥼 Status de Jalecos",
        "🛍️ Vendas de Souvenirs",
        "🖨️ Registro de Impressões"
    ])

    # =======================================================================
    # ABA 0: FLUXO DE CAIXA PRÓPRIO DO BALCÃO
    # =======================================================================
    with tab_caixa_proprio:
        st.markdown("### 📊 Extrato do Fluxo de Caixa do Balcão")
        st.caption("Visão detalhada de todas as movimentações financeiras geradas exclusivamente pelas operações de balcão.")

        try:
            conn = sqlite3.connect('database/financeiro_farmaciajr.db')
            df_caixa_balcao = pd.read_sql_query("SELECT * FROM caixa_balcao ORDER BY id DESC", conn)
            conn.close()
        except Exception:
            df_caixa_balcao = pd.DataFrame()

        if df_caixa_balcao.empty:
            st.info("Nenhum lançamento registrado no caixa do balcão até o momento.")
        else:
            total_arrecadado = df_caixa_balcao['valor'].sum()
            total_transacoes = len(df_caixa_balcao)

            c_bx1, c_bx2 = st.columns(2)
            c_bx1.metric("💰 Total Arrecadado no Balcão", f"R$ {total_arrecadado:.2f}")
            c_bx2.metric("📋 Total de Operações", f"{total_transacoes} vendas")
            st.markdown("---")

            for idx, row in df_caixa_balcao.iterrows():
                with st.container():
                    col_b1, col_b2, col_b3, col_b4 = st.columns([2, 3, 2, 1])
                    col_b1.write(f"🕒 {row['data_hora']}")
                    col_b2.write(f"**{row['descricao']}**\n\n*Cliente:* {row['cliente']} | *Setor:* {row['diretoria']}")
                    col_b3.write(f"💸 **R$ {row['valor']:.2f}**\n\nStatus: {row['status_pagamento']}")
                    
                    if col_b4.button("🗑️", key=f"del_caixa_b_{row['id']}", help="Excluir lançamento do balcão"):
                        conn = sqlite3.connect('database/financeiro_farmaciajr.db')
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM caixa_balcao WHERE id = ?", (row['id'],))
                        conn.commit()
                        conn.close()
                        st.success("Lançamento estornado com sucesso!")
                        st.rerun()
                st.markdown("<hr style='margin: 4px 0; border: 0.5px solid #F0F0F0;'>", unsafe_allow_html=True)

    # =======================================================================
    # ABA 1: IMPORTADOR DE RELATÓRIO DO APP OFFLINE
    # =======================================================================
    with tab_importar:
        st.markdown("### 📄 Leitura e Injeção do Relatório do Balcão")
        st.info("💡 Importe o extrato em **.csv** ou **.xlsx** gerado pelo app offline do balcão para atualizar automaticamente o Caixa Próprio e o Fluxo de Caixa Geral.")

        arquivo_offline = st.file_uploader("Selecione o arquivo de vendas:", type=["csv", "xlsx"], key="uploader_totem_offline")

        if arquivo_offline is not None:
            try:
                if arquivo_offline.name.endswith(".csv"):
                    df_vendas = pd.read_csv(arquivo_offline)
                else:
                    df_vendas = pd.read_excel(arquivo_offline)

                st.markdown(f"#### 🔎 Prévia das Transações ({len(df_vendas)} registros)")
                st.dataframe(df_vendas, use_container_width=True)

                if st.button("🚀 Processar e Sincronizar Tudo no Sistema", type="primary", use_container_width=True):
                    qtd_sucesso = 0
                    hoje = datetime.now()
                    mes_atual = lista_meses[hoje.month - 1]
                    data_str = hoje.strftime("%Y-%m-%d")

                    conn = sqlite3.connect('database/financeiro_farmaciajr.db')
                    cursor = conn.cursor()

                    for _, line in df_vendas.iterrows():
                        categoria = str(line.get("categoria", "Serviço Prestado")).strip()
                        tipo_item = str(line.get("tipo", "Geral")).strip().lower()
                        descricao = str(line.get("descricao", "Venda de Balcão")).strip()
                        valor = float(line.get("valor", 0.0))
                        depto = str(line.get("diretoria", "VP")).strip()
                        cliente = str(line.get("cliente", "Cliente Balcão")).strip()
                        horario_reg = str(line.get("horario", hoje.strftime("%H:%M:%S"))).strip()
                        dt_hora_completa = f"{data_str} {horario_reg}"

                        if valor > 0:
                            is_dda = any(k in tipo_item or k in descricao.lower() for k in ["açaí", "acai", "sundae", "dda"])
                            is_souvenir = any(k in tipo_item or k in descricao.lower() for k in ["souvenir", "caneca", "camisa", "tirante", "brinde", "chaveiro"])
                            is_impressao = any(k in tipo_item or k in descricao.lower() for k in ["impressao", "impressão", "xerox", "copia", "cópia", "folha"])
                            is_jaleco = "jaleco" in tipo_item or "jaleco" in descricao.lower()

                            if is_dda:
                                cat_fluxo = "Serviço Prestado"
                                tipo_servico_balcao = "DDA (Açaí/Sundae)"
                                desc_final = f"DDA: {descricao} (Cliente: {cliente})"
                                cursor.execute(
                                    "INSERT INTO vendas_dda (data_hora, produto, cliente_nome, valor, diretoria) VALUES (?, ?, ?, ?, ?)",
                                    (dt_hora_completa, descricao, cliente, valor, depto)
                                )
                            elif is_souvenir:
                                cat_fluxo = "ADM: Operacional"
                                tipo_servico_balcao = "Souvenir"
                                desc_final = f"Souvenir: {descricao} (Cliente: {cliente})"
                                cursor.execute(
                                    "INSERT INTO vendas_souvenirs (data_hora, item, cliente_nome, valor, diretoria) VALUES (?, ?, ?, ?, ?)",
                                    (dt_hora_completa, descricao, cliente, valor, depto)
                                )
                            elif is_impressao:
                                cat_fluxo = "Serviço Prestado"
                                tipo_servico_balcao = "Impressão/Xerox"
                                desc_final = f"Impressão/Xerox (Cliente: {cliente})"
                                paginas_est = int(line.get("paginas", 1))
                                cursor.execute(
                                    "INSERT INTO registro_impressoes (data_hora, cliente_nome, paginas, valor, diretoria) VALUES (?, ?, ?, ?, ?)",
                                    (dt_hora_completa, cliente, paginas_est, valor, depto)
                                )
                            else:
                                cat_fluxo = categoria
                                tipo_servico_balcao = "Outro"
                                desc_final = f"{descricao} (Cliente: {cliente})"

                            # 1. Salva no Caixa Próprio do Balcão
                            cursor.execute(
                                "INSERT INTO caixa_balcao (data_hora, tipo_servico, descricao, cliente, valor, diretoria, status_pagamento) VALUES (?, ?, ?, ?, ?, ?, '🟢 Pago')",
                                (dt_hora_completa, tipo_servico_balcao, descricao, cliente, valor, depto)
                            )

                            # 2. Salva no Fluxo de Caixa Geral oficial da EJ
                            salvar_lancamento(
                                mes_atual, data_str, depto, "Receita", 
                                cat_fluxo, desc_final, 
                                valor, valor * 0.0199, valor * 0.9801, 
                                "PicPay", "🟢 Pago", "⚪ Não se aplica", "❌ Não enviado"
                            )

                            # 3. Se for aluguel de Jaleco, registra no controle de empréstimos
                            if is_jaleco:
                                telefone = str(line.get("telefone", "Não informado")).strip()
                                assessor = str(line.get("assessor", "Balcão Offline")).strip()
                                cursor.execute(
                                    "INSERT INTO emprestimos_jaleco (data_hora, cliente_nome, cliente_telefone, membro_responsavel, status_pagamento, status_devolucao) VALUES (?, ?, ?, ?, '🟢 Pago', '🟡 Com o Aluno')",
                                    (dt_hora_completa, cliente, telefone, assessor)
                                )

                            qtd_sucesso += 1

                    conn.commit()
                    conn.close()

                    st.success(f"🎉 Sucesso! {qtd_sucesso} registros foram sincronizados no Caixa do Balcão e no Fluxo de Caixa Geral!")
                    st.rerun()

            except Exception as e:
                st.error(f"❌ Erro ao processar arquivo offline: {e}. Verifique a formatação das colunas.")

    # =======================================================================
    # ABA 2: HISTÓRICO DE VENDAS DO DDA (AÇAÍ E SUNDAE)
    # =======================================================================
    with tab_dda:
        st.markdown("### 🍧 Painel de Vendas — DDA (Dia do Açaí)")
        try:
            conn = sqlite3.connect('database/financeiro_farmaciajr.db')
            df_dda = pd.read_sql_query("SELECT * FROM vendas_dda ORDER BY id DESC", conn)
            conn.close()
        except Exception:
            df_dda = pd.DataFrame()

        if df_dda.empty:
            st.info("Nenhuma venda do DDA registrada até o momento.")
        else:
            c_d1, c_d2 = st.columns(2)
            c_d1.metric("Arrecadação Total DDA", f"R$ {df_dda['valor'].sum():.2f}")
            c_d2.metric("Total de Copos/Produtos Vendidos", f"{len(df_dda)} un")
            st.markdown("---")

            st.dataframe(
                df_dda.rename(columns={
                    'data_hora': 'Data / Hora',
                    'produto': 'Produto',
                    'cliente_nome': 'Cliente',
                    'valor': 'Valor (R$)',
                    'diretoria': 'Diretoria Meta'
                })[['Data / Hora', 'Produto', 'Cliente', 'Valor (R$)', 'Diretoria Meta']],
                use_container_width=True
            )

    # =======================================================================
    # ABA 3: CONTROLE DE JALECOS PENDENTES
    # =======================================================================
    with tab_jalecos:
        st.markdown("### 🥼 Histórico de Jalecos em Circulação")
        try:
            conn = sqlite3.connect('database/financeiro_farmaciajr.db')
            df_j = pd.read_sql_query("SELECT * FROM emprestimos_jaleco WHERE status_devolucao = '🟡 Com o Aluno' ORDER BY id DESC", conn)
            conn.close()
        except Exception:
            df_j = pd.DataFrame()

        if df_j.empty:
            st.success("🎉 Nenhum jaleco pendente de devolução no momento!")
        else:
            for idx, row in df_j.iterrows():
                with st.container():
                    st.markdown(f"""
                    <div style='background-color: #FAFAFA; border-left: 5px solid #FF1493; padding: 12px; border-radius: 6px; margin-bottom: 8px;'>
                        <b>👤 Locatário: {row['cliente_nome']}</b> | 📞 Telefone: {row['cliente_telefone']}<br>
                        🔑 Responsável no Balcão: {row['membro_responsavel']} | 🕒 Retirada: {row['data_hora']}<br>
                        <span style='background-color: #E8F5E9; color: #2E7D32; padding: 2px 6px; border-radius: 4px; font-size: 11px; font-weight: bold;'>{row['status_pagamento']}</span>
                    </div>
                    """, unsafe_allow_html=True)

                    if st.button(f"📥 Confirmar Devolução do Jaleco #{row['id']}", key=f"bx_dev_jaleco_{row['id']}", use_container_width=True):
                        conn = sqlite3.connect('database/financeiro_farmaciajr.db')
                        cursor = conn.cursor()
                        cursor.execute("UPDATE emprestimos_jaleco SET status_devolucao = '🟢 Devolvido' WHERE id = ?", (row['id'],))
                        conn.commit()
                        conn.close()
                        st.success("Jaleco devolvido ao estoque com sucesso!")
                        st.rerun()

    # =======================================================================
    # ABA 4: HISTÓRICO DE VENDAS DE SOUVENIRS
    # =======================================================================
    with tab_souvenirs:
        st.markdown("### 🛍️ Painel de Vendas de Souvenirs")
        try:
            conn = sqlite3.connect('database/financeiro_farmaciajr.db')
            df_s = pd.read_sql_query("SELECT * FROM vendas_souvenirs ORDER BY id DESC", conn)
            conn.close()
        except Exception:
            df_s = pd.DataFrame()

        if df_s.empty:
            st.info("Nenhuma venda de souvenir registrada até o momento.")
        else:
            total_souv = df_s['valor'].sum()
            st.metric("Arrecadação Total com Souvenirs", f"R$ {total_souv:.2f}")
            st.markdown("---")
            
            st.dataframe(
                df_s.rename(columns={
                    'data_hora': 'Data / Hora',
                    'item': 'Item Vendido',
                    'cliente_nome': 'Cliente',
                    'valor': 'Valor (R$)',
                    'diretoria': 'Diretoria Meta'
                })[['Data / Hora', 'Item Vendido', 'Cliente', 'Valor (R$)', 'Diretoria Meta']],
                use_container_width=True
            )

    # =======================================================================
    # ABA 5: HISTÓRICO DE IMPRESSÕES E XEROX
    # =======================================================================
    with tab_impressoes:
        st.markdown("### 🖨️ Painel de Serviços de Impressão e Xerox")
        try:
            conn = sqlite3.connect('database/financeiro_farmaciajr.db')
            df_imp = pd.read_sql_query("SELECT * FROM registro_impressoes ORDER BY id DESC", conn)
            conn.close()
        except Exception:
            df_imp = pd.DataFrame()

        if df_imp.empty:
            st.info("Nenum serviço de impressão registrado até o momento.")
        else:
            c_i1, c_i2 = st.columns(2)
            c_i1.metric("Total Arrecadado com Impressão", f"R$ {df_imp['valor'].sum():.2f}")
            c_i2.metric("Volume Total de Páginas Impressas", f"{df_imp['paginas'].sum()} págs")
            st.markdown("---")

            st.dataframe(
                df_imp.rename(columns={
                    'data_hora': 'Data / Hora',
                    'cliente_nome': 'Cliente',
                    'paginas': 'Páginas',
                    'valor': 'Valor Total (R$)',
                    'diretoria': 'Diretoria Meta'
                })[['Data / Hora', 'Cliente', 'Páginas', 'Valor Total (R$)', 'Diretoria Meta']],
                use_container_width=True
            )