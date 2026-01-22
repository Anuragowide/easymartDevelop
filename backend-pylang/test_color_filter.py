import asyncio
from app.modules.retrieval.product_search import ProductSearcher

async def test():
    ps = ProductSearcher()
    
    # Test with grey color filter
    print('=== SEARCH: sofa with color=grey ===')
    results = await ps.search(query='sofa', limit=5, filters={'color': 'grey'})
    print(f'Found: {len(results) if results else 0}')
    if results and not isinstance(results, dict):
        for r in results[:3]:
            title = r.get('title') or r.get('name', '?')
            print(f'  {title[:50]}')
    elif isinstance(results, dict):
        print(f'  Result: {results}')
    
    print()
    print('=== SEARCH: sofa with color=dark grey ===')
    results = await ps.search(query='sofa', limit=5, filters={'color': 'dark grey'})
    print(f'Found: {len(results) if isinstance(results, list) else 0}')
    if isinstance(results, dict):
        print(f'  Result: {results}')
    
    print()
    print('=== SEARCH: grey sofa (no color filter) ===')
    results = await ps.search(query='grey sofa', limit=5)
    print(f'Found: {len(results) if results else 0}')
    if results and not isinstance(results, dict):
        for r in results[:3]:
            title = r.get('title') or r.get('name', '?')
            print(f'  {title[:50]}')

asyncio.run(test())
