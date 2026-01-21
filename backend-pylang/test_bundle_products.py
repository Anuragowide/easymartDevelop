"""
Test to verify that bundle responses return product cards.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import asyncio
from app.modules.assistant.handler import EasymartAssistantHandler, AssistantRequest


async def test_bundle_products():
    """Test that bundle responses include product cards."""
    handler = EasymartAssistantHandler()
    
    # First message - user asks for cat supplies
    request1 = AssistantRequest(
        message="Setting up for a new cat, budget $200",
        session_id="test-bundle-products"
    )
    
    response1 = await handler.handle_message(request1)
    print("\n" + "="*80)
    print("RESPONSE 1: Initial request")
    print("="*80)
    print(f"Message: {response1.message[:200]}...")
    print(f"Products count: {len(response1.products)}")
    print(f"Is clarification: {handler._is_clarification_response(response1.message)}")
    
    # Second message - user says "you choose"
    request2 = AssistantRequest(
        message="you choose",
        session_id="test-bundle-products"
    )
    
    response2 = await handler.handle_message(request2)
    print("\n" + "="*80)
    print("RESPONSE 2: User says 'you choose'")
    print("="*80)
    print(f"Message: {response2.message[:300]}...")
    print(f"Products count: {len(response2.products)}")
    print(f"Is clarification: {handler._is_clarification_response(response2.message)}")
    
    if response2.products:
        print("\n✅ PASS: Products are returned!")
        print(f"\nFirst 3 products:")
        for i, product in enumerate(response2.products[:3], 1):
            print(f"  {i}. {product.get('name') or product.get('title')} - ${product.get('price')}")
    else:
        print("\n❌ FAIL: No products returned!")
        print("\nDEBUG: Check metadata")
        print(f"Metadata: {response2.metadata}")


if __name__ == "__main__":
    asyncio.run(test_bundle_products())
