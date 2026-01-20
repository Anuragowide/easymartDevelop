"""
Test that searching for items shows correct stock messaging
"""
import asyncio
from dotenv import load_dotenv

load_dotenv()

from app.modules.assistant.handler import EasymartAssistantHandler, AssistantRequest

async def main():
    print("🧪 Testing Stock Availability Messaging")
    print("=" * 80)
    
    handler = EasymartAssistantHandler()
    session_id = "test-stock-messaging"
    user_id = "test-user"
    
    # Test case: Queen size bed frame
    print("Test: Search for 'queen size bed frame'")
    print("-" * 80)
    
    search_request = AssistantRequest(
        message="show me queen size bed frame",
        session_id=session_id,
        user_id=user_id
    )
    
    response = await handler.handle_message(search_request)
    
    print(f"Response message: {response.message}")
    print()
    print(f"Products returned: {len(response.products)}")
    
    if response.products:
        print("\nProducts:")
        in_stock_count = 0
        out_of_stock_count = 0
        
        for i, product in enumerate(response.products, 1):
            name = product.get('name', 'Unknown')
            qty = product.get('inventory_quantity', 'N/A')
            in_stock = product.get('inventory_quantity', 0) > 0
            
            if in_stock:
                in_stock_count += 1
                stock_status = "✓ IN STOCK"
            else:
                out_of_stock_count += 1
                stock_status = "✗ OUT OF STOCK"
            
            print(f"  {i}. {name}")
            print(f"     Inventory: {qty} - {stock_status}")
        
        print()
        print(f"Summary: {in_stock_count} in stock, {out_of_stock_count} out of stock")
        print()
        
        # Check if message is contradictory
        message_lower = response.message.lower()
        says_no_items = any(phrase in message_lower for phrase in [
            "don't have", "no items", "out of stock", "not available",
            "currently unavailable", "none available"
        ])
        
        if says_no_items and len(response.products) > 0:
            if in_stock_count > 0:
                print("❌ FAIL - Message says 'no items' but showing IN-STOCK products!")
                print("   This is contradictory and confusing to users")
            else:
                print("⚠ MIXED - Message says 'no items' and all shown items are out of stock")
                print("   Message should clarify: 'No in-stock items, but here are some out-of-stock options'")
        elif not says_no_items and len(response.products) > 0:
            if in_stock_count > 0:
                print("✅ SUCCESS - Message doesn't say 'no items' and products are shown")
            else:
                print("✅ IMPROVED - Showing out-of-stock items without false 'in stock' claims")
        else:
            print("⚠ No products shown")
    else:
        print("No products returned")
    
    print()
    print("=" * 80)
    print("Test complete!")

if __name__ == "__main__":
    asyncio.run(main())
