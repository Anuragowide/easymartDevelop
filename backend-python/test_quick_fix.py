"""
Quick test to verify the clarification fix works
"""
import requests
import json
import time

API_BASE = "http://localhost:8000"

def test_clarification_fix():
    """Test the bedroom clarification flow that was broken"""
    session_id = f"test_fix_{int(time.time())}"
    
    print("\n" + "="*60)
    print("Testing Bedroom Clarification Fix")
    print("="*60)
    
    # Test 1: Send vague query
    print("\n📤 User: 'something for my bedroom'")
    try:
        response1 = requests.post(
            f"{API_BASE}/api/assistant/message",
            json={"session_id": session_id, "message": "something for my bedroom"},
            timeout=15
        )
        response1.raise_for_status()
        data1 = response1.json()
        
        print(f"\n🤖 Bot: {data1['message']}")
        print(f"📊 Intent: {data1['metadata'].get('intent')}")
        
        if data1['metadata'].get('intent') != 'clarification_needed':
            print("❌ FAIL: Expected clarification")
            return False
        
        print("✓ PASS: Clarification triggered correctly")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False
    
    # Test 2: Send clarification response
    print("\n📤 User: 'mattress'")
    try:
        response2 = requests.post(
            f"{API_BASE}/api/assistant/message",
            json={"session_id": session_id, "message": "mattress"},
            timeout=15
        )
        response2.raise_for_status()
        data2 = response2.json()
        
        print(f"\n🤖 Bot: {data2['message'][:100]}...")
        print(f"📊 Products returned: {len(data2.get('products', []))}")
        
        if len(data2.get('products', [])) == 0:
            print("❌ FAIL: No products returned")
            return False
        
        print("✓ PASS: Products returned successfully")
        print(f"✅ FIX VERIFIED: No 'active_filters' error!")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

if __name__ == "__main__":
    print("\n🔧 VERIFYING CLARIFICATION FIX")
    
    # Wait for server
    print("\n⏳ Waiting for server to be ready...")
    for i in range(10):
        try:
            health = requests.get(f"{API_BASE}/health", timeout=2)
            if health.status_code == 200:
                print("✓ Server is ready")
                break
        except:
            time.sleep(1)
    else:
        print("❌ Server not responding")
        exit(1)
    
    # Run test
    result = test_clarification_fix()
    
    if result:
        print("\n" + "="*60)
        print("🎉 SUCCESS: Fix verified - no more AttributeError!")
        print("="*60)
    else:
        print("\n" + "="*60)
        print("❌ FAIL: Issue still exists")
        print("="*60)
