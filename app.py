import os
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv

# 1. CONFIGURAÇÕES INICIAIS & CONEXÃO
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

try:
    supabase: Client = create_client(url, key)
    conexao_ok = True
except Exception:
    conexao_ok = False

st.set_page_config(page_title="PCP Ateliê Pro", layout="wide")
st.title("🏭 Sistema de Gestão PCP & Fábrica")
st.markdown("---")

if not conexao_ok:
    st.error("❌ Erro ao conectar ao Supabase. Verifique o arquivo .env")
    st.stop()

# CAPACIDADE DIÁRIA DA FÁBRICA (Defina quantas horas você trabalha por dia)
CAPACIDADE_DIARIA_HORAS = 8.0

# 2. ABAS DO SISTEMA
aba_producao, aba_estoque, aba_financeiro = st.tabs([
    "📦 Linha de Produção & Prazos", 
    "🪵 Controle de Estoque", 
    "💰 Controle de Caixa & Lucro"
])

# ==========================================
# ABAL 1: LINHA DE PRODUÇÃO & PRAZOS
# ==========================================
with aba_producao:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("📝 Cadastrar Pedido")
        with st.form("form_novo_pedido", clear_on_submit=True):
            cliente = st.text_input("Nome do Cliente")
            horas = st.number_input("Horas de Produção Necessárias", min_value=0.5, step=0.5, value=2.0)
            data_solicitada = st.date_input("Prazo solicitado pelo cliente", min_value=datetime.today())
            urgente = st.checkbox("🔥 PEDIDO URGENTE (Furar Fila)")
            
            # Parte financeira atrelada ao pedido
            st.markdown("**Dados de Venda:**")
            valor_venda = st.number_input("Valor da Venda (R$)", min_value=0.0, step=10.0, value=100.0)
            custo_material = st.number_input("Custo Estimado de Material (R$)", min_value=0.0, step=5.0, value=30.0)
            
            submeter = st.form_submit_button("Agendar e Registrar")
            
            if submeter and cliente:
                try:
                    # 1. Insere o Pedido
                    pedido_data = {
                        "cliente": cliente,
                        "horas_necessarias": horas,
                        "data_solicitada_cliente": str(data_solicitada),
                        "status_urgente": urgente,
                        "status_producao": "Na Fila"
                    }
                    res_pedido = supabase.table("pedidos").insert(pedido_data).execute()
                    pedido_id = res_pedido.data[0]["id"]
                    
                    # 2. Insere o Financeiro atrelado ao pedido
                    lucro = valor_venda - custo_material
                    financeiro_data = {
                        "pedido_id": pedido_id,
                        "valor_venda": valor_venda,
                        "custo_total": custo_material,
                        "lucro_liquido": lucro,
                        "status_financeiro": "Pendente",
                        "data_pagamento": str(data_solicitada)
                    }
                    supabase.table("vendas_e_financas").insert(financeiro_data).execute()
                    st.success(f"Pedido de {cliente} registrado com sucesso!")
                except Exception as e:
                    st.error(f"Erro ao salvar dados: {e}")

    with col2:
        st.subheader("📊 Fila de Produção e Cronograma Dinâmico")
        
        # Puxa os pedidos do banco
        res = supabase.table("pedidos").select("*").execute()
        
        if res.data:
            df = pd.DataFrame(res.data)
            
            # --- ALGORITMO DE ENCAIXE DINÂMICO ---
            # Regra: Urgentes primeiro (True vem antes de False no decrescente), depois data de criação
            df = df.sort_values(by=["status_urgente", "created_at"], ascending=[False, True]).reset_index(drop=True)
            
            datas_programadas = []
            data_atual_ponteiro = datetime.today().date()
            horas_acumuladas_no_dia = 0.0
            
            for index, row in df.iterrows():
                # Se o status já for finalizado, mantém a data ou ignora a alocação de carga
                if row["status_producao"] == "Finalizado":
                    datas_programadas.append(row["data_programada_producao"])
                    continue
                    
                horas_pedido = row["horas_necessarias"]
                
                # Se o pedido sozinho estoura o dia, pula pro próximo dia
                if horas_acumuladas_no_dia + horas_pedido > CAPACIDADE_DIARIA_HORAS:
                    data_atual_ponteiro += timedelta(days=1)
                    horas_acumuladas_no_dia = 0.0
                
                datas_programadas.append(str(data_atual_ponteiro))
                horas_acumuladas_no_dia += horas_pedido
            
            df["data_programada_producao"] = datas_programadas
            # --------------------------------------
            
            # Verificação de alertas de atraso
            alertas = []
            for idx, row in df.iterrows():
                prog = datetime.strptime(str(row["data_programada_producao"]), "%Y-%m-%d").date()
                solic = datetime.strptime(str(row["data_solicitada_cliente"]), "%Y-%m-%d").date()
                if prog > solic and row["status_producao"] != "Finalizado":
                    alertas.append("⚠️ ATRASARÁ")
                else:
                    alertas.append("✅ No Prazo")
            df["Alerta Prazo"] = alertas
            
            # Exibe os dados formatados
            st.dataframe(
                df[["id", "cliente", "horas_necessarias", "status_urgente", "data_solicitada_cliente", "data_programada_producao", "Alerta Prazo", "status_producao"]],
                column_config={
                    "status_urgente": "🔥 Urgente",
                    "data_solicitada_cliente": "Prazo Cliente",
                    "data_programada_producao": "Data Alocada Fábrica",
                },
                use_container_width=True
            )
            
            # Atualizar Status ou Finalizar Pedido
            st.markdown("**Atualizar Status de Produção:**")
            pid = st.number_input("Digite o ID do Pedido para alterar:", min_value=1, step=1)
            novo_status = st.selectbox("Novo Status", ["Na Fila", "Em Produção", "Finalizado"])
            if st.button("Atualizar Status"):
                supabase.table("pedidos").update({"status_producao": novo_status}).eq("id", pid).execute()
                st.success(f"Status do pedido #{pid} alterado!")
                st.rerun()
        else:
            st.info("Nenhum pedido na fila de produção.")

# ==========================================
# ABA 2: CONTROLE DE ESTOQUE
# ==========================================
with aba_estoque:
    st.subheader("🪵 Gerenciamento de Materiais")
    ec1, ec2 = st.columns([1, 2])
    
    with ec1:
        st.markdown("**Adicionar/Atualizar Material**")
        with st.form("form_estoque", clear_on_submit=True):
            item = st.text_input("Nome da Matéria-Prima (ex: Tecido Algodão)")
            qtd_atual = st.number_input("Quantidade em Estoque", min_value=0.0, step=1.0)
            qtd_min = st.number_input("Quantidade Mínima de Alerta", min_value=0.0, step=1.0)
            custo_un = st.number_input("Preço de Custo (R$)", min_value=0.0, step=1.0)
            
            bt_estoque = st.form_submit_button("Salvar no Estoque")
            if bt_estoque and item:
                estoque_data = {"item_nome": item, "quantidade_atual": qtd_atual, "quantidade_minima": qtd_min, "preco_custo": custo_un}
                supabase.table("estoque").insert(estoque_data).execute()
                st.success(f"{item} adicionado!")
                st.rerun()
                
    with ec2:
        res_est = supabase.table("estoque").select("*").execute()
        if res_est.data:
            df_est = pd.DataFrame(res_est.data)
            
            # Regra visual de alerta de reposição do fornecedor
            df_est["Status Material"] = df_est.apply(lambda r: "🚨 COMPRAR DO FORNECEDOR" if r["quantidade_atual"] <= r["quantidade_minima"] else "✅ OK", axis=1)
            
            st.dataframe(df_est[["id", "item_nome", "quantidade_atual", "quantidade_minima", "preco_custo", "Status Material"]], use_container_width=True)
        else:
            st.info("Estoque vazio.")

# ==========================================
# ABA 3: CONTROLE DE CAIXA & LUCRO
# ==========================================
with aba_financeiro:
    st.subheader("💰 Fluxo Financeiro e Margem de Lucro")
    
    res_fin = supabase.table("vendas_e_financas").select("*").execute()
    if res_fin.data:
        df_fin = pd.DataFrame(res_fin.data)
        
        # Indicadores no topo do Painel Financeiro
        faturamento_total = df_fin["valor_venda"].sum()
        custos_totais = df_fin["custo_total"].sum()
        lucro_total = df_fin["lucro_liquido"].sum()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("💰 Faturamento Bruto Total", f"R$ {faturamento_total:,.2f}")
        m2.metric("📉 Custo de Produção Total", f"R$ {custos_totais:,.2f}")
        m3.metric("📈 Lucro Líquido Real", f"R$ {lucro_total:,.2f}", delta=f"{((lucro_total/faturamento_total)*100 if faturamento_total > 0 else 0):.1f}% Margem")
        
        st.markdown("---")
        st.markdown("**Histórico de Transações do Caixa:**")
        st.dataframe(df_fin[["id", "pedido_id", "valor_venda", "custo_total", "lucro_liquido", "status_financeiro", "data_pagamento"]], use_container_width=True)
    else:
        st.info("Nenhuma movimentação financeira registrada.")