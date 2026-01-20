"""
Simulating the exact scenario from the user's screenshot:
1. Show office chairs
2. User says "tell me about option 1"
3. Should return product details, not error
"""
import asyncio
from dotenv import load_dotenv

load_dotenv()

from app.modules.assistant.handler import EasymartAssistantHandler, AssistantRequest
from app.modules.assistant.session_store import SessionStore

async def main():
    print("🎯 Simulating Exact User Scenario")
    print("=" * 80)
    print("Reproducing the issue: 'tell me about option 1' after product search")
    print()
    
    # Initialize
    handler = EasymartAssistantHandler()
    session_store = SessionStore()
    
    # Create session
    session_id = "screenshot-test"
    user_id = "screenshot-user"
    
    # Step 1: User searches for chairs (like in screenshot)
    print("Step 1: User searches for office chairs")
    print("-" * 80)
    
    search_request = AssistantRequest(
        message="show me office chairs",
        session_id=session_id,
        user_id=user_id
    )
    
    search_response = await handler.handle_message(search_request)
    print(f"Assistant: {search_response.message[:150]}...")
    print()
    
    if search_response.products and len(search_response.products) >= 2:
        print(f"✓ Assistant showed {len(search_response.products)} products:")
        for i, product in enumerate(search_response.products[:2], 1):
            name = product.get('name') or product.get('title', 'Unknown')
            price = product.get('price', 'N/A')
            sku = product.get('sku') or product.get('id', 'N/A')
            print(f"  Option {i}: {name}")
            print(f"            Price: ${price}, SKU: {sku}")
        print()
    else:
        print("✗ Not enough products shown")
        return
    
    # Step 2: User says "tell me about option 1" (THE CRITICAL TEST)
    print("Step 2: User says 'tell me about option 1'")
    print("-" * 80)
    
    ref_request = AssistantRequest(
        message="tell me about option 1",
        session_id=session_id,
        user_id=user_id
    )
    
    ref_response = await handler.handle_message(ref_request)
    
    # Check for the error message from screenshot
    error_phrases = [
        "couldn't get those product details",
        "couldn't get the product details", 
        "couldn't find that product",
        "error",
        "try asking about a different product"
    ]
    
    has_error = any(phrase in ref_response.message.lower() for phrase in error_phrases)
    
    print(f"Assistant: {ref_response.message}")
    print()
    
    if has_error:
        print("❌ FAIL - Got error message (same as screenshot)")
        print("   This means the fix didn't work properly")
    else:
        print("✅ SUCCESS - Product details returned!")
        print("   The 'option 1' reference was resolved correctly")
    
    print()
    print("=" * 80)
    
    # Additional verification
    if search_response.products:
        first_product = search_response.products[0]
        first_sku = first_product.get('sku') or first_product.get('id')
        
        if first_sku and first_sku in ref_response.message:
            print(f"✓ Response mentions SKU '{first_sku}' - verification passed")
        elif first_product.get('name') and first_product.get('name') in ref_response.message:
            print(f"✓ Response mentions product name - verification passed")
        else:
            print("⚠ Could not verify product details in response")
    
    print()
    print("Test complete!")

if __name__ == "__main__":
    asyncio.run(main())
