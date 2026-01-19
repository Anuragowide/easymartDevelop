# Production Notes (PyLang)

## Recommended Run Command

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 2 --timeout-keep-alive 5
```

## Environment Checklist

- `OPENAI_API_KEY` set
- `NODE_BACKEND_URL` reachable
- `data/` is writable for session persistence
- `LOG_FORMAT=json` for structured logs

## Scaling

- Use Redis to replace in-memory sessions for multi-instance deployments.
- Add a reverse proxy (nginx) for TLS and request buffering.
