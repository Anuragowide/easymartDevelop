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
from app.modules.assistant.categories import (
    is_valid_category, 
    ALL_CATEGORIES, 
    ALL_SUBCATEGORIES,
    CATEGORY_MAPPING
)

# Configuration
NODE_API_URL = os.getenv("NODE_BACKEND_URL", "http://localhost:3002")
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

        # Normalize list fields if provided as JSON strings
        for key in ["tags", "options", "variants", "images"]:
            if isinstance(p.get(key), str):
                try:
                    p[key] = json.loads(p[key])
                except Exception:
                    p[key] = []
        
        # Extract inventory_quantity from specs to top level
        if isinstance(p.get('specs'), dict):
            p['inventory_quantity'] = p['specs'].get('inventory_quantity', 0)
        else:
            p['inventory_quantity'] = 0

        if p.get("available") is None:
            if p.get("inventory_managed") is False:
                p["available"] = True
            else:
                p["available"] = (p.get("inventory_quantity") or 0) > 0

        # Flatten option values for searchability
        option_values = []
        for opt in p.get("options", []) or []:
            values = opt.get("values") if isinstance(opt, dict) else None
            if values:
                option_values.extend(values)
        if option_values:
            p["option_values"] = option_values

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
        # Increased timeout to 120 seconds for large product catalogs
        response = requests.get(url, timeout=120)
        response.raise_for_status()
        data = response.json()
        
        if not isinstance(data, list):
            raise ValueError("API response expected to be a list of products")
            
        print(f"[Catalog] Successfully fetched {len(data)} products from API.")
        
        # Log categories found
        categories = set(p.get('category', 'Unknown') for p in data)
        print(f"[Catalog] Categories found: {', '.join(sorted(categories))}")
        
        # Validate categories against known mappings
        invalid_categories = [cat for cat in categories if not is_valid_category(cat) and cat not in ['Unknown', 'Uncategorized']]
        if invalid_categories:
            print(f"[Catalog] Warning: Found products with unmapped categories: {', '.join(invalid_categories)}")
            print(f"[Catalog] Valid categories are: {', '.join(ALL_CATEGORIES)}")
        
        # Category breakdown
        category_count = {}
        for p in data:
            cat = p.get('category', 'Unknown')
            category_count[cat] = category_count.get(cat, 0) + 1
        
        print("\n[Catalog] Product Distribution by Category:")
        for cat, count in sorted(category_count.items()):
            print(f"  - {cat}: {count} products")
        print()
        
        return process_products(data)
    except requests.exceptions.RequestException as e:
        print(f"[Catalog] API Fetch failed: {e}")
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
            "handle": p.get("Handle"),
            # Extract spec data from CSV - filter out NaN/None values
            "specs": {
                "specifications": p.get("Specifications") if pd.notna(p.get("Specifications")) else None,
                "features": p.get("Features") if pd.notna(p.get("Features")) else None,
                "material": p.get("Material") if pd.notna(p.get("Material")) else None,
                "dimensions": {
                    "length": p.get("Length") if pd.notna(p.get("Length")) else None,
                    "width": p.get("Width") if pd.notna(p.get("Width")) else None,
                    "height": p.get("Height") if pd.notna(p.get("Height")) else None
                }
            }
        }
        mapped_products.append(mapped)
                
    return process_products(mapped_products)

def extract_specs_from_products(products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extract specs from products for indexing"""
    all_specs = []
    
    for product in products:
        sku = product.get('sku')
        if not sku:
            continue
            
        specs_data = product.get('specs', {})
        
        # Add Specifications section
        if specs_data.get('specifications'):
            all_specs.append({
                'sku': sku,
                'section': 'Specifications',
                'spec_text': specs_data['specifications'],
                'attributes': {}
            })
        
        # Add Features section
        if specs_data.get('features'):
            all_specs.append({
                'sku': sku,
                'section': 'Features',
                'spec_text': specs_data['features'],
                'attributes': {}
            })
        
        # Add Material section
        if specs_data.get('material'):
            all_specs.append({
                'sku': sku,
                'section': 'Material',
                'spec_text': f"Material: {specs_data['material']}",
                'attributes': {'material': specs_data['material']}
            })
        
        # Add Dimensions section
        dims = specs_data.get('dimensions', {})
        if any([dims.get('length'), dims.get('width'), dims.get('height')]):
            dim_parts = []
            # Only add dimensions that aren't None/NaN
            if dims.get('length') and pd.notna(dims.get('length')):
                dim_parts.append(f"Length: {dims['length']}cm")
            if dims.get('width') and pd.notna(dims.get('width')):
                dim_parts.append(f"Width: {dims['width']}cm")
            if dims.get('height') and pd.notna(dims.get('height')):
                dim_parts.append(f"Height: {dims['height']}cm")
            
            # Only add dimension section if we have at least one valid dimension
            if dim_parts:
                all_specs.append({
                    'sku': sku,
                    'section': 'Dimensions',
                    'spec_text': ' | '.join(dim_parts),
                    'attributes': {k: v for k, v in dims.items() if v and pd.notna(v)}
                })

        # Add Options section
        options = product.get("options") or specs_data.get("options") or []
        if options:
            option_lines = []
            for opt in options:
                name = opt.get("name") if isinstance(opt, dict) else None
                values = opt.get("values") if isinstance(opt, dict) else None
                if name and values:
                    option_lines.append(f"{name}: {', '.join(values)}")
            if option_lines:
                all_specs.append({
                    'sku': sku,
                    'section': 'Options',
                    'spec_text': " | ".join(option_lines),
                    'attributes': {"options": options}
                })

        # Add Variants summary section
        variants = product.get("variants") or specs_data.get("variants") or []
        if variants:
            variant_lines = []
            for v in variants[:10]:
                title = v.get("title") if isinstance(v, dict) else None
                price = v.get("price") if isinstance(v, dict) else None
                if title and price:
                    variant_lines.append(f"{title}: ${price}")
            if variant_lines:
                all_specs.append({
                    'sku': sku,
                    'section': 'Variants',
                    'spec_text': " | ".join(variant_lines),
                    'attributes': {"variants": variants}
                })
    
    return all_specs

async def load_all_products(allow_csv_fallback: bool = True):
    indexer = CatalogIndexer()
    
    # 1. Try API first
    products = fetch_from_node_adapter()
    
    # 2. Fallback to CSV if API returned nothing (optional, good for dev)
    if not products and allow_csv_fallback:
        print("[Catalog] Falling back to local CSV data...")
        products = load_from_csv()
        
    if not products:
        print("[Catalog] No products found from API or CSV. Aborting.")
        return

    # 3. Index the products
    print(f"[Catalog] Starting indexing for {len(products)} products...")
    await asyncio.to_thread(indexer.addProducts, products)
    
    # 4. Extract and index specs
    specs = extract_specs_from_products(products)
    if specs:
        print(f"[Catalog] Indexing {len(specs)} specifications...")
        await asyncio.to_thread(indexer.addSpecs, specs)
    else:
        print("[Catalog] No specifications found to index")
    
    print("[Catalog] Catalog loading and indexing complete.")

if __name__ == "__main__":
    asyncio.run(load_all_products())
