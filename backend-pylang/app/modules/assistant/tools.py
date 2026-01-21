"""
LangChain Tools for Easymart Assistant
"""

import asyncio
import logging
import re
from contextvars import ContextVar
from typing import Dict, Any, List, Optional

import httpx
from pydantic import BaseModel, Field
from langchain.tools import tool

from app.core.config import get_settings
from app.modules.assistant.session_store import get_session_store
from app.modules.retrieval.product_search import ProductSearcher
from app.modules.retrieval.spec_search import SpecSearcher
from app.modules.assistant.prompts import POLICIES, STORE_INFO, get_policy_text, get_contact_text
from app.modules.assistant.bundle_planner import BundlePlanner

logger = logging.getLogger(__name__)

CURRENT_SESSION_ID: ContextVar[Optional[str]] = ContextVar("CURRENT_SESSION_ID", default=None)


class SearchProductsArgs(BaseModel):
    query: str = Field(..., description="Search query or keywords")
    category: Optional[str] = Field(default=None, description="Category filter")
    material: Optional[str] = Field(default=None, description="Material filter")
    style: Optional[str] = Field(default=None, description="Style filter")
    room_type: Optional[str] = Field(default=None, description="Room type filter")
    color: Optional[str] = Field(default=None, description="Color filter")
    price_max: Optional[float] = Field(default=None, description="Maximum price in AUD")
    sort_by: Optional[str] = Field(default="relevance", description="Sort order")
    limit: int = Field(default=5, description="Maximum results to return")


class ProductSpecsArgs(BaseModel):
    product_id: str = Field(..., description="Product SKU or ID")
    question: Optional[str] = Field(default=None, description="Question about the product")


class AvailabilityArgs(BaseModel):
    product_id: str = Field(..., description="Product SKU or ID")


class CompareProductsArgs(BaseModel):
    product_ids: List[str] = Field(..., description="List of 2-4 product IDs")


class UpdateCartArgs(BaseModel):
    action: str = Field(..., description="Cart action: add, remove, set, update_quantity, view, clear")
    product_id: Optional[str] = Field(default=None, description="Product SKU")
    quantity: Optional[int] = Field(default=1, description="Quantity to add")
    session_id: Optional[str] = Field(default=None, description="Session ID")


class PolicyArgs(BaseModel):
    policy_type: str = Field(..., description="returns, shipping, payment, warranty")


class ContactArgs(BaseModel):
    info_type: str = Field(default="all", description="all, phone, email, hours, location, chat")


class ShippingArgs(BaseModel):
    order_total: float = Field(..., description="Order subtotal in AUD")
    postcode: Optional[str] = Field(default=None, description="Australian postcode")


class FindSimilarArgs(BaseModel):
    product_id: str = Field(..., description="Product SKU or ID")
    exclude_ids: Optional[List[str]] = Field(default=None, description="Exclude product IDs")
    limit: int = Field(default=5, description="Maximum results to return")


class ProductFitArgs(BaseModel):
    product_id: str = Field(..., description="Product SKU or ID")
    space_length: float = Field(..., description="Space length in cm")
    space_width: float = Field(..., description="Space width in cm")


class BundleItemArgs(BaseModel):
    type: str = Field(..., description="Item type (chair, table, desk, etc.)")
    quantity: int = Field(..., description="Quantity requested")


class BuildBundleArgs(BaseModel):
    request: str = Field(..., description="Bundle request text (e.g., '5 tables and 6 chairs under 2000')")
    items: Optional[List[BundleItemArgs]] = Field(default=None, description="Structured item list")
    budget_total: Optional[float] = Field(default=None, description="Total budget in AUD")
    color: Optional[str] = Field(default=None, description="Color preference")
    material: Optional[str] = Field(default=None, description="Material preference")
    room_type: Optional[str] = Field(default=None, description="Room context")
    descriptor: Optional[str] = Field(default=None, description="Descriptor like 'l shape', 'corner'")
    strategy: Optional[str] = Field(default="closest_to_budget", description="cheapest | closest_to_budget")


class CheapestBundleArgs(BaseModel):
    request: str = Field(..., description="Bundle request text")
    items: Optional[List[BundleItemArgs]] = Field(default=None, description="Structured item list")
    color: Optional[str] = Field(default=None, description="Color preference")
    material: Optional[str] = Field(default=None, description="Material preference")
    room_type: Optional[str] = Field(default=None, description="Room context")
    descriptor: Optional[str] = Field(default=None, description="Descriptor like 'l shape', 'corner'")


class SmallSpaceSearchArgs(BaseModel):
    category: str = Field(default="table", description="Product type to search (table, desk, etc.)")
    space_length: float = Field(..., description="Available length in cm")
    space_width: float = Field(..., description="Available width in cm")
    limit: int = Field(default=5, description="Maximum results to return")


class EasymartAssistantTools:
    def __init__(self):
        self.product_searcher = ProductSearcher()
        self.spec_searcher = SpecSearcher()
        self.settings = get_settings()
        self.bundle_planner = BundlePlanner(self.product_searcher)

    def _get_base_product_name(self, name: str) -> str:
        """
        Extract base product name by removing quantity/size/variant variations.
        E.g., '200pcs Puppy Dog Training Pads' -> 'puppy dog training pads'
        E.g., 'Dog Bed Large Orthopedic' -> 'dog bed'
        Used for deduplicating similar products in search results.
        """
        name_lower = name.lower()
        
        # Remove quantity patterns like "200pcs", "400 pcs", "1 x", "2x", etc.
        name_lower = re.sub(r'\b\d+\s*(?:pcs?|pieces?|pack|count|x|units?)\b', '', name_lower)
        
        # Remove size patterns like "small", "medium", "large", "xl", "xxl", etc.
        name_lower = re.sub(r'\b(?:x?x?small|x?x?large|medium|mini|big|huge|tiny|xl|xxl|xs|xxs)\b', '', name_lower)
        
        # Remove standalone size letters only when they appear as size indicators
        name_lower = re.sub(r'\b[sml]\b', '', name_lower)
        
        # Remove dimension patterns like "60x90cm", "100cm", etc.
        name_lower = re.sub(r'\b\d+\s*x\s*\d+\s*(?:cm|mm|m|inch|in|ft)?\b', '', name_lower)
        name_lower = re.sub(r'\b\d+\s*(?:cm|mm|m|inch|in|ft)\b', '', name_lower)
        
        # Remove variant descriptors that don't change the core product type
        name_lower = re.sub(r'\b(?:orthopedic|washable|waterproof|foldable|portable|deluxe|premium|basic|standard|pro|plus)\b', '', name_lower)
        
        # Remove color patterns
        name_lower = re.sub(r'\b(?:black|white|red|blue|green|yellow|pink|purple|grey|gray|brown|beige|orange|navy|cream)\b', '', name_lower)
        
        # Normalize whitespace
        name_lower = re.sub(r'\s+', ' ', name_lower).strip()
        
        return name_lower

    def _resolve_product_id_reference(self, session, product_id: str) -> Optional[str]:
        """
        Resolve a product_id that might be a reference (like "2", "3", "option 1") 
        to an actual product SKU from the session's last shown products.
        
        This is CRITICAL for cart operations where the LLM might pass numeric
        references instead of actual SKUs.
        
        Args:
            session: The user's session containing last_shown_products
            product_id: The product_id passed by the LLM (could be "2", "option 1", or actual SKU)
        
        Returns:
            Resolved product SKU if found, otherwise the original product_id
        """
        if not product_id:
            return product_id
        
        product_id_str = str(product_id).strip()
        
        # Check if this looks like a product reference (numeric or "option X")
        is_numeric_ref = product_id_str.isdigit()
        is_option_ref = re.match(r'^(?:option|item|product|choice|number)\s*(\d+)$', product_id_str, re.IGNORECASE)
        is_ordinal_ref = product_id_str.lower() in ['first', 'second', 'third', 'fourth', 'fifth', '1st', '2nd', '3rd', '4th', '5th']
        
        if not (is_numeric_ref or is_option_ref or is_ordinal_ref):
            # Doesn't look like a reference, return as-is (it's probably a real SKU)
            return product_id
        
        # Try to resolve using session's last shown products
        if not session or not session.last_shown_products:
            logger.warning(f"Cannot resolve product reference '{product_id}': No products in session")
            return product_id
        
        # Resolve the reference
        resolved = session.resolve_product_reference(product_id_str, "index")
        
        if resolved:
            # Double-check: find the product to get its details
            for product in session.last_shown_products:
                pid = product.get("id") or product.get("sku") or product.get("product_id")
                if pid == resolved:
                    logger.info(f"Resolved product reference '{product_id}' to SKU '{resolved}' ({product.get('name', 'Unknown')})")
                    return resolved
        
        logger.warning(f"Could not resolve product reference '{product_id}' to a valid SKU")
        return product_id

    async def search_products(
        self,
        query: str,
        category: Optional[str] = None,
        material: Optional[str] = None,
        style: Optional[str] = None,
        room_type: Optional[str] = None,
        color: Optional[str] = None,
        price_max: Optional[float] = None,
        sort_by: Optional[str] = "relevance",
        limit: int = 5
    ) -> Dict[str, Any]:
        filters = {}
        if category:
            filters["category"] = category
        if material:
            filters["material"] = material
        if style:
            filters["style"] = style
        if room_type:
            filters["room_type"] = room_type
        if color:
            filters["color"] = color
        if price_max:
            filters["price_max"] = price_max
        if "in_stock" not in filters:
            filters["in_stock"] = True

        session_store = get_session_store()
        session_id = CURRENT_SESSION_ID.get()
        session = session_store.get_or_create_session(session_id) if session_id else None
        brief = session.metadata.get("shopping_brief") if session else None

        if brief:
            for key in ["category", "material", "style", "room_type", "color", "price_max", "descriptor", "size"]:
                if key not in filters and brief.get(key):
                    filters[key] = brief[key]

        preferences = dict(brief) if brief else {}
        if session:
            preferences["liked_categories"] = session.metadata.get("liked_categories", [])
            preferences["liked_vendors"] = session.metadata.get("liked_vendors", [])

        results = await self.product_searcher.search(
            query=query,
            filters=filters,
            limit=min(limit, 10),
            preferences=preferences
        )

        # Track if we're showing out-of-stock items
        showing_out_of_stock = False
        
        # Only relax in_stock filter if we got ZERO results
        if not results and filters.get("in_stock"):
            relaxed = dict(filters)
            relaxed.pop("in_stock", None)
            results = await self.product_searcher.search(
                query=query,
                filters=relaxed,
                limit=min(limit, 10),
                preferences=preferences
            )
            if results:
                # We're now showing out-of-stock items
                showing_out_of_stock = True

        # If still no results and category filter was applied, try without category
        if not results and "category" in filters:
            relaxed = dict(filters)
            relaxed.pop("category", None)
            results = await self.product_searcher.search(
                query=query,
                filters=relaxed,
                limit=min(limit, 10),
                preferences=preferences
            )

        # If we have results but fewer than requested, try relaxing category to get more
        if results and isinstance(results, list) and len(results) < limit and "category" in filters:
            relaxed = dict(filters)
            relaxed.pop("category", None)
            results = await self.product_searcher.search(
                query=query,
                filters=relaxed,
                limit=min(limit, 10),
                preferences=preferences
            )

        if isinstance(results, dict) and results.get("no_color_match"):
            return results

        if sort_by == "price_low":
            results.sort(key=lambda x: x.get("price", 0))
        elif sort_by == "price_high":
            results.sort(key=lambda x: x.get("price", 0), reverse=True)

        formatted = []
        seen_base_names = set()
        for idx, product in enumerate(results):
            if not product.get("name") or product.get("name").startswith("product_"):
                product["name"] = product.get("title") or product.get("description", f"Product {idx + 1}")
            product["id"] = product.get("sku") or product.get("id")
            product["price"] = product.get("price", 0.0)
            
            # Deduplicate: Skip products with very similar names (e.g., 200pcs vs 400pcs of same item)
            base_name = self._get_base_product_name(product.get("name", ""))
            if base_name in seen_base_names:
                continue  # Skip duplicate
            seen_base_names.add(base_name)
            
            formatted.append(product)

        # If in_stock filter was requested, filter out out-of-stock items from results
        # (The catalog search may return mixed results even with in_stock=True)
        if filters.get("in_stock") and not showing_out_of_stock:
            in_stock_products = [p for p in formatted if p.get("inventory_quantity", 0) > 0]
            if in_stock_products:
                # We have in-stock items, so only show those
                formatted = in_stock_products
            # Otherwise keep all results (even if out of stock)

        if session:
            session.update_shown_products(formatted)
            session.metadata["last_search_filters"] = filters

        result = {
            "products": formatted,
            "total": len(formatted),
            "showing": len(formatted),
            "sort_applied": sort_by
        }
        
        # Add message based on what we're showing
        if showing_out_of_stock and formatted:
            result["message"] = "Note: These items may be out of stock."
            result["showing_out_of_stock"] = True
        elif formatted and filters.get("in_stock"):
            # Explicitly state we found in-stock items
            result["message"] = f"Found {len(formatted)} in-stock items matching your search."
        
        return result

    async def get_product_specs(self, product_id: str, question: Optional[str] = None) -> Dict[str, Any]:
        product = await self.product_searcher.get_product(product_id)
        if not product:
            return {"error": f"Product '{product_id}' not found", "product_id": product_id}

        if not product.get("name"):
            product["name"] = product.get("title") or product.get("handle", "").replace("-", " ").title() or "Unknown Product"

        specs_list = await self.spec_searcher.get_specs_for_product(product_id)
        answer = None
        if question and specs_list:
            answer = await self.spec_searcher.answer_question(question=question, sku=product_id)

        # Extract color options from tags if present
        available_colors = []
        tags = product.get("tags", [])
        if isinstance(tags, str):
            try:
                import json
                tags = json.loads(tags)
            except Exception:
                tags = []
        for tag in tags:
            tag_lower = str(tag).lower()
            if tag_lower.startswith("color_") or tag_lower.startswith("colour_"):
                available_colors.append(tag_lower.split("_", 1)[1].title())
        available_colors = sorted(list(set(available_colors)))

        options = product.get("options") or []
        if isinstance(options, str):
            try:
                import json
                options = json.loads(options)
            except Exception:
                options = []
        for opt in options:
            if not isinstance(opt, dict):
                continue
            opt_name = str(opt.get("name", "")).lower()
            opt_values = opt.get("values") or []
            if opt_name in ["color", "colour"] and opt_values:
                available_colors.extend([str(v).title() for v in opt_values])
        available_colors = sorted(list(set(available_colors)))

        if not specs_list:
            return {
                "product_id": product_id,
                "product_name": product["name"],
                "price": product.get("price"),
                "description": product.get("description", ""),
                "specs": {"Available Colors": ", ".join(available_colors)} if available_colors else {},
                "available_colors": available_colors if available_colors else None,
                "message": "Detailed specifications not available. Basic product information provided above.",
                "answer": answer
            }

        formatted_specs = {}
        for spec in specs_list:
            section = spec.get("section", "General")
            formatted_specs[section] = spec.get("spec_text", "")

        if available_colors:
            formatted_specs.setdefault("Available Colors", ", ".join(available_colors))

        return {
            "product_id": product_id,
            "product_name": product["name"],
            "price": product.get("price"),
            "specs": formatted_specs,
            "available_colors": available_colors if available_colors else None,
            "answer": answer,
            "estimated_delivery": "5-10 business days"
        }

    async def check_availability(self, product_id: str) -> Dict[str, Any]:
        product = await self.product_searcher.get_product(product_id)
        if not product:
            return {"error": f"Product '{product_id}' not found", "product_id": product_id}

        qty = product.get("inventory_quantity", 0) or 0
        return {
            "product_id": product_id,
            "in_stock": qty > 0,
            "quantity_available": qty,
            "estimated_delivery": "5-10 business days" if qty > 0 else "Out of stock"
        }

    async def compare_products(self, product_ids: List[str]) -> Dict[str, Any]:
        products = await self.product_searcher.get_products_batch(product_ids)
        if not products:
            return {"error": "No products found for comparison"}

        prices = [p.get("price") for p in products if p.get("price") is not None]
        price_range = f"${min(prices):.2f} - ${max(prices):.2f} AUD" if prices else "N/A"

        return {
            "products": products,
            "comparison": {
                "price_range": price_range,
                "count": len(products)
            }
        }

    async def update_cart(
        self,
        action: str,
        product_id: Optional[str] = None,
        quantity: Optional[int] = None,
        session_id: Optional[str] = None,
        skip_sync: bool = False,
        product_snapshot: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        action = (action or "").lower()
        normalized_action = "set" if action in ["update_quantity", "set"] else action
        session_store = get_session_store()
        session_id = session_id or CURRENT_SESSION_ID.get()
        session = session_store.get_or_create_session(session_id)

        # CRITICAL FIX: Resolve product references like "2", "3", "option 1" to actual SKUs
        # This handles cases where LLM passes numeric references instead of real product IDs
        if product_id:
            resolved_product_id = self._resolve_product_id_reference(session, product_id)
            if resolved_product_id and resolved_product_id != product_id:
                logger.info(f"Resolved product reference '{product_id}' -> '{resolved_product_id}'")
                product_id = resolved_product_id

        async def _get_cart_state():
            cart_details = []
            total_price = 0.0

            if not session.cart_items:
                return {"items": [], "item_count": 0, "total": 0.0}

            pids = [item["product_id"] for item in session.cart_items]
            products_list = await self.product_searcher.get_products_batch(pids)
            products_map = {p.get("sku"): p for p in products_list if p.get("sku")}

            for item in session.cart_items:
                pid = item["product_id"]
                product = products_map.get(pid)
                if product:
                    price = float(product.get("price", 0.0))
                    qty = item["quantity"]
                    item_total = price * qty
                    total_price += item_total
                    name = product.get("title") or product.get("name") or pid
                    cart_details.append({
                        "product_id": pid,
                        "id": pid,
                        "title": name,
                        "name": name,
                        "price": price,
                        "image": product.get("image_url", ""),
                        "quantity": qty,
                        "item_total": item_total,
                        "added_at": item.get("added_at")
                    })
                else:
                    price = float(item.get("price") or 0.0)
                    qty = item.get("quantity", 1)
                    cart_details.append({
                        "product_id": pid,
                        "id": pid,
                        "title": item.get("name") or pid or "Unknown Product",
                        "quantity": qty,
                        "price": price,
                        "image": "",
                        "item_total": price * qty
                    })

            return {
                "items": cart_details,
                "item_count": len(cart_details),
                "total": total_price
            }

        async def _sync_with_node(action_val, pid=None, qty=None):
            if skip_sync:
                return None
            try:
                async with httpx.AsyncClient() as client:
                    payload = {
                        "action": action_val,
                        "session_id": session_id,
                        "from_assistant": True
                    }
                    if pid:
                        payload["product_id"] = pid
                    if qty is not None:
                        payload["quantity"] = qty
                    response = await client.post(
                        f"{self.settings.NODE_BACKEND_URL}/api/cart/add",
                        json=payload,
                        timeout=self.settings.API_TIMEOUT
                    )
                    if response.status_code == 200:
                        return response.json()
            except Exception as sync_e:
                logger.error(f"Cart sync failed: {sync_e}")
            return None

        if normalized_action == "view":
            cart_state = await _get_cart_state()
            return {
                "action": "view",
                "success": True,
                "cart": cart_state,
                "message": f"Your cart has {cart_state['item_count']} items totaling ${cart_state['total']:.2f}" if cart_state["items"] else "Your cart is currently empty."
            }

        if normalized_action == "clear":
            session.clear_cart()
            if not skip_sync:
                await _sync_with_node("clear")
            session.metadata["last_cart_action"] = {"type": "clear_cart"}
            return {
                "action": "clear",
                "success": True,
                "message": "Your cart has been emptied.",
                "cart": {"items": [], "item_count": 0, "total": 0.0}
            }

        if not product_id:
            return {"error": "product_id required for this action", "success": False}

        product_info = await self.product_searcher.get_product(product_id)
        if not product_info and product_snapshot:
            product_info = product_snapshot
        product_name = product_info.get("title", product_id) if product_info else product_id
        product_category = product_info.get("category") if product_info else None
        product_vendor = product_info.get("vendor") if product_info else None

        if normalized_action == "add":
            quantity = quantity or 1
            session.add_to_cart(
                product_id,
                quantity,
                price=product_info.get("price") if product_info else None,
                name=product_name,
                image_url=product_info.get("image_url") if product_info else None
            )
            if product_category:
                liked = session.metadata.get("liked_categories", [])
                if product_category not in liked:
                    liked.append(product_category)
                session.metadata["liked_categories"] = liked
            if product_vendor:
                liked = session.metadata.get("liked_vendors", [])
                if product_vendor not in liked:
                    liked.append(product_vendor)
                session.metadata["liked_vendors"] = liked
            if not skip_sync:
                await _sync_with_node("add", product_id, quantity)
            session.metadata["last_cart_action"] = {
                "type": "add_to_cart",
                "product_id": product_id,
                "product_name": product_name,
                "quantity": quantity
            }
            cart_state = await _get_cart_state()
            return {
                "action": "add",
                "success": True,
                "product_id": product_id,
                "product_name": product_name,
                "quantity": quantity,
                "message": f"Added {quantity} x {product_name} to your cart.",
                "cart": cart_state
            }

        if normalized_action == "remove":
            session.remove_from_cart(product_id)
            if not skip_sync:
                await _sync_with_node("remove", product_id)
            session.metadata["last_cart_action"] = {
                "type": "remove_from_cart",
                "product_id": product_id
            }
            cart_state = await _get_cart_state()
            return {
                "action": "remove",
                "success": True,
                "product_id": product_id,
                "product_name": product_name,
                "message": f"Removed {product_name} from your cart.",
                "cart": cart_state
            }

        if normalized_action == "set":
            if quantity is None:
                return {"error": "quantity required for set action", "success": False}
            session.remove_from_cart(product_id)
            if quantity > 0:
                session.add_to_cart(
                    product_id,
                    quantity,
                    price=product_info.get("price") if product_info else None,
                    name=product_name,
                    image_url=product_info.get("image_url") if product_info else None
                )
            if not skip_sync:
                await _sync_with_node("set", product_id, quantity)
            session.metadata["last_cart_action"] = {
                "type": "update_quantity",
                "product_id": product_id,
                "quantity": quantity
            }
            cart_state = await _get_cart_state()
            return {
                "action": "set",
                "success": True,
                "product_id": product_id,
                "quantity": quantity,
                "message": f"Updated quantity to {quantity}" if quantity > 0 else "Removed from cart",
                "cart": cart_state
            }

        return {"error": f"Unknown action: {action}", "success": False}

    def get_policy_info(self, policy_type: str) -> Dict[str, Any]:
        policy_text = get_policy_text(policy_type)
        policy_details = POLICIES.get(policy_type, {})
        return {
            "policy_type": policy_type,
            "policy_text": policy_text,
            "details": policy_details
        }

    def get_contact_info(self, info_type: str = "all") -> Dict[str, Any]:
        contact = STORE_INFO["contact"]
        location = STORE_INFO["location"]

        if info_type == "phone":
            return {
                "info_type": "phone",
                "phone": contact["phone"],
                "text": f"You can call us at {contact['phone']}"
            }
        if info_type == "email":
            return {
                "info_type": "email",
                "email": contact["email"],
                "response_time": contact["response_time"],
                "text": f"Email us at {contact['email']}. Response time: {contact['response_time']}"
            }
        if info_type == "hours":
            return {
                "info_type": "hours",
                "hours": contact["hours"],
                "text": f"Business hours: {contact['hours']}"
            }
        if info_type == "location":
            return {
                "info_type": "location",
                "address": location["warehouse"],
                "showroom": location["showroom"],
                "pickup": location["pickup"],
                "text": f"Location: {location['warehouse']}. {location['showroom']}. {location['pickup']}"
            }
        if info_type == "chat":
            return {
                "info_type": "chat",
                "available": contact["live_chat"],
                "text": f"Live chat: {contact['live_chat']}"
            }

        return {
            "info_type": "all",
            "contact_text": get_contact_text(),
            "phone": contact["phone"],
            "email": contact["email"],
            "hours": contact["hours"],
            "location": location["warehouse"]
        }

    def calculate_shipping(self, order_total: float, postcode: Optional[str] = None) -> Dict[str, Any]:
        shipping_policy = POLICIES["shipping"]
        free_threshold = shipping_policy["free_threshold"]

        if order_total >= free_threshold:
            shipping_cost = 0.00
            free_shipping = True
            amount_to_free = 0.00
        else:
            shipping_cost = shipping_policy["standard_cost"]
            free_shipping = False
            amount_to_free = free_threshold - order_total

        delivery_time = shipping_policy["delivery_time"]
        if postcode and int(postcode) > 4000:
            delivery_time = "10-15 business days"

        return {
            "order_total": order_total,
            "shipping_cost": shipping_cost,
            "total": order_total + shipping_cost,
            "free_shipping": free_shipping,
            "free_shipping_threshold": free_threshold,
            "amount_to_free_shipping": amount_to_free if not free_shipping else 0,
            "delivery_time": delivery_time,
            "express_available": shipping_policy["express_available"],
            "express_cost": shipping_policy["express_cost"],
            "express_time": shipping_policy["express_time"]
        }

    async def find_similar_products(self, product_id: str, exclude_ids: Optional[List[str]] = None, limit: int = 5) -> Dict[str, Any]:
        product = await self.product_searcher.get_product(product_id)
        if not product:
            return {"error": f"Product '{product_id}' not found"}

        category = product.get("category") or ""
        query = product.get("title") or category or product_id
        results = await self.product_searcher.search(query=query, limit=limit + 5, filters={"category": category} if category else None)

        exclude_ids = set(exclude_ids or [])
        filtered = [p for p in results if p.get("id") not in exclude_ids and p.get("sku") not in exclude_ids]
        filtered = filtered[:limit]

        session_store = get_session_store()
        session_id = CURRENT_SESSION_ID.get()
        if session_id and filtered:
            session = session_store.get_or_create_session(session_id)
            session.update_shown_products(filtered)

        return {"products": filtered, "total": len(filtered)}

    async def check_product_fit(self, product_id: str, space_length: float, space_width: float) -> Dict[str, Any]:
        specs = await self.spec_searcher.get_specs_for_product(product_id)
        if not specs:
            return {"error": "No specs available to determine fit", "product_id": product_id}

        text = " ".join([s.get("spec_text", "") for s in specs]).lower()
        dim_match = re.search(r'(\d+(?:\.\d+)?)\s*cm\s*[xX]\s*(\d+(?:\.\d+)?)\s*cm', text)

        if not dim_match:
            return {
                "product_id": product_id,
                "fits": None,
                "message": "Could not parse dimensions from specs. Please check product details."
            }

        width = float(dim_match.group(1))
        depth = float(dim_match.group(2))
        fits = width <= space_width and depth <= space_length

        return {
            "product_id": product_id,
            "fits": fits,
            "product_dimensions_cm": {"width": width, "depth": depth},
            "space_cm": {"length": space_length, "width": space_width},
            "message": "It should fit in the provided space." if fits else "It may not fit in the provided space."
        }

    async def search_small_space(
        self,
        category: str,
        space_length: float,
        space_width: float,
        limit: int = 5
    ) -> Dict[str, Any]:
        search_query = category
        results = await self.product_searcher.search(
            query=search_query,
            limit=min(limit * 3, 30),
            filters={"in_stock": True, "category": category}
        )

        if isinstance(results, dict) and results.get("no_color_match"):
            results = []

        matching = []
        for product in results:
            sku = product.get("sku") or product.get("id")
            if not sku:
                continue

            specs = await self.spec_searcher.get_specs_for_product(sku)
            if not specs:
                continue

            text = " ".join([s.get("spec_text", "") for s in specs]).lower()
            dim_match = re.search(r'(\d+(?:\.\d+)?)\s*cm\s*[xX]\s*(\d+(?:\.\d+)?)\s*cm', text)
            if not dim_match:
                dim_match = re.search(r'(\d+(?:\.\d+)?)\s*cm\s*[xX]\s*(\d+(?:\.\d+)?)\s*cm\s*[xX]\s*(\d+(?:\.\d+)?)\s*cm', text)

            if not dim_match:
                continue

            width = float(dim_match.group(1))
            depth = float(dim_match.group(2))
            fits = width <= space_width and depth <= space_length
            if not fits:
                continue

            product["product_dimensions_cm"] = {"width": width, "depth": depth}
            matching.append(product)

            if len(matching) >= limit:
                break

        return {
            "products": matching,
            "total": len(matching),
            "space_cm": {"length": space_length, "width": space_width},
            "category": category
        }

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
    ) -> Dict[str, Any]:
        result = await self.bundle_planner.build_bundle(
            request=request,
            items=items,
            budget_total=budget_total,
            color=color,
            material=material,
            room_type=room_type,
            descriptor=descriptor,
            strategy=strategy,
        )
        session_id = CURRENT_SESSION_ID.get()
        if session_id:
            session_store = get_session_store()
            session = session_store.get_or_create_session(session_id)
            session.metadata["last_bundle_request"] = {
                "request": request,
                "items": items,
                "budget_total": budget_total,
                "color": color,
                "material": material,
                "room_type": room_type,
                "descriptor": descriptor,
                "strategy": strategy
            }
            bundle_items = result.get("bundle", {}).get("items", [])
            session.metadata["last_bundle_items"] = [
                {
                    "product_id": item.get("product_id"),
                    "quantity": item.get("quantity", 1),
                    "name": item.get("name"),
                    "price": item.get("unit_price"),
                    "product_url": item.get("product_url"),
                    "image_url": item.get("image_url")
                }
                for item in bundle_items
                if item.get("product_id")
            ]
            session.metadata["last_bundle_total"] = result.get("bundle", {}).get("total_estimate")
        return result


_assistant_tools: Optional[EasymartAssistantTools] = None


def get_assistant_tools() -> EasymartAssistantTools:
    global _assistant_tools
    if _assistant_tools is None:
        _assistant_tools = EasymartAssistantTools()
    return _assistant_tools


@tool("search_products", args_schema=SearchProductsArgs)
async def search_products_tool(**kwargs) -> Dict[str, Any]:
    """Search products in the Easymart catalog."""
    return await get_assistant_tools().search_products(**kwargs)


@tool("get_product_specs", args_schema=ProductSpecsArgs)
async def get_product_specs_tool(**kwargs) -> Dict[str, Any]:
    """Fetch detailed specifications for a product."""
    return await get_assistant_tools().get_product_specs(**kwargs)


@tool("check_availability", args_schema=AvailabilityArgs)
async def check_availability_tool(**kwargs) -> Dict[str, Any]:
    """Check stock availability for a product."""
    return await get_assistant_tools().check_availability(**kwargs)


@tool("compare_products", args_schema=CompareProductsArgs)
async def compare_products_tool(**kwargs) -> Dict[str, Any]:
    """Compare multiple products side-by-side."""
    return await get_assistant_tools().compare_products(**kwargs)


@tool("update_cart", args_schema=UpdateCartArgs)
async def update_cart_tool(**kwargs) -> Dict[str, Any]:
    """Add/remove/update items in the cart."""
    return await get_assistant_tools().update_cart(**kwargs)


@tool("get_policy_info", args_schema=PolicyArgs)
def get_policy_info_tool(**kwargs) -> Dict[str, Any]:
    """Return policy details by type."""
    return get_assistant_tools().get_policy_info(**kwargs)


@tool("get_contact_info", args_schema=ContactArgs)
def get_contact_info_tool(**kwargs) -> Dict[str, Any]:
    """Return Easymart contact details."""
    return get_assistant_tools().get_contact_info(**kwargs)


@tool("calculate_shipping", args_schema=ShippingArgs)
def calculate_shipping_tool(**kwargs) -> Dict[str, Any]:
    """Calculate shipping cost for a given order total."""
    return get_assistant_tools().calculate_shipping(**kwargs)


@tool("find_similar_products", args_schema=FindSimilarArgs)
async def find_similar_products_tool(**kwargs) -> Dict[str, Any]:
    """Find products similar to a given product."""
    return await get_assistant_tools().find_similar_products(**kwargs)


@tool("check_product_fit", args_schema=ProductFitArgs)
async def check_product_fit_tool(**kwargs) -> Dict[str, Any]:
    """Check whether a product fits in a specified space."""
    return await get_assistant_tools().check_product_fit(**kwargs)


@tool("build_bundle", args_schema=BuildBundleArgs)
async def build_bundle_tool(**kwargs) -> Dict[str, Any]:
    """Build a multi-item bundle within a total budget."""
    return await get_assistant_tools().build_bundle(**kwargs)


@tool("build_cheapest_bundle", args_schema=CheapestBundleArgs)
async def build_cheapest_bundle_tool(**kwargs) -> Dict[str, Any]:
    """Build the cheapest multi-item bundle that matches the request."""
    kwargs["strategy"] = "cheapest"
    return await get_assistant_tools().build_bundle(**kwargs)


@tool("search_small_space", args_schema=SmallSpaceSearchArgs)
async def search_small_space_tool(**kwargs) -> Dict[str, Any]:
    """Search for products that fit within a given space."""
    return await get_assistant_tools().search_small_space(**kwargs)


def get_langchain_tools():
    return [
        search_products_tool,
        get_product_specs_tool,
        check_availability_tool,
        compare_products_tool,
        update_cart_tool,
        get_policy_info_tool,
        get_contact_info_tool,
        calculate_shipping_tool,
        find_similar_products_tool,
        check_product_fit_tool,
        build_bundle_tool,
        build_cheapest_bundle_tool,
        search_small_space_tool
    ]
