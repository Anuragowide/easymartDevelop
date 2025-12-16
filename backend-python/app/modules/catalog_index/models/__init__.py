"""
Catalog Index Models

Data models for products and specifications.
"""

from .product import Product, ProductImage
from .spec_doc import ProductSpecDoc
from .index_document import IndexDocument

__all__ = [
    'Product',
    'ProductImage',
    'ProductSpecDoc',
    'IndexDocument'
]
