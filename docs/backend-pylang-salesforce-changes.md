# Backend PyLang — Salesforce Integration Changes

This document summarizes the concrete changes made in `backend-pylang` to support Salesforce integration and normalization.

## Summary of changes
- Added `app/modules/salesforce_client.py`:
  - Implements JWT Bearer and password OAuth flows to obtain Salesforce access tokens.
  - Methods: `ensure_token()`, `_request_token_with_jwt()`, `_request_token_with_password()`, `post_search()` and `get_product()`.
  - Uses `requests` and `PyJWT` for RS256 signing.

- Added `app/modules/normalizer.py`:
  - `normalize_product(raw)` now maps common Apex field names: `productId`, `productName`, `UnitPrice`, `imageUrl`, etc.
  - Returns the normalized shape expected by the Node gateway and Python catalog indexer.

- Added `app/modules/salesforce_api.py`:
  - Exposes endpoints used by Node:
    - POST `/internal/salesforce/search` (POST body: {query,page,pageSize}) → returns products + paging
    - GET `/internal/salesforce/export` (query params: ?query=&page=&pageSize=) → supports paginated export
    - GET `/internal/salesforce/product/{product_id}` → returns product details
  - Accepts both A) dict-wrapped responses (e.g., {products:[], totalSize: N}) and B) raw list responses from Apex.

- Modified `app/main.py` to include `salesforce_router` and `load_dotenv()`.

- Requirements updated: `PyJWT` and `cryptography` added in `requirements.txt`.

## Implementation notes
- Token acquisition uses JWT assertion (RS256). If the `SALESFORCE_JWT_PRIVATE_KEY` is present, the client attempts the JWT flow first then falls back to the password flow.
- `post_search()` returns `(status_code, parsed_json_or_empty_dict)` and the router maps and normalizes the results to a consistent shape.

## Environment variables to set
- SALESFORCE_TOKEN_URL
- SALESFORCE_JWT_CLIENT_ID
- SALESFORCE_JWT_USERNAME
- SALESFORCE_JWT_PRIVATE_KEY (multi-line, replace \n with newline in .env or pass raw)
- Alternative password fields: SALESFORCE_CLIENT_ID, SALESFORCE_CLIENT_SECRET, SALESFORCE_USERNAME, SALESFORCE_PASSWORD, SALESFORCE_SECURITY_TOKEN

## How to test manually
1. Start Python server:
   ```bash
   cd backend-pylang
   .\.venv\Scripts\Activate.ps1
   uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
   ```
2. Test search:
   ```bash
   curl -X POST "http://127.0.0.1:8000/internal/salesforce/search" -H "Content-Type: application/json" -d '{"query":"chair","page":1,"pageSize":5}'
   ```
3. Test export:
   ```bash
   curl "http://127.0.0.1:8000/internal/salesforce/export?page=1&pageSize=5"
   ```

---

Document created on: 2026-01-30
