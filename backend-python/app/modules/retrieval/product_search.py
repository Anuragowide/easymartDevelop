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
from app.modules.observability.logging_config import get_logger

logger = get_logger(__name__)


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
        filters: Optional[Dict[str, Any]] = None,
        sort: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for products based on a query and optional filters.
        """
        # 1. Broad search using CatalogIndexer
        # We fetch more results than limit to allow for post-filtering
        results = await asyncio.to_thread(self.catalog.searchProducts, query, limit=limit * 10)
        
        # 2. Format results
        formatted_results = []
        for res in results:
            product = res.get("product", {})
            score = res.get("score", 0)
            
            # Extract essential fields
            formatted_results.append({
                "id": str(product.get("id", "")),
                "sku": product.get("sku", ""),
                "name": product.get("name", ""),
                "price": float(product.get("price", 0)),
                "category": product.get("category", ""),
                "description": product.get("description", ""),
                "image_url": product.get("image_url", ""),
                "attributes": product.get("attributes", {}),
                "score": score
            })
            
        # 3. Apply filters if provided
        if filters:
            formatted_results = self._apply_filters(formatted_results, filters)
        
        # 4. Apply sorting if provided
        if sort == "price_asc":
            formatted_results.sort(key=lambda x: x.get("price", 0))
        elif sort == "price_desc":
            formatted_results.sort(key=lambda x: x.get("price", 0), reverse=True)
        elif sort == "relevance":
            # Already sorted by score from CatalogIndexer, but let's be explicit
            formatted_results.sort(key=lambda x: x.get("score", 0), reverse=True)
            
        # 5. Return top N results
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
