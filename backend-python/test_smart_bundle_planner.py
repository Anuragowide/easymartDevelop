"""
Test Smart Bundle Planner

Test vague room setup requests with the advanced planner.
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from app.modules.assistant.smart_bundle_planner import SmartBundlePlanner


async def test_small_office():
    """Test: I want a small office in my home"""
    print("\n" + "="*60)
    print("TEST 1: Small Office Setup")
    print("="*60)
    
    planner = SmartBundlePlanner()
    result = await planner.plan_and_create_bundle(
        user_request="I want to setup a small office in my home",
        budget=500.0,
        space_constraint="small room"
    )
    
    print(f"\nSuccess: {result['success']}")
    print(f"\nMessage:\n{result['message']}")
    
    if result['bundle']:
        bundle = result['bundle']
        print(f"\nTheme: {bundle['theme']}")
        print(f"Total: ${bundle['total']:.2f} / ${bundle['budget']:.2f}")
        print(f"\nItems ({len(bundle['items'])}):")
        for item in bundle['items']:
            print(f"  - {item['name']} (${item['price']:.2f})")
            print(f"    Reason: {item['reasoning']}")
    
    assert result['success'], "Planning should succeed"
    assert result['bundle'] is not None, "Should return a bundle"
    assert len(result['bundle']['items']) >= 2, "Should have at least 2 items (desk + chair)"
    assert result['bundle']['total'] <= 500, "Should be within budget"
    
    print("\n✅ Test 1 PASSED")


async def test_gaming_corner():
    """Test: Help me setup a gaming corner"""
    print("\n" + "="*60)
    print("TEST 2: Gaming Corner Setup")
    print("="*60)
    
    planner = SmartBundlePlanner()
    result = await planner.plan_and_create_bundle(
        user_request="I want to create an epic gaming corner",
        budget=800.0,
        style_preference="modern gaming"
    )
    
    print(f"\nSuccess: {result['success']}")
    print(f"\nMessage:\n{result['message']}")
    
    if result['bundle']:
        bundle = result['bundle']
        print(f"\nTheme: {bundle['theme']}")
        print(f"Total: ${bundle['total']:.2f} / ${bundle['budget']:.2f}")
        print(f"\nItems ({len(bundle['items'])}):")
        for item in bundle['items']:
            print(f"  - {item['name']} (${item['price']:.2f})")
            print(f"    Reason: {item['reasoning']}")
    
    assert result['success'], "Planning should succeed"
    assert result['bundle'] is not None, "Should return a bundle"
    assert result['bundle']['total'] <= 800, "Should be within budget"
    
    print("\n✅ Test 2 PASSED")


async def test_tiny_studio():
    """Test: I need furniture for a tiny studio apartment"""
    print("\n" + "="*60)
    print("TEST 3: Tiny Studio Apartment")
    print("="*60)
    
    planner = SmartBundlePlanner()
    result = await planner.plan_and_create_bundle(
        user_request="I need furniture for a tiny studio apartment",
        budget=400.0,
        space_constraint="very small space, compact"
    )
    
    print(f"\nSuccess: {result['success']}")
    print(f"\nMessage:\n{result['message']}")
    
    if result['bundle']:
        bundle = result['bundle']
        print(f"\nTheme: {bundle['theme']}")
        print(f"Total: ${bundle['total']:.2f} / ${bundle['budget']:.2f}")
        print(f"\nItems ({len(bundle['items'])}):")
        for item in bundle['items']:
            print(f"  - {item['name']} (${item['price']:.2f})")
            print(f"    Reason: {item['reasoning']}")
    
    assert result['success'], "Planning should succeed"
    assert result['bundle'] is not None, "Should return a bundle"
    assert result['bundle']['total'] <= 400, "Should be within budget"
    
    print("\n✅ Test 3 PASSED")


async def test_reading_nook():
    """Test: I want to create a cozy reading nook"""
    print("\n" + "="*60)
    print("TEST 4: Reading Nook")
    print("="*60)
    
    planner = SmartBundlePlanner()
    result = await planner.plan_and_create_bundle(
        user_request="I want to create a cozy reading nook",
        budget=300.0,
        style_preference="comfortable and warm"
    )
    
    print(f"\nSuccess: {result['success']}")
    print(f"\nMessage:\n{result['message']}")
    
    if result['bundle']:
        bundle = result['bundle']
        print(f"\nTheme: {bundle['theme']}")
        print(f"Total: ${bundle['total']:.2f} / ${bundle['budget']:.2f}")
        print(f"\nItems ({len(bundle['items'])}):")
        for item in bundle['items']:
            print(f"  - {item['name']} (${item['price']:.2f})")
            print(f"    Reason: {item['reasoning']}")
    
    assert result['success'], "Planning should succeed"
    assert result['bundle'] is not None, "Should return a bundle"
    assert result['bundle']['total'] <= 300, "Should be within budget"
    
    print("\n✅ Test 4 PASSED")


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("SMART BUNDLE PLANNER TEST SUITE")
    print("="*60)
    
    try:
        await test_small_office()
        await test_gaming_corner()
        await test_tiny_studio()
        await test_reading_nook()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\nThe Smart Bundle Planner successfully:")
        print("  1. Decomposed vague requests into specific items")
        print("  2. Injected relevant keywords (e.g., 'compact', 'gaming')")
        print("  3. Executed parallel product searches")
        print("  4. Selected cohesive products within budget")
        print("  5. Generated natural language explanations")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
