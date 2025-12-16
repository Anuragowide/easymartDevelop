"""
Product specification data model
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class ProductSpecDoc:
    """Represents a product specification document"""
    sku: str                              # Product reference
    section: str                          # Spec category (dimensions, material, etc.)
    spec_text: str                        # Human-readable text
    attributes_json: Optional[Dict[str, Any]] = None  # Structured data
