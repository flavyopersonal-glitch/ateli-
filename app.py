import os
import re
from pathlib import Path
from urllib.parse import quote
import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from supabase import create_client, Client
from dotenv import load_dotenv
from orcamento_utils import gerar_link_whatsapp, gerar_pdf_orcamento

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

st.set_page_config(page_title="PCP Ateliê Pro", layout="centered", initial_sidebar_state="collapsed")

# Estilo visual para uma aparência mais profissional e responsiva
st.markdown(
    """
    <style>
        .stApp {
            background: #f4f7fb;
            color: #0f172a;
        }
        .block-container {
            padding-top: 0.6rem;
            padding-left: 0.45rem;
            padding-right: 0.45rem;
            max-width: 1200px;
        }
        .title-block {
            font-size: 2.8rem;
            font-weight: 700;
            color: #111827;
            margin: 0;
        }
        .subtitle {
            color: #475569;
            font-size: 1rem;
            margin-top: 0.25rem;
            margin-bottom: 0.75rem;
        }
        .section-card {
            background: #ffffff;
            border-radius: 24px;
            padding: 1.75rem;
            box-shadow: 0 18px 45px rgba(15, 23, 42, 0.06);
            margin-bottom: 1.75rem;
            border: 1px solid #e2e8f0;
            scroll-margin-top: 92px;
        }
        .section-card h2 {
            color: #0f172a;
            font-size: 1.45rem;
            margin-bottom: 0.35rem;
        }
        .section-subtitle {
            color: #64748b;
            margin-top: -0.1rem;
            margin-bottom: 1.15rem;
            font-size: 0.95rem;
        }
        .stButton>button {
            border-radius: 14px;
            padding: 0.72rem 1.2rem;
            background-color: #0f172a;
            color: white;
            border: none;
            font-weight: 600;
            box-shadow: 0 8px 20px rgba(15, 23, 42, 0.12);
            min-height: 2.6rem;
        }
        .stButton>button:hover {
            background-color: #111827;
        }
        .stMetric {
            background: #f8fafc;
            border-radius: 18px;
            padding: 0.85rem 1rem;
            margin-bottom: 0.4rem;
        }
        .css-1lsmgbg.e16nr0p32 {
            box-shadow: none;
        }
        .stTextInput>div>div>input,
        .stTextArea>div>div>textarea,
        .stNumberInput>div>div>input {
            border-radius: 12px;
            border: 1px solid #d1d5db;
            background: #f8fafc;
            padding: 0.85rem 1rem;
            font-size: 1rem;
            min-height: 2.7rem;
        }
        .stSelectbox>div>div>div>div {
            border-radius: 12px;
            background: #f8fafc;
            border: 1px solid #d1d5db;
            min-height: 2.7rem;
        }
        label, .stTextInput label, .stTextArea label, .stNumberInput label, .stSelectbox label {
            font-size: 0.96rem;
            font-weight: 600;
            color: #334155;
        }
        .st-expander > div {
            border-radius: 18px;
        }
        .app-header {
            position: sticky;
            top: 0;
            z-index: 99;
            background: linear-gradient(90deg, #0f172a 0%, #111827 100%);
            padding: 1.1rem 1.2rem;
            margin-bottom: 1rem;
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 16px 30px rgba(15, 23, 42, 0.16);
        }
        .header-block {
            text-align: left;
            width: 100%;
        }
        .header-title {
            margin-bottom: 0.2rem;
            color: #ffffff;
            font-size: 3rem;
            font-weight: 800;
            text-shadow: 0 2px 10px rgba(0, 0, 0, 0.35);
        }
        .header-subtitle {
            margin-top: 0.25rem;
            color: rgba(255, 255, 255, 0.9);
            font-size: 1.05rem;
            font-weight: 500;
            letter-spacing: 0.16em;
            text-shadow: 0 1px 6px rgba(0, 0, 0, 0.22);
            opacity: 1;
        }

        @media (max-width: 768px) {
            .block-container {
                padding-left: 0.25rem !important;
                padding-right: 0.25rem !important;
            }
            .app-header {
                padding: 0.65rem 0.6rem;
                margin-bottom: 0.6rem;
            }
            .app-header img {
                max-width: 52px !important;
            }
            .header-title {
                font-size: 1.1rem;
                line-height: 1.1;
            }
            .header-subtitle {
                font-size: 0.64rem;
                letter-spacing: 0.06em;
            }
            .section-card {
                padding: 0.9rem;
                border-radius: 14px;
                margin-bottom: 0.8rem;
            }
            .section-card h2 {
                font-size: 1.08rem;
            }
            .section-subtitle {
                font-size: 0.86rem;
            }
            .stButton>button {
                width: 100%;
                padding: 0.8rem 0.95rem;
            }
            div[data-testid="stHorizontalBlock"] > div {
                width: 100% !important;
                max-width: 100% !important;
                min-width: 100% !important;
                margin-bottom: 0.35rem;
            }
            .stMetric {
                padding: 0.8rem 0.9rem;
            }
            [data-testid="stDataFrame"] {
                font-size: 0.85rem;
            }
        }

        @media (max-width: 480px) {
            .header-title {
                font-size: 1.15rem;
            }
            .header-subtitle {
                font-size: 0.65rem;
            }
            .section-card {
                padding: 0.85rem;
            }
            div[data-testid="stSelectbox"] {
                width: 100% !important;
            }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

app_dir = Path(__file__).resolve().parent
logo_path = app_dir / "logo.jpeg"
with st.container():
    st.markdown('<div class="app-header">', unsafe_allow_html=True)
    header_cols = st.columns([1, 4])
    with header_cols[0]:
        if logo_path.exists():
            st.image(str(logo_path), width=120)
    with header_cols[1]:
        st.markdown('<div class="header-block"><h1 class="title-block header-title">ATELIÊ CRISTO REI</h1><p class="header-subtitle">ADVÉNIAT REGNUM TUUM</p></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# Painel resumo executivo
if conexao_ok:
    try:
        pedidos_resumo = supabase.table("pedidos").select("*").execute().data or []
        total_pedidos = len(pedidos_resumo)
        pedidos_urgentes = sum(1 for pedido in pedidos_resumo if pedido.get("status_urgente"))
    except Exception:
        total_pedidos = 0
        pedidos_urgentes = 0
else:
    total_pedidos = 0
    pedidos_urgentes = 0

metric_col1, metric_col2 = st.columns([1, 1])
metric_col1.metric("Pedidos ativos", total_pedidos)
metric_col2.metric("Pedidos urgentes", pedidos_urgentes)

st.caption("Painel rápido para visualizar demanda e urgência sem perder espaço.")
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

def begin_section(title, subtitle="", anchor=None):
    section_id = anchor or re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
    st.markdown(f"<div class='section-card' id='{section_id}'><h2>{title}</h2><p class='section-subtitle'>{subtitle}</p>", unsafe_allow_html=True)

def end_section():
    st.markdown("</div>", unsafe_allow_html=True)

# 2. NAVEGAÇÃO RÁPIDA DO SISTEMA
selected_section = st.selectbox(
    "Selecione a área",
    ["Produção", "Estoque", "Finanças", "Orçamentos", "Configurações"],
    key="section_nav"
)

# ==========================================
# ABA 1: LINHA DE PRODUÇÃO & PRAZOS
# ==========================================
if selected_section == "Produção":
    begin_section("Cadastrar Pedido", "Registre pedidos com prioridade e dados completos para a produção.", anchor="cadastrar-pedido")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        with st.form("form_novo_pedido", clear_on_submit=True):
            cliente = st.text_input("Nome do Cliente")
            descricao_servico = st.text_area(
                "Descrição do Serviço",
                placeholder="Descreva o serviço, detalhes, acabamento e observações importantes...",
                height=120
            )
            horas = st.number_input("Horas de Produção Necessárias", min_value=0.5, step=0.5, value=2.0)
            data_solicitada = st.date_input("Prazo solicitado pelo cliente", min_value=datetime.today())
            urgente = st.checkbox("Pedido urgente (prioridade de produção)")
            
            st.markdown("**Dados de Venda:**")
            valor_venda = st.number_input("Valor da Venda (R$)", min_value=0.0, step=10.0, value=100.0)
            custo_material = st.number_input("Custo Estimado de Material (R$)", min_value=0.0, step=5.0, value=30.0)
            
            submeter = st.form_submit_button("Agendar e Registrar")
            
            if submeter and cliente:
                try:
                    pedido_data = {
                        "cliente": cliente,
                        "descricao_servico": descricao_servico,
                        "horas_necessarias": horas,
                        "data_solicitada_cliente": str(data_solicitada),
                        "status_urgente": urgente,
                        "status_producao": "Na Fila"
                    }
                    try:
                        res_pedido = supabase.table("pedidos").insert(pedido_data).execute()
                    except Exception as erro_coluna:
                        pedido_data_sem_descricao = {k: v for k, v in pedido_data.items() if k != "descricao_servico"}
                        res_pedido = supabase.table("pedidos").insert(pedido_data_sem_descricao).execute()
                        st.warning("A descrição do serviço foi recebida, mas a coluna de banco ainda não está disponível. O pedido foi salvo sem esse campo.")
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
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao salvar dados: {e}")
    end_section()

    with col2:
        begin_section("📊 Agenda de Fábrica", "Visualize a fila, prazos e alertas de entrega em uma visão clara.")
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
            df["descricao_servico"] = df.get("descricao_servico", pd.Series([""] * len(df)))
            
            alertas = []
            for idx, row in df.iterrows():
                if row["status_producao"] == "Finalizado":
                    alertas.append("Finalizado")
                    continue
                prog = datetime.strptime(str(row["data_programada_producao"]), "%Y-%m-%d").date()
                solic = datetime.strptime(str(row["data_solicitada_cliente"]), "%Y-%m-%d").date()
                if prog > solic:
                    alertas.append("Atraso previsto")
                else:
                    alertas.append("No prazo")
            df["Alerta Prazo"] = alertas
            
            st.dataframe(
                df[["id", "cliente", "descricao_servico", "horas_necessarias", "Tempo de Fábrica", "status_urgente", "data_solicitada_cliente", "data_programada_producao", "Alerta Prazo", "status_producao"]],
                column_config={
                    "horas_necessarias": "Horas Totais",
                    "status_urgente": "Urgente",
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
                st.rerun()
        else:
            st.info("Nenhum pedido na fila de produção.")
    end_section()
# ABA 2: CONTROLE DE ESTOQUE
# ==========================================
elif selected_section == "Estoque":
    begin_section("Gerenciamento de Materiais", "Controle o estoque com alertas de reposição e custos detalhados.", anchor="gerenciamento-de-materiais")
    ec1, ec2 = st.columns([1, 2])
    
    with ec1:
        st.markdown("**Adicionar/Atualizar Materiais**")
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
                st.rerun()
                
    with ec2:
        res_est = supabase.table("estoque").select("*").execute()
        if res_est.data:
            df_est = pd.DataFrame(res_est.data)
            df_est["Status Material"] = df_est.apply(lambda r: "Comprar do fornecedor" if r["quantidade_atual"] <= r["quantidade_minima"] else "Em nível seguro", axis=1)
            st.dataframe(df_est[["id", "item_nome", "quantidade_atual", "quantidade_minima", "preco_custo", "Status Material"]], use_container_width=True)
        else:
            st.info("Estoque vazio.")
    end_section()

# ==========================================
# ABA 3: CONTROLE DE CAIXA & IA PREVISÃO
# ==========================================
elif selected_section == "Finanças":
    begin_section("Finanças e Previsões", "Monitore receita, margem e a tendência de faturamento com inteligência.", anchor="financas-e-previsoes")
    
    res_fin = supabase.table("vendas_e_financas").select("*").execute()
    if res_fin.data:
        df_fin = pd.DataFrame(res_fin.data)
        
        faturamento_total = df_fin["valor_venda"].sum()
        custos_totais = df_fin["custo_total"].sum()
        lucro_total = df_fin["lucro_liquido"].sum()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Faturamento Bruto Total", f"R$ {faturamento_total:,.2f}")
        m2.metric("Custo de Produção Total", f"R$ {custos_totais:,.2f}")
        m3.metric("Lucro Líquido Real", f"R$ {lucro_total:,.2f}", delta=f"{((lucro_total/faturamento_total)*100 if faturamento_total > 0 else 0):.1f}% Margem")
        
        # --- BLOCO: INTELIGÊNCIA ARTIFICIAL ---
        st.markdown("---")
        st.subheader("Previsão de Tendência de Faturamento")
        
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
            st.warning("Aguardando dados: cadastre movimentações financeiras em pelo menos duas datas diferentes para treinar o modelo.")
        
        st.markdown("---")
        st.markdown("**Histórico de Transações do Caixa:**")
        df_exibir = df_fin.copy()
        df_exibir['data_pagamento'] = df_exibir['data_pagamento'].dt.strftime('%d/%m/%Y')
        st.dataframe(df_exibir[["id", "pedido_id", "valor_venda", "custo_total", "lucro_liquido", "status_financeiro", "data_pagamento"]], use_container_width=True)
        
        # --- ENTRADA DE BAIXA DO FINANCEIRO ---
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
                st.success(f"Lançamento #{fid} updated para {novo_status_fin} com sucesso!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao atualizar status financeiro: {e}")
                
    else:
        st.info("Nenhuma movimentação financeira registrada.")
    end_section()
# ABA 4: ORÇAMENTO
# ==========================================
elif selected_section == "Orçamentos":
    begin_section("Orçamentos Profissionais", "Gere propostas elegantes em PDF e envie automaticamente pelo WhatsApp.", anchor="orcamentos-profissionais")

    with st.form("form_orcamento", clear_on_submit=True):
        nome_servico = st.text_input("Nome do Serviço")
        descricao_orcamento = st.text_area(
            "Descrição do Orçamento",
            placeholder="Descreva o serviço, acabamento e itens inclusos...",
            height=100
        )
        horas_orcamento = st.number_input("Horas estimadas", min_value=0.5, step=0.5, value=2.0, key="orc_horas")
        custo_material_orcamento = st.number_input("Custo estimado de material (R$)", min_value=0.0, step=5.0, value=30.0, key="orc_material")
        valor_hora = st.number_input("Valor da hora de produção (R$)", min_value=0.0, step=5.0, value=60.0, key="orc_valor_hora")
        margem_desejada = st.number_input("Margem desejada (%)", min_value=0.0, max_value=100.0, step=1.0, value=30.0, key="orc_margem")
        status_orcamento = st.selectbox("Status do Orçamento", ["Pendente", "Enviado", "Aprovado", "Recusado"], key="orc_status")
        telefone_whatsapp = st.text_input("Telefone/WhatsApp", placeholder="5511999999999", key="orc_tel")

        submit_orcamento = st.form_submit_button("Calcular e Salvar Orçamento")

        if submit_orcamento and nome_servico:
            custo_hora = horas_orcamento * valor_hora
            custo_total = custo_hora + custo_material_orcamento
            margem_decimal = margem_desejada / 100
            valor_orcamento = custo_total / (1 - margem_decimal) if margem_decimal < 1 else custo_total
            lucro_estimado = valor_orcamento - custo_total

            orcamento_data = {
                "nome_servico": nome_servico,
                "descricao_orcamento": descricao_orcamento,
                "horas_estimadas": horas_orcamento,
                "custo_material": custo_material_orcamento,
                "valor_hora": valor_hora,
                "margem_desejada": margem_desejada,
                "custo_total": custo_total,
                "valor_orcamento": valor_orcamento,
                "lucro_estimado": lucro_estimado,
                "status_orcamento": status_orcamento,
                "telefone_whatsapp": telefone_whatsapp,
                "data_criacao": str(datetime.now())
            }

            try:
                supabase.table("orcamentos").insert(orcamento_data).execute()
                st.success(f"Orçamento preparado e salvo para {nome_servico}")
            except Exception as e:
                try:
                    dados_fallback = {k: v for k, v in orcamento_data.items() if k not in {"descricao_orcamento", "telefone_whatsapp"}}
                    supabase.table("orcamentos").insert(dados_fallback).execute()
                    st.success(f"Orçamento preparado e salvo para {nome_servico}")
                except Exception as e2:
                    st.warning(f"Orçamento calculado, mas não foi possível salvar no banco: {e2}")

            col_orc1, col_orc2, col_orc3 = st.columns(3)
            col_orc1.metric("Custo Total", f"R$ {custo_total:,.2f}")
            col_orc2.metric("Valor do Orçamento", f"R$ {valor_orcamento:,.2f}")
            col_orc3.metric("Lucro Estimado", f"R$ {lucro_estimado:,.2f}")

            with st.expander("Detalhes do orçamento"):
                st.write(f"**Descrição:** {descricao_orcamento or 'Sem descrição adicional.'}")
                st.write(f"**Horas estimadas:** {horas_orcamento}")
                st.write(f"**Margem desejada:** {margem_desejada}%")
                st.write(f"**Status:** {status_orcamento}")

            pdf_bytes = gerar_pdf_orcamento({
                "nome_servico": nome_servico,
                "descricao_orcamento": descricao_orcamento,
                "horas_estimadas": horas_orcamento,
                "custo_material": custo_material_orcamento,
                "valor_hora": valor_hora,
                "margem_desejada": margem_desejada,
                "custo_total": custo_total,
                "valor_orcamento": valor_orcamento,
                "lucro_estimado": lucro_estimado,
                "status_orcamento": status_orcamento,
                "telefone_whatsapp": telefone_whatsapp,
            }, logo_path=str(logo_path) if logo_path.exists() else None)

            btn_col1, btn_col2 = st.columns([1, 1])
            with btn_col1:
                st.download_button(
                    "Baixar PDF do orçamento",
                    data=pdf_bytes,
                    file_name=f"orcamento_{nome_servico.lower().replace(' ', '_')}.pdf",
                    mime="application/pdf"
                )
            with btn_col2:
                if telefone_whatsapp:
                    url_whatsapp = gerar_link_whatsapp(telefone_whatsapp, nome_servico, valor_orcamento, status_orcamento)
                    st.link_button("Enviar por WhatsApp", url_whatsapp)
                else:
                    st.info("Preencha o telefone/WhatsApp para ativar o envio.")

    end_section()
    st.markdown("---")
    begin_section("Orçamentos Salvos", "Acompanhe o histórico de propostas e atualize seus status com agilidade.")

    status_id = st.number_input("ID do orçamento para atualizar status", min_value=1, step=1, key="orc_update_id")
    novo_status = st.selectbox("Novo status", ["Pendente", "Enviado", "Aprovado", "Recusado"], key="orc_update_status")
    if st.button("Atualizar status do orçamento"):
        try:
            supabase.table("orcamentos").update({"status_orcamento": novo_status}).eq("id", status_id).execute()
            st.success("Status atualizado com sucesso!")
            st.rerun()
        except Exception as e:
            st.error(f"Não foi possível atualizar o status: {e}")

    try:
        res_orcamentos = supabase.table("orcamentos").select("*").execute()
        if res_orcamentos.data:
            df_orcamentos = pd.DataFrame(res_orcamentos.data)
            st.dataframe(
                df_orcamentos[["id", "nome_servico", "status_orcamento", "valor_orcamento", "custo_total", "lucro_estimado", "data_criacao"]],
                use_container_width=True
            )
        else:
            st.info("Nenhum orçamento salvo ainda.")
    except Exception as e:
        st.info("Ainda não há orçamentos salvos ou a tabela não está disponível no momento.")
    end_section()

# ==========================================
# ABA 5: CONFIGURAÇÕES & SISTEMA
# ==========================================
elif selected_section == "Configurações":
    begin_section("Configurações do Sistema", "Ajuste o app, faça backups e mantenha o ateliê sempre organizado.", anchor="configuracoes-do-sistema")
    
    # SEÇÃO 1: BACKUP TOTAL DE DADOS
    st.markdown("### 💾 Backup de Segurança")
    st.write("Baixe todas as tabelas do sistema em formato CSV para salvar em seu computador.")
    
    if st.button("Gerar Arquivos de Backup"):
        try:
            # Puxa os dados brutos de todas as tabelas do Supabase
            b_pedidos = supabase.table("pedidos").select("*").execute().data
            b_financas = supabase.table("vendas_e_financas").select("*").execute().data
            b_estoque = supabase.table("estoque").select("*").execute().data
            
            # Converte para CSV em texto string simples
            csv_pedidos = pd.DataFrame(b_pedidos).to_csv(index=False).encode('utf-8')
            csv_financas = pd.DataFrame(b_financas).to_csv(index=False).encode('utf-8')
            csv_estoque = pd.DataFrame(b_estoque).to_csv(index=False).encode('utf-8')
            
            st.success("Arquivos de backup gerados com sucesso. Use os botões abaixo para baixar.")
            
            # Cria os botões de download nativos do navegador
            st.download_button("📥 Baixar Tabela de Pedidos", data=csv_pedidos, file_name="backup_pedidos.csv", mime="text/csv")
            st.download_button("📥 Baixar Tabela de Finanças", data=csv_financas, file_name="backup_financas.csv", mime="text/csv")
            st.download_button("📥 Baixar Tabela de Estoque", data=csv_estoque, file_name="backup_estoque.csv", mime="text/csv")
        except Exception as e:
            st.error(f"Não foi possível gerar o backup: {e}")
            
    st.markdown("---")
    
    # SEÇÃO 2: REINICIAR SISTEMA (Zerar Tudo)
    st.markdown("### Área de Perigo: Reiniciar Sistema")
    st.warning("Atenção: A ação abaixo apagará permanentemente todos os pedidos, finanças e estoque salvos no banco de dados!")
    
    # Caixa de confirmação de segurança para evitar cliques acidentais
    confirmacao = st.checkbox("Estou ciente de que esta ação é irreversível e quero apagar tudo.")
    
    if st.button("Apagar todos os dados do banco", type="secondary"):
        if confirmacao:
            try:
                # Deleta os dados respeitando a integridade das chaves estrangeiras
                # Primeiro a tabela dependente (finanças), depois a principal (pedidos)
                supabase.table("vendas_e_financas").delete().neq("id", 0).execute()
                supabase.table("pedidos").delete().neq("id", 0).execute()
                supabase.table("estoque").delete().neq("id", 0).execute()
                
                st.success("💥 Sistema reiniciado com sucesso! Todos os dados foram apagados.")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao limpar o banco de dados: {e}")
        else:
            st.error("❌ Operação cancelada. Você precisa marcar a caixa de confirmação antes de clicar no botão.")