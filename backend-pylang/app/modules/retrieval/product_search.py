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

# Subjective price term mappings (convert to actual price ranges)
SUBJECTIVE_PRICE_MAP = {
    'cheap': 200,
    'affordable': 300,
    'budget': 250,
    'inexpensive': 250,
    'expensive': 500,
    'premium': 800,
    'luxury': 1000,
    'high-end': 1000,
    'designer': 1200,
}

# Subjective size term mappings (for future dimension filtering)
SUBJECTIVE_SIZE_MAP = {
    'small': {'max_width': 24, 'max_depth': 24},
    'compact': {'max_width': 30, 'max_depth': 30},
    'tiny': {'max_width': 18, 'max_depth': 18},
    'large': {'min_width': 48},
    'spacious': {'min_width': 48},
    'huge': {'min_width': 60},
}

COLOR_KEYWORDS = ['black', 'white', 'red', 'green', 'blue', 'brown', 'grey', 'gray', 'yellow', 'orange', 'pink', 'purple', 'beige']
MATERIAL_KEYWORDS = ['wood', 'metal', 'leather', 'fabric', 'glass', 'plastic', 'steel']
ROOM_KEYWORDS = ['office', 'bedroom', 'living room', 'dining room']

class ProductSearcher:
    """
    High-level product search interface.
    Wraps CatalogIndexer with additional features.
    Optimized for catalogs with 2000+ products.
    """
    
    _cache = {}  # Simple in-memory cache
    _cache_max_size = 500  # Increased for large catalogs
    _cache_hits = 0
    _cache_misses = 0
    
    def __init__(self):
        from app.core.dependencies import get_catalog_indexer
        self.catalog = get_catalog_indexer()
    
    async def search(
        self,
        query: str,
        limit: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        preferences: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search products with optional filters and caching.
        """
        # Create cache key
        cache_key = f"{query}:{limit}:{str(filters)}:{str(preferences)}"
        if cache_key in self._cache:
            logger.info(f"[SEARCH] Cache hit for: {query}")
            return self._cache[cache_key]
        
        # Get raw search results from catalog (increased multiplier for large catalogs)
        search_limit = min(limit * 8, 100)  # Get more candidates but cap at 100
        results = await asyncio.to_thread(self.catalog.searchProducts, query, limit=search_limit)
        
        # Format results properly
        formatted_results = []
        for result in results:
            product_data = result.get("content", {})
            inventory_qty = product_data.get("inventory_quantity")
            stock_status = product_data.get("stock_status")
            available = product_data.get("available")
            
            # Determine in_stock based on multiple signals:
            # 1. Explicit stock_status from adapter
            # 2. available flag from Shopify
            # 3. inventory_quantity count
            if stock_status == "out_of_stock":
                in_stock = False
            elif stock_status == "in_stock":
                in_stock = True
            elif available == 0 or available is False:
                in_stock = False
            elif available == 1 or available is True:
                in_stock = True
            elif inventory_qty is not None and inventory_qty > 0:
                in_stock = True
            elif inventory_qty is not None and inventory_qty <= 0:
                in_stock = False
            else:
                # No inventory data - assume available (unmanaged inventory)
                in_stock = True
            formatted_product = {
                "id": product_data.get("sku", result.get("id", "")),
                "sku": product_data.get("sku", result.get("id", "")),
                "name": product_data.get("title", "Unknown Product"),
                "price": product_data.get("price", 0.00),
                "compare_at_price": product_data.get("compare_at_price"),
                "description": product_data.get("description", ""),
                "image_url": product_data.get("image_url", ""),
                "handle": product_data.get("handle", ""),
                "vendor": product_data.get("vendor", ""),
                "tags": product_data.get("tags", []),
                "currency": product_data.get("currency", "AUD"),
                "product_url": product_data.get("product_url", ""),
                "category": product_data.get("category", ""),
                "product_type": product_data.get("product_type", ""),
                "status": product_data.get("status", ""),
                "options": product_data.get("options", []),
                "variants": product_data.get("variants", []),
                "images": product_data.get("images", []),
                "available": product_data.get("available"),
                "inventory_managed": product_data.get("inventory_managed"),
                "barcode": product_data.get("barcode"),
                "score": result.get("score", 0),
                "inventory_quantity": product_data.get("inventory_quantity", 0),
                "in_stock": in_stock,
            }
            formatted_results.append(formatted_product)
        
        # Apply filters if provided - make a copy to avoid mutating caller's dict
        if filters is None:
            filters = {}
        else:
            filters = dict(filters)  # Create a copy to avoid mutation
        filters["query_text"] = query
            
        # AUTO-DETECT FILTERS from query
        query_lower = query.lower()
        
        if "color" not in filters:
            for color in COLOR_KEYWORDS:
                # More flexible color matching - check if color word appears anywhere
                if color in query_lower:
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
            # First, check for explicit price patterns
            for pattern in PRICE_PATTERNS:
                match = pattern.search(query_lower)
                if match:
                    filters["price_max"] = float(match.group(1))
                    break
            
            # If no explicit price, check for subjective price terms
            if "price_max" not in filters:
                for term, max_price in SUBJECTIVE_PRICE_MAP.items():
                    if re.search(r'\b' + term + r'\b', query_lower):
                        filters["price_max"] = max_price
                        logger.info(f"[SEARCH] Converted '{term}' to price_max={max_price}")
                        break
        
        # Track available colors before filtering (for "no color match" feedback)
        available_colors = set()
        requested_color = filters.get("color") if filters else None
        if requested_color:
            for product in formatted_results:
                # Extract colors from tags (may be list or JSON string)
                tags = product.get("tags", [])
                if isinstance(tags, str):
                    # Parse JSON string like '["Color_Black", "Color_White"]'
                    import json
                    try:
                        tags = json.loads(tags)
                    except:
                        tags = []
                
                for tag in tags:
                    tag_lower = tag.lower()
                    if tag_lower.startswith("color_"):
                        available_colors.add(tag_lower.replace("color_", "").title())
                    elif tag_lower in COLOR_KEYWORDS:
                        available_colors.add(tag_lower.title())
        
        if filters:
            formatted_results = self._apply_filters(formatted_results, filters)
        
        formatted_results = self._apply_query_ranking(formatted_results, query)

        if preferences:
            formatted_results = self._apply_preference_ranking(formatted_results, preferences)

        final_results = formatted_results[:limit]
        
        # Update cache
        if len(self._cache) >= self._cache_max_size:
            # Simple eviction: clear oldest (dictionary insertion order in 3.7+)
            first_key = next(iter(self._cache))
            del self._cache[first_key]
        
        self._cache[cache_key] = final_results
        
        # If color filter applied but no results, return available colors info
        if requested_color and len(final_results) == 0 and available_colors:
            return {
                "products": [],
                "total": 0,
                "requested_color": requested_color,
                "available_colors": sorted(list(available_colors)),
                "no_color_match": True
            }
        
        return final_results
    
    def _parse_tags(self, tags) -> List[str]:
        """Parse tags - handle both list and JSON string formats"""
        if isinstance(tags, list):
            return tags
        if isinstance(tags, str):
            import json
            try:
                return json.loads(tags)
            except:
                return []
        return []
    
    def _apply_filters(
        self, 
        results: List[Dict[str, Any]], 
        filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Apply filters to search results.
        Enhanced with room-aware category filtering.
        """
        filtered = []
        
        # Get room-to-category mapping if room_type is specified
        room_categories = None
        if "room_type" in filters:
            from app.modules.assistant.intent_detector import ROOM_CATEGORY_MAP
            room = filters["room_type"].lower().replace(" ", "_")
            room_categories = ROOM_CATEGORY_MAP.get(room, [])
        
        for result in results:
            # FIX: Use result directly (not nested under 'content')
            product = result
            query_text = (filters.get("query_text") or "").lower()
            
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
            
            # Parse tags once for all tag-based filters
            prod_tags = self._parse_tags(product.get("tags", []))
            prod_tags_lower = [t.lower() for t in prod_tags]
            prod_title = (product.get("name") or "").lower()
            prod_desc = (product.get("description") or "").lower()

            if query_text and not any(tok in query_text for tok in ["kid", "kids", "child", "children"]):
                if any(tok in prod_title or tok in prod_desc for tok in ["kid", "kids", "child", "children"]):
                    if any(tok in query_text for tok in ["office", "gaming", "desk", "table", "chair"]):
                        continue

            primary_types = [
                "chair", "desk", "table", "sofa", "bed", "shelf", "cabinet",
                "locker", "stool", "workstation"
            ]
            if query_text and any(t in query_text for t in primary_types):
                if not any(
                    t in prod_title or t in prod_desc or t in prod_tags_lower or t in (product.get("category") or "").lower()
                    for t in primary_types
                ):
                    continue
            
            # ENHANCED: Room Type + Category validation
            # If room_type specified, ensure product category is valid for that room
            if room_categories:
                prod_cat = (product.get("category") or "").lower()
                prod_type = (product.get("type") or "").lower()
                if filters.get("room_type") == "office":
                    if (
                        "kid" in prod_cat or
                        "kid" in prod_type or
                        "kid" in prod_title or
                        "kid" in prod_desc or
                        any("kid" in tag for tag in prod_tags_lower)
                    ):
                        continue
                
                # Check if product's category matches any valid room categories
                is_valid_for_room = False
                for valid_cat in room_categories:
                    valid_cat_lower = valid_cat.lower()
                    if (valid_cat_lower in prod_cat or 
                        valid_cat_lower in prod_type or
                        any(valid_cat_lower in tag for tag in prod_tags_lower)):
                        is_valid_for_room = True
                        break
                
                if not is_valid_for_room:
                    continue  # Skip products not valid for specified room
            
            # Categories list filter (for bundle context filtering)
            if "categories" in filters:
                allowed_cats = [c.lower() for c in filters["categories"]]
                prod_cat = (product.get("category") or "").lower()
                prod_type = (product.get("product_type") or "").lower()
                
                # Check if product category matches any allowed category
                found_in_allowed = any(
                    allowed in prod_cat or prod_cat in allowed or
                    allowed in prod_type or prod_type in allowed
                    for allowed in allowed_cats
                )
                if not found_in_allowed:
                    continue
            
            # Category filter (flexible matching)
            if "category" in filters:
                target_cat = filters["category"].lower()
                prod_cat = (product.get("category") or "").lower()
                prod_type = (product.get("type") or "").lower() # Sometimes stored as type
                prod_title = (product.get("name") or product.get("title") or "").lower()
                
                # Split target into words for flexible matching
                target_words = set(target_cat.replace("_", " ").split())
                cat_words = set(prod_cat.replace("_", " ").split())
                type_words = set(prod_type.replace("_", " ").split())
                
                # Check category field, type field, tags, OR title
                # More flexible: check if ANY significant word matches
                significant_words = target_words - {"home", "and", "the", "a", "for"}
                
                found_cat = (
                    # Substring match in either direction
                    target_cat in prod_cat or
                    prod_cat in target_cat or
                    target_cat in prod_type or
                    prod_type in target_cat or
                    # Word overlap (e.g., "furniture" in "home furniture" matches "living room furniture")
                    bool(significant_words & cat_words) or
                    bool(significant_words & type_words) or
                    # Check if product title contains the product type from query
                    any(w in prod_title for w in significant_words if len(w) > 3) or
                    # Tag-based check
                    any(target_cat in tag for tag in prod_tags_lower) or
                    f"category_{target_cat}" in prod_tags_lower
                )
                if not found_cat:
                    continue
            
            # Color filter
            if "color" in filters:
                target_color = filters["color"].lower()
                # Check tags for "Color_Red" format or simple "Red"
                # Also check description for mentions of the color
                prod_desc = (product.get("description") or "").lower()
                prod_title = (product.get("name") or "").lower()
                
                # More flexible matching - check if color appears anywhere
                # FIX: Check if target_color is a SUBSTRING of any tag (not exact match in list)
                # e.g., "grey" should match "color_dark grey", "color_grey", "grey"
                found_in_tags = any(target_color in tag for tag in prod_tags_lower)
                
                found_color = (
                    found_in_tags or  # "grey" in any of ["color_dark grey", "color_grey", etc.]
                    target_color in prod_title or  # Strong signal if in title
                    target_color in prod_desc  # More flexible desc matching
                )
                if not found_color:
                    continue
            
            # Material filter
            if "material" in filters:
                target_mat = filters["material"].lower()
                prod_desc = (product.get("description") or "").lower()
                
                found_mat = (
                    target_mat in prod_tags_lower or
                    f"material_{target_mat}" in prod_tags_lower or
                    target_mat in prod_desc
                )
                if not found_mat:
                    continue
            
            # Style filter
            if "style" in filters:
                target_style = filters["style"].lower()
                prod_desc = (product.get("description") or "").lower()
                
                found_style = (
                    target_style in prod_tags_lower or
                    f"style_{target_style}" in prod_tags_lower or
                    target_style in prod_desc
                )
                if not found_style:
                    continue

            # Generic Tags filter (preserved)
            if "tags" in filters:
                product_tags_set = set(prod_tags_lower)
                filter_tags = set(tag.lower() for tag in filters["tags"])
                if not filter_tags.intersection(product_tags_set):
                    continue
            
            # In Stock filter
            if "in_stock" in filters:
                is_in_stock = product.get("in_stock", True)
                if is_in_stock != filters["in_stock"]:
                    continue
            
            # Filter out invalid $0 or missing price products
            # These are likely data errors or placeholder products
            price = product.get("price", 0)
            if price is None or price <= 0:
                continue
            
            filtered.append(result)
        
        return filtered

    def _apply_query_ranking(self, results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        if not results:
            return results

        query_lower = query.lower()
        stopwords = {"the", "a", "an", "and", "or", "for", "with", "to", "in", "of", "my"}
        tokens = [t for t in re.split(r"\W+", query_lower) if t and t not in stopwords]

        def score_product(product: Dict[str, Any]) -> float:
            title = (product.get("name") or "").lower()
            desc = (product.get("description") or "").lower()
            tags = self._parse_tags(product.get("tags", []))
            tags_lower = [t.lower() for t in tags]
            category = (product.get("category") or "").lower()

            score = 0.0
            for token in tokens:
                if token in title:
                    score += 1.5
                if token in category:
                    score += 1.2
                if token in tags_lower:
                    score += 1.0
                if token in desc:
                    score += 0.4
            return score

        for product in results:
            product["query_score"] = score_product(product)

        return sorted(
            results,
            key=lambda p: (p.get("query_score", 0), p.get("score", 0)),
            reverse=True
        )

    def _apply_preference_ranking(
        self,
        results: List[Dict[str, Any]],
        preferences: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        if not results:
            return results

        def score_product(product: Dict[str, Any]) -> float:
            score = float(product.get("query_score") or 0.0)
            title = (product.get("name") or "").lower()
            desc = (product.get("description") or "").lower()
            tags = self._parse_tags(product.get("tags", []))
            tags_lower = [t.lower() for t in tags]

            for key in ["color", "material", "style", "descriptor"]:
                pref = preferences.get(key)
                if not pref:
                    continue
                pref_lower = str(pref).lower()
                if pref_lower in title or pref_lower in desc or pref_lower in tags_lower:
                    score += 1.5

            room_type = preferences.get("room_type")
            if room_type:
                room_lower = str(room_type).lower()
                if room_lower in title or room_lower in desc or room_lower in tags_lower:
                    score += 1.0

            size_pref = preferences.get("size")
            if size_pref:
                size_lower = str(size_pref).lower()
                if size_lower in title or size_lower in desc or size_lower in tags_lower:
                    score += 0.8

            price_max = preferences.get("price_max")
            price = product.get("price")
            if price_max and price is not None:
                try:
                    price = float(price)
                    if price <= price_max:
                        score += 0.5 + (price / price_max) * 0.5
                except (TypeError, ValueError):
                    pass

            liked_categories = preferences.get("liked_categories") or []
            if liked_categories:
                prod_category = (product.get("category") or "").lower()
                if any(cat.lower() in prod_category for cat in liked_categories):
                    score += 1.0

            liked_vendors = preferences.get("liked_vendors") or []
            if liked_vendors:
                prod_vendor = (product.get("vendor") or "").lower()
                if any(v.lower() == prod_vendor for v in liked_vendors):
                    score += 0.5

            return score

        return sorted(
            results,
            key=lambda p: (score_product(p), p.get("score", 0)),
            reverse=True
        )
    
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
