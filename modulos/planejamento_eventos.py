import pandas as pd
import streamlit as st
from database.conexao_db import get_connection


def conectar_banco_eventos():
    """Devolve uma conexão com o banco (Postgres/Supabase, já com as tabelas criadas)."""
    return get_connection()


def renderizar_pagina_planejamento_eventos():
    lista_depto = ["IMAGEM", "AR", "VP", "PRESIDÊNCIA", "PROJETOS", "NEGÓCIOS"]

    st.title("🏆 Central de Planejamento de Eventos (VP)")
    st.write("Gerencie as metas, aportes e despesas críticas de projetos sazonais como o DDA.")

    evento_sel = st.selectbox(
        "Selecione o Projeto para Gestão:",
        [
            "Dia do Açaí e Sundae (DDA)",
            "Treinamento de Imersão Interna",
            "Workshop de Rotulagem",
        ],
    )

    # Formulário para planejar os custos
    with st.expander("➕ Mapear Novo Custo / Aporte Planejado"):
        c1, c2, c3 = st.columns(3)
        resp = c1.text_input("Membro Responsável:")
        depto = c2.selectbox("Diretoria Executora:", lista_depto, key="ev_dep_sel")
        tipo = c3.selectbox(
            "Tipo de Registro:",
            ["Previsão de Gasto", "Orçamento Alocado (Aporte)"],
        )

        c4, c5, c6 = st.columns(3)
        item = c4.text_input("Insumo / Item Mapeado:")
        prio = c5.selectbox(
            "Classificação de Prioridade:", ["essencial", "adicional", "NA"]
        )
        valor = c6.number_input(
            "Valor Estimado (R$):", min_value=0.0, value=10.0
        )

        if st.button("💾 Adicionar ao Planejamento Estratégico", use_container_width=True):
            if resp and item and valor > 0:
                conn = conectar_banco_eventos()
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO planejamento_eventos (evento, responsavel, departamento, tipo_registro, prioridade, item, valor, status_compra)
                    VALUES (?, ?, ?, ?, ?, ?, ?, '⚪ Planejado')
                """,
                    (evento_sel, resp, depto, tipo, prio, item, valor),
                )
                conn.commit()
                conn.close()
                st.success("✅ Item acoplado ao plano financeiro!")
                st.rerun()

    st.markdown("---")

    # Renderização e cálculo de viabilidade
    conn = conectar_banco_eventos()
    df = pd.read_sql_query(
        "SELECT id, responsavel, departamento, tipo_registro, prioridade, item, valor, status_compra "
        f"FROM planejamento_eventos WHERE evento = '{evento_sel}'",
        conn,
    )
    conn.close()

    if not df.empty:
        # Consolidação matemática automática
        aporte = df[df["tipo_registro"] == "Orçamento Alocado (Aporte)"]["valor"].sum()
        essencial = df[
            (df["tipo_registro"] == "Previsão de Gasto") & (df["prioridade"] == "essencial")
        ]["valor"].sum()
        adicional = df[
            (df["tipo_registro"] == "Previsão de Gasto") & (df["prioridade"] == "adicional")
        ]["valor"].sum()
        saldo_projetado = aporte - (essencial + adicional)

        st.markdown("##### 📊 Sumário Executivo de Saúde Financeira")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Orçamento Garantido", f"R$ {aporte:.2f}")
        m2.metric("Insumos Críticos (Essencial)", f"R$ {essencial:.2f}")
        m3.metric("Custos Opcionais (Adicional)", f"R$ {adicional:.2f}")
        m4.metric(
            "Margem Projetada",
            f"R$ {saldo_projetado:.2f}",
            delta=f"{saldo_projetado:.2f}",
        )

        st.markdown("##### 📋 Itens Mapeados no Planejamento")

        def colorir_prioridades(row):
            styles = [""] * len(row)
            if row["prioridade"] == "essencial":
                styles[4] = "background-color: #E8F5E9; color: #2E7D32; font-weight: bold;"
            elif row["prioridade"] == "adicional":
                styles[4] = "background-color: #FFFDE7; color: #F57F17; font-weight: bold;"
            return styles

        df_styled = df.style.apply(colorir_prioridades, axis=1)
        st.dataframe(df_styled, use_container_width=True, hide_index=True)

        # Checklist de Suprimentos
        st.markdown("---")
        st.markdown("##### 🛒 Checklist de Compras Logística")
        sel_item = st.selectbox(
            "Selecione o Insumo:", df["id"].astype(str) + " - " + df["item"]
        )
        id_item = int(sel_item.split(" - ")[0])
        status_novo = st.selectbox(
            "Fase Atual da Aquisição:",
            ["⚪ Planejado", "🟡 Em cotação", "🟢 Comprado", "🔵 Entregue no local"],
        )

        if st.button("💾 Atualizar Etapa Logística", use_container_width=True, type="primary"):
            conn = conectar_banco_eventos()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE planejamento_eventos SET status_compra = ? WHERE id = ?",
                (status_novo, id_item),
            )
            conn.commit()
            conn.close()
            st.success("Fase de suprimentos atualizada!")
            st.rerun()
    else:
        st.info("Nenhum planejamento traçado para este projeto até o momento.")
