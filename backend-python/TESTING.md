# Catalog Sync Testing

Quick reference for testing catalog synchronization.

## Quick Test Commands

### 1. Check CSV Data
```bash
cd d:\easymart-v1\backend-python
python check_csv.py
```

### 2. Test Shopify API Connection
```bash
# Test Node.js catalog endpoint
curl http://localhost:3001/api/internal/catalog/export | ConvertFrom-Json | Select -First 3

# Or stats endpoint
curl http://localhost:3001/api/internal/catalog/stats
```

### 3. Run Full Sync Test
```bash
cd d:\easymart-v1\backend-python
python test_catalog_sync.py
```

### 4. Load Catalog (Production)
```bash
cd d:\easymart-v1\backend-python
python -m app.modules.catalog_index.load_catalog
```

## Expected Flow

1. **Node Backend** fetches from Shopify API
2. **Normalizes** products to standard format
3. **Python Backend** consumes via `/api/internal/catalog/export`
4. **Indexes** into BM25 + ChromaDB
5. **Ready** for search queries

## Troubleshooting

**No products from Shopify?**
- Check SHOPIFY_ACCESS_TOKEN is valid
- Verify SHOPIFY_STORE_DOMAIN is correct
- Ensure backend-node is running on port 3001

**Indexing fails?**
- Check ChromaDB path exists: `data/chromadb/`
- Check BM25 path exists: `data/bm25/`
- Verify sentence-transformers model downloaded

**Search returns nothing?**
- Run `test_catalog_sync.py` to verify data loaded
- Check logs for indexing errors
- Try rebuilding indexes: delete `data/bm25/` and `data/chromadb/`, then reload
