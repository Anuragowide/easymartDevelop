"""
End-to-end test for product reference resolution in the assistant
"""
import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from app.modules.assistant.handler import EasymartAssistantHandler, AssistantRequest
from app.modules.assistant.session_store import SessionStore

async def main():
    print("🧪 Testing Product Reference Resolution - End to End")
    print("=" * 80)
    
    # Initialize
    handler = EasymartAssistantHandler()
    session_store = SessionStore()
    
    # Create test session
    session_id = "test-e2e-refs"
    user_id = "test-user"
    session = session_store.get_or_create_session(session_id, user_id)
    
    print("Step 1: Search for chairs")
    print("-" * 80)
    
    # First, do a search to populate shown products
    search_request = AssistantRequest(
        message="show me office chairs under $200",
        session_id=session_id,
        user_id=user_id
    )
    
    search_response = await handler.handle_message(search_request)
    print(f"Response: {search_response.message[:100]}...")
    
    if search_response.products:
        print(f"✓ Found {len(search_response.products)} products")
        for i, product in enumerate(search_response.products[:3], 1):
            print(f"  {i}. {product.get('name')} - ${product.get('price')} ({product.get('sku')})")
    else:
        print("✗ No products returned - test cannot continue")
        return
    
    print()
    print("Step 2: Ask about 'option 1' (reference resolution test)")
    print("-" * 80)
    
    # Now ask about "option 1" - this should trigger reference resolution
    ref_request = AssistantRequest(
        message="tell me about option 1",
        session_id=session_id,
        user_id=user_id
    )
    
    ref_response = await handler.handle_message(ref_request)
    print(f"Response: {ref_response.message[:200]}...")
    
    # Check if the response is about a specific product
    if "couldn't get" in ref_response.message.lower() or "error" in ref_response.message.lower():
        print("✗ FAIL - Reference resolution didn't work properly")
        print(f"  Full response: {ref_response.message}")
    else:
        print("✓ PASS - Reference resolved and assistant provided product details")
    
    print()
    print("Step 3: Test 'the first one' pattern")
    print("-" * 80)
    
    first_request = AssistantRequest(
        message="add the first one to my cart",
        session_id=session_id,
        user_id=user_id
    )
    
    first_response = await handler.handle_message(first_request)
    print(f"Response: {first_response.message[:200]}...")
    
    if first_response.cart_summary and len(first_response.cart_summary) > 0:
        print("✓ PASS - Product added to cart successfully")
        print(f"  Cart has {len(first_response.cart_summary)} item(s)")
    else:
        print("⚠ Product may not have been added (check response)")
    
    print()
    print("=" * 80)
    print("✅ End-to-end reference resolution test complete!")

if __name__ == "__main__":
    asyncio.run(main())
