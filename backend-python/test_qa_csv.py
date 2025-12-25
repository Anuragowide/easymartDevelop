
import asyncio
import csv
import os
import sys
import uuid
from typing import List, Dict, Any
import httpx

API_URL = "http://localhost:8000/assistant/message"

async def run_qa_tests(csv_path: str):
    print(f"Starting QA tests from {csv_path}...")
    print(f"Target API: {API_URL}")
    
    results = []
    
    # Use a persistent session for better performance
    async with httpx.AsyncClient(timeout=60.0) as client:
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
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
                
                try:
                    response = await client.post(API_URL, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    
                    bot_message = data.get('message', '')
                    intent = data.get('intent', '')
                    
                    results.append({
                        'S. No': s_no,
                        'Query Type': query_type,
                        'User Query': query,
                        'Bot Response': bot_message,
                        'Expected Response': expected,
                        'Intent': intent,
                        'Status': 'Success',
                        'Passed': 'TBD' 
                    })
                    
                    print(f"   Bot: {bot_message[:80]}...")
                except Exception as e:
                    print(f"   Error: {e}")
                    results.append({
                        'S. No': s_no,
                        'Query Type': query_type,
                        'User Query': query,
                        'Bot Response': f"ERROR: {str(e)}",
                        'Expected Response': expected,
                        'Intent': 'ERROR',
                        'Status': 'Failed',
                        'Passed': 'No'
                    })

    # Write results to a new CSV
    output_path = "QA_Results_Output.csv"
    if results:
        keys = results[0].keys()
        with open(output_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(results)
        print(f"\nTests completed. Results saved to {output_path}")
        print(f"Total tests run: {len(results)}")

if __name__ == "__main__":
    # Path handling for Windows
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_file = os.path.join(base_dir, "EasyMart_Chatbot_QA_Professional_v1.csv")
    
    if not os.path.exists(csv_file):
        csv_file = "EasyMart_Chatbot_QA_Professional_v1.csv"
        
    if os.path.exists(csv_file):
        asyncio.run(run_qa_tests(csv_file))
    else:
        print(f"CSV file not found at {csv_file}")
