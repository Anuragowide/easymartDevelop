# Indexing Script: `index_from_salesforce.py` 🔧

## 📌 Overview
This document explains the new Python script added during our debugging session: `app/scripts/index_from_salesforce.py`.

- **Path:** `app/scripts/index_from_salesforce.py`
- **Purpose:** populate the local Catalog index by fetching products from the Python Salesforce exporter and, if needed, by running fallback seeded searches against the Python search endpoint.
- **Why it was created:** while testing the assistant tool loop, the catalog index was empty which caused product searches from the assistant to return zero results. To reproduce and validate the end-to-end behavior (LLM → tools → product cards in UI) without changing existing Python classes or Apex, this safe, non-invasive script was added to gather and index products.

---

## 🧭 Behavior & Implementation Details

Key features:

- Adds project root to `sys.path` so the script can be executed directly from the repository root.
- Configurable constants at top of the script:
  - `PYTHON_URL` (default: `http://127.0.0.1:8000`)
  - `EXPORT_PATH` (`/internal/salesforce/export`)
  - `PAGE_SIZE` and `MAX_PAGES` for pagination

Main flow (function `fetch_all_products()`):
1. **Try the exporter first**: page through `/internal/salesforce/export` and collect `products` pages until exhausted.
2. **Fallback (if exporter empty)**: run seeded search queries against `/internal/salesforce/search` (queries like `sofa`, `chair`, `bed`, etc.) and deduplicate results by product id/sku. This was necessary because some orgs return limited export results and the search endpoint responds to targeted queries.
3. **Index**: use `CatalogIndexer.addProducts()` to add products to BM25 and vector indexes and then call `addSpecs()` to index extracted specs (using existing `extract_specs_from_products()` logic).
4. Respect light throttling (`time.sleep(0.2)`) and safety limits (stop after a reasonable product count).

Important implementation notes:
- The script performs HTTP calls only to local Python endpoints (no changes to existing routes or classes were required).
- It is designed to be non-destructive: it only adds to the index; clearing indexes must be done separately if needed.

---

## ✅ Why this was useful (session context)
- While debugging, the assistant tool loop was correctly invoking `search_products`, but the Catalog was empty, so the assistant returned no product cards. The indexing script enabled us to:
  - Populate the local catalog quickly for test scenarios, and
  - Validate that once the index is populated, the assistant returns product cards to the UI.

---

## ▶️ How to run (local dev)

1. Ensure Python server is running:
```bash
cd backend-pylang
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
2. Run the indexing script:
```bash
python app/scripts/index_from_salesforce.py
```
3. Test the assistant via the trace script or messaging endpoint:
```bash
python trace_tool_calls.py
# or
curl -X POST "http://127.0.0.1:8000/assistant/message" -H "Content-Type: application/json" -d '{"message":"Show me queen size bed frame","session_id":"test"}'
```

---

## 📝 Results we observed (during the session)
- Exporter returned 0 products on page 1, so the script fell back to seeded searches.
- The seeded queries returned 194 distinct products which were indexed successfully.
- After indexing, `search_products` returned non-empty results and `/assistant/message` responses included product cards.

---

## ⚠️ Notes and next steps
- This script is intended for development/testing only (not production).
- Suggestions for improvements:
  - Add CLI flags (e.g., `--source=export|search`, `--limit`, `--dry-run`).
  - Add better error handling and retries for transient HTTP errors.
  - Add an integration test that runs the script (or a mock) and asserts that `/assistant/message` returns products.

---

If you want, I can:
- Add a small CLI wrapper to accept parameters and make the script more robust, and/or
- Add an automated test and CI job that indexes sample products in test mode and asserts the assistant returns products.

Would you like me to add a CLI and tests? ✅
