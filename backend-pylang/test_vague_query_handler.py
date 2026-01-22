"""
Test script for the Vague Query Handler

Run with: python -m pytest test_vague_query_handler.py -v
Or directly: python test_vague_query_handler.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.modules.assistant.vague_query_handler import (
    VagueQueryHandler, 
    VagueCategory,
    analyze_vague_query
)


def test_symptom_queries():
    """Test Category 1: Symptom & Problem Solving"""
    handler = VagueQueryHandler()
    
    test_cases = [
        {
            "query": "My lower back is killing me after work.",
            "expected_category": VagueCategory.SYMPTOM_PROBLEM,
            "expected_tool": "search_products",
            "should_contain": ["ergonomic", "lumbar", "chair"]
        },
        {
            "query": "My apartment is so cluttered.",
            "expected_category": VagueCategory.SYMPTOM_PROBLEM,
            "expected_tool": "search_products",
            "should_contain": ["storage", "cabinet", "organizer"]
        },
        {
            "query": "I keep spilling coffee on my desk.",
            "expected_category": VagueCategory.SYMPTOM_PROBLEM,
            "expected_tool": "search_products",
            "should_contain": ["water", "resistant", "stain"]
        },
        {
            "query": "The sun is glaring on my screen.",
            "expected_category": VagueCategory.SYMPTOM_PROBLEM,
            "expected_tool": "search_products",
            "should_contain": ["curtain", "lamp"]
        },
    ]
    
    print("\n=== Category 1: Symptom & Problem Solving ===\n")
    
    for case in test_cases:
        result = handler.analyze(case["query"])
        
        print(f"Query: \"{case['query']}\"")
        print(f"  Category: {result.category.value}")
        print(f"  Intent: {result.interpreted_intent}")
        print(f"  Suggested Query: {result.suggested_query}")
        print(f"  Tool: {result.suggested_tool}")
        print(f"  Confidence: {result.confidence:.0%}")
        
        # Verify
        assert result.is_vague, f"Should be vague: {case['query']}"
        assert result.category == case["expected_category"], f"Wrong category for: {case['query']}"
        assert result.suggested_tool == case["expected_tool"], f"Wrong tool for: {case['query']}"
        
        query_lower = result.suggested_query.lower()
        for word in case["should_contain"]:
            assert word in query_lower, f"Missing '{word}' in suggested query for: {case['query']}"
        
        print("  ✅ PASSED\n")


def test_spatial_queries():
    """Test Category 2: Spatial & Physical Constraints"""
    handler = VagueQueryHandler()
    
    test_cases = [
        {
            "query": "I live in a shoe box studio.",
            "expected_category": VagueCategory.SPATIAL_CONSTRAINT,
            "should_contain": ["compact", "folding", "space"]
        },
        {
            "query": "I need a table for a family of 8.",
            "expected_category": VagueCategory.SPATIAL_CONSTRAINT,
            "should_contain": ["large", "dining", "table"]
        },
        {
            "query": "Something to put in that awkward corner.",
            "expected_category": VagueCategory.SPATIAL_CONSTRAINT,
            "should_contain": ["corner"]
        },
    ]
    
    print("\n=== Category 2: Spatial & Physical Constraints ===\n")
    
    for case in test_cases:
        result = handler.analyze(case["query"])
        
        print(f"Query: \"{case['query']}\"")
        print(f"  Category: {result.category.value}")
        print(f"  Intent: {result.interpreted_intent}")
        print(f"  Suggested Query: {result.suggested_query}")
        print(f"  Filters: {result.suggested_filters}")
        print(f"  Confidence: {result.confidence:.0%}")
        
        assert result.is_vague
        assert result.category == case["expected_category"]
        
        query_lower = result.suggested_query.lower()
        for word in case["should_contain"]:
            assert word in query_lower, f"Missing '{word}' in: {result.suggested_query}"
        
        print("  ✅ PASSED\n")


def test_slang_queries():
    """Test Category 3: Subjective & Slang"""
    handler = VagueQueryHandler()
    
    test_cases = [
        {
            "query": "Show me the boujee stuff.",
            "expected_category": VagueCategory.SUBJECTIVE_SLANG,
            "expected_filters": {"sort_by": "price_high"}
        },
        {
            "query": "I'm a broke student.",
            "expected_category": VagueCategory.SUBJECTIVE_SLANG,
            "expected_filters": {"sort_by": "price_low"}
        },
        {
            "query": "Give me that industrial loft look.",
            "expected_category": VagueCategory.SUBJECTIVE_SLANG,
            "expected_filters": {"style": "industrial"}
        },
        {
            "query": "I want a desk that looks like an Apple store.",
            "expected_category": VagueCategory.SUBJECTIVE_SLANG,
            "should_contain": ["minimalist", "modern"]
        },
    ]
    
    print("\n=== Category 3: Subjective & Slang ===\n")
    
    for case in test_cases:
        result = handler.analyze(case["query"])
        
        print(f"Query: \"{case['query']}\"")
        print(f"  Category: {result.category.value}")
        print(f"  Intent: {result.interpreted_intent}")
        print(f"  Suggested Query: {result.suggested_query}")
        print(f"  Filters: {result.suggested_filters}")
        print(f"  Confidence: {result.confidence:.0%}")
        
        assert result.is_vague
        assert result.category == case["expected_category"]
        
        if "expected_filters" in case:
            for key, val in case["expected_filters"].items():
                assert result.suggested_filters.get(key) == val, \
                    f"Filter {key} should be {val}, got {result.suggested_filters.get(key)}"
        
        print("  ✅ PASSED\n")


def test_lifestyle_queries():
    """Test Category 4: Usage & Lifestyle Context"""
    handler = VagueQueryHandler()
    
    test_cases = [
        {
            "query": "I'm starting a streaming channel.",
            "expected_category": VagueCategory.LIFESTYLE_CONTEXT,
            "should_contain": ["gaming"]
        },
        {
            "query": "My cat scratches everything.",
            "expected_category": VagueCategory.LIFESTYLE_CONTEXT,
            "should_contain": ["scratch", "resistant", "pet"]
        },
        {
            "query": "I work standing up.",
            "expected_category": VagueCategory.LIFESTYLE_CONTEXT,
            "should_contain": ["standing", "desk"]
        },
        {
            "query": "Furniture for a man cave.",
            "expected_category": VagueCategory.LIFESTYLE_CONTEXT,
            "should_contain": ["recliner", "leather"]
        },
    ]
    
    print("\n=== Category 4: Usage & Lifestyle Context ===\n")
    
    for case in test_cases:
        result = handler.analyze(case["query"])
        
        print(f"Query: \"{case['query']}\"")
        print(f"  Category: {result.category.value}")
        print(f"  Intent: {result.interpreted_intent}")
        print(f"  Suggested Query: {result.suggested_query}")
        print(f"  Confidence: {result.confidence:.0%}")
        
        assert result.is_vague
        assert result.category == case["expected_category"]
        
        query_lower = result.suggested_query.lower()
        for word in case["should_contain"]:
            assert word in query_lower, f"Missing '{word}' in: {result.suggested_query}"
        
        print("  ✅ PASSED\n")


def test_negation_queries():
    """Test Category 5: Negation & Complexity"""
    handler = VagueQueryHandler()
    
    test_cases = [
        {
            "query": "Show me desks that aren't wood.",
            "expected_category": VagueCategory.NEGATION_COMPLEXITY,
            "should_contain": ["metal", "glass"]
        },
        {
            "query": "Chairs without wheels.",
            "expected_category": VagueCategory.NEGATION_COMPLEXITY,
            "should_contain": ["stationary", "no wheels"]
        },
    ]
    
    print("\n=== Category 5: Negation & Complexity ===\n")
    
    for case in test_cases:
        result = handler.analyze(case["query"])
        
        print(f"Query: \"{case['query']}\"")
        print(f"  Category: {result.category.value}")
        print(f"  Intent: {result.interpreted_intent}")
        print(f"  Suggested Query: {result.suggested_query}")
        print(f"  Confidence: {result.confidence:.0%}")
        
        assert result.is_vague
        assert result.category == case["expected_category"]
        
        query_lower = result.suggested_query.lower()
        matched = any(word in query_lower for word in case["should_contain"])
        assert matched, f"Should contain one of {case['should_contain']} in: {result.suggested_query}"
        
        print("  ✅ PASSED\n")


def test_sentiment_queries():
    """Test Category 6: Sentiment & Action Implied"""
    handler = VagueQueryHandler()
    
    test_cases = [
        {
            "query": "I bought this last week and I hate it.",
            "expected_category": VagueCategory.SENTIMENT_ACTION,
            "expected_tool": "get_policy_info",
        },
    ]
    
    print("\n=== Category 6: Sentiment & Action Implied ===\n")
    
    for case in test_cases:
        result = handler.analyze(case["query"])
        
        print(f"Query: \"{case['query']}\"")
        print(f"  Category: {result.category.value}")
        print(f"  Intent: {result.interpreted_intent}")
        print(f"  Tool: {result.suggested_tool}")
        print(f"  Clarification: {result.clarification_message}")
        print(f"  Confidence: {result.confidence:.0%}")
        
        assert result.is_vague
        assert result.category == case["expected_category"]
        assert result.suggested_tool == case["expected_tool"]
        
        print("  ✅ PASSED\n")


def test_clear_queries():
    """Test that clear product queries are not flagged as vague"""
    handler = VagueQueryHandler()
    
    clear_queries = [
        "office chair",
        "wooden desk",
        "leather sofa",
        "queen size bed",
        "black metal shelf",
    ]
    
    print("\n=== Clear Queries (Should NOT be vague) ===\n")
    
    for query in clear_queries:
        result = handler.analyze(query)
        
        print(f"Query: \"{query}\"")
        print(f"  Is Vague: {result.is_vague}")
        print(f"  Category: {result.category.value}")
        
        assert not result.is_vague or result.category == VagueCategory.CLEAR, \
            f"Clear query flagged as vague: {query}"
        
        print("  ✅ PASSED\n")


def test_convenience_function():
    """Test the analyze_vague_query convenience function"""
    result = analyze_vague_query("My back is killing me")
    
    print("\n=== Convenience Function Test ===\n")
    print(f"Result type: {type(result)}")
    print(f"Keys: {result.keys()}")
    
    assert isinstance(result, dict)
    assert "is_vague" in result
    assert "category" in result
    assert "suggested_query" in result
    assert "tool_args" in result
    
    print("  ✅ PASSED\n")


if __name__ == "__main__":
    print("=" * 60)
    print("VAGUE QUERY HANDLER TEST SUITE")
    print("=" * 60)
    
    test_symptom_queries()
    test_spatial_queries()
    test_slang_queries()
    test_lifestyle_queries()
    test_negation_queries()
    test_sentiment_queries()
    test_clear_queries()
    test_convenience_function()
    
    print("=" * 60)
    print("ALL TESTS PASSED! ✅")
    print("=" * 60)
