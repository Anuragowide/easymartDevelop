
import asyncio
import csv
import os
import uuid
from typing import List, Dict, Any
import httpx
import time

API_URL = "http://localhost:8000/assistant/message"

REPRESENTATIVE_QUERIES = [
    {"type": "Greeting", "query": "Hello"},
    {"type": "Product Search", "query": "Show me office chairs"},
    {"type": "Product Specs", "query": "tell me about the first one"},
    {"type": "Availability", "query": "is it in stock?"},
    {"type": "Cart", "query": "add it to my cart"},
    {"type": "Cart View", "query": "show my cart"},
    {"type": "Policy", "query": "what is your return policy?"},
    {"type": "Contact", "query": "how can I call you?"},
    {"type": "Shipping", "query": "how much is shipping to 2000?"},
    {"type": "Off-topic", "query": "can you write a java function for me?"},
    {"type": "Reset", "query": "reset chat"}
]

async def run_tests():
    print(f"Starting Representative QA Tests...")
    print(f"Target API: {API_URL}")
    
    session_id = f"test_rep_{uuid.uuid4().hex[:8]}"
    print(f"Using Session ID: {session_id}")
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        for item in REPRESENTATIVE_QUERIES:
            query_type = item["type"]
            query = item["query"]
            
            print(f"\nTesting [{query_type}]: {query}")
            
            payload = {
                "message": query,
                "session_id": session_id
            }
            
            start_time = time.time()
            try:
                response = await client.post(API_URL, json=payload)
                response.raise_for_status()
                data = response.json()
                
                bot_message = data.get('message', '')
                intent = data.get('intent', '')
                products_count = len(data.get('products', [])) if data.get('products') else 0
                duration = time.time() - start_time
                
                print(f"   Intent: {intent}")
                print(f"   Products Found: {products_count}")
                print(f"   Bot ({duration:.2f}s): {bot_message[:150]}...")
                
                if query_type == "Off-topic" and "EasyMart" not in bot_message and "furniture" not in bot_message:
                    print("   ⚠️ WARNING: Bot might have answered off-topic query!")
                
            except Exception as e:
                print(f"   Error: {e}")

if __name__ == "__main__":
    asyncio.run(run_tests())
