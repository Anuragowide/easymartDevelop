import asyncio
import sys
import os
import uuid
from typing import Optional

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.modules.assistant.handler import get_assistant_handler, AssistantRequest
from app.core.config import settings

# ANSI colors for terminal
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

async def main():
    print(f"{BOLD}{BLUE}=== Easymart Assistant CLI ==={RESET}")
    print("Type 'quit' or 'exit' to stop.")
    print("-" * 30)
    
    # Initialize handler
    print(f"{YELLOW}Initializing assistant...{RESET}")
    try:
        handler = get_assistant_handler()
        # Pre-load LLM client
        from app.modules.assistant.hf_llm_client import create_llm_client
        handler.llm_client = await create_llm_client()
        print(f"{GREEN}Assistant ready!{RESET}")
    except Exception as e:
        print(f"{RED}Failed to initialize assistant: {e}{RESET}")
        return

    # Create session
    session_id = f"cli-{uuid.uuid4().hex[:8]}"
    print(f"Session ID: {session_id}")
    print("-" * 30)

    while True:
        try:
            user_input = input(f"{BOLD}You: {RESET}").strip()
            
            if user_input.lower() in ["quit", "exit"]:
                print("Goodbye!")
                break
            
            if not user_input:
                continue
                
            # Send request
            request = AssistantRequest(
                message=user_input,
                session_id=session_id
            )
            
            print(f"{YELLOW}Thinking...{RESET}", end="\r")
            
            response = await handler.handle_message(request)
            
            # Clear "Thinking..."
            print(" " * 20, end="\r")
            
            # Print assistant message
            print(f"{GREEN}Assistant: {RESET}{response.message}")
            
            # Display products ONLY for product search intent (not for Q&A, cart ops, etc.)
            intent = response.metadata.get("intent", "")
            if intent == "product_search" and response.products and len(response.products) > 0:
                print(f"\n{BOLD}{BLUE}Products Found:{RESET}")
                for i, product in enumerate(response.products, 1):
                    print(f"{i}. {BOLD}{product.get('name', 'Unknown Product')}{RESET} - ${product.get('price', 0)}")
                    # Only show description if it's real (not placeholder)
                    desc = product.get('description', '')
                    if desc and desc.upper() not in ['PRODUCT DESCRIPTION', 'DESCRIPTION', 'N/A']:
                        desc = desc[:100] + "..." if len(desc) > 100 else desc
                        print(f"   {desc}")
                print()
            
            # Print metadata (optional, for demo)
            if response.metadata.get("intent"):
                print(f"{BLUE}[Intent: {response.metadata['intent']}]{RESET}")
                
            print("-" * 30)
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\n{RED}Error: {e}{RESET}")

if __name__ == "__main__":
    asyncio.run(main())
