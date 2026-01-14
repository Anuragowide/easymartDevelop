"""
Startup script for Python backend
Checks if catalog is indexed and provides guidance
"""

import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.modules.catalog_index.catalog import CatalogIndexer

def check_catalog_status():
    """Check if catalog has products indexed"""
    print("\n" + "="*80)
    print("EASYMART BACKEND - CATALOG STATUS CHECK")
    print("="*80 + "\n")
    
    try:
        indexer = CatalogIndexer()
        product_count = indexer.get_product_count()
        
        if product_count > 0:
            print(f"✅ Catalog is ready with {product_count} products indexed")
            print(f"✅ Backend is ready to handle search queries\n")
            return True
        else:
            print("⚠️  WARNING: No products found in catalog index!")
            print("\n📝 To index products from Shopify:")
            print("   1. Ensure Node.js backend is running on port 3002")
            print("   2. Run: python -m app.modules.assistant.cli index-catalog")
            print("\n💡 Or use CSV fallback for testing:")
            print("   - Products will load from data/products.csv\n")
            return False
            
    except Exception as e:
        print(f"❌ Error checking catalog: {str(e)}")
        print("\n💡 To fix:")
        print("   1. Run: python -m app.modules.assistant.cli index-catalog")
        print("   2. Or check logs for specific errors\n")
        return False

if __name__ == "__main__":
    check_catalog_status()
    print("="*80)
    print("Starting backend server...")
    print("="*80 + "\n")
