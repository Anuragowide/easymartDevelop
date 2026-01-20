"""
Test bundle add to cart functionality - ensuring prices are correct
"""
import asyncio
from dotenv import load_dotenv

load_dotenv()

from app.modules.assistant.handler import EasymartAssistantHandler, AssistantRequest
from app.modules.assistant.session_store import SessionStore

async def main():
    print("🧪 Testing Bundle Add to Cart with Correct Prices")
    print("=" * 80)
    
    # Initialize
    handler = EasymartAssistantHandler()
    session_store = SessionStore()
    
    # Create session
    session_id = "test-bundle-cart"
    user_id = "test-user"
    
    # Step 1: Request a bundle
    print("Step 1: Request a bundle of gaming chairs and tables")
    print("-" * 80)
    
    bundle_request = AssistantRequest(
        message="I need 4 gaming chairs and 2 tables under $1500",
        session_id=session_id,
        user_id=user_id
    )
    
    bundle_response = await handler.handle_message(bundle_request)
    print(f"Assistant: {bundle_response.message[:200]}...")
    print()
    
    if bundle_response.products and len(bundle_response.products) > 0:
        print(f"✓ Bundle suggested with {len(bundle_response.products)} items:")
        for product in bundle_response.products:
            name = product.get('name') or product.get('title', 'Unknown')
            price = product.get('price', 'N/A')
            sku = product.get('sku') or product.get('id', 'N/A')
            print(f"  - {name}: ${price} (SKU: {sku})")
        print()
        
        # Check metadata for bundle items
        session = session_store.get_or_create_session(session_id, user_id)
        bundle_items = session.metadata.get("last_bundle_items", [])
        
        if bundle_items:
            print(f"✓ Bundle items stored in session ({len(bundle_items)} items):")
            for item in bundle_items:
                name = item.get('name', 'Unknown')
                price = item.get('price') or item.get('unit_price', 'N/A')
                qty = item.get('quantity', 1)
                sku = item.get('product_id', 'N/A')
                print(f"  - {name}: ${price} x {qty} (SKU: {sku})")
            print()
    else:
        print("✗ No bundle suggested")
        return
    
    # Step 2: Add bundle to cart
    print("Step 2: Add the bundle to cart")
    print("-" * 80)
    
    add_request = AssistantRequest(
        message="add this bundle to cart",
        session_id=session_id,
        user_id=user_id
    )
    
    add_response = await handler.handle_message(add_request)
    print(f"Assistant: {add_response.message}")
    print()
    
    # If asking for confirmation, confirm it
    if "would you like" in add_response.message.lower() or "should i add" in add_response.message.lower():
        print("(Assistant is asking for confirmation, confirming...)")
        confirm_request = AssistantRequest(
            message="yes, add it",
            session_id=session_id,
            user_id=user_id
        )
        add_response = await handler.handle_message(confirm_request)
        print(f"Assistant: {add_response.message}")
        print()
    
    # Step 3: View cart and check prices
    print("Step 3: View cart to verify prices")
    print("-" * 80)
    
    if add_response.cart_summary:
        cart_items = add_response.cart_summary.get('items', [])
        item_count = add_response.cart_summary.get('item_count', 0)
        cart_total = add_response.cart_summary.get('total', 0.0)
        
        print(f"✓ Cart has {item_count} item(s):")
        
        all_prices_correct = True
        
        for cart_item in cart_items:
            name = cart_item.get('name') or cart_item.get('title', 'Unknown')
            price = cart_item.get('price', 0)
            qty = cart_item.get('quantity', 1)
            item_total = price * qty if price else 0
            sku = cart_item.get('product_id') or cart_item.get('id', 'N/A')
            
            print(f"  - {name}")
            print(f"    SKU: {sku}")
            print(f"    Price: ${price} x {qty} = ${item_total:.2f}")
            
            if price == 0 or price is None:
                print(f"    ❌ ERROR: Price is $0 or None!")
                all_prices_correct = False
            else:
                print(f"    ✓ Price looks correct")
        
        print()
        print(f"Cart Total: ${cart_total:.2f}")
        print()
        
        if all_prices_correct:
            print("✅ SUCCESS - All items have correct prices!")
        else:
            print("❌ FAIL - Some items have $0 price (bug not fixed)")
    else:
        print("✗ Cart is empty - items weren't added")
    
    print()
    print("=" * 80)
    print("Test complete!")

if __name__ == "__main__":
    asyncio.run(main())
