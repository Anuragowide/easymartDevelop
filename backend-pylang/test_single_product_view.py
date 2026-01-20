"""
Test that asking about "option 1" only shows that ONE product, not all 5
"""
import asyncio
from dotenv import load_dotenv

load_dotenv()

from app.modules.assistant.handler import EasymartAssistantHandler, AssistantRequest

async def main():
    print("🧪 Testing Single Product View (Option 1)")
    print("=" * 80)
    
    handler = EasymartAssistantHandler()
    session_id = "test-single-product"
    user_id = "test-user"
    
    # Step 1: Search for chairs (should show 5 products)
    print("Step 1: Search for office chairs")
    print("-" * 80)
    
    search_request = AssistantRequest(
        message="show me office chairs",
        session_id=session_id,
        user_id=user_id
    )
    
    search_response = await handler.handle_message(search_request)
    products_shown = len(search_response.products)
    
    print(f"✓ Search returned {products_shown} products")
    if products_shown > 0:
        print("Products shown:")
        for i, p in enumerate(search_response.products[:5], 1):
            print(f"  {i}. {p.get('name', 'Unknown')}")
    print()
    
    # Step 2: Ask about option 1 (should show ONLY 1 product)
    print("Step 2: Ask 'tell me about option 1'")
    print("-" * 80)
    
    detail_request = AssistantRequest(
        message="tell me about option 1",
        session_id=session_id,
        user_id=user_id
    )
    
    detail_response = await handler.handle_message(detail_request)
    products_in_response = len(detail_response.products)
    
    print(f"Response message: {detail_response.message[:150]}...")
    print()
    print(f"Products in response: {products_in_response}")
    
    if products_in_response == 1:
        print("✅ SUCCESS - Only 1 product shown!")
        print(f"   Product: {detail_response.products[0].get('name', 'Unknown')}")
    elif products_in_response == 0:
        print("⚠ WARNING - No products shown (might be intentional)")
    else:
        print(f"❌ FAIL - {products_in_response} products shown (should be 1)")
        print("   Products:")
        for i, p in enumerate(detail_response.products, 1):
            print(f"   {i}. {p.get('name', 'Unknown')}")
    
    print()
    print("=" * 80)
    print("Test complete!")

if __name__ == "__main__":
    asyncio.run(main())
