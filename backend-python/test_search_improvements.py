"""
Test Search Improvements

Tests the enhanced search functionality with various query patterns to verify:
1. FTS5 full-text search
2. Enhanced BM25 tokenization with bigrams
3. Phrase matching boost in hybrid search
4. Database indexes for performance
"""

import asyncio
import sys
from pathlib import Path

# Add backend-python to path
sys.path.insert(0, str(Path(__file__).parent))

from app.modules.catalog_index import CatalogIndexer
from app.modules.retrieval.product_search import ProductSearcher
from app.modules.catalog_index.indexing.database import DatabaseManager
from app.modules.catalog_index.config import index_config


def print_results(query: str, results: list, max_display: int = 5):
    """Pretty print search results"""
    print(f"\n{'='*80}")
    print(f"Query: '{query}'")
    print(f"Found {len(results)} results (showing top {min(max_display, len(results))})")
    print(f"{'='*80}")
    
    for i, result in enumerate(results[:max_display], 1):
        # Handle both format types (CatalogIndexer vs ProductSearcher)
        if 'content' in result:
            # CatalogIndexer format
            product = result['content']
            score = result.get('score', 0)
            phrase_boost = result.get('phrase_boost', 1.0)
        else:
            # ProductSearcher format
            product = result
            score = result.get('score', 0)
            phrase_boost = 1.0
        
        print(f"\n{i}. {product.get('title', 'Unknown')}")
        print(f"   SKU: {product.get('sku', 'N/A')}")
        print(f"   Price: ${product.get('price', 0):.2f}")
        print(f"   Score: {score:.4f}", end="")
        if phrase_boost > 1.0:
            print(f" (phrase boost: {phrase_boost:.1f}x)", end="")
        print()
        
        # Show description snippet
        desc = product.get('description', '')
        if desc and len(desc) > 100:
            print(f"   Description: {desc[:100]}...")
        elif desc:
            print(f"   Description: {desc}")
        
        # Show tags if available
        tags = product.get('tags', [])
        if tags:
            tags_str = ', '.join(tags[:5])
            if len(tags) > 5:
                tags_str += f' (+{len(tags)-5} more)'
            print(f"   Tags: {tags_str}")


async def test_catalog_indexer():
    """Test CatalogIndexer with enhanced search"""
    print("\n" + "="*80)
    print("Testing CatalogIndexer (BM25 + Vector Hybrid Search)")
    print("="*80)
    
    indexer = CatalogIndexer()
    
    test_queries = [
        "gaming chair",
        "blue office chair",
        "ergonomic desk",
        "wooden dining table",
        "leather sofa",
        "storage cabinet for office",
        "chair",  # Single word
        "modern minimalist furniture",  # Style query
    ]
    
    for query in test_queries:
        results = indexer.searchProducts(query, limit=5)
        print_results(query, results)


async def test_product_searcher():
    """Test ProductSearcher with auto-filtering"""
    print("\n" + "="*80)
    print("Testing ProductSearcher (With Auto-Filters)")
    print("="*80)
    
    searcher = ProductSearcher()
    
    test_queries = [
        "gaming chair under $500",
        "blue office chair",
        "red fabric sofa",
        "metal desk",
    ]
    
    for query in test_queries:
        results = await searcher.search(query, limit=5)
        print_results(query, results)


async def test_fts5_direct():
    """Test FTS5 full-text search directly"""
    print("\n" + "="*80)
    print("Testing FTS5 Full-Text Search (Direct)")
    print("="*80)
    
    db_manager = DatabaseManager()
    
    test_queries = [
        "gaming chair",
        "ergonomic office",
        "modern minimalist",
    ]
    
    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"FTS5 Query: '{query}'")
        print(f"{'='*80}")
        
        results = db_manager.search_fts5(query, limit=5)
        
        if not results:
            print("No results found")
            continue
        
        print(f"Found {len(results)} results\n")
        for i, product in enumerate(results, 1):
            print(f"{i}. {product.get('title', 'Unknown')}")
            print(f"   SKU: {product.get('sku', 'N/A')}")
            print(f"   Relevance: {product.get('relevance', 0)}")


async def test_performance():
    """Test search performance"""
    import time
    
    print("\n" + "="*80)
    print("Testing Search Performance")
    print("="*80)
    
    searcher = ProductSearcher()
    
    test_queries = [
        "chair",
        "gaming chair",
        "blue office chair under $300",
    ]
    
    for query in test_queries:
        start = time.time()
        results = await searcher.search(query, limit=10)
        elapsed = time.time() - start
        
        print(f"\nQuery: '{query}'")
        print(f"Results: {len(results)}")
        print(f"Time: {elapsed*1000:.2f}ms")


async def main():
    """Run all tests"""
    print("\n" + "#"*80)
    print("# SEARCH IMPROVEMENTS TEST SUITE")
    print("#"*80)
    
    try:
        # Test 1: FTS5 Direct
        await test_fts5_direct()
        
        # Test 2: CatalogIndexer (Hybrid Search)
        await test_catalog_indexer()
        
        # Test 3: ProductSearcher (With Filters)
        await test_product_searcher()
        
        # Test 4: Performance
        await test_performance()
        
        print("\n" + "#"*80)
        print("# ALL TESTS COMPLETED")
        print("#"*80)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
