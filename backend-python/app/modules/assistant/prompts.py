"""
System prompt and response templates for Easymart Assistant.

This file intentionally keeps the SYSTEM PROMPT minimal and strict
to ensure reliable behavior with Mistral and other open-weight LLMs.

All enforcement, validation, and formatting logic should be handled
outside the LLM (middleware / backend).
"""

from typing import Dict


# -------------------------------------------------------------------
# Store Information (Used in templates, NOT injected fully into prompt)
# -------------------------------------------------------------------

STORE_INFO: Dict = {
    "name": "Easymart",
    "website": "https://easymart.com.au",
    "country": "Australia",
    "currency": "AUD",
    "timezone": "AEST (UTC+10)",
    "contact": {
        "phone": "1300 327 962",
        "email": "support@easymart.com.au",
        "hours": (
            "Monday–Friday: 9:00 AM – 6:00 PM AEST, "
            "Saturday: 10:00 AM – 4:00 PM AEST, "
            "Sunday: Closed"
        ),
        "response_time": "24–48 hours for email inquiries",
        "live_chat": "Available during business hours",
    },
    "location": {
        "warehouse": "Unit 5, 7-9 Production-way, Avenell Heights QLD 4670",
        "showroom": "No physical showroom - online only",
        "pickup": "Free warehouse pickup available at our Bundaberg warehouse",
    },
}

POLICIES: Dict = {
    "returns": {
        "period": "30 days",
        "condition": "Items must be unused and in original packaging",
        "exclusions": "Custom-made items, final sale items, mattresses",
        "refund": "Original payment method within 5–10 business days",
    },
    "shipping": {
        "free_threshold": 199.00,
        "standard_cost": 15.00,
        "delivery_time": "5–10 business days (metro), 10–15 (regional)",
        "express_cost": 35.00,
        "express_time": "2–5 business days",
        "international": "Australia only",
        "express_available": True,
    },
    "payment": {
        "methods": ["Visa", "Mastercard", "American Express", "PayPal"],
        "bnpl": ["Afterpay", "Zip Pay"],
        "currency": "AUD",
    },
    "warranty": {
        "duration": "12 months",
        "coverage": "Manufacturing defects and structural issues",
        "exclusions": "Normal wear and tear, misuse, accidental damage",
    },
    "promotions": {
        "active": "None",
        "info": "We currently do not have any active discount codes or site-wide sales. Please check back later or subscribe to our newsletter for updates.",
    },
}

SYSTEM_PROMPT = """You are the official AI Shopping Assistant for Easymart, a leading Australian furniture retailer. Your goal is to help users find the perfect furniture and provide information about our products and services.

AVAILABLE TOOLS:
- search_products: Search catalog by attributes. Use for ANY search or broad availability check.
- get_product_specs: Get technical details for a specific item. Use for price, size, material of a SPECIFIC product.
- check_availability: Check if a specific SKU is in stock.
- update_cart: Add, remove, or view items in the user's shopping cart.
- compare_products: Compare features of 2-4 products.
- get_policy_info: Retrieve store policies (shipping, returns, payment, warranty, promotions).
- calculate_shipping: Estimate shipping costs based on total and postcode.

RESPONSE RULES:
1. IDENTITY: You are Easymart's Shopping Assistant. Never mention being an AI model.
2. SOURCE OF TRUTH: Use tools for ALL product and policy data. Never invent specifications, prices, or policies.
3. CURRENCY: All prices are in AUD.
4. TONE: Professional, helpful, and concise. Use Australian English.
5. PRODUCT CARDS: When showing products from search_products, describe them briefly and highlight key features.
6. NO SPECULATION: If a tool returns no results, state that the item is not available.
7. OFF-TOPIC BLOCK: Block any queries not related to furniture or store policies (e.g., requests for jokes, stories, poems, coding, general trivia) with: "I'm EasyMart's shopping assistant, specialized in helping you find furniture and home products. What products are you looking for today?"
8. CONCISE & STRUCTURED: Responses must be concise, professional, and use bullet points for technical specs.
9. CLARIFICATION: If a user mentions redoing or furnishing a room (e.g., "redoing my living room") without specifying items, do NOT use search tools. Instead, politely ask: "Tell me what furniture do you want for your living room tell me i will assist you with what you want"
10. DISCOUNTS: If asked about discounts or promotions, use get_policy_info with policy_type="promotions".
11. CATEGORY AVAILABILITY: If asked if a category of items is available (e.g., "Beds available?"), always use search_products to check our catalog.
12. PRICE QUERIES: If asked for the cheapest or most expensive item, use search_products with the 'sort' parameter, then identify the specific item from the results.
13. MULTI-INTENT: If a query has multiple parts (e.g., "price of option 1 and delivery time"), call all relevant tools and answer all parts.
14. SKU LOOKUP: If asked about availability, price, or specs of a product by name but you don't have the SKU, first use search_products to find the item and its SKU, then use the appropriate tool.

TOOL_CALL_FORMAT:
To use a tool, you must use the following format:
[TOOL_CALLS]
[
  {"name": "tool_name", "arguments": {"arg1": "val1"}}
]
[/TOOL_CALLS]
"""

def get_system_prompt() -> str:
    """
    Returns the system prompt used for all LLM requests.
    """
    return SYSTEM_PROMPT


# -------------------------------------------------------------------
# RESPONSE TEMPLATES (SAFE, DETERMINISTIC)
# -------------------------------------------------------------------

def get_returns_policy_text() -> str:
    policy = POLICIES["returns"]
    return (
        f"We offer a {policy['period']} return period. "
        f"Items must be {policy['condition']}. "
        f"Exclusions apply: {policy['exclusions']}. "
        f"Refunds are issued to the {policy['refund']}."
    )


def get_shipping_policy_text() -> str:
    policy = POLICIES["shipping"]
    return (
        f"Free shipping on orders over ${policy['free_threshold']} AUD. "
        f"Standard delivery costs ${policy['standard_cost']} AUD "
        f"and takes {policy['delivery_time']}. "
        f"Express delivery is ${policy['express_cost']} AUD "
        f"({policy['express_time']}). "
        f"Shipping is available within Australia only."
    )


def get_payment_policy_text() -> str:
    policy = POLICIES["payment"]
    methods = ", ".join(policy["methods"])
    bnpl = ", ".join(policy["bnpl"])
    return (
        f"We accept {methods}. "
        f"Buy now, pay later options include {bnpl}. "
        f"All payments are processed securely in {policy['currency']}."
    )


def get_warranty_policy_text() -> str:
    policy = POLICIES["warranty"]
    return (
        f"All products include a {policy['duration']} warranty covering "
        f"{policy['coverage']}. "
        f"Exclusions include {policy['exclusions']}."
    )


def get_promotions_policy_text() -> str:
    policy = POLICIES["promotions"]
    return policy["info"]


def get_contact_text() -> str:
    contact = STORE_INFO["contact"]
    return (
        f"You can contact Easymart on {contact['phone']} or email "
        f"{contact['email']}. "
        f"Our business hours are: {contact['hours']}."
    )


def get_greeting_message() -> str:
    return (
        f"Welcome to {STORE_INFO['name']}. "
        "How can I help you find the right furniture today?"
    )


def get_no_results_message(query: str) -> str:
    return (
        f"I couldn’t find any products matching \"{query}\" "
        "in our catalog."
    )


def get_spec_not_available_message(product_name: str, spec_type: str) -> str:
    return (
        f"I don’t have {spec_type} information for {product_name}. "
        f"You can check the product page on {STORE_INFO['website']} "
        f"or contact us on {STORE_INFO['contact']['phone']}."
    )


# -------------------------------------------------------------------
# BACKWARD COMPATIBILITY WRAPPERS
# -------------------------------------------------------------------

def get_policy_text(policy_type: str) -> str:
    """
    Compatibility wrapper for old code that calls get_policy_text().
    Routes to the appropriate specific policy function.
    
    Args:
        policy_type: One of "returns", "shipping", "payment", "warranty", "promotions"
    
    Returns:
        Formatted policy text
    """
    if policy_type == "returns":
        return get_returns_policy_text()
    elif policy_type == "shipping":
        return get_shipping_policy_text()
    elif policy_type == "payment":
        return get_payment_policy_text()
    elif policy_type == "warranty":
        return get_warranty_policy_text()
    elif policy_type == "promotions":
        return get_promotions_policy_text()
    else:
        return f"Unknown policy type: {policy_type}"


def get_clarification_prompt(ambiguity: str) -> str:
    """Get clarification prompt when user intent is unclear."""
    return (
        f"I'd like to help you with that! Could you please clarify {ambiguity}? "
        "This will help me find exactly what you're looking for."
    )


def get_empty_results_prompt(query: str) -> str:
    """Alias for get_no_results_message for backward compatibility."""
    return get_no_results_message(query)


def get_spec_not_found_prompt(product_name: str, spec_type: str) -> str:
    """Alias for get_spec_not_available_message for backward compatibility."""
    return get_spec_not_available_message(product_name, spec_type)


# Critical behavioral rules (enforcement happens in backend)
TOOL_CALL_FORMAT = """[TOOLCALLS] [{"name": "tool_name", "arguments": {...}}] [/TOOLCALLS]"""

RESPONSE_RULES = """
AFTER receiving tool results:
- Give SHORT intro only (max 1-2 sentences)
- DO NOT list products - UI will show cards
- NEVER include [TOOLCALLS] syntax in final response
"""