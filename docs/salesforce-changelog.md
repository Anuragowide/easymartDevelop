# Salesforce Integration — Changelog

This changelog summarizes all notable changes across the repository made during the Salesforce integration work.

## 2026-01-30 — Major integration (node + python)

### backend-node
- Added `src/modules/salesforce_adapter/`:
  - `client.ts` — Salesforce OAuth client (JWT + password flow)
  - `products.ts` — product search and getById adapters (normalization)
  - `cart.ts` — cart helpers (get/add/update/remove)
  - `types.ts` and `index.ts`
- Updated `src/config/env.ts` to include Salesforce env vars and `ACTIVE_PLATFORM` support.
- Updated `src/modules/web/routes/catalog.route.ts`:
  - Fixed GET/POST route registration and removed nested registrations.
  - Added `POST /api/internal/catalog/export` forwarding to Python export endpoint.
  - Added `POST /api/internal/catalog/debug-search` forwarding to Python search endpoint.
  - Added diagnostics and richer upstream error logging.

### backend-pylang
- Added `app/modules/salesforce_client.py`, `app/modules/normalizer.py`, and `app/api/salesforce_api.py`.
- Registered `salesforce_router` in `app/main.py`.
- Added `PyJWT` and `cryptography` to requirements.
- Updated normalizer to better handle Apex payload shapes.

### Docs & tests
- Added test & operations docs:
  - `docs/testing-salesforce-e2e.md` (E2E test instructions)
  - `docs/backend-pylang-salesforce-changes.md` (Python changes summary)
  - `docs/salesforce-changelog.md` (this changelog)

## Notes
- The Node route previously forwarded POST to a Python GET endpoint causing 405; fixed by mapping POST → GET for export and POST → POST for search.
- Normalization rules were iterated after seeing real Apex responses — run the debug endpoints to validate.

---

Document created on: 2026-01-30
