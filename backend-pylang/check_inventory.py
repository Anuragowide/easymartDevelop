"""Check inventory data from database vs Shopify"""
import asyncio
from app.modules.retrieval.product_search import ProductSearcher

async def check():
    searcher = ProductSearcher()
    
    # Search for the specific desk
    results = await searcher.search(query='Artiss 2 Drawer Wood Computer Desk', filters={}, limit=5)
    print('=== Artiss 2 Drawer Wood Computer Desk ===')
    for p in results:
        print(f"Name: {p.get('name')}")
        print(f"Price: {p.get('price')}")
        print(f"inventory_quantity: {p.get('inventory_quantity')}")
        print(f"in_stock: {p.get('in_stock')}")
        print(f"available: {p.get('available')}")
        print(f"SKU: {p.get('sku')}")
        print(f"All keys: {list(p.keys())}")
        print()

if __name__ == "__main__":
    asyncio.run(check())
