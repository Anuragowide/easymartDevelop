# Salesforce API Testing Plan (Search + Cart)

This document covers how to test the Salesforce-related APIs (Search, Cart) and includes commands, expected behavior, and a plan for implementing tests where functionality is missing.

## Scope
- Search: `/internal/salesforce/search` (POST), `/internal/salesforce/export` (GET)
- Product detail: `/internal/salesforce/product/{id}` (GET)
- Cart: Apex endpoints exposed by `CartApi` on Salesforce (mapped by Python to `CartService`):
  - `CartApi/getCart` (GET) → Node adapter `cart.getCart`
  - `CartApi/addItem` (POST) → Node adapter `cart.addToCart`
  - `CartApi/updateItem` (POST or PATCH) → Node adapter `cart.updateCartItem`
  - `CartApi/removeItem` (POST or DELETE) → Node adapter `cart.removeFromCart`

## Manual test commands

### Python (direct)
- Search (POST):
```bash
curl -i -X POST "http://127.0.0.1:8000/internal/salesforce/search" \
  -H "Content-Type: application/json" -d '{"query":"chair","page":1,"pageSize":5}'
```

- Export (GET):
```bash
curl -i "http://127.0.0.1:8000/internal/salesforce/export?page=1&pageSize=5&query=chair"
```

- Product detail:
```bash
curl -i "http://127.0.0.1:8000/internal/salesforce/product/01tdL00000YFNAYQA5"
```

### Node (via gateway)
- Debug search (should return raw/normalized search results):
```bash
curl -i -X POST "http://127.0.0.1:3001/api/internal/catalog/debug-search" \
  -H "Content-Type: application/json" -d '{"query":"chair","page":1,"pageSize":5}'
```

- Export (gateway forwards to Python export):
```bash
curl -i -X POST "http://127.0.0.1:3001/api/internal/catalog/export" \
  -H "Content-Type: application/json" -d '{"query":"chair","page":1,"pageSize":5}'
```

### Cart (node -> python -> salesforce)
> Note: Apex Cart endpoints behavior depends on your org's Cart API (examples below assume the `CartApi` above)

- Get cart:
```bash
curl -i "http://127.0.0.1:8000/internal/salesforce/cart?buyerAccountId=001..."
```

- Add to cart:
```bash
curl -i -X POST "http://127.0.0.1:8000/internal/salesforce/cart/add" -H "Content-Type: application/json" -d '{"productId":"01tdL...","quantity":1,"buyerAccountId":"001..."}'
```

- Update cart item:
```bash
curl -i -X POST "http://127.0.0.1:8000/internal/salesforce/cart/update" -H "Content-Type: application/json" -d '{"cartItemId":"500...","quantity":2,"buyerAccountId":"001..."}'
```

- Remove cart item:
```bash
curl -i -X POST "http://127.0.0.1:8000/internal/salesforce/cart/remove" -H "Content-Type: application/json" -d '{"cartItemId":"500...","buyerAccountId":"001..."}'
```

## Automated tests to add

### Python (pytest)
- Unit tests for `salesforce_client` with `responses` or `requests-mock` to simulate token responses and Apex JSON payloads.
- Integration tests for `salesforce_api` using FastAPI TestClient to assert behavior when `post_search()` returns either dict or list responses.

### Node (jest + supertest)
- Test `/api/internal/catalog/debug-search` and `/api/internal/catalog/export` using a running Python test server (or a mocked HTTP server that returns Apex-like payloads).
- Assert normalized keys and `totalSize` on `export`.

## If functionality is not implemented (Plan)
1. Implement missing adapter methods in `backend-node/src/modules/salesforce_adapter/cart.ts` (getCart/addToCart/updateCartItem/removeFromCart), using the `SalesforceClient` axios instance to call the Apex Cart endpoints.
2. Add Python endpoints (optional) to proxy cart operations if you want Node -> Python -> Salesforce path.
3. Add unit tests for new methods and integration tests using a test Salesforce sandbox or mocked endpoints.
4. Add CI job to run these integration tests when secrets are set.

## Edge cases & notes
- Ensure `SALESFORCE_JWT_PRIVATE_KEY` formatting is correct when stored in `.env` (newlines replaced or use the raw multi-line file loader).
- Be mindful of rate limits in Salesforce; add exponential backoff if you see 429s.
- For cart operations, validate buyer identity/authorization; the Cart API often needs a buyerAccountId or session context.

---

Document created on: 2026-01-30
