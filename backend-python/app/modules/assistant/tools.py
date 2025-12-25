"""
Easymart Assistant Tools

Implements 8 tools for furniture search, specs, cart, policies, and contact.
"""

import asyncio
from typing import Dict, Any, Callable, List, Optional
from pydantic import BaseModel

# Import catalog indexer
from ..catalog_index.catalog import CatalogIndexer
from ...core.dependencies import get_catalog_indexer

# Import retrieval modules
from ..retrieval.product_search import ProductSearcher
from ..retrieval.spec_search import SpecSearcher

# Import prompts for policy info
from .prompts import POLICIES, STORE_INFO, get_policy_text, get_contact_text


# Tool definitions in OpenAI format (compatible with Mistral)
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "search_products",
            "description": "Search Easymart furniture catalog by keyword, category, style, material, or price range. Returns EXACT products from database - NO MORE, NO LESS. Display results exactly as returned. If 0 results, inform user that items in that category/color/style are not available.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query or keywords (e.g., 'office chair', 'modern dining table')"
                    },
                    "category": {
                        "type": "string",
                        "enum": ["chair", "table", "sofa", "bed", "desk", "shelf", "stool", "storage", "locker"],
                        "description": "Product category filter"
                    },
                    "material": {
                        "type": "string",
                        "enum": ["wood", "metal", "leather", "fabric", "glass", "rattan", "plastic"],
                        "description": "Material filter"
                    },
                    "style": {
                        "type": "string",
                        "enum": ["modern", "contemporary", "industrial", "minimalist", "rustic", "scandinavian", "classic"],
                        "description": "Style filter"
                    },
                    "room_type": {
                        "type": "string",
                        "enum": ["office", "bedroom", "living_room", "dining_room", "outdoor"],
                        "description": "Room type filter"
                    },
                    "price_max": {
                        "type": "number",
                        "description": "Maximum price in AUD"
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["price_low", "price_high", "relevance"],
                        "description": "Sort order for results"
                    },
                    "color": {
                        "type": "string",
                        "description": "Color filter (e.g., 'black', 'white')"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum results to return (default 5, max 10)",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_specs",
            "description": "Get detailed specifications for a specific product. IMPORTANT: Always use this tool when asked about product specs - NEVER make up specifications. Returns dimensions, materials, colors, weight capacity, assembly info, care instructions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "Product SKU or ID (e.g., 'CHR-001')"
                    },
                    "question": {
                        "type": "string",
                        "description": "Specific question about the product (optional, for Q&A search in specs)"
                    }
                },
                "required": ["product_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Check if a product is in stock and available for purchase.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {
                        "type": "string",
                        "description": "Product SKU or ID"
                    }
                },
                "required": ["product_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_products",
            "description": "Compare specifications and features of 2-4 products side-by-side.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_ids": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of 2-4 product IDs to compare",
                        "minItems": 2,
                        "maxItems": 4
                    }
                },
                "required": ["product_ids"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_cart",
            "description": "Add, remove, or update quantity of items in shopping cart. This communicates with the Node.js backend cart service.",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["add", "remove", "update_quantity", "view"],
                        "description": "Cart action to perform"
                    },
                    "product_id": {
                        "type": "string",
                        "description": "Product SKU (required for add/remove/update)"
                    },
                    "quantity": {
                        "type": "integer",
                        "description": "Quantity (required for add/update)",
                        "minimum": 1
                    },
                    "session_id": {
                        "type": "string",
                        "description": "User session ID (provided by system)"
                    }
                },
                "required": ["action"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_policy_info",
            "description": "Get detailed information about Easymart policies: returns, shipping, payment options, warranty.",
            "parameters": {
                "type": "object",
                "properties": {
                    "policy_type": {
                        "type": "string",
                        "enum": ["returns", "shipping", "payment", "warranty"],
                        "description": "Type of policy information requested"
                    }
                },
                "required": ["policy_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_contact_info",
            "description": "Get Easymart contact information: phone, email, live chat, business hours, store location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "info_type": {
                        "type": "string",
                        "enum": ["all", "phone", "email", "hours", "location", "chat"],
                        "description": "Type of contact info (default: all)",
                        "default": "all"
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_shipping",
            "description": "Calculate shipping cost based on order total and delivery postcode. Returns cost, delivery time estimate, and free shipping eligibility.",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_total": {
                        "type": "number",
                        "description": "Order subtotal in AUD"
                    },
                    "postcode": {
                        "type": "string",
                        "description": "Australian postcode (4 digits)",
                        "pattern": "^\\d{4}$"
                    }
                },
                "required": ["order_total"]
            }
        }
    }
]


class EasymartAssistantTools:
    """
    Tool executor for Easymart assistant.
    Implements all 8 tool functions.
    """
    
    def __init__(self):
        """Initialize tools with dependencies"""
        self.product_searcher = ProductSearcher()
        self.spec_searcher = SpecSearcher()
    
    async def search_products(
        self,
        query: str,
        category: Optional[str] = None,
        material: Optional[str] = None,
        style: Optional[str] = None,
        room_type: Optional[str] = None,
        color: Optional[str] = None,
        price_max: Optional[float] = None,
        sort_by: Optional[str] = "relevance",  # NEW: Add sort_by
        limit: int = 5
    ) -> Dict[str, Any]:
        """
        Search products with filters and sorting.
        """
        try:
            # Build filters
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
            
            # Search using product searcher
            results = await self.product_searcher.search(
                query=query,
                filters=filters,
                limit=min(limit, 10)
            )
            
            # SORTING: Handle price_low, price_high
            if sort_by == "price_low":
                results.sort(key=lambda x: x.get("price", 0))
            elif sort_by == "price_high":
                results.sort(key=lambda x: x.get("price", 0), reverse=True)
            
            # FIX: Ensure all products have proper names
            formatted_products = []
            for idx, product in enumerate(results):
                if not product.get("name") or product.get("name").startswith("product_"):
                    product["name"] = product.get("title") or product.get("description", f"Product {idx + 1}")
                
                product["id"] = product.get("sku") or product.get("id")
                product["price"] = product.get("price", 0.00)
                
                formatted_products.append(product)
            
            return {
                "products": formatted_products,
                "total": len(formatted_products),
                "showing": len(formatted_products),
                "sort_applied": sort_by
            }
        
        except Exception as e:
            return {
                "error": f"Search failed: {str(e)}",
                "products": [],
                "total": 0
            }
    
    async def get_product_specs(
        self,
        product_id: str,
        question: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get product specifications.
        CRITICAL: Never make up specs - always use actual data.
        
        Returns:
            {
                "product_id": "CHR-001",
                "product_name": "Modern Office Chair",
                "specs": {
                    "dimensions": {"width": 60, "depth": 58, "height": 95, "unit": "cm"},
                    "weight": 12.5,
                    "material": "Mesh back, fabric seat, metal frame",
                    "color": "Black, Grey",
                    "weight_capacity": 120,
                    "assembly_required": true,
                    "care_instructions": "...",
                    "warranty": "12 months"
                },
                "answer": "..." (if question provided)
            }
        """
        try:
            # Get product details
            product = await self.product_searcher.get_product(product_id)
            if not product:
                return {
                    "error": f"Product '{product_id}' not found",
                    "product_id": product_id
                }
            
            # FIX: Ensure product has 'name' field (map from 'title' if needed)
            if 'name' not in product or not product.get('name'):
                product['name'] = product.get('title') or product.get('handle', '').replace('-', ' ').title() or 'Unknown Product'
            
            # Get specs document
            specs_list = await self.spec_searcher.get_specs_for_product(product_id)
            
            # If question provided, use Q&A search
            answer = None
            if question and specs_list:
                qa_result = await self.spec_searcher.answer_question(
                    product_id=product_id,
                    question=question
                )
                answer = qa_result.get("answer")
            
            # If no specs available, provide basic product info as fallback
            if not specs_list:
                return {
                    "product_id": product_id,
                    "product_name": product['name'],
                    "price": product.get("price"),
                    "description": product.get("description", ""),
                    "specs": {},
                    "message": "Detailed specifications not available. Basic product information provided above.",
                    "answer": answer
                }
            
            # Format specs into organized structure
            formatted_specs = {}
            full_text_parts = []
            
            for spec in specs_list:
                section = spec.get('section', 'General')
                spec_text = spec.get('spec_text', '')
                
                formatted_specs[section] = spec_text
                full_text_parts.append(f"{section}: {spec_text}")
            
            return {
                "product_id": product_id,
                "product_name": product['name'],
                "price": product.get("price"),
                "specs": formatted_specs,
                "answer": answer,
                "estimated_delivery": "5-10 business days (metro Australia)",
                "full_spec_text": " | ".join(full_text_parts)
            }
        
        except Exception as e:
            return {
                "error": f"Failed to get specs: {str(e)}",
                "product_id": product_id
            }
    
    async def check_availability(self, product_id: str) -> Dict[str, Any]:
        """
        Check product availability.
        
        Returns:
            {
                "product_id": "CHR-001",
                "in_stock": true,
                "quantity_available": 15,
                "estimated_delivery": "5-10 business days"
            }
        """
        try:
            product = await self.product_searcher.get_product(product_id)
            if not product:
                return {
                    "error": f"Product '{product_id}' not found",
                    "product_id": product_id,
                    "in_stock": False
                }
            
            # FIX: Ensure product has 'name' field
            if 'name' not in product or not product.get('name'):
                product['name'] = product.get('title') or product.get('handle', '').replace('-', ' ').title() or 'Unknown Product'
            
            # Use actual inventory quantity if available
            qty = product.get("inventory_quantity", 10)
            in_stock = qty > 0
            
            return {
                "product_id": product_id,
                "product_name": product['name'],
                "in_stock": in_stock,
                "quantity_available": qty,
                "estimated_delivery": "5-10 business days"
            }
        
        except Exception as e:
            return {
                "error": f"Availability check failed: {str(e)}",
                "product_id": product_id,
                "in_stock": False
            }
    
    async def compare_products(self, product_ids: List[str], position_labels: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Compare multiple products side-by-side.
        
        Args:
            product_ids: List of product SKUs to compare
            position_labels: Optional list of user-facing labels (e.g., ["Option 2", "Option 3"])
        
        Returns:
            {
                "products": [
                    {
                        "id": "CHR-001",
                        "name": "...",
                        "price": 199.00,
                        "specs": {...}
                    }
                ],
                "position_labels": ["Option 2", "Option 3"],
                "comparison": {
                    "price_range": "199.00 - 349.00 AUD",
                    "common_features": [...],
                    "differences": [...]
                }
            }
        """
        if len(product_ids) < 2 or len(product_ids) > 4:
            return {"error": "Can only compare 2-4 products"}
        
        try:
            # Get all products
            products = []
            for pid in product_ids:
                product = await self.product_searcher.get_product(pid)
                if product:
                    # FIX: Ensure product has 'name' field (map from 'title' if needed)
                    if 'name' not in product or not product.get('name'):
                        product['name'] = product.get('title') or product.get('handle', '').replace('-', ' ').title() or 'Unknown Product'
                    
                    specs_list = await self.spec_searcher.get_specs_for_product(pid)
                    # Convert list to dict
                    specs_dict = {}
                    if specs_list:
                        for spec in specs_list:
                            section = spec.get('section', 'General')
                            specs_dict[section] = spec.get('spec_text', '')
                    
                    products.append({
                        "id": pid,
                        "name": product['name'],
                        "price": product.get("price"),
                        "specs": specs_dict
                    })
            
            if not products:
                return {"error": "No valid products found for comparison"}
            
            # Basic comparison
            prices = [p["price"] for p in products if p.get("price")]
            price_range = f"${min(prices):.2f} - ${max(prices):.2f} AUD" if prices else "N/A"
            
            result = {
                "products": products,
                "comparison": {
                    "price_range": price_range,
                    "count": len(products)
                }
            }
            
            # Add position labels if provided
            if position_labels:
                result["position_labels"] = position_labels
            
            return result
        
        except Exception as e:
            return {"error": f"Comparison failed: {str(e)}"}
    
    async def update_cart(
        self,
        action: str,
        product_id: Optional[str] = None,
        quantity: Optional[int] = None,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update shopping cart.
        Actually stores items in session store.
        
        Returns:
            {
                "action": "add",
                "success": true,
                "message": "Added to cart"
            }
        """
        from app.modules.assistant.session_store import get_session_store
        
        session_store = get_session_store()
        session = session_store.get_or_create_session(session_id)
        
        if action == "view":
            cart_details = []
            total_price = 0.0
            
            for item in session.cart_items:
                product_id = item["product_id"]
                product = await self.product_searcher.get_product(product_id)
                if product:
                    price = product.get("price", 0.0)
                    qty = item["quantity"]
                    item_total = price * qty
                    total_price += item_total
                    
                    cart_details.append({
                        "product_id": product_id,
                        "name": product.get("title", "Unknown Product"),
                        "price": price,
                        "quantity": qty,
                        "item_total": item_total
                    })
            
            return {
                "action": "view",
                "success": True,
                "cart": {
                    "items": cart_details,
                    "item_count": len(cart_details),
                    "total": total_price
                },
                "message": f"Your cart has {len(cart_details)} items totaling ${total_price:.2f}" if cart_details else "Your cart is currently empty."
            }
        
        if not product_id:
            return {"error": "product_id required for this action", "success": False}
        
        # Get product info for better feedback
        product = await self.product_searcher.get_product(product_id)
        product_name = product.get("title", product_id) if product else product_id
        
        if action == "add":
            if not quantity or quantity < 1:
                quantity = 1
            session.add_to_cart(product_id, quantity)
            return {
                "action": "add",
                "success": True,
                "product_id": product_id,
                "product_name": product_name,
                "quantity": quantity,
                "message": f"Added {quantity} x {product_name} to your cart."
            }
        
        elif action == "remove":
            session.remove_from_cart(product_id)
            return {
                "action": "remove",
                "success": True,
                "product_id": product_id,
                "product_name": product_name,
                "message": f"Removed {product_name} from your cart."
            }
        
        elif action == "set":
            if quantity is None:
                return {"error": "quantity required for set action", "success": False}
            
            logger.info(f"[CART SET] Before remove - cart_items: {session.cart_items}")
            
            # Remove item first
            session.remove_from_cart(product_id)
            
            logger.info(f"[CART SET] After remove - cart_items: {session.cart_items}")
            
            # Add back with new quantity if > 0
            if quantity > 0:
                session.add_to_cart(product_id, quantity)
                logger.info(f"[CART SET] After add ({quantity}) - cart_items: {session.cart_items}")
            
            return {
                "action": "set",
                "success": True,
                "product_id": product_id,
                "quantity": quantity,
                "message": f"Updated quantity to {quantity}" if quantity > 0 else "Removed from cart"
            }
        
        else:
            return {"error": f"Unknown action: {action}", "success": False}
    
    def get_policy_info(self, policy_type: str) -> Dict[str, Any]:
        """
        Get policy information.
        
        Returns:
            {
                "policy_type": "returns",
                "policy_text": "...",
                "details": {...}
            }
        """
        policy_text = get_policy_text(policy_type)
        policy_details = POLICIES.get(policy_type, {})
        
        return {
            "policy_type": policy_type,
            "policy_text": policy_text,
            "details": policy_details
        }
    
    def get_contact_info(self, info_type: str = "all") -> Dict[str, Any]:
        """
        Get contact information.
        
        Returns:
            {
                "contact_text": "...",
                "phone": "...",
                "email": "...",
                "hours": "...",
                "location": "..."
            }
        """
        contact = STORE_INFO["contact"]
        location = STORE_INFO["location"]
        
        if info_type == "phone":
            return {
                "info_type": "phone",
                "phone": contact["phone"],
                "text": f"You can call us at {contact['phone']}"
            }
        
        elif info_type == "email":
            return {
                "info_type": "email",
                "email": contact["email"],
                "response_time": contact["response_time"],
                "text": f"Email us at {contact['email']}. Response time: {contact['response_time']}"
            }
        
        elif info_type == "hours":
            return {
                "info_type": "hours",
                "hours": contact["hours"],
                "text": f"Business hours: {contact['hours']}"
            }
        
        elif info_type == "location":
            return {
                "info_type": "location",
                "address": location["warehouse"],
                "showroom": location["showroom"],
                "pickup": location["pickup"],
                "text": f"Location: {location['warehouse']}. {location['showroom']}. {location['pickup']}"
            }
        
        elif info_type == "chat":
            return {
                "info_type": "chat",
                "available": contact["live_chat"],
                "text": f"Live chat: {contact['live_chat']}"
            }
        
        else:  # "all"
            return {
                "info_type": "all",
                "contact_text": get_contact_text(),
                "phone": contact["phone"],
                "email": contact["email"],
                "hours": contact["hours"],
                "location": location["warehouse"]
            }
    
    def calculate_shipping(
        self,
        order_total: float,
        postcode: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Calculate shipping cost.
        
        Returns:
            {
                "order_total": 150.00,
                "shipping_cost": 15.00,
                "total": 165.00,
                "free_shipping": false,
                "free_shipping_threshold": 199.00,
                "amount_to_free_shipping": 49.00,
                "delivery_time": "5-10 business days",
                "express_available": true,
                "express_cost": 35.00
            }
        """
        shipping_policy = POLICIES["shipping"]
        free_threshold = shipping_policy["free_threshold"]
        
        # Check for free shipping
        if order_total >= free_threshold:
            shipping_cost = 0.00
            free_shipping = True
            amount_to_free = 0.00
        else:
            shipping_cost = shipping_policy["standard_cost"]
            free_shipping = False
            amount_to_free = free_threshold - order_total
        
        # Regional surcharge check (simplified - real implementation would use postcode)
        delivery_time = shipping_policy["delivery_time"]
        if postcode and int(postcode) > 4000:  # Rough check for regional
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


async def execute_tool(
    tool_name: str,
    arguments: Dict[str, Any],
    tools_instance: Optional[EasymartAssistantTools] = None
) -> Dict[str, Any]:
    """
    Execute a tool by name with given arguments.
    
    Args:
        tool_name: Name of the tool to execute
        arguments: Tool arguments
        tools_instance: Optional EasymartAssistantTools instance (creates new if None)
    
    Returns:
        Tool execution result
    
    Example:
        >>> result = await execute_tool(
        ...     "search_products",
        ...     {"query": "office chair", "price_max": 300}
        ... )
        >>> print(result["products"])
    """
    if not tools_instance:
        tools_instance = EasymartAssistantTools()
    
    # Map tool names to methods
    tool_map = {
        "search_products": tools_instance.search_products,
        "get_product_specs": tools_instance.get_product_specs,
        "check_availability": tools_instance.check_availability,
        "compare_products": tools_instance.compare_products,
        "update_cart": tools_instance.update_cart,
        "get_policy_info": tools_instance.get_policy_info,
        "get_contact_info": tools_instance.get_contact_info,
        "calculate_shipping": tools_instance.calculate_shipping
    }
    
    tool_func = tool_map.get(tool_name)
    if not tool_func:
        return {"error": f"Unknown tool: {tool_name}"}
    
    try:
        # Extract special parameters that aren't part of tool signature
        position_labels = arguments.pop('_position_labels', None)
        
        # Execute tool (handle both sync and async)
        if asyncio.iscoroutinefunction(tool_func):
            result = await tool_func(**arguments)
        else:
            result = tool_func(**arguments)
        
        # Re-add position labels to result if they were provided (for compare_products)
        if position_labels and tool_name == 'compare_products':
            if isinstance(result, dict) and 'position_labels' not in result:
                result['position_labels'] = position_labels
        
        return result
    
    except Exception as e:
        return {"error": f"Tool execution failed: {str(e)}"}
