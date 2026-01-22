"""
Bundle planner for multi-item budget requests.
"""

from dataclasses import dataclass
import re
from typing import Dict, Any, List, Optional, Tuple

from app.modules.observability.logging_config import get_logger
from app.modules.retrieval.product_search import ProductSearcher
from app.modules.assistant.category_intelligence import get_category_intelligence

logger = get_logger(__name__)


@dataclass(frozen=True)
class BundleItem:
    item_type: str
    quantity: int


ITEM_ALIASES = {
    "chairs": "chair",
    "chair": "chair",
    "tables": "table",
    "table": "table",
    "desks": "desk",
    "desk": "desk",
    "sofas": "sofa",
    "sofa": "sofa",
    "couches": "sofa",
    "couch": "sofa",
    "beds": "bed",
    "bed": "bed",
    "stools": "stool",
    "stool": "stool",
    "lockers": "locker",
    "locker": "locker",
    "cabinets": "cabinet",
    "cabinet": "cabinet",
    "shelves": "shelf",
    "shelf": "shelf",
}

ITEM_PATTERN = re.compile(
    r'(\d+)\s*(?:x\s*)?(chairs?|tables?|desks?|sofas?|couches?|beds?|stools?|lockers?|cabinets?|shelves?)',
    re.IGNORECASE,
)

BUDGET_PATTERNS = [
    re.compile(r'under\s+\$?(\d+(?:\.\d+)?)', re.IGNORECASE),
    re.compile(r'budget\s+\$?(\d+(?:\.\d+)?)', re.IGNORECASE),
    re.compile(r'total\s+\$?(\d+(?:\.\d+)?)', re.IGNORECASE),
    re.compile(r'\$?(\d+(?:\.\d+)?)\s+budget', re.IGNORECASE),
]

COLOR_KEYWORDS = [
    "black", "white", "red", "green", "blue", "brown", "grey", "gray",
    "yellow", "orange", "pink", "purple", "beige",
]
MATERIAL_KEYWORDS = ["wood", "metal", "leather", "fabric", "glass", "plastic", "steel"]
ROOM_KEYWORDS = ["office", "bedroom", "living room", "dining room", "outdoor", "gym"]
DESCRIPTOR_KEYWORDS = ["l shape", "l-shaped", "lshape", "corner"]


def parse_bundle_request(text: str) -> Tuple[List[BundleItem], Dict[str, Any]]:
    """Parse bundle request using intelligent category detection."""
    items: List[BundleItem] = []
    extracted: Dict[str, Any] = {}
    
    # Use CategoryIntelligence for smart context detection
    cat_intel = get_category_intelligence()
    bundle_context = cat_intel.get_bundle_context(text)

    for match in ITEM_PATTERN.finditer(text):
        qty = int(match.group(1))
        raw_type = match.group(2).lower()
        item_type = ITEM_ALIASES.get(raw_type, raw_type.rstrip("s"))
        items.append(BundleItem(item_type=item_type, quantity=qty))

    for pattern in BUDGET_PATTERNS:
        match = pattern.search(text)
        if match:
            extracted["budget_total"] = float(match.group(1))
            break

    text_lower = text.lower()
    
    # Use intelligent context detection from CategoryIntelligence
    if bundle_context.get("bundle_context"):
        extracted["bundle_context"] = bundle_context["bundle_context"]
        extracted["allowed_categories"] = bundle_context.get("allowed_categories", [])
        extracted["detected_items"] = bundle_context.get("detected_items", [])
        logger.info(f"[BUNDLE] Detected context: {bundle_context['bundle_context']}, "
                   f"categories: {len(extracted['allowed_categories'])}, "
                   f"items: {bundle_context.get('detected_items', [])}")
    
    for color in COLOR_KEYWORDS:
        if color in text_lower:
            extracted["color"] = color
            break

    for material in MATERIAL_KEYWORDS:
        if material in text_lower:
            extracted["material"] = material
            break

    for room in ROOM_KEYWORDS:
        if room in text_lower:
            extracted["room_type"] = room
            break

    for descriptor in DESCRIPTOR_KEYWORDS:
        if descriptor in text_lower:
            extracted["descriptor"] = "l shape"
            break

    return items, extracted


class BundlePlanner:
    def __init__(self, product_searcher: Optional[ProductSearcher] = None):
        self.product_searcher = product_searcher or ProductSearcher()
        self.category_intel = get_category_intelligence()

    async def build_bundle(
        self,
        request: str,
        items: Optional[List[Dict[str, Any]]] = None,
        budget_total: Optional[float] = None,
        color: Optional[str] = None,
        material: Optional[str] = None,
        room_type: Optional[str] = None,
        descriptor: Optional[str] = None,
        strategy: Optional[str] = None,
        allowed_categories: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        parsed_items: List[BundleItem] = []
        bundle_context = None

        if items:
            for item in items:
                if hasattr(item, "model_dump"):
                    item = item.model_dump()
                item_type = item.get("type") or item.get("item_type")
                quantity = int(item.get("quantity", 1))
                if item_type:
                    parsed_items.append(BundleItem(item_type=item_type, quantity=quantity))

        if not parsed_items:
            parsed_items, parsed_meta = parse_bundle_request(request)
            budget_total = budget_total or parsed_meta.get("budget_total")
            color = color or parsed_meta.get("color")
            material = material or parsed_meta.get("material")
            room_type = room_type or parsed_meta.get("room_type")
            descriptor = descriptor or parsed_meta.get("descriptor")
            bundle_context = parsed_meta.get("bundle_context")
            allowed_categories = allowed_categories or parsed_meta.get("allowed_categories")

        if not parsed_items:
            return {
                "error": "No bundle items found in request",
                "bundle": {"items": [], "feasible": False},
                "products": [],
            }

        total_qty = sum(item.quantity for item in parsed_items)
        per_unit_budget = (budget_total / total_qty) if budget_total else None
        strategy = (strategy or "closest_to_budget").lower()

        base_filters: Dict[str, Any] = {}
        if color:
            base_filters["color"] = color
        if material:
            base_filters["material"] = material
        if room_type:
            base_filters["room_type"] = room_type
        if allowed_categories:
            base_filters["categories"] = allowed_categories
        base_filters["in_stock"] = True
        
        if bundle_context:
            logger.info(f"[BUNDLE] Detected context: {bundle_context}, filtering to categories: {allowed_categories}")

        bundle_items = []
        products_for_cards = []
        missing_items = []
        total_estimate = 0.0
        used_fallback = False
        min_total_estimate = 0.0
        candidates_by_item: List[List[Dict[str, Any]]] = []

        for item in parsed_items:
            filters = dict(base_filters)
            if per_unit_budget:
                filters["price_max"] = per_unit_budget

            query = item.item_type
            if room_type:
                query = f"{room_type} {query}"
            if descriptor and item.item_type in ["table", "desk"]:
                query = f"{descriptor} {item.item_type}"
            results = await self.product_searcher.search(query=query, limit=10, filters=filters)
            if isinstance(results, dict) and results.get("no_color_match"):
                results = []

            if not results and per_unit_budget:
                used_fallback = True
                results = await self.product_searcher.search(query=query, limit=10, filters=base_filters)
                if isinstance(results, dict) and results.get("no_color_match"):
                    results = []

            results = sorted(results or [], key=lambda p: p.get("price", 0))
            candidates_by_item.append(results)

            if not results:
                missing_items.append({"type": item.item_type, "quantity": item.quantity})
                continue

            min_total_estimate += float(results[0].get("price", 0.0)) * item.quantity

        chosen_indexes = [0 for _ in parsed_items]
        if budget_total is not None and strategy == "closest_to_budget":
            total_estimate = 0.0
            for idx, item in enumerate(parsed_items):
                results = candidates_by_item[idx] if idx < len(candidates_by_item) else []
                if not results:
                    continue
                total_estimate += float(results[0].get("price", 0.0)) * item.quantity

            while True:
                best_upgrade = None
                for idx, item in enumerate(parsed_items):
                    results = candidates_by_item[idx] if idx < len(candidates_by_item) else []
                    current_idx = chosen_indexes[idx]
                    if not results or current_idx + 1 >= len(results):
                        continue

                    current_price = float(results[current_idx].get("price", 0.0))
                    next_price = float(results[current_idx + 1].get("price", 0.0))
                    delta = (next_price - current_price) * item.quantity
                    if total_estimate + delta <= budget_total:
                        if best_upgrade is None or delta > best_upgrade["delta"]:
                            best_upgrade = {"idx": idx, "delta": delta}

                if not best_upgrade:
                    break

                chosen_indexes[best_upgrade["idx"]] += 1
                total_estimate += best_upgrade["delta"]
        else:
            total_estimate = 0.0

        total_estimate = 0.0
        for idx, item in enumerate(parsed_items):
            results = candidates_by_item[idx] if idx < len(candidates_by_item) else []
            if not results:
                continue
            chosen = results[chosen_indexes[idx]]
            unit_price = float(chosen.get("price", 0.0))
            line_total = unit_price * item.quantity
            total_estimate += line_total

            bundle_items.append({
                "type": item.item_type,
                "quantity": item.quantity,
                "product_id": chosen.get("sku") or chosen.get("id"),
                "name": chosen.get("name") or chosen.get("title"),
                "unit_price": unit_price,
                "line_total": line_total,
                "product_url": chosen.get("product_url"),
                "image_url": chosen.get("image_url"),
            })
            products_for_cards.append(chosen)

        feasible = True
        budget_shortfall = 0.0
        if budget_total is not None and total_estimate > budget_total:
            feasible = False
            budget_shortfall = total_estimate - budget_total

        remaining_budget = None
        if budget_total is not None:
            remaining_budget = budget_total - total_estimate

        return {
            "bundle": {
                "items": bundle_items,
                "requested_items": [{"type": i.item_type, "quantity": i.quantity} for i in parsed_items],
                "missing_items": missing_items,
                "budget_total": budget_total,
                "total_estimate": total_estimate,
                "min_total_estimate": min_total_estimate,
                "budget_shortfall": budget_shortfall,
                "remaining_budget": remaining_budget,
                "per_unit_budget": per_unit_budget,
                "feasible": feasible,
                "used_fallback_search": used_fallback,
            },
            "products": products_for_cards,
        }
