# Salesforce E2E Tests (Node → Python → Salesforce)

This document describes tests to cover the full end-to-end flow from the Node gateway to the Python exporter and onward to Salesforce Apex endpoints (search/export).

## Goals
- Verify Node forwards requests to Python correctly (paths, methods, query/body mapping).
- Verify Python authenticates with Salesforce and transforms Apex responses to normalized product shape.
- Validate the final returned product list shape and paging/totalSize handling.

## Test matrix
- Unit tests (fast, local): Node adapters + Python unit tests for `normalizer`.
- Integration tests (requires Python running): Node -> Python, mocking Salesforce responses.
- E2E tests (optional, live): Node -> Python -> real Salesforce sandbox (requires credentials).

## Suggested tests

1) Unit
- Node: Test `getAdapter()` when `ACTIVE_PLATFORM=salesforce` to ensure adapter methods exist and `client.getAxios()` is available.
- Python: Test `normalize_product()` with representative Apex product payloads.

2) Integration (Node + Python)
- Start Python server `uvicorn app.main:app --reload --port 8000` (use local test mode or mock Salesforce calls).
- Node test (jest + supertest):
  - POST `/api/internal/catalog/debug-search` with JSON {query,page,pageSize} and verify status 200 and body.products is an array with normalized keys (`id`, `title`, `price`).
  - POST `/api/internal/catalog/export` with JSON {query,page,pageSize} and verify response has `page`, `pageSize`, `totalSize`, `products`.

3) E2E (live Salesforce)
- Provision sandbox and set env vars in `backend-node/.env` and `backend-pylang/.env` (SALESFORCE_JWT_PRIVATE_KEY, SALESFORCE_JWT_CLIENT_ID, SALESFORCE_JWT_USERNAME, SALESFORCE_TOKEN_URL).
- Start Python and Node servers locally.
- Run Node POST `/api/internal/catalog/export` and assert returned `totalSize > 0` and products are non-empty.

## Test examples (commands)

- Run Python locally:
```bash
cd backend-pylang
python -m venv .venv
.\.venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- Run Node locally:
```bash
cd backend-node
pnpm install
pnpm dev
```

- Quick curl (Node export):
```bash
curl -v -X POST "http://127.0.0.1:3001/api/internal/catalog/export" \
  -H "Content-Type: application/json" -H "Origin: http://localhost:3000" \
  -d '{"query":"chair","page":1,"pageSize":5}'
```

- PowerShell (Node export):
```powershell
$body = @{ query='chair'; page=1; pageSize=5 } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:3001/api/internal/catalog/export' -Headers @{ Origin='http://localhost:3000' } -Body $body -ContentType 'application/json'
```

## Test assertions
- HTTP 200 returned from Node for queries.
- `products` array exists and each product contains: `id`, `sku` (if present), `title`, `price`, `image_url` (or null), `product_url`.
- `totalSize` should be present and consistent across pages.

## CI suggestions
- Add a GitHub Actions job that starts Python (test mode) and Node and runs the integration tests.
- Keep live Salesforce tests gated behind a secret-driven job that runs only on demand.

---

Document created on: 2026-01-30
