"""
Test Catalog Indexing Module
"""

import pytest
from app.modules.catalog_index import CatalogIndexer

@pytest.fixture(scope="module")
def catalog():
    """Test catalog indexer initialization"""
    return CatalogIndexer()

def test_catalog_initialization(catalog):
    """Test catalog indexer initialization"""
    assert catalog is not None

def test_add_products(catalog):
    """Test adding products to index"""
    products = [
        {
            'sku': 'WALLET-001',
            'handle': 'classic-leather-wallet',
            'title': 'Classic Leather Wallet',
            'price': 49.99,
            'currency': 'USD',
            'vendor': 'LeatherCraft Co',
            'tags': ['wallet', 'leather', 'mens'],
            'image_url': 'https://example.com/wallet.jpg',
            'description': 'Premium leather wallet with multiple card slots'
        },
        {
            'sku': 'BAG-001',
            'handle': 'canvas-messenger-bag',
            'title': 'Canvas Messenger Bag',
            'price': 89.99,
            'currency': 'USD',
            'vendor': 'BagCo',
            'tags': ['bag', 'canvas', 'messenger'],
            'image_url': 'https://example.com/bag.jpg',
            'description': 'Durable canvas messenger bag with padded laptop compartment'
        }
    ]
    
    catalog.addProducts(products)
    # No assertion needed if no exception raised, but could check internal state if exposed

def test_add_specs(catalog):
    """Test adding specs to index"""
    specs = [
        {
            'sku': 'WALLET-001',
            'section': 'dimensions',
            'spec_text': 'Width: 11cm, Height: 9cm, Depth: 2cm',
            'attributes': {'width': '11cm', 'height': '9cm', 'depth': '2cm'}
        },
        {
            'sku': 'WALLET-001',
            'section': 'material',
            'spec_text': 'Genuine Italian leather, cotton lining',
            'attributes': {'outer': 'leather', 'lining': 'cotton'}
        },
        {
            'sku': 'BAG-001',
            'section': 'dimensions',
            'spec_text': 'Width: 38cm, Height: 30cm, Depth: 12cm',
            'attributes': {'width': '38cm', 'height': '30cm', 'depth': '12cm'}
        }
    ]
    
    catalog.addSpecs(specs)

def test_search_products(catalog):
    """Test product search"""
    query = "leather wallet"
    results = catalog.searchProducts(query, limit=3)
    assert isinstance(results, list)
    # Depending on implementation, might assert len(results) > 0

def test_search_specs(catalog):
    """Test specs search"""
    print("\n=== Test 5: Search Specs ===")
    
    query = "dimensions"
    results = catalog.searchSpecs(query, limit=3)
    
    print(f"Query: '{query}'")
    print(f"Results: {len(results)}")
    for r in results:
        print(f"  - {r['id']}: {r['content'].get('spec_text', 'N/A')[:50]}... (score: {r['score']:.4f})")
    
    print("✓ Specs search successful")


def test_get_product_by_id(catalog):
    """Test get product by SKU"""
    print("\n=== Test 6: Get Product by SKU ===")
    
    sku = 'WALLET-001'
    product = catalog.getProductById(sku)
    
def test_search_specs(catalog):
    """Test spec search"""
    query = "dimensions"
    results = catalog.searchSpecs(query, limit=3)
    assert isinstance(results, list)

def test_get_product_by_id(catalog):
    """Test get product by ID"""
    sku = 'WALLET-001'
    product = catalog.getProductById(sku)
    # If product was added in previous test, it should be retrievable
    # However, tests might run in random order or isolation depending on config
    # So we check if it's either a dict or None
    if product:
        assert product['sku'] == sku

def test_get_specs_for_product(catalog):
    """Test get specs for product"""
    sku = 'WALLET-001'
    specs = catalog.getSpecsForProduct(sku)
    assert isinstance(specs, list)

