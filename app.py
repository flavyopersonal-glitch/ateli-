import os
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv

# Importação da IA (Scikit-Learn)
from sklearn.linear_model import LinearRegression

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
st.title("🏭 Sistema de Gestão PCP & Fábrica (Agenda Industrial + IA)")
st.markdown("---")

if not conexao_ok:
    st.error("❌ Erro ao conectar ao Supabase. Verifique o arquivo .env")
    st.stop()

# CAPACIDADE DIÁRIA DA FÁBRICA (Agenda fixa de Segunda a Sexta)
CAPACIDADE_DIARIA_HORAS = 8.0

def calcular_proximo_dia_util(data_atual):
    amanha = data_atual + timedelta(days=1)
    while amanha.weekday() >= 5:  # 5 = Sábado, 6 = Domingo
        amanha += timedelta(days=1)
    return amanha

# 2. ABAS DO SISTEMA
aba_producao, aba_estoque, aba_financeiro = st.tabs([
    "📦 Linha de Produção & Prazos", 
    "🪵 Controle de Estoque", 
    "💰 Controle de Caixa & Lucro + Previsão IA"
])

# ==========================================
# ABA 1: LINHA DE PRODUÇÃO & PRAZOS
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
            
            st.markdown("**Dados de Venda:**")
            valor_venda = st.number_input("Valor da Venda (R$)", min_value=0.0, step=10.0, value=100.0)
            custo_material = st.number_input("Custo Estimado de Material (R$)", min_value=0.0, step=5.0, value=30.0)
            
            submeter = st.form_submit_button("Agendar e Registrar")
            
            if submeter and cliente:
                try:
                    pedido_data = {
                        "cliente": cliente,
                        "horas_necessarias": horas,
                        "data_solicitada_cliente": str(data_solicitada),
                        "status_urgente": urgente,
                        "status_producao": "Na Fila"
                    }
                    res_pedido = supabase.table("pedidos").insert(pedido_data).execute()
                    pedido_id = res_pedido.data[0]["id"]
                    
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
                    st.experimental_rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar dados: {e}")

    with col2:
        st.subheader("📊 Agenda de Fábrica (Segunda a Sexta - 8h/dia)")
        res = supabase.table("pedidos").select("*").execute()
        
        if res.data:
            df = pd.DataFrame(res.data)
            df = df.sort_values(by=["status_urgente", "created_at"], ascending=[False, True]).reset_index(drop=True)
            
            datas_conclusao = []
            dias_necessarios_lista = []
            
            ponteiro_data = datetime.today().date()
            while ponteiro_data.weekday() >= 5:
                ponteiro_data += timedelta(days=1)
                
            horas_disponiveis_hoje = CAPACIDADE_DIARIA_HORAS
            
            for index, row in df.iterrows():
                if row["status_producao"] == "Finalizado":
                    datas_conclusao.append(row.get("data_programada_producao", str(ponteiro_data)))
                    dias_necessarios_lista.append("-")
                    continue
                    
                horas_restantes_pedido = float(row["horas_necessarias"])
                data_inicio_pedido = ponteiro_data
                
                while horas_restantes_pedido > 0:
                    if horas_restantes_pedido <= horas_disponiveis_hoje:
                        horas_disponiveis_hoje -= horas_restantes_pedido
                        horas_restantes_pedido = 0
                        if horas_disponiveis_hoje == 0:
                            ponteiro_data = calcular_proximo_dia_util(ponteiro_data)
                            horas_disponiveis_hoje = CAPACIDADE_DIARIA_HORAS
                    else:
                        horas_restantes_pedido -= horas_disponiveis_hoje
                        ponteiro_data = calcular_proximo_dia_util(ponteiro_data)
                        horas_disponiveis_hoje = CAPACIDADE_DIARIA_HORAS
                
                data_fim_pedido = ponteiro_data
                datas_conclusao.append(str(data_fim_pedido))
                
                dias_ocupados = (data_fim_pedido - data_inicio_pedido).days + 1
                dias_necessarios_lista.append(f"{dias_ocupados} dia(s)")
            
            df["data_programada_producao"] = datas_conclusao
            df["Tempo de Fábrica"] = dias_necessarios_lista
            
            alertas = []
            for idx, row in df.iterrows():
                if row["status_producao"] == "Finalizado":
                    alertas.append("✅ Finalizado")
                    continue
                prog = datetime.strptime(str(row["data_programada_producao"]), "%Y-%m-%d").date()
                solic = datetime.strptime(str(row["data_solicitada_cliente"]), "%Y-%m-%d").date()
                if prog > solic:
                    alertas.append("⚠️ ATRASARÁ")
                else:
                    alertas.append("✅ No Prazo")
            df["Alerta Prazo"] = alertas
            
            st.dataframe(
                df[["id", "cliente", "horas_necessarias", "Tempo de Fábrica", "status_urgente", "data_solicitada_cliente", "data_programada_producao", "Alerta Prazo", "status_producao"]],
                column_config={
                    "horas_necessarias": "Horas Totais",
                    "status_urgente": "🔥 Urgente",
                    "data_solicitada_cliente": "Prazo Solicitado",
                    "data_programada_producao": "Data Prevista de Entrega",
                },
                use_container_width=True
            )
            
            st.markdown("**Atualizar Status de Produção:**")
            pid = st.number_input("Digite o ID do Pedido para alterar:", min_value=1, step=1)
            novo_status = st.selectbox("Novo Status", ["Na Fila", "Em Produção", "Finalizado"])
            if st.button("Atualizar Status"):
                supabase.table("pedidos").update({"status_producao": novo_status}).eq("id", pid).execute()
                st.success(f"Status do pedido #{pid} alterado!")
                st.experimental_rerun()
        else:
            st.info("Nenhum pedido na fila de produção.")

# ==========================================
# ABA 2: CONTROLE DE ESTOQUE
# ==========================================
with aba_estoque:
    st.subheader("🪵 Gerenciamento de Materials")
    ec1, ec2 = st.columns([1, 2])
    
    with ec1:
        st.markdown("**Adicionar/Atualizar Material**")
        with st.form("form_estoque", clear_on_submit=True):
            item = st.text_input("Nome da Matéria-Prima")
            qtd_atual = st.number_input("Quantidade em Estoque", min_value=0.0, step=1.0)
            qtd_min = st.number_input("Quantidade Mínima de Alerta", min_value=0.0, step=1.0)
            custo_un = st.number_input("Preço de Custo (R$)", min_value=0.0, step=1.0)
            
            bt_estoque = st.form_submit_button("Salvar no Estoque")
            if bt_estoque and item:
                estoque_data = {"item_nome": item, "quantidade_atual": qtd_atual, "quantidade_minima": qtd_min, "preco_custo": custo_un}
                supabase.table("estoque").insert(estoque_data).execute()
                st.success(f"{item} adicionado!")
                st.experimental_rerun()
                
    with ec2:
        res_est = supabase.table("estoque").select("*").execute()
        if res_est.data:
            df_est = pd.DataFrame(res_est.data)
            df_est["Status Material"] = df_est.apply(lambda r: "🚨 COMPRAR DO FORNECEDOR" if r["quantidade_atual"] <= r["quantidade_minima"] else "✅ OK", axis=1)
            st.dataframe(df_est[["id", "item_nome", "quantidade_atual", "quantidade_minima", "preco_custo", "Status Material"]], use_container_width=True)
        else:
            st.info("Estoque vazio.")

# ==========================================
# ABA 3: CONTROLE DE CAIXA & IA PREVISÃO
# ==========================================
with aba_financeiro:
    st.subheader("💰 Fluxo Financeiro e Margem de Lucro")
    
    res_fin = supabase.table("vendas_e_financas").select("*").execute()
    if res_fin.data:
        df_fin = pd.DataFrame(res_fin.data)
        
        faturamento_total = df_fin["valor_venda"].sum()
        custos_totais = df_fin["custo_total"].sum()
        lucro_total = df_fin["lucro_liquido"].sum()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("💰 Faturamento Bruto Total", f"R$ {faturamento_total:,.2f}")
        m2.metric("📉 Custo de Produção Total", f"R$ {custos_totais:,.2f}")
        m3.metric("📈 Lucro Líquido Real", f"R$ {lucro_total:,.2f}", delta=f"{((lucro_total/faturamento_total)*100 if faturamento_total > 0 else 0):.1f}% Margem")
        
        # --- BLOCO: INTELIGÊNCIA ARTIFICIAL ---
        st.markdown("---")
        st.subheader("🤖 Previsão de Tendência de Faturamento com IA")
        
        df_fin['data_pagamento'] = pd.to_datetime(df_fin['data_pagamento'])
        df_agrupado = df_fin.groupby('data_pagamento')['valor_venda'].sum().reset_index().sort_values('data_pagamento')
        
        if len(df_agrupado) >= 2:
            data_minima = df_agrupado['data_pagamento'].min()
            df_agrupado['Dias_Numericos'] = (df_agrupado['data_pagamento'] - data_minima).dt.days
            
            X = df_agrupado[['Dias_Numericos']].values
            Y = df_agrupado['valor_venda'].values
            
            modelo_ia = LinearRegression()
            modelo_ia.fit(X, Y)
            
            ultimo_dia_numerico = int(df_agrupado['Dias_Numericos'].max())
            futuro_dias = np.array([[ultimo_dia_numerico + 1], [ultimo_dia_numerico + 2], [ultimo_dia_numerico + 3]])
            previsoes_futuras = modelo_ia.predict(futuro_dias)
            
            st.info("💡 A inteligência artificial analisou o histórico de entradas e calculou a tendência para os próximos dias:")
            pc1, pc2, pc3 = st.columns(3)
            pc1.metric("🔮 Dia +1 (Amanhã)", f"R$ {max(0.0, previsoes_futuras[0]):,.2f}")
            pc2.metric("🔮 Dia +2", f"R$ {max(0.0, previsoes_futuras[1]):,.2f}")
            pc3.metric("🔮 Dia +3", f"R$ {max(0.0, previsoes_futuras[2]):,.2f}")
        else:
            st.warning("🤖 IA Aguardando Dados: Cadastre movimentações financeiras em pelo menos 2 datas diferentes para treinar a inteligência.")
        
        st.markdown("---")
        st.markdown("**Histórico de Transações do Caixa:**")
        df_exibir = df_fin.copy()
        df_exibir['data_pagamento'] = df_exibir['data_pagamento'].dt.strftime('%d/%m/%Y')
        st.dataframe(df_exibir[["id", "pedido_id", "valor_venda", "custo_total", "lucro_liquido", "status_financeiro", "data_pagamento"]], use_container_width=True)
        
        # --- NOVO: ENTRADA DE BAIXA DO FINANCEIRO ---
        st.markdown("---")
        st.markdown("**Confirmar Recebimento de Valor:**")
        fcol1, fcol2 = st.columns([1, 1])
        
        with fcol1:
            fid = st.number_input("Digite o ID do Lançamento para dar baixa:", min_value=1, step=1, key="financeiro_id")
        with fcol2:
            novo_status_fin = st.selectbox("Alterar Status Financeiro para:", ["Pendente", "Pago"], key="financeiro_status")
            
        if st.button("Confirmar Baixa de Caixa", type="primary"):
            try:
                supabase.table("vendas_e_financas").update({"status_financeiro": novo_status_fin}).eq("id", fid).execute()
                st.success(f"Lançamento #{fid} atualizado para {novo_status_fin} com sucesso!")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Erro ao atualizar status financeiro: {e}")
                
    else:
        st.info("Nenhuma movimentação financeira registrada.")