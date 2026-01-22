"""Test multiple search queries to verify fix is robust"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

async def main():
    from app.modules.assistant.handler import EasymartAssistantHandler, AssistantRequest
    
    handler = EasymartAssistantHandler()
    
    test_queries = [
        "show me grey sofas",
        "I need a black office chair",
        "looking for a wooden desk",
        "show me pet beds for dogs",
        "find me a bed frame",
    ]
    
    for query in test_queries:
        request = AssistantRequest(
            session_id=f"test-{hash(query)}",
            user_id="debug-user",
            message=query
        )
        
        print("="*80)
        print(f"QUERY: '{query}'")
        print("="*80)
        
        response = await handler.handle_message(request)
        
        print(f"PRODUCTS: {len(response.products)}")
        if response.products:
            for p in response.products[:3]:
                print(f"  - {p.get('name')[:50]}... - ${p.get('price')}")
        else:
            print(f"  Response: {response.message[:100]}...")
        print()

if __name__ == "__main__":
    asyncio.run(main())
