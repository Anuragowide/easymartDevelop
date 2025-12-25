import sqlite3
import os

db_path = 'backend-python/data/easymart.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute('PRAGMA table_info(products)')
columns = cur.fetchall()
print("Products table columns:")
for col in columns:
    print(col)

cur.execute('SELECT * FROM products LIMIT 1')
row = cur.fetchone()
print("\nExample row:")
print(row)

cur.execute('SELECT sku, title FROM products WHERE title LIKE "%bed%"')
rows = cur.fetchall()
print(f"\nFound {len(rows)} beds:")
for row in rows:
    print(row)

conn.close()
