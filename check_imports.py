import importlib
import sys
print('PYTHON_OK')
modules = ['streamlit','supabase','dotenv','pandas','sklearn','numpy','scipy']
for m in modules:
    try:
        importlib.import_module(m)
        print(f'{m} OK')
    except Exception as e:
        print(f'{m} ERR: {e}')
sys.stdout.flush()
