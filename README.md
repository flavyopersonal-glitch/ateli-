# Ateliê Cristo Rei

Aplicação para acompanhar pedidos de imagens de gesso, criar orçamentos em PDF e registrar o financeiro do ateliê.

## Executar

```powershell
venv\Scripts\python.exe -m pip install -r requirements.txt
venv\Scripts\python.exe -m streamlit run app.py
```

Os dados são salvos automaticamente no arquivo `data/atelie.db`. Faça uma cópia desse arquivo para manter um backup dos seus pedidos e lançamentos.
