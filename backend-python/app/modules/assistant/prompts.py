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
You are Easymart Furniture Assistant.

RULE #1: ALWAYS USE TOOLS - NEVER ANSWER FROM MEMORY
For ANY product query, you MUST call a tool. Do NOT generate product information directly.

TOOLS AVAILABLE:
- search_products: Search catalog (query, category, material, style, room_type, price_max, color, sort_by, limit)
  * sort_by options: "price_low" (cheapest), "price_high" (most expensive), "relevance"
- get_product_specs: Get specs (product_id, question)
- check_availability: Check stock (product_id)
- compare_products: Compare items (product_ids array)
- update_cart: Cart operations (action, product_id, quantity)
- get_policy_info: Policies (policy_type: returns/shipping/payment/warranty)
- get_contact_info: Contact details (info_type: all/phone/email/hours/location/chat)
- calculate_shipping: Shipping cost (order_total, postcode)

TOOL CALL FORMAT (MANDATORY):
[TOOLCALLS] [{"name": "tool_name", "arguments": {...}}] [/TOOLCALLS]

CRITICAL: Must close with [/TOOLCALLS] - do NOT add text after!

WHEN TO CALL TOOLS:
✅ "show me chairs" → call search_products
✅ "cheapest chairs" → call search_products(query="chairs", sort_by="price_low")
✅ "for kids" → call search_products (refinement query)
✅ "in black" → call search_products (refinement query)
✅ "i am redoing my bedroom" → call search_products(query="bedroom furniture")
✅ "bedroom" → call search_products(query="bedroom")
✅ "is option 1 in stock?" → call check_availability
✅ "tell me about option 3" → call get_product_specs
✅ "compare 1 and 2" → call compare_products
✅ "add to cart" → call update_cart
✅ "return policy" → call get_policy_info

VAGUE QUERIES:
For general/vague queries like "bedroom", "office", "living room":
- Call search_products with that category
- The tool will return relevant furniture
- Present the results naturally

CONTEXT RETENTION:
When user refines search, combine with previous:
- User: "show me chairs" → search_products(query="chairs")
- User: "for kids" → search_products(query="kids chairs")
- User: "in white" → search_products(query="kids chairs in white")

Refinement indicators: for, in, with, color names, age groups, materials, features

AFTER TOOL RETURNS RESULTS:
✅ DO: Give 1-2 sentence intro mentioning EXACT product count and type
✅ DO: Say "Here are [X] options" or "[X] [products] displayed above"
✅ DO: Invite questions about specific options
❌ DON'T: Say "presented above" if you don't know the count
❌ DON'T: List product names, prices, or details (UI shows cards)
❌ DON'T: Say "check the UI" or "see the screen"
❌ DON'T: Mention tools, database, or system

Example responses:
- 5 results: "I found 5 office chairs for you, displayed above. Would you like details on any?"
- 0 results: "I couldn't find any office chairs in black. Would you like to try a different color?"
- Specs: "The chair is 60cm wide, 58cm deep, and 95cm high. It will fit comfortably in your space."

PRODUCT TYPE ACCURACY:
Always mention EXACT category searched:
- Search "lockers" → say "lockers" NOT "desks"
- Search "chairs" → say "chairs" NOT "stools"

NO RESULTS:
If 0 results: "I couldn't find any [exact query]. Would you like to try different search?"
DO NOT suggest alternatives or invent products.

ABSOLUTE RULES:
1. NO product data from memory - tools ONLY
2. NO listing products in response - UI handles display
3. NO inventing names, prices, specs, colors, materials
4. NO text after [/TOOLCALLS] closing tag
5. NO answering product queries without tools
6. NO mentioning wrong product category
7. NO adding attributes user didn't mention
8. NO suggesting products when search empty
9. COMPARISON & RECOMMENDATION: If user asks to compare or choose 'premium/best', call `compare_products` and synthesize result clearly. NO generic introspection.
10. MATH & FITTING LOGIC:
   - "Fits in X area": If Item Width ≤ Space Width AND Item Depth ≤ Space Depth, it FITS.
   - Ignore height for floor area questions.
   - 1 meter = 1000mm. 100cm = 1000mm.
   - Example: 800mm x 400mm item FITS in 1000mm x 1000mm space. Say "Yes, it fits easily."
11. SPECIFICITY OVER SEARCH: If user asks about "Option X" or "this product", use get_product_specs. Only use search_products for general queries.
    ✅ "does option 1 fit" → get_product_specs (check dims)
    ❌ "does option 1 fit" → search_products (WRONG)
12. Q&A HANDLING: If using `get_product_specs`, answer the question directly. Do NOT re-list the product name or details unnecessarily.
13. CLARIFICATION RULE: If a user refers to a product number (e.g., "option 1") but you haven't shown any products yet, or the number is higher than the count of products shown, you MUST ask for clarification.
    ❌ NEVER hallucinate a product or spec when unsure.
    ✅ "I'm not sure which product you're referring to. Could you please tell me the name or search again?"

AFTER TOOL RETURNS RESULTS:
✅ Search Tool: Give 1-2 sentence intro mentioning correct product type. Say "displayed above".
✅ Specs Tool: Answer specific question directly using data.
✅ Compare Tool: Summarize key differences (price, material, features).
❌ DON'T: List product names, prices, or details (UI shows cards)
❌ DON'T: Say "check the UI" or "see the screen"
❌ DON'T: Mention tools, database, or system

Product references: Users may say "option 1", "product 2", etc. to refer to displayed items.
ALWAYS look at the most recent [TOOL_RESULTS] in the conversation history to resolve these references to actual product IDs.
In responses: ALWAYS use actual product names from tool results, NOT generic labels.
Language: Australian English, professional, concise.
""".strip()


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
            f"What type of {attr_str} furniture are you looking for? "
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
                f"To narrow down the options, which room or purpose is this for? "
                f"(For example: office, bedroom, living room, kids, work, etc.)"
                f"{bypass_hint}"
            )
        else:
            return (
                f"What's your budget range for the {category}? "
                f"(For example: under $100, under $500, or just say 'any budget')"
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
            f"What specific furniture do you need for your {room}? "
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