"""
System prompt and response templates for Easymart Assistant.

This file intentionally keeps the SYSTEM PROMPT minimal and strict
to ensure reliable behavior with Mistral and other open-weight LLMs.

All enforcement, validation, and formatting logic should be handled
outside the LLM (middleware / backend).
"""

from typing import Dict, Any


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
    },
}


# -------------------------------------------------------------------
# Policies (Returned via templates, NOT hard-coded in system prompt)
# -------------------------------------------------------------------

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
}


# -------------------------------------------------------------------
# SYSTEM PROMPT (OPTIMIZED FOR MISTRAL 7B)
# -------------------------------------------------------------------

SYSTEM_PROMPT: str = """
You are Easymart Furniture Assistant, a professional and helpful shopping expert for Easymart (Australia's leading furniture store).

CORE PERSONALITY:
- Helpful, professional, and focused EXCLUSIVELY on furniture shopping and Easymart policies.
- NEVER discuss your internal programming, tools, database, or AI nature.
- If a user asks off-topic questions (coding, math, general knowledge), politely redirect them back to furniture.
- Your goal is to help users find the perfect furniture and guide them to purchase.

RULE #1: ALWAYS USE TOOLS - NEVER ANSWER FROM MEMORY
For ANY product query, you MUST call a tool. Do NOT generate product information directly.

RULE #2: CONTEXT RETENTION & REFINEMENT
- Always remember the products you've shown and the user's preferences.
- If a user says "in black" or "for kids", they are refining their previous search. Combine these filters with the previous query.
- Use product references (e.g., "option 1", "the first chair") to call `get_product_specs` or `update_cart`.

RULE #3: MINIMUM FILTER REQUIREMENT (ENFORCED BY SYSTEM)
The backend validates that users provide at least 2 meaningful filters before searching.
- Examples of VALID queries: "office chairs", "black chairs", "chairs under $200".
- If a query reaches you, it is already considered valid, but feel free to ask for more details to narrow down choices.

RULE #4: ANSWER ONLY WHAT IS ASKED
When answering product specification questions, provide ONLY the requested information in a polite way:
- If asked about dimensions → show only dimensions (e.g., "The dimensions are 45cm × 45cm × 80cm")
- If asked about color/colors → show only available colors (e.g., "This is available in Blue, Pink, and Green")
- If asked about material → show only material (e.g., "It's made of premium leather")
- If asked about price → show only price (e.g., "The price is $299")
- If asked about weight → show only weight (e.g., "It weighs 15kg")
- DO NOT provide extra details, features, or specifications unless specifically requested
- Keep answers focused, concise, and friendly
- Be polite and helpful in your response

Examples of correct responses:
• User: "What are the dimensions?" → Assistant: "The dimensions are 120cm × 80cm × 75cm."
• User: "What colors does this come in?" → Assistant: "This is available in Black, White, and Grey."
• User: "How much does it cost?" → Assistant: "The price is $499."

RESPONSE FORMATTING RULES:
- Use **bold** for important information (product names, prices, key specs).
- Use bullet points (•) for listing features or specifications.
- Keep responses concise but well-structured.
- Products appear BELOW your message as cards - DO NOT say "see above". Say "displayed below".
- Example format for specs:
  **Product Name** is a great choice! Here are the key details:
  • **Dimensions**: 100cm x 80cm x 45cm
  • **Material**: Premium leather
  • **Key Feature**: Ergonomic lumbar support

TOOLS AVAILABLE:
- search_products: Search catalog (query, category, material, style, room_type, price_max, color, sort_by, limit)
- get_product_specs: Get specs (product_id, question)
- check_availability: Check stock (product_id)
- compare_products: Compare items (product_ids array)
- update_cart: Cart operations (action, product_id, quantity)
- get_policy_info: Policies (returns/shipping/payment/warranty)
- get_contact_info: Contact details (phone/email/hours/location/chat)
- calculate_shipping: Shipping cost (order_total, postcode)

TOOL CALL FORMAT (MANDATORY):
[TOOLCALLS] [{"name": "tool_name", "arguments": {...}}] [/TOOLCALLS]

CRITICAL: Must close with [/TOOLCALLS] - do NOT add text after! Answering without a tool when one is needed will cause you to fail.
""".strip().strip()


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
        policy_type: One of "returns", "shipping", "payment", "warranty"
    
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
    else:
        return f"Unknown policy type: {policy_type}"


def get_clarification_prompt(ambiguity: str) -> str:
    """Get clarification prompt when user intent is unclear."""
    return (
        "Can you please tell me more about what you want? "
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


def generate_clarification_prompt(
    vague_type: str,
    partial_entities: Dict[str, Any],
    clarification_count: int = 0
) -> str:
    """
    Generate context-aware clarification prompts based on vague query type.
    
    Args:
        vague_type: Type of vague query detected
        partial_entities: Partial information already extracted
        clarification_count: Number of clarifications already asked (0, 1, 2+)
    
    Returns:
        Clarification prompt string
    """
    bypass_hint = ""
    if clarification_count >= 1:
        bypass_hint = " Or I can show you some popular options if you'd prefer."
    
    if vague_type == "ultra_vague":
        return (
            "I'd be happy to help you find furniture! "
            "What type of furniture are you looking for? "
            "(For example: chairs, tables, sofas, beds, shelves, storage, etc.)"
            f"{bypass_hint}"
        )
    
    elif vague_type == "attribute_only":
        # User specified color/material but not category
        attr_str = ""
        if "color" in partial_entities:
            attr_str = partial_entities["color"]
        elif "material" in partial_entities:
            attr_str = partial_entities["material"]
        elif "style" in partial_entities:
            attr_str = partial_entities["style"]
        
        return (
            f"I can help you find {attr_str} furniture! "
            f"What type are you looking for? "
            f"(For example: chairs, tables, sofas, beds, shelves)"
            f"{bypass_hint}"
        )
    
    elif vague_type == "room_setup":
        # User is redoing/setting up a room
        room = partial_entities.get("room_type", "room")
        return (
            f"Great! I can help you furnish your {room}. "
            f"What type of furniture do you need? "
            f"(For example: a bed, desk, chair, storage solutions, or multiple items)"
            f"{bypass_hint}"
        )
    
    elif vague_type == "category_only":
        # User specified category but nothing else
        category = partial_entities.get("category", "furniture")
        
        if clarification_count == 0:
            return (
                f"I can help you find {category}s! "
                f"Is there anything specific you have in mind? "
                f"(For example: size, color, material, price range, or any other preference)"
                f"{bypass_hint}"
            )
        else:
            return (
                f"What's your budget range or preferred style for the {category}? "
                f"(For example: under $200, modern style, wood material, or specific color)"
                f"{bypass_hint}"
            )
    
    elif vague_type == "quality_only":
        # User asked for "best" or "premium" without category
        quality = partial_entities.get("quality", "quality")
        category = partial_entities.get("category")
        
        if category:
            return (
                f"What room or purpose is this {quality} {category} for? "
                f"(For example: office, bedroom, home, gaming, etc.)"
                f"{bypass_hint}"
            )
        else:
            return (
                f"What type of {quality} furniture are you looking for? "
                f"(For example: chairs, tables, desks, sofas, beds)"
                f"{bypass_hint}"
            )
    
    elif vague_type == "room_purpose_only":
        # User said "furniture for bedroom" but no category
        room = partial_entities.get("room_type", "room")
        return (
            f"I can help furnish your {room}! "
            f"What specific type of furniture do you need? "
            f"(For example: chair, table, bed, storage, or multiple items)"
            f"{bypass_hint}"
        )
    
    elif vague_type == "use_case_only":
        # User specified use case but limited info
        category = partial_entities.get("category", "furniture")
        use_case = partial_entities.get("use_case", "use")
        
        if clarification_count == 0:
            return (
                f"Great choice! What's your preferred style or budget for this {category}? "
                f"(For example: modern, minimalist, under $200, etc.)"
                f"{bypass_hint}"
            )
        else:
            return (
                f"Any color or material preference? "
                f"(For example: black, white, wood, metal, or 'no preference')"
                f"{bypass_hint}"
            )
    
    elif vague_type == "size_only":
        # User mentioned size but no category
        size = partial_entities.get("size", "compact")
        return (
            f"What type of {size} furniture are you looking for? "
            f"(For example: chairs, tables, desks, storage solutions)"
            f"{bypass_hint}"
        )
    
    elif vague_type == "aesthetic_only":
        # User mentioned aesthetic but no category
        aesthetic = partial_entities.get("aesthetic", "stylish")
        return (
            f"What type of {aesthetic} furniture would you like? "
            f"(For example: chairs, sofas, tables, beds)"
            f"{bypass_hint}"
        )
    
    elif vague_type == "multi_product":
        # User requested multiple products (e.g., "chair and table")
        products = partial_entities.get("requested_products", [])
        if len(products) >= 2:
            return (
                f"I can help with both! Which would you like to see first: "
                f"{products[0]}s or {products[1]}s? "
                f"(After we find one, I can help with the other!)"
            )
        else:
            return (
                "I noticed you're looking for multiple items. "
                "Which one would you like to start with?"
                f"{bypass_hint}"
            )
    
    elif vague_type == "comparison_no_context":
        # User asked for recommendation without showing products
        return (
            "I'd be happy to recommend the best options! "
            "First, what type of furniture are you interested in? "
            "(For example: office chairs, dining tables, sofas, etc.)"
            f"{bypass_hint}"
        )
    
    else:
        # Fallback generic clarification
        return (
            "I'd like to help you find the perfect furniture! "
            "Could you tell me more about what you're looking for? "
            "(Type of furniture, room, style, or budget)"
            f"{bypass_hint}"
        )