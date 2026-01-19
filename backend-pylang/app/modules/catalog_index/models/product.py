"""
Product data models
"""

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Product:
    """Represents a product in the catalog"""
    handle: str          # URL slug
    title: str           # Display name
    sku: str            # Unique identifier
    price: float        # Product price
    currency: str       # Currency code (USD, EUR, etc.)
    image_url: Optional[str]  # Main image URL
    vendor: str         # Brand/manufacturer
    tags: List[str]     # Category tags
    description: str    # Full description


@dataclass
class ProductImage:
    """Represents a product image"""
    image_id: str       # Unique image identifier
    sku: str           # Product reference
    image_url: str     # Image URL
