"""
Debug script to understand what search_products returns
"""
import asyncio
from dotenv import load_dotenv

load_dotenv()

from app.modules.assistant.tools import EasymartAssistantTools

async def main():
    tools = EasymartAssistantTools()
    
    print("Testing search_products with in_stock=True")
    print("=" * 80)
    
    result = await tools.search_products(
        query="queen size bed frame",
        limit=5
    )
    
    print(f"Result keys: {result.keys()}")
    print(f"Products returned: {len(result.get('products', []))}")
    print(f"Message: {result.get('message', 'N/A')}")
    print(f"Showing out of stock: {result.get('showing_out_of_stock', False)}")
    print()
    
    products = result.get('products', [])
    if products:
        print("Products:")
        for i, p in enumerate(products, 1):
            name = p.get('name', 'Unknown')
            qty = p.get('inventory_quantity', 'N/A')
            in_stock = p.get('inventory_quantity', 0) > 0
            print(f"{i}. {name}")
            print(f"   Inventory: {qty} - {'IN STOCK' if in_stock else 'OUT OF STOCK'}")

if __name__ == "__main__":
    asyncio.run(main())
