import sqlite3

conn = sqlite3.connect('data/easymart.db')

print("Categories for Queen Bed Frames:")
print("=" * 80)
cursor = conn.execute(
    "SELECT DISTINCT category FROM products WHERE title LIKE '%Queen%' AND title LIKE '%Bed Frame%'"
)
for row in cursor:
    print(f"- {row[0]}")

print()
print("Sample products:")
cursor = conn.execute(
    "SELECT sku, title, category, inventory_quantity FROM products WHERE title LIKE '%Queen%' AND title LIKE '%Bed Frame%' LIMIT 5"
)
for row in cursor:
    sku, title, category, qty = row
    print(f"\nSKU: {sku}")
    print(f"Title: {title}")
    print(f"Category: {category}")
    print(f"Stock: {qty}")

conn.close()
