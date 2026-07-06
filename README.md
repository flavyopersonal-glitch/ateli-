# Ateliê Cristo Rei

Aplicação Streamlit para gestão de produção, estoque, finanças e orçamentos de ateliê com visual escuro, navegação limpa e integração com Supabase.

## Recursos principais
- Cadastro e acompanhamento de pedidos de produção
- Controle de estoque com alertas de reposição
- Dashboard financeiro com receita, custo e margem
- Previsão de faturamento por tendência usando regressão linear
- Geração de orçamentos em PDF e envio via WhatsApp
- Backup de tabelas em CSV
- Área de configurações para reset do banco e exportação de dados

## Pré-requisitos
- Python 3.11
- Conta Supabase ativa
- Variáveis de ambiente:
  - `SUPABASE_URL`
  - `SUPABASE_KEY`

## Instalação local
1. Crie e ative um ambiente virtual:

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
```

2. Instale as dependências:

```powershell
pip install -r requirements.txt
```

3. Configure as credenciais:

```powershell
copy .env.example .env
```

Edite o arquivo `.env` e adicione `SUPABASE_URL` e `SUPABASE_KEY`.

## Execução

```powershell
venv\Scripts\python.exe -m streamlit run app.py
```

## Verificações úteis
- Testar a conexão com Supabase:

```powershell
venv\Scripts\python.exe testar_conexao.py
```

- Verificar se as dependências importam corretamente:

```powershell
venv\Scripts\python.exe check_imports.py
```

## Tabelas esperadas no Supabase
- `pedidos`
- `estoque`
- `vendas_e_financas`
- `orcamentos`

## Execução com Docker

```powershell
docker build -t atelie-cristo-rei .
docker run --rm -p 8501:8501 atelie-cristo-rei
```

O app ficará disponível em `http://localhost:8501`.

## Observações
- Não compartilhe suas credenciais `SUPABASE_KEY` em repositórios públicos.
- O app tem foco em usabilidade móvel e visual escuro profissional.

## Contribuição
- Abra uma issue para bugs ou melhorias.
