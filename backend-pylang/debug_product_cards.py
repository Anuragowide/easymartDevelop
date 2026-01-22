"""
Debug script to trace why product cards are sometimes not shown
"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.modules.assistant.handler import EasymartAssistantHandler, AssistantRequest

async def debug_product_cards():
    handler = EasymartAssistantHandler()
    
    # Test the exact query from the screenshot
    test_query = "ya i need a desk and a gaming chair"
    
    print("=" * 70)
    print(f"Testing query: \"{test_query}\"")
    print("=" * 70)
    
    request = AssistantRequest(
        message=test_query,
        session_id="debug-session-1"
    )
    
    response = await handler.handle_message(request)
    
    print(f"\n--- RESPONSE MESSAGE ---")
    print(response.message)
    
    print(f"\n--- PRODUCTS RETURNED ---")
    print(f"Product count: {len(response.products)}")
    
    if response.products:
        for i, product in enumerate(response.products[:5], 1):
            name = product.get("name") or product.get("title")
            sku = product.get("sku") or product.get("id")
            price = product.get("price")
            print(f"  {i}. {name} (SKU: {sku}) - ${price}")
    else:
        print("  NO PRODUCTS RETURNED!")
    
    print(f"\n--- METADATA ---")
    print(f"Intent: {response.metadata.get('intent')}")
    print(f"Function calls made: {response.metadata.get('function_calls_made', 0)}")
    
    # Now let's trace deeper
    print("\n" + "=" * 70)
    print("DEEP TRACE - Running with verbose logging")
    print("=" * 70)
    
    # Check what the LLM does with this
    from app.modules.assistant.session_store import get_session_store
    from app.modules.assistant.intent_detector import IntentDetector
    from app.modules.assistant.bundle_planner import parse_bundle_request
    
    session_store = get_session_store()
    session = session_store.get_or_create_session("debug-session-2")
    
    # Check intent detection
    intent_detector = IntentDetector()
    intent = intent_detector.detect(test_query).value
    print(f"\n1. Intent detected: {intent}")
    
    # Check if bundle parsing happens
    bundle_items, budget = parse_bundle_request(test_query)
    print(f"\n2. Bundle parsing:")
    print(f"   Items found: {bundle_items}")
    print(f"   Budget: {budget}")
    
    if len(bundle_items) >= 2:
        print(f"   -> Will trigger bundle handling (2+ items)")
    
    # Check vague patterns
    vague = intent_detector.detect_vague_patterns(test_query)
    print(f"\n3. Vague pattern detected: {vague}")
    
    # Run again with clean session
    print("\n" + "=" * 70)
    print("SECOND RUN - Clean session")
    print("=" * 70)
    
    request2 = AssistantRequest(
        message=test_query,
        session_id="debug-session-3"
    )
    
    response2 = await handler.handle_message(request2)
    
    print(f"\nProducts returned: {len(response2.products)}")
    print(f"Message: {response2.message[:200]}...")
    
    # Check if the issue is inconsistent
    print("\n" + "=" * 70)
    print("CONSISTENCY CHECK - 5 runs")
    print("=" * 70)
    
    for i in range(5):
        request_n = AssistantRequest(
            message=test_query,
            session_id=f"debug-run-{i}"
        )
        response_n = await handler.handle_message(request_n)
        products_count = len(response_n.products)
        has_text = "desk" in response_n.message.lower() or "chair" in response_n.message.lower()
        print(f"Run {i+1}: {products_count} products, has_text={has_text}")


if __name__ == "__main__":
    asyncio.run(debug_product_cards())
