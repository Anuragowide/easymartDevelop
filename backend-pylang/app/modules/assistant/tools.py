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
    action: str = Field(..., description="Cart action: add, remove, update_quantity, view, clear")
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


class EasymartAssistantTools:
    def __init__(self):
        self.product_searcher = ProductSearcher()
        self.spec_searcher = SpecSearcher()
        self.settings = get_settings()

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

        results = await self.product_searcher.search(query=query, filters=filters, limit=min(limit, 10))

        if isinstance(results, dict) and results.get("no_color_match"):
            return results

        if sort_by == "price_low":
            results.sort(key=lambda x: x.get("price", 0))
        elif sort_by == "price_high":
            results.sort(key=lambda x: x.get("price", 0), reverse=True)

        formatted = []
        for idx, product in enumerate(results):
            if not product.get("name") or product.get("name").startswith("product_"):
                product["name"] = product.get("title") or product.get("description", f"Product {idx + 1}")
            product["id"] = product.get("sku") or product.get("id")
            product["price"] = product.get("price", 0.0)
            formatted.append(product)

        session_store = get_session_store()
        session_id = CURRENT_SESSION_ID.get()
        if session_id:
            session = session_store.get_or_create_session(session_id)
            session.update_shown_products(formatted)

        return {
            "products": formatted,
            "total": len(formatted),
            "showing": len(formatted),
            "sort_applied": sort_by
        }

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

        if not specs_list:
            return {
                "product_id": product_id,
                "product_name": product["name"],
                "price": product.get("price"),
                "description": product.get("description", ""),
                "specs": {},
                "message": "Detailed specifications not available. Basic product information provided above.",
                "answer": answer
            }

        formatted_specs = {}
        for spec in specs_list:
            section = spec.get("section", "General")
            formatted_specs[section] = spec.get("spec_text", "")

        return {
            "product_id": product_id,
            "product_name": product["name"],
            "price": product.get("price"),
            "specs": formatted_specs,
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
        skip_sync: bool = False
    ) -> Dict[str, Any]:
        session_store = get_session_store()
        session_id = session_id or CURRENT_SESSION_ID.get()
        session = session_store.get_or_create_session(session_id)

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
                        "image_url": product.get("image_url", ""),
                        "quantity": qty,
                        "item_total": item_total,
                        "added_at": item.get("added_at")
                    })
                else:
                    cart_details.append({
                        "product_id": pid,
                        "id": pid,
                        "title": pid or "Unknown Product",
                        "quantity": item.get("quantity", 1),
                        "price": 0.0,
                        "item_total": 0.0
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
                        timeout=5.0
                    )
                    if response.status_code == 200:
                        return response.json()
            except Exception as sync_e:
                logger.error(f"Cart sync failed: {sync_e}")
            return None

        if action == "view":
            cart_state = await _get_cart_state()
            return {
                "action": "view",
                "success": True,
                "cart": cart_state,
                "message": f"Your cart has {cart_state['item_count']} items totaling ${cart_state['total']:.2f}" if cart_state["items"] else "Your cart is currently empty."
            }

        if action == "clear":
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
        product_name = product_info.get("title", product_id) if product_info else product_id

        if action == "add":
            quantity = quantity or 1
            session.add_to_cart(product_id, quantity)
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

        if action == "remove":
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

        if action in ["set", "update_quantity"]:
            if quantity is None:
                return {"error": "quantity required for set action", "success": False}
            session.remove_from_cart(product_id)
            if quantity > 0:
                session.add_to_cart(product_id, quantity)
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
        check_product_fit_tool
    ]
