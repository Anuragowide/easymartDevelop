"""Debug grey sofa search - trace the entire flow"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

async def main():
    from app.modules.retrieval.product_search import ProductSearcher
    
    ps = ProductSearcher()
    
    # Test 1: Basic "grey sofa" search
    print("="*80)
    print("TEST 1: Search 'grey sofa' with color='grey'")
    print("="*80)
    
    result = await ps.search(
        query="grey sofa",
        filters={"color": "grey", "in_stock": True},
        limit=5
    )
    
    if isinstance(result, dict):
        print(f"Result is dict: {result}")
    else:
        print(f"Found {len(result)} results:")
        for i, p in enumerate(result[:5]):
            print(f"  {i+1}. {p.get('name')} - ${p.get('price')} - {p.get('inventory_quantity')} in stock")
            print(f"      Category: {p.get('category')}, Color tag check...")
    
    # Test 2: Just "sofa" without color filter
    print("\n" + "="*80)
    print("TEST 2: Search 'sofa' no color filter")
    print("="*80)
    
    result2 = await ps.search(
        query="sofa",
        filters={"in_stock": True},
        limit=5
    )
    
    if isinstance(result2, dict):
        print(f"Result is dict: {result2}")
    else:
        print(f"Found {len(result2)} results:")
        for i, p in enumerate(result2[:5]):
            print(f"  {i+1}. {p.get('name')} - ${p.get('price')}")
    
    # Test 3: Check what's in the raw results before filtering
    print("\n" + "="*80)
    print("TEST 3: Check raw hybrid search results for 'grey sofa'")
    print("="*80)
    
    # Access the internal method
    raw = await ps._hybrid_search("grey sofa", limit=10)
    print(f"Raw hybrid results: {len(raw)} items")
    for i, r in enumerate(raw[:5]):
        name = r.get('name') or r.get('title', 'Unknown')
        print(f"  {i+1}. {name}")
        # Check for grey in tags/description
        tags = r.get('tags', [])
        if isinstance(tags, str):
            import json
            try:
                tags = json.loads(tags)
            except:
                tags = []
        desc = (r.get('description') or '')[:100]
        grey_found = 'grey' in str(tags).lower() or 'grey' in desc.lower() or 'grey' in name.lower()
        print(f"      Grey found: {grey_found}, Tags: {tags[:3] if tags else 'none'}")

if __name__ == "__main__":
    asyncio.run(main())
