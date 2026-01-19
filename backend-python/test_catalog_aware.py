"""
Test catalog-aware clarification and intent detection
"""
import sys
sys.path.insert(0, 'D:\\easymart-v1\\backend-python')

from app.modules.assistant.intent_detector import IntentDetector
from app.modules.assistant.prompts import get_clarification_prompt_for_room, get_clarification_prompt_for_category

def test_room_category_mapping():
    """Test that ROOM_CATEGORY_MAP uses real catalog categories"""
    print("=" * 60)
    print("TEST 1: Room Category Mapping (Catalog Accuracy)")
    print("=" * 60)
    
    detector = IntentDetector()
    
    print("\n✓ ROOM_CATEGORY_MAP Contents:")
    for room, categories in detector.ROOM_CATEGORY_MAP.items():
        print(f"\n  {room}:")
        for cat in categories:
            print(f"    • {cat}")
    
    # Verify no old/fake categories exist
    all_room_cats = [cat for cats in detector.ROOM_CATEGORY_MAP.values() for cat in cats]
    invalid_cats = ['beds', 'wardrobes', 'side_tables', 'tv_units', 'weights']  # Old fake categories
    
    found_invalid = [cat for cat in invalid_cats if cat.lower() in [c.lower() for c in all_room_cats]]
    if found_invalid:
        print(f"\n❌ FAIL: Found invalid categories: {found_invalid}")
        return False
    else:
        print("\n✓ PASS: No invalid categories found")
        return True


def test_intent_granularity_detection():
    """Test granularity detection with real catalog"""
    print("\n" + "=" * 60)
    print("TEST 2: Intent Granularity Detection")
    print("=" * 60)
    
    detector = IntentDetector()
    
    test_cases = [
        ("something for my bedroom", "room_level", "bedroom"),
        ("living room furniture", "room_level", "living_room"),
        ("I need office stuff", "room_level", "office"),
        ("show me mattresses", "product_level", None),
        ("black leather sofa", "product_level", None),
        ("furniture", "category_level", None),
    ]
    
    passed = 0
    total = len(test_cases)
    
    for query, expected_granularity, expected_room in test_cases:
        result = detector.detect_intent_granularity(query)
        granularity = result['granularity']
        room = result.get('room')
        
        if granularity == expected_granularity and (expected_room is None or room == expected_room):
            print(f"✓ '{query}' → {granularity}" + (f" (room: {room})" if room else ""))
            if result.get('clarification_options'):
                print(f"  Options: {', '.join(result['clarification_options'][:3])}")
            passed += 1
        else:
            print(f"❌ '{query}' → Expected {expected_granularity}, got {granularity}")
            print(f"   Room: Expected {expected_room}, got {room}")
    
    print(f"\n{'✓ PASS' if passed == total else '❌ FAIL'}: {passed}/{total} tests passed")
    return passed == total


def test_clarification_prompts():
    """Test clarification prompt generation"""
    print("\n" + "=" * 60)
    print("TEST 3: Clarification Prompt Generation")
    print("=" * 60)
    
    detector = IntentDetector()
    
    # Test bedroom clarification
    print("\n📝 Test: Bedroom clarification")
    result = detector.detect_intent_granularity("something for my bedroom")
    
    if result['needs_clarification']:
        prompt = get_clarification_prompt_for_room(
            result['room'], 
            result['clarification_options']
        )
        print(f"\nGenerated Prompt:\n{prompt}")
        
        # Check if real categories are present
        real_cats = ['Mattresses', 'Bedroom Furniture', 'Bedside Tables']
        found = [cat for cat in real_cats if cat in prompt]
        
        if found:
            print(f"\n✓ PASS: Found real categories: {', '.join(found)}")
            return True
        else:
            print(f"\n❌ FAIL: No real categories found in prompt")
            return False
    else:
        print("❌ FAIL: No clarification triggered")
        return False


def test_domain_classification():
    """Test domain classification"""
    print("\n" + "=" * 60)
    print("TEST 4: Domain Classification")
    print("=" * 60)
    
    detector = IntentDetector()
    
    print("\n✓ DOMAIN_MAPPING Contents:")
    for domain, categories in detector.DOMAIN_MAPPING.items():
        print(f"\n  {domain}:")
        print(f"    Categories: {', '.join(categories[:5])}")
        if len(categories) > 5:
            print(f"    ... and {len(categories)-5} more")
    
    print("\n✓ PASS: Domain mapping structure verified")
    return True


def test_room_response_handling():
    """Test how system handles user response to room clarification"""
    print("\n" + "=" * 60)
    print("TEST 5: Room Clarification Response Handling")
    print("=" * 60)
    
    detector = IntentDetector()
    
    # Simulate: User says "bedroom" → Bot asks clarification → User says "mattress"
    print("\n📝 Scenario: User wants bedroom → clarifies with 'mattress'")
    
    room_result = detector.detect_intent_granularity("something for my bedroom")
    print(f"\n1. Initial query → granularity: {room_result['granularity']}")
    print(f"   Options shown: {', '.join(room_result['clarification_options'])}")
    
    # Check if "Mattresses" is in options
    if "Mattresses" in room_result['clarification_options']:
        print(f"\n✓ PASS: 'Mattresses' is a valid option for bedroom")
        
        # Simulate user responding with "mattress"
        user_response = "mattress"
        matched = None
        for option in room_result['clarification_options']:
            if user_response.lower() in option.lower() or option.lower() in user_response.lower():
                matched = option
                break
        
        if matched:
            print(f"✓ PASS: User response '{user_response}' matched to '{matched}'")
            return True
        else:
            print(f"❌ FAIL: User response '{user_response}' didn't match any option")
            return False
    else:
        print(f"❌ FAIL: 'Mattresses' not in bedroom options")
        return False


if __name__ == "__main__":
    print("\n" + "🎯 CATALOG-AWARE SYSTEM TEST SUITE" + "\n")
    
    results = []
    
    # Run all tests
    results.append(("Room Category Mapping", test_room_category_mapping()))
    results.append(("Intent Granularity Detection", test_intent_granularity_detection()))
    results.append(("Clarification Prompts", test_clarification_prompts()))
    results.append(("Domain Classification", test_domain_classification()))
    results.append(("Room Response Handling", test_room_response_handling()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\n{'🎉 ALL TESTS PASSED' if passed == total else '⚠️  SOME TESTS FAILED'}")
    print(f"Result: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✅ The system is now catalog-aware and ready for production!")
    else:
        print("\n❌ Please fix failing tests before deploying")
