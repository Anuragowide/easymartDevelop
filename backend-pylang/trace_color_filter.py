"""Trace exactly where grey sofa filtering fails"""
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

async def main():
    from app.modules.retrieval.product_search import ProductSearcher
    
    ps = ProductSearcher()
    
    # 1. Test raw search without filters
    print("="*80)
    print("STEP 1: Raw search 'grey sofa' - NO filters")
    print("="*80)
    raw_results = await ps.search(query="grey sofa", filters={}, limit=10)
    if isinstance(raw_results, dict):
        print(f"Got dict: {raw_results}")
    else:
        print(f"Got {len(raw_results)} results")
        for r in raw_results[:3]:
            print(f"  - {r.get('name')}")
    
    # 2. Test with color filter
    print("\n" + "="*80)
    print("STEP 2: Search 'grey sofa' with color='grey' filter")
    print("="*80)
    filtered_results = await ps.search(query="grey sofa", filters={"color": "grey"}, limit=10)
    if isinstance(filtered_results, dict):
        print(f"Got dict: {filtered_results}")
    else:
        print(f"Got {len(filtered_results)} results")
        for r in filtered_results[:3]:
            print(f"  - {r.get('name')}")
    
    # 3. Test the filter function directly
    print("\n" + "="*80)
    print("STEP 3: Test _apply_filters directly")
    print("="*80)
    
    # Get some results first
    test_results = await ps.search(query="sofa", filters={}, limit=20)
    print(f"Before filtering: {len(test_results)} sofas")
    
    # Now apply color filter manually
    filtered = ps._apply_filters(test_results, {"color": "grey", "query_text": "grey sofa"})
    print(f"After color=grey filter: {len(filtered)} sofas")
    for r in filtered[:5]:
        name = r.get('name', 'Unknown')
        tags = r.get('tags', [])
        print(f"  - {name}")
        print(f"    Tags: {tags}")
    
    # 4. Debug the color matching logic
    print("\n" + "="*80)
    print("STEP 4: Debug color matching for first sofa")
    print("="*80)
    
    if test_results:
        product = test_results[0]
        print(f"Product: {product.get('name')}")
        
        prod_tags = ps._parse_tags(product.get("tags", []))
        prod_tags_lower = [t.lower() for t in prod_tags]
        prod_title = (product.get("name") or "").lower()
        prod_desc = (product.get("description") or "")[:200].lower()
        
        target_color = "grey"
        
        print(f"\nChecking for color '{target_color}':")
        print(f"  prod_tags_lower: {prod_tags_lower}")
        print(f"  prod_title: {prod_title[:50]}...")
        
        # Check each condition
        check1 = target_color in prod_tags_lower
        check2 = f"color_{target_color}" in prod_tags_lower
        check3 = any(target_color in tag for tag in prod_tags_lower)
        check4 = target_color in prod_title
        check5 = target_color in prod_desc
        
        print(f"\n  Check 1 (exact in tags list): {check1}")
        print(f"  Check 2 (color_grey in tags): {check2}")
        print(f"  Check 3 (substring in any tag): {check3}")
        print(f"  Check 4 (in title): {check4}")
        print(f"  Check 5 (in desc): {check5}")
        
        found_color = check1 or check2 or check3 or check4 or check5
        print(f"\n  FINAL: found_color = {found_color}")

if __name__ == "__main__":
    asyncio.run(main())
