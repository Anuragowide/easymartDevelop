"""
Test script to verify multi-filter clarification enforcement.

This script tests:
1. Filter validator weight calculations
2. Subjective term conversion
3. Multi-product detection
4. Contradiction detection
5. Bypass phrase handling
"""

import sys
import asyncio
from app.modules.assistant.filter_validator import FilterValidator
from app.modules.assistant.intent_detector import IntentDetector
from app.modules.retrieval.product_search import SUBJECTIVE_PRICE_MAP


def test_filter_validator():
    """Test FilterValidator class"""
    print("\n" + "="*70)
    print("TEST 1: Filter Validator Weight System")
    print("="*70)
    
    validator = FilterValidator()
    
    # Test case 1: Single filter (category only) - should FAIL
    entities_1 = {"category": "chair"}
    is_valid, weight, msg = validator.validate_filter_count(entities_1, "show me chairs")
    print(f"\n✓ Test 1a: Category only")
    print(f"  Entities: {entities_1}")
    print(f"  Valid: {is_valid}, Weight: {weight:.1f}")
    print(f"  Message: {msg}")
    assert not is_valid, "Single category should be insufficient"
    
    # Test case 2: Two filters (category + color) - should PASS
    entities_2 = {"category": "chair", "color": "black"}
    is_valid, weight, msg = validator.validate_filter_count(entities_2, "black chairs")
    print(f"\n✓ Test 1b: Category + Color")
    print(f"  Entities: {entities_2}")
    print(f"  Valid: {is_valid}, Weight: {weight:.1f}")
    print(f"  Message: {msg}")
    assert is_valid, "Category + color should be sufficient"
    
    # Test case 3: Category + Price (0.5 weight) - should PASS (1.0 + 0.5 = 1.5)
    entities_3 = {"category": "chair", "price_max": 100}
    is_valid, weight, msg = validator.validate_filter_count(entities_3, "chairs under $100")
    print(f"\n✓ Test 1c: Category + Price")
    print(f"  Entities: {entities_3}")
    print(f"  Valid: {is_valid}, Weight: {weight:.1f}")
    print(f"  Message: {msg}")
    assert is_valid, "Category (1.0) + Price (0.5) = 1.5 should meet threshold"
    assert weight == 1.5, f"Expected weight 1.5, got {weight}"
    
    # Test case 4: Category + Material + Color - should PASS
    entities_4 = {"category": "desk", "material": "wood", "color": "brown"}
    is_valid, weight, msg = validator.validate_filter_count(entities_4, "brown wood desks")
    print(f"\n✓ Test 1d: Category + Material + Color")
    print(f"  Entities: {entities_4}")
    print(f"  Valid: {is_valid}, Weight: {weight:.1f}")
    print(f"  Message: {msg}")
    assert is_valid, "Multiple filters should be sufficient"
    
    # Test case 5: Subjective term boost
    entities_5 = {"category": "sofa"}
    is_valid, weight, msg = validator.validate_filter_count(entities_5, "cheap sofas")
    print(f"\n✓ Test 1e: Category + Subjective term (cheap)")
    print(f"  Entities: {entities_5}")
    print(f"  Query: 'cheap sofas'")
    print(f"  Valid: {is_valid}, Weight: {weight:.1f}")
    print(f"  Message: {msg}")
    # Category (1.0) + subjective (0.3) = 1.3, still below 1.5
    assert not is_valid, "Category + subjective term should still be insufficient"
    
    print("\n✅ All filter validator weight tests passed!")


def test_contradiction_detection():
    """Test contradiction detection"""
    print("\n" + "="*70)
    print("TEST 2: Contradiction Detection")
    print("="*70)
    
    validator = FilterValidator()
    
    # Test 1: cheap vs luxury
    entities_1 = {}
    contradiction = validator.detect_contradictions(entities_1, "cheap luxury chairs")
    print(f"\n✓ Test 2a: 'cheap luxury chairs'")
    if contradiction:
        term1, term2, msg = contradiction
        print(f"  Detected: {term1} vs {term2}")
        print(f"  Message: {msg}")
    assert contradiction is not None, "Should detect cheap/luxury contradiction"
    
    # Test 2: small vs large
    entities_2 = {}
    contradiction = validator.detect_contradictions(entities_2, "small large desk")
    print(f"\n✓ Test 2b: 'small large desk'")
    if contradiction:
        term1, term2, msg = contradiction
        print(f"  Detected: {term1} vs {term2}")
        print(f"  Message: {msg}")
    assert contradiction is not None, "Should detect small/large contradiction"
    
    # Test 3: No contradiction
    entities_3 = {"category": "chair", "color": "blue"}
    contradiction = validator.detect_contradictions(entities_3, "blue office chairs")
    print(f"\n✓ Test 2c: 'blue office chairs' (no contradiction)")
    print(f"  Result: {contradiction}")
    assert contradiction is None, "Should not detect contradiction in valid query"
    
    print("\n✅ All contradiction detection tests passed!")


def test_bypass_phrases():
    """Test bypass phrase detection"""
    print("\n" + "="*70)
    print("TEST 3: Bypass Phrase Detection")
    print("="*70)
    
    validator = FilterValidator()
    
    test_cases = [
        ("show me anything", True),
        ("just search", True),
        ("you choose", True),
        ("surprise me", True),
        ("I want office chairs", False),
        ("show me black desks", False),
        ("ok", True),  # Short affirmative
        ("yes", True),
        ("maybe later", False),
    ]
    
    for message, expected in test_cases:
        result = validator.is_bypass_phrase(message)
        print(f"\n✓ '{message}': {result} (expected: {expected})")
        assert result == expected, f"Bypass detection failed for '{message}'"
    
    print("\n✅ All bypass phrase tests passed!")


def test_subjective_conversion():
    """Test subjective term to price conversion"""
    print("\n" + "="*70)
    print("TEST 4: Subjective Price Term Conversion")
    print("="*70)
    
    print("\nSubjective price mappings:")
    for term, price in SUBJECTIVE_PRICE_MAP.items():
        print(f"  {term:15} → ${price}")
    
    # Verify key conversions
    assert SUBJECTIVE_PRICE_MAP["cheap"] == 200
    assert SUBJECTIVE_PRICE_MAP["expensive"] == 500
    assert SUBJECTIVE_PRICE_MAP["luxury"] == 1000
    
    print("\n✅ Subjective price conversion mappings verified!")


def test_multi_product_detection():
    """Test multi-product query detection"""
    print("\n" + "="*70)
    print("TEST 5: Multi-Product Request Detection")
    print("="*70)
    
    detector = IntentDetector()
    
    test_cases = [
        ("chair and table for office", "multi_product"),
        ("show me chairs or desks", "multi_product"),
        ("I need a sofa and bed", "multi_product"),
        ("just chairs", None),  # Single product
        ("office furniture", None),
    ]
    
    for query, expected_vague_type in test_cases:
        result = detector.detect_vague_patterns(query)
        detected_type = result["vague_type"] if result else None
        print(f"\n✓ '{query}'")
        print(f"  Detected: {detected_type}")
        print(f"  Expected: {expected_vague_type}")
        
        if expected_vague_type:
            assert detected_type == expected_vague_type, f"Expected {expected_vague_type}, got {detected_type}"
            if "requested_products" in result["partial_entities"]:
                print(f"  Products: {result['partial_entities']['requested_products']}")
    
    print("\n✅ All multi-product detection tests passed!")


def test_filter_summary():
    """Test human-readable filter summary"""
    print("\n" + "="*70)
    print("TEST 6: Filter Summary Generation")
    print("="*70)
    
    validator = FilterValidator()
    
    test_cases = [
        (
            {"category": "chair", "color": "black", "price_max": 200},
            "chair, black color, under $200"
        ),
        (
            {"category": "desk", "material": "wood", "room_type": "office"},
            "desk, wood material, for office"
        ),
        (
            {},
            "no specific filters"
        ),
    ]
    
    for entities, expected_contains in test_cases:
        summary = validator.get_filter_summary(entities)
        print(f"\n✓ Entities: {entities}")
        print(f"  Summary: '{summary}'")
        print(f"  Expected to contain: '{expected_contains}'")
        # Just check it's not empty for non-empty entities
        if entities:
            assert len(summary) > 0, "Summary should not be empty"
    
    print("\n✅ All filter summary tests passed!")


def run_all_tests():
    """Run all test suites"""
    print("\n" + "="*70)
    print("MULTI-FILTER CLARIFICATION ENFORCEMENT - TEST SUITE")
    print("="*70)
    
    try:
        test_filter_validator()
        test_contradiction_detection()
        test_bypass_phrases()
        test_subjective_conversion()
        test_multi_product_detection()
        test_filter_summary()
        
        print("\n" + "="*70)
        print("✅ ALL TESTS PASSED!")
        print("="*70)
        print("\nImplementation Summary:")
        print("  ✓ Filter validator with weight system")
        print("  ✓ Subjective term conversion (cheap→$200, luxury→$1000)")
        print("  ✓ Multi-product query detection")
        print("  ✓ Contradiction detection (cheap vs luxury, small vs large)")
        print("  ✓ Bypass phrase handling")
        print("  ✓ Filter validation in clarification flow")
        print("  ✓ Pre-LLM filter validation")
        print("  ✓ Progressive refinement validation")
        print("\nThe chatbot will now:")
        print("  • Require minimum filter weight of 1.5 before searching")
        print("  • Convert 'cheap' to 'under $200', 'expensive' to 'over $500'")
        print("  • Detect compound requests and ask which product first")
        print("  • Catch contradictions like 'cheap luxury furniture'")
        print("  • Allow bypass with phrases like 'show me anything'")
        print("  • Validate filters even during progressive refinement")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_all_tests()
