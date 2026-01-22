"""Trace the AssistantTools.search_products call"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

async def main():
    from app.modules.assistant.tools import EasymartAssistantTools
    
    tools = EasymartAssistantTools()
    
    print("="*80)
    print("Testing AssistantTools.search_products('grey sofa')")
    print("="*80)
    
    result = await tools.search_products(
        query="grey sofa",
        color="grey",
        limit=5
    )
    
    print(f"\nResult type: {type(result)}")
    print(f"Result keys: {result.keys() if isinstance(result, dict) else 'N/A'}")
    
    if isinstance(result, dict):
        if result.get("no_color_match"):
            print(f"\n*** NO_COLOR_MATCH RETURNED ***")
            print(f"  requested_color: {result.get('requested_color')}")
            print(f"  available_colors: {result.get('available_colors')}")
        elif result.get("products"):
            print(f"\nProducts found: {len(result['products'])}")
            for p in result['products'][:3]:
                print(f"  - {p.get('name')} - ${p.get('price')}")
        else:
            print(f"\nFull result: {result}")

if __name__ == "__main__":
    asyncio.run(main())
