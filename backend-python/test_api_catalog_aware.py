"""
End-to-end test of catalog-aware chatbot behavior
Tests actual API with clarification-first logic
"""
import requests
import json
import time

# API Configuration
API_BASE = "http://localhost:8000"
ASSISTANT_ENDPOINT = f"{API_BASE}/api/assistant/message"

def create_session():
    """Generate a unique session ID"""
    return f"test_catalog_aware_{int(time.time())}"

def send_message(session_id, message):
    """Send message to assistant API"""
    payload = {
        "session_id": session_id,
        "message": message
    }
    
    try:
        response = requests.post(ASSISTANT_ENDPOINT, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"❌ API Error: {e}")
        return None

def test_bedroom_clarification_flow():
    """Test: User says 'bedroom' → Bot asks clarification → User says 'mattress'"""
    print("\n" + "=" * 70)
    print("TEST 1: Bedroom Clarification Flow")
    print("=" * 70)
    
    session_id = create_session()
    
    # Step 1: Vague query
    print("\n📤 User: 'I want something for my bedroom'")
    response1 = send_message(session_id, "I want something for my bedroom")
    
    if not response1:
        print("❌ FAIL: No response from API")
        return False
    
    bot_message1 = response1.get('message', '')
    products1 = response1.get('products', [])
    metadata1 = response1.get('metadata', {})
    
    print(f"\n🤖 Bot: {bot_message1}")
    print(f"\n📊 Products returned: {len(products1)}")
    print(f"📊 Intent: {metadata1.get('intent', 'unknown')}")
    
    # Validate clarification triggered
    if metadata1.get('intent') != 'clarification_needed':
        print(f"❌ FAIL: Expected 'clarification_needed', got '{metadata1.get('intent')}'")
        return False
    
    if len(products1) > 0:
        print(f"❌ FAIL: Bot should NOT return products during clarification")
        return False
    
    # Check if real categories are mentioned
    real_categories = ['Mattresses', 'Bedroom Furniture', 'Bedside Tables']
    mentioned = [cat for cat in real_categories if cat in bot_message1]
    
    if not mentioned:
        print(f"❌ FAIL: Bot didn't mention real categories. Message: {bot_message1[:200]}")
        return False
    
    print(f"✓ PASS: Bot asked for clarification with real categories: {', '.join(mentioned)}")
    
    # Step 2: User responds with specific product
    print("\n📤 User: 'mattress'")
    response2 = send_message(session_id, "mattress")
    
    if not response2:
        print("❌ FAIL: No response from API")
        return False
    
    bot_message2 = response2.get('message', '')
    products2 = response2.get('products', [])
    
    print(f"\n🤖 Bot: {bot_message2[:150]}...")
    print(f"\n📊 Products returned: {len(products2)}")
    
    if len(products2) == 0:
        print(f"❌ FAIL: Bot should return mattresses after clarification")
        return False
    
    # Check if products are actually mattresses
    mattress_products = [p for p in products2 if 'mattress' in p.get('name', '').lower()]
    
    if len(mattress_products) == 0:
        print(f"❌ FAIL: Products don't seem to be mattresses")
        print(f"   Product names: {[p.get('name') for p in products2[:3]]}")
        return False
    
    print(f"✓ PASS: Bot returned {len(mattress_products)} mattress products")
    return True


def test_living_room_clarification():
    """Test: Living room query triggers clarification"""
    print("\n" + "=" * 70)
    print("TEST 2: Living Room Clarification")
    print("=" * 70)
    
    session_id = create_session()
    
    print("\n📤 User: 'show me living room furniture'")
    response = send_message(session_id, "show me living room furniture")
    
    if not response:
        print("❌ FAIL: No response from API")
        return False
    
    bot_message = response.get('message', '')
    metadata = response.get('metadata', {})
    
    print(f"\n🤖 Bot: {bot_message}")
    print(f"\n📊 Intent: {metadata.get('intent', 'unknown')}")
    
    if metadata.get('intent') != 'clarification_needed':
        print(f"❌ FAIL: Expected clarification, got {metadata.get('intent')}")
        return False
    
    # Check for living room categories
    living_room_cats = ['Sofas', 'Coffee Tables', 'TV Units', 'Living Room Furniture']
    mentioned = [cat for cat in living_room_cats if cat in bot_message]
    
    if not mentioned:
        print(f"❌ FAIL: No living room categories mentioned")
        return False
    
    print(f"✓ PASS: Bot asked for clarification with: {', '.join(mentioned)}")
    return True


def test_specific_product_no_clarification():
    """Test: Specific product query should NOT trigger clarification"""
    print("\n" + "=" * 70)
    print("TEST 3: Specific Product (No Clarification)")
    print("=" * 70)
    
    session_id = create_session()
    
    print("\n📤 User: 'show me office chairs'")
    response = send_message(session_id, "show me office chairs")
    
    if not response:
        print("❌ FAIL: No response from API")
        return False
    
    bot_message = response.get('message', '')
    products = response.get('products', [])
    metadata = response.get('metadata', {})
    
    print(f"\n🤖 Bot: {bot_message[:150]}...")
    print(f"\n📊 Products returned: {len(products)}")
    print(f"📊 Intent: {metadata.get('intent', 'unknown')}")
    
    if metadata.get('intent') == 'clarification_needed':
        print(f"❌ FAIL: Bot should NOT ask clarification for specific product")
        return False
    
    if len(products) == 0:
        print(f"❌ FAIL: Bot should return office chairs")
        return False
    
    print(f"✓ PASS: Bot directly showed {len(products)} products without clarification")
    return True


def test_gym_equipment_domain():
    """Test: Gym equipment clarification uses correct categories"""
    print("\n" + "=" * 70)
    print("TEST 4: Gym Equipment Domain")
    print("=" * 70)
    
    session_id = create_session()
    
    print("\n📤 User: 'I need gym equipment'")
    response = send_message(session_id, "I need gym equipment")
    
    if not response:
        print("❌ FAIL: No response from API")
        return False
    
    bot_message = response.get('message', '')
    metadata = response.get('metadata', {})
    
    print(f"\n🤖 Bot: {bot_message}")
    print(f"\n📊 Intent: {metadata.get('intent', 'unknown')}")
    
    # Check for gym categories
    gym_cats = ['Treadmills', 'Exercise Bikes', 'Dumbbells', 'Kettlebell', 'Gym Bench']
    mentioned = [cat for cat in gym_cats if cat in bot_message]
    
    if not mentioned:
        print(f"❌ FAIL: No gym equipment categories mentioned")
        return False
    
    print(f"✓ PASS: Bot mentioned gym categories: {', '.join(mentioned)}")
    return True


def test_category_boundary_enforcement():
    """Test: Bedroom query should NOT show office furniture"""
    print("\n" + "=" * 70)
    print("TEST 5: Category Boundary Enforcement")
    print("=" * 70)
    
    session_id = create_session()
    
    # First message: bedroom clarification
    print("\n📤 User: 'something for bedroom'")
    response1 = send_message(session_id, "something for bedroom")
    
    if not response1:
        print("❌ FAIL: No response from API")
        return False
    
    # Second message: user specifies mattress
    print("\n📤 User: 'mattress'")
    response2 = send_message(session_id, "mattress")
    
    if not response2:
        print("❌ FAIL: No response from API")
        return False
    
    products = response2.get('products', [])
    
    # Check for invalid categories in results
    invalid_keywords = ['desk', 'office', 'filing', 'locker', 'drawer unit']
    invalid_products = []
    
    for product in products:
        name = product.get('name', '').lower()
        category = product.get('category', '').lower()
        
        if any(keyword in name or keyword in category for keyword in invalid_keywords):
            invalid_products.append(product.get('name'))
    
    if invalid_products:
        print(f"❌ FAIL: Found invalid products for bedroom: {invalid_products[:3]}")
        return False
    
    print(f"✓ PASS: All {len(products)} products are valid for bedroom context")
    return True


if __name__ == "__main__":
    print("\n" + "🎯 END-TO-END CATALOG-AWARE API TEST" + "\n")
    print("⚠️  Make sure the API server is running on http://localhost:8000")
    
    # Check if API is running
    try:
        health_check = requests.get(f"{API_BASE}/health", timeout=5)
        if health_check.status_code == 200:
            print("✓ API server is running")
        else:
            print(f"❌ API returned status {health_check.status_code}")
            exit(1)
    except requests.exceptions.RequestException:
        print("❌ ERROR: Cannot connect to API server")
        print("   Please start the server with: python backend-python/startup.py")
        exit(1)
    
    # Run tests
    results = []
    
    results.append(("Bedroom Clarification Flow", test_bedroom_clarification_flow()))
    time.sleep(1)  # Rate limiting
    
    results.append(("Living Room Clarification", test_living_room_clarification()))
    time.sleep(1)
    
    results.append(("Specific Product (No Clarification)", test_specific_product_no_clarification()))
    time.sleep(1)
    
    results.append(("Gym Equipment Domain", test_gym_equipment_domain()))
    time.sleep(1)
    
    results.append(("Category Boundary Enforcement", test_category_boundary_enforcement()))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\n{'🎉 ALL TESTS PASSED' if passed == total else '⚠️  SOME TESTS FAILED'}")
    print(f"Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ The catalog-aware system is working correctly!")
    else:
        print("\n❌ Please review failures and fix issues")
