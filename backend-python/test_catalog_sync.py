"""
Test script to verify catalog synchronization from Shopify
"""
import asyncio
import requests
import os
from dotenv import load_dotenv

load_dotenv()

NODE_API_URL = os.getenv("NODE_BACKEND_URL", "http://localhost:3001")

def test_node_catalog_endpoint():
    """Test if Node.js catalog export endpoint is working"""
    print("\n" + "="*60)
    print("🔍 TESTING SHOPIFY CATALOG SYNC")
    print("="*60 + "\n")
    
    url = f"{NODE_API_URL}/api/internal/catalog/export"
    print(f"📡 Fetching from: {url}\n")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        products = response.json()
        
        print(f"✅ SUCCESS: Fetched {len(products)} products from Shopify\n")
        
        if products:
            # Show first 5 products
            sample = products[:5]
            
            print("📦 SAMPLE PRODUCTS (First 5):")
            print("-" * 100)
            print(f"{'SKU':<20} {'Title':<40} {'Price':<10} {'Category':<20} {'Stock':<10}")
            print("-" * 100)
            
            for p in sample:
                sku = (p.get('sku', 'N/A') or 'N/A')[:20]
                title = (p.get('title', 'N/A') or 'N/A')[:40]
                price = f"${p.get('price', 0):.2f}"
                category = (p.get('category', 'N/A') or 'N/A')[:20]
                stock = p.get('stock_status', 'N/A')
                
                print(f"{sku:<20} {title:<40} {price:<10} {category:<20} {stock:<10}")
            
            print("-" * 100)
            
            # Validation checks
            print("\n🔍 DATA VALIDATION:")
            checks = {
                "All have SKUs": all(p.get('sku') for p in products),
                "All have titles": all(p.get('title') for p in products),
                "All have prices": all(p.get('price') is not None for p in products),
                "All have URLs": all(p.get('product_url') for p in products),
                "All have handles": all(p.get('handle') for p in products),
            }
            
            for check, passed in checks.items():
                status = "✅" if passed else "❌"
                print(f"  {status} {check}")
            
            # Category breakdown
            categories = {}
            for p in products:
                cat = p.get('category', 'Uncategorized')
                categories[cat] = categories.get(cat, 0) + 1
            
            print(f"\n📊 CATEGORY BREAKDOWN:")
            for cat, count in sorted(categories.items(), key=lambda x: -x[1])[:10]:
                print(f"  • {cat}: {count} products")
            
            # Vendor breakdown
            vendors = {}
            for p in products:
                vendor = p.get('vendor', 'Unknown')
                vendors[vendor] = vendors.get(vendor, 0) + 1
            
            print(f"\n🏪 VENDOR BREAKDOWN:")
            for vendor, count in sorted(vendors.items(), key=lambda x: -x[1])[:5]:
                print(f"  • {vendor}: {count} products")
            
            return True, products
            
        else:
            print("⚠️  WARNING: No products returned from Shopify")
            return False, []
            
    except requests.exceptions.ConnectionError:
        print(f"❌ ERROR: Cannot connect to Node backend at {NODE_API_URL}")
        print("   Make sure backend-node is running on port 3001")
        return False, []
    except requests.exceptions.HTTPError as e:
        print(f"❌ ERROR: HTTP {e.response.status_code}")
        print(f"   Response: {e.response.text[:200]}")
        return False, []
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return False, []

def test_catalog_loading():
    """Test the full catalog loading process"""
    print("\n" + "="*60)
    print("📚 TESTING CATALOG INDEXING")
    print("="*60 + "\n")
    
    success, products = test_node_catalog_endpoint()
    
    if not success or not products:
        print("\n⚠️  Skipping indexing test - no products available")
        return
    
    print(f"\n🔨 Indexing {len(products)} products...")
    
    try:
        from app.modules.catalog_index.catalog import CatalogIndexer
        
        indexer = CatalogIndexer()
        indexer.addProducts(products)
        
        print("✅ Indexing complete!")
        
        # Test search
        print("\n🔍 Testing search functionality...")
        test_queries = ["chair", "table", "sofa", "desk"]
        
        for query in test_queries:
            results = indexer.search(query, limit=3)
            
            if results:
                print(f"\n  Search: '{query}' - Found {len(results)} results:")
                for r in results[:3]:
                    print(f"    • {r.get('title', 'N/A')} - ${r.get('price', 0):.2f}")
            else:
                print(f"\n  Search: '{query}' - No results")
                
    except Exception as e:
        print(f"❌ Indexing failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("\n🚀 EASYMART CATALOG SYNC VERIFICATION\n")
    
    # Test catalog loading and indexing
    test_catalog_loading()
    
    print("\n" + "="*60)
    print("✅ ALL TESTS COMPLETE")
    print("="*60 + "\n")
    
    print("💡 NEXT STEPS:")
    print("  1. If successful, run: python -m app.modules.catalog_index.load_catalog")
    print("  2. Start the assistant server: python start_server.py")
    print("  3. Test queries via: curl -X POST http://localhost:8000/assistant/message")
    print()
