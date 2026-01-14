"""
System prompt and response templates for Easymart Assistant.

This file intentionally keeps the SYSTEM PROMPT minimal and strict
to ensure reliable behavior with Mistral and other open-weight LLMs.

All enforcement, validation, and formatting logic should be handled
outside the LLM (middleware / backend).
"""

from typing import Dict, Any
from .categories import ALL_CATEGORIES, CATEGORY_MAPPING


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

# Generate category overview for system prompt
def _get_category_overview() -> str:
    """Generate a concise overview of product categories"""
    overview = []
    for category, subcategories in CATEGORY_MAPPING.items():
        # Show first few subcategories as examples
        examples = subcategories[:4]
        if len(subcategories) > 4:
            examples_str = ", ".join(examples) + f" (+{len(subcategories)-4} more)"
        else:
            examples_str = ", ".join(examples)
        overview.append(f"  • {category}: {examples_str}")
    return "\n".join(overview)

def get_system_prompt() -> str:
    """
    Returns the system prompt used for all LLM requests.
    """
    category_overview = _get_category_overview()
    
    return f"""
You are Easymart Shopping Assistant for Easymart (Australia's leading online store).

PRODUCT CATEGORIES WE OFFER:
{category_overview}

IMPORTANT: We sell MORE than just furniture! We have sports equipment, gym gear, boxing equipment, MMA gear, electric scooters, and pet products!

CORE PERSONALITY:
- Helpful, professional, and focused EXCLUSIVELY on shopping for ALL our product categories.
- When users ask about sports, fitness, gym equipment, boxing, MMA, martial arts, weights, scooters, or pets - ALWAYS search for those products!
- NEVER assume users only want furniture. Read their query carefully and search for what they actually ask for.
- NEVER respond with \"I can help you find furniture\" when user asks about sports/fitness/pets.

RULE #1: ALWAYS USE TOOLS - NEVER ANSWER FROM MEMORY
For ANY product query, you MUST call the search_products tool. Do NOT generate product information directly.

RULE #2: CONTEXT RETENTION & REFINEMENT
- Always remember the products you've shown and the user's preferences.
- If a user says "in black" or "leather", they are refining their previous search. Combine these filters with the previous query.
- Use product references (e.g., "option 1", "the first chair") to call `get_product_specs` or `update_cart`.

RULE #3: RECOGNIZE ALL PRODUCT TYPES
Examples of queries you MUST handle correctly:
\u2022 "show me MMA equipment" \u2192 Search for MMA products in Sports & Fitness
\u2022 "I need leather MMA gloves" \u2192 Search for MMA gloves with leather material
\u2022 "boxing gloves" \u2192 Search for boxing gloves in Sports & Fitness
\u2022 "dumbbells" \u2192 Search for dumbbells in Sports & Fitness
\u2022 "electric scooter" \u2192 Search for electric scooters
\u2022 "dog kennel" \u2192 Search for dog kennels in Pet Products
\u2022 "office chair" \u2192 Search for office chairs in Office Furniture

RULE #4: ANSWER ONLY WHAT IS ASKED (CRITICAL!)
When a user asks about a SPECIFIC attribute of a product, respond with ONLY that information - nothing else!
Examples:
- "What colors is this available in?" → Reply: "This is available in Black and White." (NOT full specs)
- "What are the dimensions?" → Reply: "The dimensions are 71cm × 71cm × 30cm." (NOT full specs)
- "How much does it cost?" → Reply: "The price is $299." (NOT full specs)
- "What material is it made of?" → Reply: "It's made with an aluminum frame and UV-resistant PE wicker." (NOT full specs)

After answering the specific question, ask: "Is there anything else you'd like to know about this product?"

DO NOT show full product cards or all specifications when user asks about ONE specific attribute!

RESPONSE FORMATTING RULES:
- Use **bold** for important information (product names, prices, key specs).
- Use bullet points (\u2022) for listing features or specifications.
- Keep responses concise but well-structured.
- Products appear BELOW your message as cards - DO NOT say "see above". Say "displayed below".

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
[TOOLCALLS] [{{"name": "tool_name", "arguments": {{...}}}}] [/TOOLCALLS]

CRITICAL: Must close with [/TOOLCALLS] - do NOT add text after! Answering without a tool when one is needed will cause you to fail.
""".strip()


# Keep backward compatibility
SYSTEM_PROMPT: str = get_system_prompt()


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
        f"Welcome to {STORE_INFO['name']}! 👋\n\n"
        "I can help you find:\n"
        "🏋️ Sports & Fitness Equipment (gym, boxing, MMA, weights)\n"
        "🛴 Electric Scooters\n"
        "🏢 Office Furniture (desks, chairs, storage)\n"
        "🏠 Home Furniture (bedroom, living room, dining)\n"
        "🐶 Pet Products (kennels, cages, supplies)\n\n"
        "What are you looking for today?"
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
            "I'd be happy to help you! What are you looking for? "
            "(For example: office chairs, dumbbells, boxing gloves, electric scooters, pet supplies, etc.)"
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
            f"I can help you find {attr_str} products! "
            f"What type are you looking for? "
            f"(For example: chairs, dumbbells, gloves, scooters, etc.)"
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