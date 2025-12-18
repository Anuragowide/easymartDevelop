"""
Product Search Wrapper

High-level interface for product search with additional features:
- Query preprocessing
- Result filtering
- Ranking adjustments
- Price/vendor filtering
"""

import asyncio
from typing import List, Dict, Any, Optional
from app.modules.catalog_index import CatalogIndexer


class ProductSearcher:
    """
    High-level product search interface.
    Wraps CatalogIndexer with additional features.
    """
    
    def __init__(self):
        self.catalog = CatalogIndexer()
    
    async def search(
        self, 
        query: str, 
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search products with optional filters.
        
        Args:
            query: Search query string
            limit: Maximum number of results
            filters: Optional filters (price_min, price_max, vendor, tags)
        
        Returns:
            List of product results with scores
        
        Example:
            >>> searcher = ProductSearcher()
            >>> results = await searcher.search(
            ...     "leather wallet",
            ...     limit=5,
            ...     filters={"price_max": 100, "vendor": "Easymart"}
            ... )
        """
        
        # Get raw search results from catalog
        results = await asyncio.to_thread(self.catalog.searchProducts, query, limit=limit * 2)
        
        # Format results properly with product names
        formatted_results = []
        for result in results:
            # Extract product data from 'content' field (actual data structure from searchProducts)
            product_data = result.get("content", {})
            
            # Build formatted product with proper name
            formatted_product = {
                "id": product_data.get("sku", result.get("id", "")),
                "name": product_data.get("title", "Unknown Product"),  # Use title as name
                "price": product_data.get("price", 0.00),
                "description": product_data.get("description", ""),
                "image_url": product_data.get("image_url", ""),
                "handle": product_data.get("handle", ""),
                "vendor": product_data.get("vendor", ""),
                "tags": product_data.get("tags", []),
                "currency": product_data.get("currency", "AUD"),
                "product_url": product_data.get("product_url", ""),
                "category": product_data.get("category", ""),
                "score": result.get("score", 0),
                "inventory_quantity": product_data.get("inventory_quantity", 0),
            }
            formatted_results.append(formatted_product)
        
        # Apply filters if provided
        if filters:
            formatted_results = self._apply_filters(formatted_results, filters)
        
        # Return top N results
        return formatted_results[:limit]
    
    def _apply_filters(
        self, 
        results: List[Dict[str, Any]], 
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Apply filters to search results.
        """
        filtered = []
        
        for result in results:
            # FIX: Use result directly (not nested under 'content')
            product = result  # Changed from result.get("content", {})
            
            # Price filter
            if "price_min" in filters:
                if product.get("price", 0) < filters["price_min"]:
                    continue
            
            if "price_max" in filters:
                if product.get("price", float('inf')) > filters["price_max"]:
                    continue
            
            # Vendor filter
            if "vendor" in filters:
                if product.get("vendor", "").lower() != filters["vendor"].lower():
                    continue
            
            # Tags filter
            if "tags" in filters:
                product_tags = set(tag.lower() for tag in product.get("tags", []))
                filter_tags = set(tag.lower() for tag in filters["tags"])
                if not filter_tags.intersection(product_tags):
                    continue
            
            # In Stock filter
            if "in_stock" in filters:
                is_in_stock = product.get("in_stock", True)
                if is_in_stock != filters["in_stock"]:
                    continue
            
            filtered.append(result)
        
        return filtered
    
    async def get_product(self, sku: str) -> Optional[Dict[str, Any]]:
        """
        Get product by SKU.
        
        Args:
            sku: Product SKU
        
        Returns:
            Product dictionary or None
        """
        return await asyncio.to_thread(self.catalog.getProductById, sku)
    
    async def search_by_category(self, category: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search products by category.
        
        Args:
            category: Category name (used as tag filter)
            limit: Maximum number of results
        
        Returns:
            List of products in category
        """
        return await self.search(
            query=category,
            limit=limit,
            filters={"tags": [category]}
        )
