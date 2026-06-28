import os
from supabase import create_client, Client
from dotenv import load_dotenv

# 1. Carrega as variáveis do .env
load_dotenv()
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_KEY")

print("--- Iniciando Teste de Conexão ---")
print(f"URL carregada: {url}")
print(f"Chave carregada: {key[:15] if key else None}... (exibindo apenas o início)")

# 2. Tenta conectar
try:
    print("\nTentando conectar ao Supabase...")
    supabase: Client = create_client(url, key)
    
    # Faz uma requisição leve para verificar se as chaves são válidas
    # Mesmo se a tabela não existir, se a chave for válida ele não dará erro de autenticação
    supabase.table("pedidos").select("id").limit(1).execute()
    print("📢 RESULTADO: Conexão realizada com sucesso total!")
    
except Exception as e:
    print("\n❌ ERRO DE CONEXÃO!")
    print(f"Detalhes do erro: {e}")