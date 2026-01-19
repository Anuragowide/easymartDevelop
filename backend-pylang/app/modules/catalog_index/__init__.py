"""
Catalog Index Module

Hybrid BM25 + Vector search for product catalog.
"""

from .catalog import CatalogIndexer
from .models import Product, ProductImage, ProductSpecDoc, IndexDocument
from .config import index_config

__all__ = [
    "CatalogIndexer",
    "Product",
    "ProductImage",
    "ProductSpecDoc",
    "IndexDocument",
    "index_config"
]
