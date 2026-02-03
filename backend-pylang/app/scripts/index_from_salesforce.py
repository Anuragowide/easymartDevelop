"""
Index products by fetching from Python's own Salesforce exporter endpoint
and adding them to the CatalogIndexer.

Usage:
  python app/scripts/index_from_salesforce.py

This script will page through /internal/salesforce/export and index all returned products
using CatalogIndexer.addProducts and addSpecs.
"""
import sys
import os
import requests
import time
# Ensure project root is on sys.path for local script execution
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.modules.catalog_index.catalog import CatalogIndexer
from app.modules.catalog_index.load_catalog import extract_specs_from_products

PYTHON_URL = "http://127.0.0.1:8000"
EXPORT_PATH = "/internal/salesforce/export"
PAGE_SIZE = 100
MAX_PAGES = 50


def fetch_all_products():
    """Try exporter first, fallback to several seeded search queries if exporter is empty."""
    all_products = []
    # 1) Try exporter pages
    for page in range(1, MAX_PAGES + 1):
        params = {"page": page, "pageSize": PAGE_SIZE}
        print(f"[IndexScript] Fetching export page {page}...")
        try:
            r = requests.get(f"{PYTHON_URL}{EXPORT_PATH}", params=params, timeout=60)
            r.raise_for_status()
            data = r.json()
        except Exception as e:
            print(f"[IndexScript] Export fetch failed: {e}")
            break

        if isinstance(data, dict) and data.get("products"):
            items = data.get("products")
        elif isinstance(data, list):
            items = data
        else:
            items = data.get("products") if isinstance(data, dict) else []

        if not items:
            print(f"[IndexScript] No products in export page {page}")
            break

        print(f"[IndexScript] Retrieved {len(items)} products from export page {page}")
        all_products.extend(items)

        if len(items) < PAGE_SIZE:
            print("[IndexScript] Last export page reached.")
            break

        time.sleep(0.2)

    # 2) If export returned nothing, fallback to seeded searches
    if not all_products:
        print("[IndexScript] Export empty — falling back to seeded search queries")
        seed_queries = ["sofa", "chair", "bed", "table", "desk", "sofa bed", "dining table", "coffee table", "tv unit", "sofa set"]
        seen_ids = set()
        for q in seed_queries:
            print(f"[IndexScript] Searching for '{q}'...")
            try:
                resp = requests.post(f"{PYTHON_URL}/internal/salesforce/search", json={"query": q, "page": 1, "pageSize": PAGE_SIZE}, timeout=60)
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                print(f"[IndexScript] Search fetch failed for '{q}': {e}")
                continue

            items = []
            if isinstance(data, dict):
                items = data.get("products") or data.get("results") or []
            elif isinstance(data, list):
                items = data

            print(f"[IndexScript] Search '{q}' returned {len(items)} items")
            for p in items:
                pid = p.get("id") or p.get("sku") or p.get("productId")
                if pid and pid not in seen_ids:
                    seen_ids.add(pid)
                    all_products.append(p)

            # Stop when we have a decent set
            if len(all_products) >= 200:
                print("[IndexScript] Enough products collected from seeded queries")
                break

            time.sleep(0.2)

    return all_products


if __name__ == "__main__":
    print("[IndexScript] Starting Salesforce -> Catalog indexing...")
    prods = fetch_all_products()
    if not prods:
        print("[IndexScript] No products fetched. Exiting.")
        exit(1)

    print(f"[IndexScript] Total products fetched: {len(prods)}")

    indexer = CatalogIndexer()
    print("[IndexScript] Indexing products...")
    indexer.addProducts(prods)

    # Extract specs (same logic as load_catalog)
    specs = extract_specs_from_products(prods)
    if specs:
        print(f"[IndexScript] Indexing {len(specs)} specs...")
        indexer.addSpecs(specs)

    print("[IndexScript] Indexing complete.")