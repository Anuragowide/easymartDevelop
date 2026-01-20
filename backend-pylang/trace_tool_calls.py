"""
Trace the exact tool calls and responses
"""
import asyncio
import json
from dotenv import load_dotenv

load_dotenv()

from app.modules.assistant.handler import EasymartAssistantHandler, AssistantRequest

async def main():
    handler = EasymartAssistantHandler()
    
    # Patch the _run_tool_loop to log tool calls
    original_run_tool_loop = handler._run_tool_loop
    
    async def logged_run_tool_loop(message, history):
        print("\n🔧 TOOL LOOP STARTED")
        print(f"Message: {message}")
        
        # Also patch tool invocations to see parameters
        from app.modules.assistant.tools import get_assistant_tools
        tools = get_assistant_tools()
        original_search = tools.search_products
        
        async def logged_search(**kwargs):
            print(f"\n  🔍 search_products called with: {json.dumps(kwargs, indent=2)}")
            result = await original_search(**kwargs)
            print(f"  📦 search_products returned: {len(result.get('products', []))} products")
            if 'message' in result:
                print(f"  💬 Tool message: {result['message']}")
            return result
        
        tools.search_products = logged_search
        
        response_text, tool_steps = await original_run_tool_loop(message, history)
        
        # Restore
        tools.search_products = original_search
        
        print(f"\n📊 TOOL STEPS ({len(tool_steps)} calls):")
        for i, (name, observation) in enumerate(tool_steps, 1):
            print(f"\n  Step {i}: {name}")
            if isinstance(observation, dict):
                if "products" in observation:
                    print(f"    Products: {len(observation['products'])}")
                if "message" in observation:
                    print(f"    Message: {observation['message']}")
                if "error" in observation:
                    print(f"    Error: {observation['error']}")
            else:
                print(f"    Result: {str(observation)[:100]}")
        print(f"\n💬 FINAL RESPONSE: {response_text[:200]}...")
        return response_text, tool_steps
    
    handler._run_tool_loop = logged_run_tool_loop
    
    # Run the test
    request = AssistantRequest(
        message="show me queen size bed frame",
        session_id="trace-test",
        user_id="test-user"
    )
    
    response = await handler.handle_message(request)
    print(f"\n✅ Response products: {len(response.products)}")

if __name__ == "__main__":
    asyncio.run(main())
