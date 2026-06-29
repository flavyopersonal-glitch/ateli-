# ateli-

Projeto Streamlit para gestão de PCP (Produção, Estoque e Financeiro) usando Supabase.

Pré-requisitos
- Python 3.11
- Ter uma instância Supabase e as chaves `SUPABASE_URL` e `SUPABASE_KEY`.

Instalação rápida
1. Crie e ative um ambiente virtual:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

2. Instale dependências:

```powershell
pip install -r requirements.txt
```

3. Copie `.env.example` para `.env` e preencha as variáveis:

```powershell
copy .env.example .env
# editar .env e colar SUPABASE_URL e SUPABASE_KEY
```

Execução

```powershell
# testar conexão com Supabase
venv\Scripts\python.exe testar_conexao.py

# rodar a aplicação Streamlit
venv\Scripts\python.exe -m streamlit run app.py
```

Observações
- As tabelas `pedidos`, `estoque` e `vendas_e_financas` devem existir no Supabase (ou serem criadas automaticamente via sua interface).
- Não compartilhe sua `SUPABASE_KEY` em repositórios públicos.

Contribuição
- Abra uma issue descrevendo o bug ou a melhoria desejada.
