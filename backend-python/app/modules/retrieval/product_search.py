"""
Product Search Wrapper

High-level interface for product search with additional features:
- Query preprocessing
- Result filtering
- Ranking adjustments
- Price/vendor filtering
"""

import asyncio
import re
from typing import List, Dict, Any, Optional
from app.modules.catalog_index import CatalogIndexer
from app.modules.observability.logging_config import get_logger

logger = get_logger(__name__)

# Pre-compiled regex patterns for performance
PRICE_PATTERNS = [
    re.compile(r'under\s+\$?(\d+)', re.IGNORECASE),
    re.compile(r'less\s+than\s+\$?(\d+)', re.IGNORECASE),
    re.compile(r'below\s+\$?(\d+)', re.IGNORECASE),
    re.compile(r'cheaper\s+than\s+\$?(\d+)', re.IGNORECASE),
    re.compile(r'max\s+\$?(\d+)', re.IGNORECASE),
    re.compile(r'maximum\s+\$?(\d+)', re.IGNORECASE),
]

COLOR_KEYWORDS = ['black', 'white', 'red', 'green', 'blue', 'brown', 'grey', 'gray', 'yellow', 'orange', 'pink', 'purple', 'beige']
MATERIAL_KEYWORDS = ['wood', 'metal', 'leather', 'fabric', 'glass', 'plastic', 'steel']
ROOM_KEYWORDS = ['office', 'bedroom', 'living room', 'dining room']

class ProductSearcher:
    """
    High-level product search interface.
    Wraps CatalogIndexer with additional features.
    """
    
    _cache = {}  # Simple in-memory cache
    _cache_max_size = 100
    
    def __init__(self):
        self.catalog = CatalogIndexer()
    
    async def search(
        self, 
        query: str, 
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search products with optional filters and caching.
        """
        # Create cache key
        cache_key = f"{query}:{limit}:{str(filters)}"
        if cache_key in self._cache:
            logger.info(f"[SEARCH] Cache hit for: {query}")
            return self._cache[cache_key]
        
        # Get raw search results from catalog
        results = await asyncio.to_thread(self.catalog.searchProducts, query, limit=limit * 5)
        
        # Format results properly
        formatted_results = []
        for result in results:
            product_data = result.get("content", {})
            formatted_product = {
                "id": product_data.get("sku", result.get("id", "")),
                "name": product_data.get("title", "Unknown Product"),
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
        if filters is None:
            filters = {}
            
        # AUTO-DETECT FILTERS from query
        query_lower = query.lower()
        
        if "color" not in filters:
            for color in COLOR_KEYWORDS:
                if f" {color} " in f" {query_lower} ":
                    filters["color"] = color
                    break
        
        if "material" not in filters:
            for mat in MATERIAL_KEYWORDS:
                if f" {mat} " in f" {query_lower} ":
                    filters["material"] = mat
                    break
                    
        if "room_type" not in filters:
            for room in ROOM_KEYWORDS:
                if room in query_lower:
                    filters["room_type"] = room
                    break
        
        if "price_max" not in filters:
            for pattern in PRICE_PATTERNS:
                match = pattern.search(query_lower)
                if match:
                    filters["price_max"] = float(match.group(1))
                    break
        
        if filters:
            formatted_results = self._apply_filters(formatted_results, filters)
        
        final_results = formatted_results[:limit]
        
        # Update cache
        if len(self._cache) >= self._cache_max_size:
            # Simple eviction: clear oldest (dictionary insertion order in 3.7+)
            first_key = next(iter(self._cache))
            del self._cache[first_key]
        
        self._cache[cache_key] = final_results
        
        return final_results
    
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
            product = result
            
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
            
            # Category filter (strict or loose)
            if "category" in filters:
                target_cat = filters["category"].lower()
                prod_cat = (product.get("category") or "").lower()
                prod_type = (product.get("type") or "").lower() # Sometimes stored as type
                
                # Check category field, type field, or tags
                found_cat = (
                    target_cat in prod_cat or
                    target_cat in prod_type or
                    any(target_cat in tag.lower() for tag in product.get("tags", [])) or
                    f"Category_{target_cat}" in [t.lower() for t in product.get("tags", [])]
                )
                if not found_cat:
                    continue
            
            # Color filter
            if "color" in filters:
                target_color = filters["color"].lower()
                # Check tags for "Color_Red" format or simple "Red"
                # Also check description for mentions of the color
                prod_tags = [t.lower() for t in product.get("tags", [])]
                prod_desc = (product.get("description") or "").lower()
                prod_title = (product.get("name") or "").lower()
                
                found_color = (
                    target_color in prod_tags or
                    f"color_{target_color}" in prod_tags or
                    f"colour_{target_color}" in prod_tags or
                    target_color in prod_title or  # Strong signal if in title
                    f" {target_color} " in f" {prod_desc} "  # Whole word match in desc
                )
                if not found_color:
                    continue

            # Material filter
            if "material" in filters:
                target_mat = filters["material"].lower()
                prod_tags = [t.lower() for t in product.get("tags", [])]
                prod_desc = (product.get("description") or "").lower()
                
                found_mat = (
                    target_mat in prod_tags or
                    f"material_{target_mat}" in prod_tags or
                    target_mat in prod_desc
                )
                if not found_mat:
                    continue
            
            # Style filter
            if "style" in filters:
                target_style = filters["style"].lower()
                prod_tags = [t.lower() for t in product.get("tags", [])]
                prod_desc = (product.get("description") or "").lower()
                
                found_style = (
                    target_style in prod_tags or
                    f"style_{target_style}" in prod_tags or
                    target_style in prod_desc
                )
                if not found_style:
                    continue
            
            # Room Type filter
            if "room_type" in filters:
                target_room = filters["room_type"].lower().replace("_", " ") # office_chair -> office chair
                prod_tags = [t.lower() for t in product.get("tags", [])]
                prod_desc = (product.get("description") or "").lower()
                
                found_room = (
                    target_room in prod_tags or
                    target_room.replace(" ", "_") in prod_tags or
                    target_room in prod_desc
                )
                if not found_room:
                    continue

            # Generic Tags filter (preserved)
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
    
    async def get_products_batch(self, skus: List[str]) -> List[Dict[str, Any]]:
        """
        Get multiple products by SKUs in batch.
        
        Args:
            skus: List of product SKUs
            
        Returns:
            List of product dictionaries
        """
        return await asyncio.to_thread(self.catalog.getProductsByIds, skus)
    
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
