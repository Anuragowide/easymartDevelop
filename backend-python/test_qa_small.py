
import asyncio
import csv
import os
import sys
import uuid
from typing import List, Dict, Any
import httpx
import time

API_URL = "http://localhost:8000/assistant/message"

async def run_qa_tests(csv_path: str, limit: int = 5):
    print(f"Starting QA tests from {csv_path} (Limit: {limit})...")
    print(f"Target API: {API_URL}")
    
    results = []
    
    # Increase timeout significantly
    async with httpx.AsyncClient(timeout=120.0) as client:
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            for row in reader:
                if count >= limit:
                    break
                
                query = row.get('User Query')
                expected = row.get('Expected Response')
                query_type = row.get('Query Type')
                s_no = row.get('S. No')
                
                if not query:
                    continue
                    
                print(f"[{s_no}] Testing [{query_type}]: {query}")
                
                session_id = f"test_session_{uuid.uuid4().hex[:8]}"
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
                    duration = time.time() - start_time
                    
                    results.append({
                        'S. No': s_no,
                        'Query Type': query_type,
                        'User Query': query,
                        'Bot Response': bot_message,
                        'Expected Response': expected,
                        'Intent': intent,
                        'Duration': f"{duration:.2f}s",
                        'Status': 'Success'
                    })
                    
                    print(f"   Bot ({duration:.2f}s): {bot_message[:80]}...")
                except Exception as e:
                    print(f"   Error: {e}")
                    results.append({
                        'S. No': s_no,
                        'Query Type': query_type,
                        'User Query': query,
                        'Bot Response': f"ERROR: {str(e)}",
                        'Expected Response': expected,
                        'Status': 'Failed'
                    })
                
                count += 1

    # Write results to a new CSV
    output_path = "QA_Results_Small.csv"
    if results:
        keys = results[0].keys()
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(results)
        print(f"\nTests completed. Results saved to {output_path}")

if __name__ == "__main__":
    csv_file = "../EasyMart_Chatbot_QA_Professional_v1.csv"
    if not os.path.exists(csv_file):
        csv_file = "EasyMart_Chatbot_QA_Professional_v1.csv"
        
    if os.path.exists(csv_file):
        asyncio.run(run_qa_tests(csv_file, limit=5))
    else:
        print(f"CSV file not found at {csv_file}")
