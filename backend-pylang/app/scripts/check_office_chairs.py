# backend-pylang/scripts/check_office_chairs.py
from pathlib import Path
import sqlite3, sys, json

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "data" / "easymart.db"
if not DB.exists():
    DB = Path(__file__).resolve().parents[1] / "data" / "easymart.db"

print(f"DB path: {DB}")

# 1) Quick SQL checks
conn = sqlite3.connect(DB)
cur = conn.cursor()
print("COUNT category LIKE '%office%':", cur.execute(
    "select count(*) from products where lower(coalesce(category,'')) like '%office%'"
).fetchone()[0])
print("\nEXAMPLES (category LIKE '%office%'):")
for row in cur.execute(
    "select sku,title,price,inventory_quantity,available,category from products where lower(coalesce(category,'')) like '%office%' limit 10"
):
    print(row)

print("\nCOUNT title LIKE '%chair%':", cur.execute(
    "select count(*) from products where lower(coalesce(title,'')) like '%chair%'"
).fetchone()[0])
print("\nEXAMPLES (title LIKE '%chair%'):")
for row in cur.execute(
    "select sku,title,price,inventory_quantity,available,category from products where lower(coalesce(title,'')) like '%chair%' limit 10"
):
    print(row)
conn.close()

# 2) BM25 / CatalogIndexer candidates (may initialize models)
try:
    sys.path.insert(0, str(ROOT))
    from app.modules.catalog_index.catalog import CatalogIndexer
    print("\nInitializing CatalogIndexer (may load embedding model)...")
    c = CatalogIndexer()
    q = "office chair"
    print(f"\nRunning BM25 candidates for: '{q}'")
    res = c.searchProducts(q, limit=20, use_advanced=False)
    print("BM25 candidate count:", len(res))
    for r in res[:20]:
        content = r.get("content") or {}
        title = content.get("title") or content.get("handle")
        print(r.get("id"), round(r.get("score", 0), 4), title, content.get("category"))
except Exception as e:
    print("CatalogIndexer check failed:", repr(e))