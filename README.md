# Crediclass Dashboard V3

Aplicacao interna para Larissa manter a base de grupos e Joyce gerar estudos financeiros.

## Stack

- Python 3.12
- FastAPI
- Uvicorn
- Pydantic
- Google Sheets API
- HTML5
- Bootstrap 5
- JavaScript Vanilla
- Chart.js
- Render

## Executar localmente

```bash
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload
```

Acesse `http://127.0.0.1:8000`.

## Etapa atual

Etapa 0 - Base:

- FastAPI servindo frontend estatico.
- Sidebar global.
- Navegacao entre telas sem reload.
- Cliente API em `api.js`.
- Health check em `/api/health`.
