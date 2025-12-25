
print("Script started")
import asyncio
import csv
import os
import sys
import uuid
import httpx
print("Imports successful")

API_URL = "http://localhost:8000/assistant/message"

async def run_qa_tests(csv_path: str):
    print(f"Starting QA tests from {csv_path}...")
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            print("HTTP client created")
            # Just test one query first
            payload = {"message": "Hi", "session_id": "test"}
            response = await client.post(API_URL, json=payload)
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text[:100]}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    csv_file = "../EasyMart_Chatbot_QA_Professional_v1.csv"
    asyncio.run(run_qa_tests(csv_file))
