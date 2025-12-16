"""
Quick single test
"""
import requests
import json

try:
    response = requests.post(
        "http://localhost:8000/assistant/message",
        json={
            "session_id": "test-quick-001",
            "message": "hello"
        }
    )

    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Response: {json.dumps(response.json(), indent=2)}")
    else:
        print(f"Error Response: {response.text}")
        
except Exception as e:
    print(f"Exception: {e}")
    import traceback
    traceback.print_exc()

