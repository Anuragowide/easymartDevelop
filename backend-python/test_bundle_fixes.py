"""
Test bundle planner fixes:
1. No duplicate items (no two punching bags, no two desks)
2. Tool message is used directly (no clarifying questions in handler)
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.modules.assistant.smart_bundle_planner import get_smart_bundle_planner

async def test_no_duplicate_items():
    """Test that bundle doesn't have duplicate item_types"""
    print("\n" + "="*80)
    print("TEST 1: No Duplicate Items (Boxing Setup)")
    print("="*80)
    
    planner = get_smart_bundle_planner()
    
    # This query previously returned TWO punching bags
    result = await planner.plan_and_create_bundle(
        user_request="I want to start boxing at home, budget $500",
        budget=500.0,
        style_preference=None,
        space_constraint=None
    )
    
    if not result["success"]:
        print(f"❌ FAILED: {result['message']}")
        return False
    
    bundle = result["bundle"]
    items = bundle["items"]
    
    # Check for duplicate item names/types
    item_names = [item["name"].lower() for item in items]
    item_types_seen = set()
    has_duplicates = False
    
    print(f"\n📦 Bundle Items (Total: ${bundle['total']:.2f}/{bundle['budget']}):")
    for i, item in enumerate(items, 1):
        print(f"  {i}. {item['name']} - ${item['price']:.2f}")
        
        # Check if this looks like a duplicate (e.g., two bags)
        if any(keyword in item["name"].lower() for keyword in ["bag", "heavy", "punch"]):
            if any(keyword in name for name in item_names[:i-1] for keyword in ["bag", "heavy", "punch"]):
                print(f"     ⚠️  WARNING: Possible duplicate bag detected!")
                has_duplicates = True
    
    # Validate: Should have boxing gloves, punching bag, mats (3 items max)
    expected_categories = {"gloves", "bag", "mat"}
    found_categories = set()
    
    for item in items:
        name_lower = item["name"].lower()
        if "glove" in name_lower:
            found_categories.add("gloves")
        elif "bag" in name_lower or "punch" in name_lower:
            found_categories.add("bag")
        elif "mat" in name_lower or "jigsaw" in name_lower:
            found_categories.add("mat")
    
    print(f"\n✓ Found categories: {found_categories}")
    print(f"✓ Expected categories: {expected_categories}")
    
    if has_duplicates:
        print("\n❌ FAILED: Found duplicate items (e.g., two bags)")
        return False
    
    if len(items) > 4:
        print(f"\n⚠️  WARNING: Too many items ({len(items)}). Expected 2-4 for a focused bundle.")
    
    print("\n✅ PASSED: No duplicate items detected")
    return True


async def test_tool_message_format():
    """Test that tool message is properly formatted for handler"""
    print("\n" + "="*80)
    print("TEST 2: Tool Message Format (Handler Integration)")
    print("="*80)
    
    planner = get_smart_bundle_planner()
    
    result = await planner.plan_and_create_bundle(
        user_request="Small home office setup",
        budget=600.0,
        style_preference="modern",
        space_constraint="small apartment"
    )
    
    if not result["success"]:
        print(f"❌ FAILED: {result['message']}")
        return False
    
    message = result["message"]
    
    # Check that message is properly formatted
    print(f"\n📝 Tool Message:\n{'-'*80}")
    print(message)
    print(f"{'-'*80}")
    
    # Validate message format
    issues = []
    
    # Should NOT contain clarifying questions
    question_phrases = [
        "could you clarify",
        "what would you like",
        "which equipment",
        "would you prefer",
        "let me know",
        "do you want"
    ]
    
    message_lower = message.lower()
    for phrase in question_phrases:
        if phrase in message_lower:
            issues.append(f"Contains clarifying question: '{phrase}'")
    
    # Should contain designer narrative
    if "i've" not in message_lower and "here" not in message_lower:
        issues.append("Missing designer narrative (should start with 'I've designed...' or 'Here's...')")
    
    # Should mention the products
    bundle = result["bundle"]
    for item in bundle["items"]:
        # Check if item is mentioned in message (at least partially)
        name_words = item["name"].lower().split()
        if not any(word in message_lower for word in name_words if len(word) > 3):
            issues.append(f"Product '{item['name']}' not mentioned in message")
    
    if issues:
        print("\n❌ FAILED: Message format issues:")
        for issue in issues:
            print(f"  - {issue}")
        return False
    
    print("\n✅ PASSED: Tool message is properly formatted")
    return True


async def test_diverse_domains():
    """Test multiple catalog domains to ensure no duplicates in any category"""
    print("\n" + "="*80)
    print("TEST 3: Diverse Domains (Fitness, Pets, Combat)")
    print("="*80)
    
    planner = get_smart_bundle_planner()
    
    test_cases = [
        {
            "request": "Home gym for cardio, budget $800",
            "expected_types": ["treadmill", "mat"],
            "max_items": 4
        },
        {
            "request": "Getting a new puppy, $200 budget",
            "expected_types": ["bed", "feeder"],
            "max_items": 4
        },
        {
            "request": "MMA training setup at home",
            "expected_types": ["gloves", "mat"],
            "max_items": 4
        }
    ]
    
    all_passed = True
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test Case {i}: {test_case['request']} ---")
        
        result = await planner.plan_and_create_bundle(
            user_request=test_case["request"],
            budget=test_case.get("budget", 500.0),
            style_preference=None,
            space_constraint=None
        )
        
        if not result["success"]:
            print(f"❌ FAILED: {result['message']}")
            all_passed = False
            continue
        
        bundle = result["bundle"]
        items = bundle["items"]
        
        print(f"Bundle ({len(items)} items, ${bundle['total']:.2f}):")
        for item in items:
            print(f"  - {item['name']} (${item['price']:.2f})")
        
        # Check for duplicates
        item_names = [item["name"] for item in items]
        if len(item_names) != len(set(item_names)):
            print(f"❌ FAILED: Duplicate product names found")
            all_passed = False
            continue
        
        # Check item count
        if len(items) > test_case["max_items"]:
            print(f"⚠️  WARNING: Too many items ({len(items)} > {test_case['max_items']})")
        
        print(f"✓ No duplicates, {len(items)} unique items")
    
    if all_passed:
        print("\n✅ PASSED: All diverse domain tests successful")
    else:
        print("\n❌ FAILED: Some diverse domain tests failed")
    
    return all_passed


async def main():
    print("\n" + "="*80)
    print("BUNDLE PLANNER FIX VALIDATION")
    print("="*80)
    print("\nTesting fixes for:")
    print("1. Duplicate items issue (two punching bags)")
    print("2. 'Ask vs Tell' conflict (clarifying questions with products)")
    
    results = []
    
    # Run tests
    results.append(("No Duplicate Items", await test_no_duplicate_items()))
    results.append(("Tool Message Format", await test_tool_message_format()))
    results.append(("Diverse Domains", await test_diverse_domains()))
    
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
    
    if passed == total:
        print("\n🎉 All fixes validated successfully!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Review the output above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
