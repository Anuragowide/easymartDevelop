"""
Retrieval Module

Provides high-level search interfaces wrapping catalog_index.
Handles product search, spec search, and result ranking.
"""

from .product_search import ProductSearcher
from .spec_search import SpecSearcher

__all__ = ["ProductSearcher", "SpecSearcher"]
