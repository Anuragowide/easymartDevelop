import sqlite3
import os

db_path = 'backend-python/data/easymart.db'
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute('SELECT sku, title, category FROM products WHERE category LIKE "%bed%" OR title LIKE "%bed%"')
rows = cur.fetchall()
print(f"Found {len(rows)} beds:")
for row in rows:
    print(row)
conn.close()
