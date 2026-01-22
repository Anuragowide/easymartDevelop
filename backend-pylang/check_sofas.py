import sqlite3
conn = sqlite3.connect('data/easymart.db')
c = conn.cursor()

print("=== SOFAS IN DATABASE ===")
c.execute("SELECT title, price, category, inventory_quantity FROM products WHERE category = 'Sofa' LIMIT 10")
for r in c.fetchall():
    print(f"{r[1]:>8.2f} | stock:{r[3]:>3} | {r[2]:15} | {r[0][:50]}")

c.execute("SELECT COUNT(*) FROM products WHERE category = 'Sofa'")
print(f"\nTotal sofas: {c.fetchone()[0]}")

# Check grey/dark grey sofas
print("\n=== GREY SOFAS ===")
c.execute("SELECT title, price FROM products WHERE category = 'Sofa' AND (title LIKE '%grey%' OR title LIKE '%Grey%' OR title LIKE '%gray%')")
for r in c.fetchall():
    print(f"{r[1]:>8.2f} | {r[0][:60]}")

# Test search
print("\n=== TESTING SEARCH ===")
import asyncio
from app.modules.retrieval.product_search import ProductSearcher

async def test():
    ps = ProductSearcher()
    
    print("Search: 'sofa'")
    results = await ps.search(query='sofa', limit=5)
    print(f"  Found: {len(results or [])}")
    for r in (results or [])[:3]:
        print(f"    {r.get('price'):>8.2f} | {r.get('title', r.get('name', '?'))[:45]}")
    
    print("\nSearch: 'grey sofa'")
    results = await ps.search(query='grey sofa', limit=5)
    print(f"  Found: {len(results or [])}")
    for r in (results or [])[:3]:
        print(f"    {r.get('price'):>8.2f} | {r.get('title', r.get('name', '?'))[:45]}")

asyncio.run(test())
conn.close()
