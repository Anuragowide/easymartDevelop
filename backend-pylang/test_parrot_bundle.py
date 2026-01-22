"""Test parrot bundle to debug the issue."""
import asyncio
from app.modules.assistant.bundle_planner import BundlePlanner, parse_bundle_request


async def test():
    # Parse request manually
    items, meta = parse_bundle_request('parrot starter bundle budget 150')
    
    print("Categories:", meta.get('allowed_categories'))
    print("Items:", [(i.item_type, i.quantity) for i in items])
    print("Template items:", meta.get('template_items', [])[:2])
    print()
    
    # Create bundle planner and search manually
    bp = BundlePlanner()
    
    cats = meta.get('allowed_categories', [])
    template_items = meta.get('template_items', [])
    template_map = {t['type']: t for t in template_items}
    
    base_filters = {
        'categories': cats,
        'in_stock': True
    }
    
    print("Base filters:", base_filters)
    print()
    
    for item in items[:2]:  # Just first 2 items
        search_terms = template_map.get(item.item_type, {}).get('search_terms', [item.item_type])
        print(f"Item: {item.item_type}")
        print(f"  Search terms: {search_terms}")
        
        for term in search_terms:
            results = await bp.product_searcher.search(
                query=term,
                limit=3,
                filters=base_filters
            )
            if results:
                print(f"  Query '{term}' found {len(results)} results:")
                for r in results[:2]:
                    title = (r.get('title') or r.get('name', '?'))[:40]
                    cat = r.get('category', '?')
                    price = r.get('price', 0)
                    print(f"    {price:>6.2f} | {cat[:20]} | {title}")
                break
            else:
                print(f"  Query '{term}' found 0 results")
        print()


if __name__ == "__main__":
    asyncio.run(test())
