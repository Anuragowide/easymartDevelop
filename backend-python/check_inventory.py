import sqlite3

conn = sqlite3.connect('data/easymart.db')
cursor = conn.execute('SELECT product_id, title, inventory_quantity FROM products LIMIT 5')

print('Sample products with inventory:')
for row in cursor:
    title = row[1][:40] if len(row[1]) > 40 else row[1]
    print(f'  {row[0]}: {title}... Stock: {row[2]}')

conn.close()
