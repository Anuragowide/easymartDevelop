"""Check what color tags/info grey sofas actually have"""
import sqlite3

db_path = "data/easymart.db"
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Find all sofas with grey in title or description
cursor.execute("""
    SELECT sku, title, category, tags, description
    FROM products
    WHERE (LOWER(title) LIKE '%sofa%' OR LOWER(category) = 'sofa')
    AND (LOWER(title) LIKE '%grey%' OR LOWER(description) LIKE '%grey%')
    LIMIT 10
""")

rows = cursor.fetchall()
print(f"Found {len(rows)} grey sofas:")
for r in rows:
    print(f"\nSKU: {r['sku']}")
    print(f"  Title: {r['title']}")
    print(f"  Category: {r['category']}")
    print(f"  Tags: {r['tags']}")
    desc = r['description'] or ''
    print(f"  Desc (first 200 chars): {desc[:200]}...")

# Check what color tags exist for sofas
print("\n" + "="*80)
print("ALL SOFAS AND THEIR COLOR TAGS:")
print("="*80)
cursor.execute("""
    SELECT sku, title, tags
    FROM products
    WHERE LOWER(title) LIKE '%sofa%' OR LOWER(category) = 'sofa'
""")

for r in cursor.fetchall():
    tags = r['tags'] or '[]'
    # Extract color tags
    if 'color' in tags.lower() or 'grey' in tags.lower():
        print(f"\n{r['title']}")
        print(f"  Tags: {tags}")

conn.close()
