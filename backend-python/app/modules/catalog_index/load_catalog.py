"""
Load Catalog Script

Ingestion script for building catalog indexes from product data.
Run this script manually to rebuild the catalog indexes.
"""

import asyncio
import os
import sys
import requests
import pandas as pd
import json
from typing import List, Dict, Any

# Add the parent directory to sys.path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.modules.catalog_index.catalog import CatalogIndexer
from app.core.config import settings

# Configuration
NODE_API_URL = os.getenv("NODE_BACKEND_URL", "http://localhost:3001")
CATALOG_ENDPOINT = "/api/internal/catalog/export"

def process_products(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Clean and enrich product data before indexing.
    Ensures every product has a valid URL.
    """
    processed = []
    # Use Shopify store domain from environment or default
    shopify_domain = os.getenv("SHOPIFY_STORE_DOMAIN", "easymartdummy.myshopify.com")
    base_url = f"https://{shopify_domain}/products/"

    for p in products:
        # Ensure specs and tags are parsed if they are strings
        if isinstance(p.get('specs'), str):
            try:
                p['specs'] = json.loads(p['specs'])
            except:
                p['specs'] = {}
        
        # URL Construction Logic
        # If product_url is missing but handle exists, construct it
        if not p.get('product_url'):
            handle = p.get('handle')
            if handle:
                p['product_url'] = f"{base_url}{handle}"
            elif p.get('title'):
                # Fallback: slugify title
                slug = p['title'].lower().replace(' ', '-')
                p['product_url'] = f"{base_url}{slug}"
            else:
                # Last resort: use SKU as handle
                sku = p.get('sku', 'unknown')
                p['product_url'] = f"{base_url}{sku}"

        processed.append(p)
    return processed

def fetch_from_node_adapter() -> List[Dict[str, Any]]:
    """
    Fetches normalized product data from the Node.js Shopify Adapter.
    """
    url = f"{NODE_API_URL}{CATALOG_ENDPOINT}"
    print(f"[Catalog] Fetching data from Node.js Adapter: {url}")
    
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if not isinstance(data, list):
            raise ValueError("API response expected to be a list of products")
            
        print(f"[Catalog] Successfully fetched {len(data)} products from API.")
        return process_products(data)
    except requests.exceptions.RequestException as e:
        print(f"[Catalog] ⚠️ API Fetch failed: {e}")
        return []

def load_from_csv(filepath: str = None) -> List[Dict[str, Any]]:
    """
    Fallback: Load from local CSV.
    """
    if filepath is None:
        # Resolve path relative to this script
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        filepath = os.path.join(base_dir, "data", "products.csv")

    if not os.path.exists(filepath):
        print(f"[Catalog] CSV file not found at {filepath}")
        return []
        
    print(f"[Catalog] Loading from local CSV: {filepath}")
    df = pd.read_csv(filepath)
    
    # Convert DataFrame to list of dicts, handling NaN values
    products = df.where(pd.notnull(df), None).to_dict(orient='records')
    
    # Map CSV columns to internal schema
    mapped_products = []
    seen_skus = set()
    
    for p in products:
        sku = p.get("Variant SKU") or p.get("Handle")
        
        # Skip duplicates
        if sku in seen_skus:
            continue
        seen_skus.add(sku)
        
        # Basic mapping
        mapped = {
            "sku": sku,
            "title": p.get("Title"),
            "description": p.get("Description") or "",
            "price": float(p.get("Variant Price") or 0),
            "currency": "AUD",
            "category": p.get("Product Category"),
            "tags": p.get("Tags", "").split(", ") if p.get("Tags") else [],
            "image_url": p.get("Image Src"),
            "vendor": p.get("Vendor"),
            "handle": p.get("Handle")
        }
        mapped_products.append(mapped)
                
    return process_products(mapped_products)

async def main():
    indexer = CatalogIndexer()
    
    # 1. Try API first
    products = fetch_from_node_adapter()
    
    # 2. Fallback to CSV if API returned nothing (optional, good for dev)
    if not products:
        print("[Catalog] Falling back to local CSV data...")
        products = load_from_csv()
        
    if not products:
        print("[Catalog] ❌ No products found from API or CSV. Aborting.")
        return

    # 3. Index the data
    print(f"[Catalog] Starting indexing for {len(products)} products...")
    
    # Run the synchronous indexing in a thread to be async-friendly
    # Note: CatalogIndexer uses addProducts, not index_products
    await asyncio.to_thread(indexer.addProducts, products)
    
    print("[Catalog] ✅ Catalog loading and indexing complete.")

if __name__ == "__main__":
    asyncio.run(main())
