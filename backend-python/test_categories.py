"""
Test script to verify category mapping
"""

import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.modules.assistant.categories import (
    CATEGORY_MAPPING,
    ALL_CATEGORIES,
    ALL_SUBCATEGORIES,
    match_category_from_query,
    match_subcategory_from_query,
    get_category_for_subcategory,
    get_category_summary
)

def test_categories():
    """Test category mapping"""
    print("=" * 80)
    print("EASYMART CATEGORY MAPPING TEST")
    print("=" * 80)
    
    print(f"\n📊 Total Categories: {len(ALL_CATEGORIES)}")
    print(f"📊 Total Subcategories: {len(ALL_SUBCATEGORIES)}")
    
    print("\n" + "=" * 80)
    print("CATEGORY BREAKDOWN")
    print("=" * 80)
    
    for category, subcategories in CATEGORY_MAPPING.items():
        print(f"\n✅ {category} ({len(subcategories)} subcategories)")
        for i, subcat in enumerate(subcategories, 1):
            print(f"   {i:2d}. {subcat}")
    
    print("\n" + "=" * 80)
    print("CATEGORY SUMMARY")
    print("=" * 80)
    print(get_category_summary())
    
    print("\n" + "=" * 80)
    print("QUERY MATCHING TESTS")
    print("=" * 80)
    
    test_queries = [
        "Show me dumbbells",
        "I need a treadmill",
        "electric scooters",
        "dog kennel",
        "office chairs",
        "gaming chair",
        "cat tree",
        "boxing equipment",
        "kettlebells for gym",
        "fitness equipment",
    ]
    
    for query in test_queries:
        category = match_category_from_query(query)
        subcategory = match_subcategory_from_query(query)
        print(f"\nQuery: '{query}'")
        print(f"  → Category: {category or 'Not matched'}")
        print(f"  → Subcategory: {subcategory or 'Not matched'}")
        if subcategory:
            parent = get_category_for_subcategory(subcategory)
            print(f"  → Parent Category: {parent}")
    
    print("\n" + "=" * 80)
    print("✅ CATEGORY MAPPING TEST COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    test_categories()
