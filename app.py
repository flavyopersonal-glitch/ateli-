import os
import streamlit as st
from supabase import create_client, Client
from dotenv import load_dotenv

# Carrega as senhas do arquivo .env
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

# Conecta ao Supabase
try:
    supabase: Client = create_client(url, key)
    conexao_ok = True
except Exception:
    conexao_ok = False

# Configuração da página do Streamlit
st.set_page_config(page_title="PCP Ateliê", layout="wide")

st.title("🏭 Controle de Produção & Prazos")
st.markdown("---")

if conexao_ok:
    st.sidebar.success("⚡ Conectado ao Supabase!")
else:
    st.sidebar.error("❌ Erro ao conectar ao Supabase. Verifique o arquivo .env")

# Abas do sistema
aba_inserir, aba_fila = st.tabs(["📝 Inserir Pedido", "📊 Fila de Produção"])

with aba_inserir:
    st.subheader("Cadastrar Novo Pedido")
    with st.form("formulario_pedido"):
        cliente = st.text_input("Nome do Cliente / Pedido")
        horas = st.number_input("Horas estimadas de produção", min_value=0.5, step=0.5, value=1.0)
        urgente = st.checkbox("🔥 PEDIDO URGENTE (Furar Fila)")
        
        botao = st.form_submit_button("Agendar na Produção")
        
        if botao:
            if cliente:
                st.info(f"Simulando agendamento: {cliente} ({horas}h) - Urgente: {urgente}")
            else:
                st.warning("Por favor, preencha o nome do cliente.")

with aba_fila:
    st.subheader("Cronograma da Fábrica")
    st.info("Aqui vai aparecer o calendário dinâmico recalculado pelo algoritmo.")