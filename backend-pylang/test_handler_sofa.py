"""Test the actual chat handler with 'grey sofa' query"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

# Clear the singleton before importing to ensure fresh state
import importlib

async def main():
    from app.modules.assistant.handler import EasymartAssistantHandler, AssistantRequest
    from app.modules.assistant import tools
    
    # Reset the singleton
    tools._assistant_tools = None
    
    handler = EasymartAssistantHandler()
    
    # Simulate a new session with unique ID
    import time
    session_id = f"test-sofa-debug-{int(time.time())}"
    
    request = AssistantRequest(
        session_id=session_id,
        user_id="debug-user",
        message="show me grey sofas"
    )
    
    print("="*80)
    print("REQUEST: 'show me grey sofas'")
    print("="*80)
    
    response = await handler.handle_message(request)
    
    print(f"\nRESPONSE MESSAGE:\n{response.message}")
    print(f"\n{'='*80}")
    print(f"PRODUCTS RETURNED: {len(response.products)}")
    for i, p in enumerate(response.products):
        print(f"  {i+1}. {p.get('name')} - ${p.get('price')}")
    print(f"\nMETADATA: {response.metadata}")
    print("="*80)

if __name__ == "__main__":
    asyncio.run(main())
