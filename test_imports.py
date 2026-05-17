import sys
sys.path.insert(0, r'c:\Users\Relanto\Downloads\hackathon\support-lens\backend')

results = {}

try:
    from database import create_tables
    results['database'] = 'OK'
except Exception as e:
    results['database'] = f'ERROR: {e}'

try:
    import fastapi
    results['fastapi'] = f'OK v{fastapi.__version__}'
except Exception as e:
    results['fastapi'] = f'ERROR: {e}'

try:
    import uvicorn
    results['uvicorn'] = 'OK'
except Exception as e:
    results['uvicorn'] = f'ERROR: {e}'

try:
    import sqlalchemy
    results['sqlalchemy'] = 'OK'
except Exception as e:
    results['sqlalchemy'] = f'ERROR: {e}'

try:
    from ai.pii_masker import mask_pii
    results['pii_masker'] = 'OK'
except Exception as e:
    results['pii_masker'] = f'ERROR: {e}'

try:
    from ai.pipeline import process_ticket
    results['pipeline'] = 'OK'
except Exception as e:
    results['pipeline'] = f'ERROR: {e}'

try:
    from ai.rag_engine import build_index
    results['rag_engine'] = 'OK'
except Exception as e:
    results['rag_engine'] = f'ERROR: {e}'

try:
    from ai.ollama_client import check_connection
    results['ollama_client'] = 'OK'
except Exception as e:
    results['ollama_client'] = f'ERROR: {e}'

for k, v in results.items():
    print(f'{k}: {v}')
