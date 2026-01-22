"""Fetch fresh data from Node.js adapter and compare with database"""
import requests

# Fetch from Node adapter
url = 'http://localhost:3002/api/internal/catalog/export'
try:
    resp = requests.get(url, timeout=60)
    data = resp.json()
    
    # Find the specific desk
    for p in data:
        if '2 Drawer' in p.get('title', '') and 'Computer Desk' in p.get('title', ''):
            print('=== Artiss 2 Drawer Wood Computer Desk from Shopify ===')
            print(f"Title: {p.get('title')}")
            print(f"Price: {p.get('price')}")
            print(f"Available: {p.get('available')}")
            print(f"Stock Status: {p.get('stock_status')}")
            print(f"Inventory Managed: {p.get('inventory_managed')}")
            specs = p.get('specs', {})
            print(f"Inventory Qty (from specs): {specs.get('inventory_quantity')}")
            print()
    
    # Count totals
    in_stock = sum(1 for p in data if p.get('stock_status') == 'in_stock' or p.get('available'))
    print(f'Total products from Shopify: {len(data)}')
    print(f'Products in stock / available: {in_stock}')
    
    # Show cheapest desks from Shopify
    print()
    print('=== Cheapest Desks from Shopify (live) ===')
    desks = [p for p in data if 'desk' in p.get('title', '').lower()]
    print(f'Found {len(desks)} desk products')
    desks.sort(key=lambda x: x.get('price', 0))
    for p in desks[:15]:
        title = p.get('title', '')[:45]
        price = p.get('price', 0)
        available = p.get('available', 'N/A')
        stock_status = p.get('stock_status', 'N/A')
        specs = p.get('specs', {})
        inv = specs.get('inventory_quantity', 'N/A')
        print(f'{price:>8.2f} | inv:{inv:>4} | avail:{available} | {stock_status} | {title}')
        
except Exception as e:
    print(f'Error: {e}')
