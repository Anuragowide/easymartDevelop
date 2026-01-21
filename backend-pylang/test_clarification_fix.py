"""
Test the clarification fix: 
1. When LLM asks a clarification question, no products should be shown
2. Products should be deduplicated (no 200pcs/400pcs of same item)
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.modules.assistant.handler import EasymartAssistantHandler


def test_clarification_detection():
    """Test that clarification responses are correctly detected"""
    print("\n" + "="*80)
    print("TEST 1: Clarification Detection")
    print("="*80)
    
    handler = EasymartAssistantHandler()
    
    # Test cases: (response_text, expected_is_clarification)
    test_cases = [
        # Should be detected as clarification (True)
        (
            "To help you get the best puppy starter kit within your $250 budget, could you specify which essential items you want to include? Common starter supplies are things like:\n\n- Bed\n- Food bowl\n- Water bowl\n- Collar & leash\n- Toys\n\nLet me know which items you need?",
            True,
            "Puppy kit clarification with bullet list"
        ),
        (
            "What type of furniture are you looking for?",
            True,
            "Simple clarification question"
        ),
        (
            "Which items would you like? Do you need a bed, bowls, or toys?",
            True,
            "Multiple choice clarification"
        ),
        (
            "Could you tell me more about your budget and preferred style?",
            True,
            "Budget/style clarification"
        ),
        # Should NOT be detected as clarification (False)
        (
            "Here are some great options for puppy supplies!",
            False,
            "Product presentation (no question)"
        ),
        (
            "I found 5 products matching your search.",
            False,
            "Search results message"
        ),
        (
            "The dog bed is $45 and comes in blue, red, and black.",
            False,
            "Product information"
        ),
    ]
    
    passed = 0
    failed = 0
    
    for response_text, expected, description in test_cases:
        result = handler._is_clarification_response(response_text)
        status = "✅ PASS" if result == expected else "❌ FAIL"
        if result == expected:
            passed += 1
        else:
            failed += 1
        print(f"\n{status} - {description}")
        print(f"  Response: {response_text[:60]}...")
        print(f"  Expected: {expected}, Got: {result}")
    
    print(f"\n{passed}/{len(test_cases)} tests passed")
    return failed == 0


def test_product_deduplication():
    """Test that similar products are deduplicated"""
    print("\n" + "="*80)
    print("TEST 2: Product Deduplication")
    print("="*80)
    
    handler = EasymartAssistantHandler()
    
    # Test products with duplicates (same product type, different sizes/variants)
    test_products = [
        {'name': '200pcs Puppy Dog Pet Training Pads Cat Toilet...', 'price': 51.00, 'sku': 'SKU-001'},
        {'name': '400pcs Puppy Dog Pet Training Pads Cat Toilet...', 'price': 98.00, 'sku': 'SKU-002'},
        {'name': 'YES4PETS 1 x Medium Pet No Spill Feeder Bowl Dog...', 'price': 12.00, 'sku': 'SKU-003'},
        {'name': 'Dog Bed Large Orthopedic', 'price': 45.00, 'sku': 'SKU-004'},
        {'name': 'Dog Bed Small Washable', 'price': 25.00, 'sku': 'SKU-005'},
        {'name': 'Pet Leash Black Retractable', 'price': 15.00, 'sku': 'SKU-006'},
    ]
    
    print(f"\nOriginal products: {len(test_products)}")
    for p in test_products:
        print(f"  - {p['name']}")
    
    unique = handler._deduplicate_products(test_products)
    
    print(f"\nAfter deduplication: {len(unique)}")
    for p in unique:
        print(f"  - {p['name']}")
    
    # The duplicate variants should be removed
    unique_names = [p['name'] for p in unique]
    
    passed = True
    
    # Check: 400pcs should be removed (duplicate of 200pcs)
    if '400pcs Puppy Dog Pet Training Pads Cat Toilet...' in unique_names:
        print("\n❌ FAIL: 400pcs duplicate should have been removed")
        passed = False
    else:
        print("\n✅ PASS: 400pcs duplicate was correctly removed")
    
    # Check: 200pcs should be kept (first occurrence)
    if '200pcs Puppy Dog Pet Training Pads Cat Toilet...' not in unique_names:
        print("❌ FAIL: 200pcs (first occurrence) should have been kept")
        passed = False
    else:
        print("✅ PASS: 200pcs (first occurrence) was correctly kept")
    
    # Check: Dog Bed Small should be removed (duplicate of Dog Bed Large - same product type)
    if 'Dog Bed Small Washable' in unique_names:
        print("❌ FAIL: Dog Bed Small should have been removed (duplicate product type)")
        passed = False
    else:
        print("✅ PASS: Dog Bed Small was correctly removed (same product type as Dog Bed Large)")
    
    # Check: Different products should be kept
    expected_count = 4  # 200pcs pads, bowl, 1 dog bed, leash
    if len(unique) != expected_count:
        print(f"❌ FAIL: Expected {expected_count} unique products, got {len(unique)}")
        passed = False
    else:
        print(f"✅ PASS: Correct number of unique products ({expected_count})")
    
    return passed


def main():
    print("\n" + "="*80)
    print("CLARIFICATION FIX VALIDATION")
    print("="*80)
    print("\nTesting fixes for:")
    print("1. 'Ask vs Tell' conflict (clarifying questions with products)")
    print("2. Duplicate products issue (200pcs vs 400pcs of same item)")
    
    results = []
    
    # Run tests
    results.append(("Clarification Detection", test_clarification_detection()))
    results.append(("Product Deduplication", test_product_deduplication()))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n{passed}/{total} tests passed")
    
    return 0 if passed == total else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
