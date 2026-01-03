# Search Improvements - Migration & Rollback Guide

## Overview

This guide covers migration, rollback, and troubleshooting for the search improvements.

## Migration Steps

### Automatic Migration (Recommended)

The changes are **backward compatible** and migrate automatically:

1. **Pull the code changes**
2. **Restart the backend server**
3. **Done!** FTS5 table and indexes are created automatically

### What Happens on First Start

```
[DB] Connected to SQLite: .../data/chromadb/catalog.db
[DB] Created FTS5 virtual table with triggers
[BM25] Initialized index: products_index
[BM25] Loaded index from .../data/bm25/products_index.pkl
```

The system will:
- ✅ Check if `products_fts` table exists
- ✅ Create FTS5 virtual table if missing
- ✅ Create triggers to keep FTS5 in sync
- ✅ Create indexes on products table
- ✅ Populate FTS5 from existing products (via triggers)

**No data loss, no manual steps required.**

## Verification

### 1. Check FTS5 Table

```bash
cd backend-python
python -c "
from app.modules.catalog_index.indexing.database import DatabaseManager
import sqlite3

db = DatabaseManager()
conn = sqlite3.connect(db.db_path)
cursor = conn.cursor()

# Check tables
cursor.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")
tables = [row[0] for row in cursor.fetchall()]
print('Tables:', tables)

# Verify FTS5 exists
if 'products_fts' in tables:
    print('✅ FTS5 table created successfully')
else:
    print('❌ FTS5 table NOT found')

conn.close()
"
```

### 2. Check Indexes

```bash
python -c "
from app.modules.catalog_index.indexing.database import DatabaseManager
import sqlite3

db = DatabaseManager()
conn = sqlite3.connect(db.db_path)
cursor = conn.cursor()

# Check indexes
cursor.execute(\"SELECT name FROM sqlite_master WHERE type='index'\")
indexes = [row[0] for row in cursor.fetchall()]
print('Indexes:', indexes)

# Check for our new indexes
if 'idx_vendor_price' in indexes:
    print('✅ Composite index created')
else:
    print('⚠️ Composite index not found')

conn.close()
"
```

### 3. Test Search

```bash
python test_search_improvements.py
```

Expected output:
```
================================================================================
Testing FTS5 Full-Text Search (Direct)
================================================================================

Query: 'gaming chair'
Found 5 results

1. Gaming Chair Pro
   SKU: CHAIR-001
   Relevance: -2.5
...
```

## Rollback (If Needed)

If you need to revert the changes:

### Option 1: Quick Rollback (Keep FTS5, Revert Code)

Just revert the code changes - FTS5 table won't hurt anything:

```bash
git checkout HEAD~1 -- app/modules/catalog_index/indexing/
```

### Option 2: Full Rollback (Remove FTS5)

Remove FTS5 table and revert code:

```bash
# 1. Remove FTS5 table
python -c "
from app.modules.catalog_index.indexing.database import DatabaseManager
import sqlite3

db = DatabaseManager()
conn = sqlite3.connect(db.db_path)
cursor = conn.cursor()

# Drop FTS5 table and triggers
cursor.execute('DROP TABLE IF EXISTS products_fts')
cursor.execute('DROP TRIGGER IF EXISTS products_fts_insert')
cursor.execute('DROP TRIGGER IF EXISTS products_fts_update')
cursor.execute('DROP TRIGGER IF EXISTS products_fts_delete')

conn.commit()
conn.close()
print('✅ FTS5 removed')
"

# 2. Revert code
git checkout HEAD~1 -- app/modules/catalog_index/indexing/
```

### Option 3: Fresh Database

Start with a clean database:

```bash
# Backup current database
cp backend-python/data/chromadb/catalog.db backend-python/data/chromadb/catalog.db.backup

# Remove database (will be recreated)
rm backend-python/data/chromadb/catalog.db

# Remove BM25 indexes
rm -rf backend-python/data/bm25/*

# Restart server (will rebuild from Shopify)
python backend-python/start_server.py
```

## Troubleshooting

### Problem: FTS5 not working

**Symptom:** No "products_fts" table found

**Solution:**
```python
from app.modules.catalog_index.indexing.database import DatabaseManager

# Force re-initialization
db = DatabaseManager()
db._setup_fts5()  # Manually call FTS5 setup
```

### Problem: Triggers not firing

**Symptom:** FTS5 table exists but has no data

**Solution:**
```python
import sqlite3
from app.modules.catalog_index.indexing.database import DatabaseManager

db = DatabaseManager()
conn = sqlite3.connect(db.db_path)
cursor = conn.cursor()

# Manually populate FTS5 from products
cursor.execute("""
    INSERT INTO products_fts(rowid, sku, title, description, search_content)
    SELECT rowid, sku, title, description, search_content FROM products
""")
conn.commit()
conn.close()

print('✅ FTS5 populated manually')
```

### Problem: Slow search after update

**Symptom:** Queries take longer than before

**Possible causes:**
1. Database needs VACUUM (defragmentation)
2. Indexes not created properly
3. Cache not working

**Solution:**
```python
import sqlite3
from app.modules.catalog_index.indexing.database import DatabaseManager

db = DatabaseManager()
conn = sqlite3.connect(db.db_path)

# Optimize database
conn.execute('VACUUM')
conn.execute('ANALYZE')
conn.commit()
conn.close()

print('✅ Database optimized')
```

### Problem: Wrong results after update

**Symptom:** Search returns unexpected products

**Debug steps:**
```python
from app.modules.catalog_index import CatalogIndexer

indexer = CatalogIndexer()
results = indexer.searchProducts("gaming chair", limit=5)

for r in results:
    print(f"\nTitle: {r['content']['title']}")
    print(f"Score: {r['score']}")
    print(f"BM25 Rank: {r.get('bm25_rank')}")
    print(f"Vector Rank: {r.get('vector_rank')}")
    print(f"Phrase Boost: {r.get('phrase_boost', 'N/A')}")
```

Check:
- Do results have phrase_boost > 1.0?
- Are BM25 and Vector ranks reasonable?
- Is the title relevant to the query?

## Performance Benchmarks

Run benchmarks to verify improvements:

```bash
python -c "
import asyncio
import time
from app.modules.retrieval.product_search import ProductSearcher

async def benchmark():
    searcher = ProductSearcher()
    
    queries = ['chair', 'gaming chair', 'blue office chair under 300']
    
    for query in queries:
        times = []
        for _ in range(10):
            start = time.time()
            await searcher.search(query, limit=10)
            times.append(time.time() - start)
        
        avg_ms = (sum(times) / len(times)) * 1000
        print(f'{query}: {avg_ms:.2f}ms avg')

asyncio.run(benchmark())
"
```

Expected results:
- Simple queries: < 20ms
- Complex queries with filters: < 50ms

## Database Schema Changes

### New Tables

```sql
-- FTS5 virtual table
CREATE VIRTUAL TABLE products_fts USING fts5(
    sku UNINDEXED,
    title,
    description,
    search_content,
    content=products,
    content_rowid=rowid
);
```

### New Triggers

```sql
-- Insert trigger
CREATE TRIGGER products_fts_insert AFTER INSERT ON products 
BEGIN
    INSERT INTO products_fts(rowid, sku, title, description, search_content)
    VALUES (new.rowid, new.sku, new.title, new.description, new.search_content);
END;

-- Update trigger
CREATE TRIGGER products_fts_update AFTER UPDATE ON products 
BEGIN
    UPDATE products_fts 
    SET sku = new.sku,
        title = new.title,
        description = new.description,
        search_content = new.search_content
    WHERE rowid = old.rowid;
END;

-- Delete trigger
CREATE TRIGGER products_fts_delete AFTER DELETE ON products 
BEGIN
    DELETE FROM products_fts WHERE rowid = old.rowid;
END;
```

### New Indexes

```sql
-- Price index (for filters)
CREATE INDEX ix_products_price ON products(price);

-- Composite indexes
CREATE INDEX idx_vendor_price ON products(vendor, price);
CREATE INDEX idx_title_price ON products(title, price);
```

## Support

If you encounter issues:

1. **Check logs** for error messages
2. **Run test script** to identify which component fails
3. **Verify database** schema with verification commands above
4. **Try rollback** if problems persist
5. **Report issue** with error logs and test results

## FAQ

### Q: Will this break existing functionality?

**A:** No. All changes are backward compatible. Existing code continues to work.

### Q: Do I need to resync products from Shopify?

**A:** No. FTS5 is automatically populated from existing products via triggers.

### Q: What if I don't want FTS5?

**A:** The code will work fine without it. BM25 + Vector search continues to work. FTS5 just adds an optimization layer.

### Q: Can I customize the stop words list?

**A:** Yes, edit `STOP_WORDS` in `bm25_index.py` to add/remove words.

### Q: How do I add more bigram patterns?

**A:** Edit `PRODUCT_KEYWORDS` in `bm25_index.py` to include more terms that should form bigrams.

---

**Last Updated:** 2024
**Version:** 1.0
