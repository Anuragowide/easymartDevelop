# Easymart PyLang Backend

LangChain-based FastAPI backend for the Easymart shopping assistant.

## Quick Start

```bash
cd backend-pylang
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8001
```

## Endpoints

- `GET /health/`
- `POST /assistant/message`
- `GET /assistant/greeting`
- `GET /assistant/session/{session_id}`
- `DELETE /assistant/session/{session_id}`
- `POST /assistant/cart`
- `GET /assistant/cart`

## Notes

- Catalog indexing uses the same hybrid BM25 + vector stack as `backend-python`.
- Sessions are stored in-memory with disk backup at `data/sessions.pkl`.
