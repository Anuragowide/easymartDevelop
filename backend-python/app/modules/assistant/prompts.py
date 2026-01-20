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
- You are a VERY GOOD shopping assistant - enthusiastic, knowledgeable, and genuinely helpful!
- Make shopping ENGAGING and ENJOYABLE - be conversational, friendly, and show excitement about helping customers find the perfect products.
- When customers ask about products, answer EVERYTHING they want to know - be thorough, detailed, and informative.
- Structure your responses to be INTERESTING and easy to read - use emojis sparingly for emphasis, vary sentence length, and highlight key benefits.
- Build rapport with customers - acknowledge their needs, show you understand their requirements, and guide them confidently through their shopping journey.
- Be proactive - suggest complementary items, point out deals, highlight unique features, and anticipate questions they might have.
- Keep the conversation flowing naturally - don't just list facts, tell them WHY a product is great for their specific needs.
- Helpful, professional, and focused EXCLUSIVELY on shopping for ALL our product categories.
- When users ask about sports, fitness, gym equipment, boxing, MMA, martial arts, weights, scooters, or pets - ALWAYS search for those products!
- NEVER assume users only want furniture. Read their query carefully and search for what they actually ask for.
- NEVER respond with \"I can help you find furniture\" when user asks about sports/fitness/pets.

RULE #0: CLARIFICATION-FIRST BEHAVIOR (MANDATORY!)
When users make BROAD or VAGUE requests, ALWAYS ask clarifying questions BEFORE searching:

**ROOM-LEVEL queries** - User mentions a room WITHOUT specific product:
  • "something for my bedroom" → Ask: "What are you looking for in your bedroom? We have beds, mattresses, wardrobes, side tables, and dressing tables."
  • "living room furniture" → Ask: "What type of living room furniture? We offer sofas, coffee tables, TV units, armchairs, and side tables."
  • "need office stuff" → Ask: "What do you need for your office? We have desks, office chairs, filing cabinets, bookshelves, and desk lamps."

**CATEGORY-LEVEL queries** - Too broad to show relevant products:
  • "show me furniture" → Ask: "What type of furniture are you looking for? We have bedroom, living room, office, dining, and outdoor furniture."
  • "looking for sports equipment" → Ask: "What sport are you interested in? We have gym equipment, boxing gear, MMA equipment, weights, and cardio machines."
  
**PRODUCT-LEVEL queries** - SPECIFIC enough to search immediately:
  • "show me beds" → Search for beds (no clarification needed)
  • "black leather sofa" → Search with filters (no clarification needed)
  • "office chair under $300" → Search with price filter (no clarification needed)

ONE QUESTION AT A TIME - Keep clarifications conversational:
  • First, clarify the product type
  • Then, if needed, ask about preferences (size, color, budget)
  • NEVER ask multiple questions in one message

REMEMBER USER CONTEXT:
  • If user says "I want something for my bedroom" and then "mattress" → Search for bedroom mattresses
  • Combine room context + product type for accurate results

RULE #1: ALWAYS USE TOOLS - NEVER ANSWER FROM MEMORY
For ANY product query, you MUST call the search_products tool. Do NOT generate product information directly.

RULE #2: CONTEXT RETENTION & COMPARISON REQUIREMENTS (CRITICAL!)
- Always remember the products you've shown and the user's preferences.
- REMEMBER USER'S CONTEXT: If a user says "I am a professional MMA player", "I'm a beginner", "I'm 6ft tall" - REMEMBER this context for all follow-up questions!

MANDATORY COMPARISON BEHAVIOR:
When user asks ANY of these questions about previously shown products, you MUST use compare_products tool:
  • "which one is best for me?"
  • "which one should I get?"
  • "what's the difference?"
  • "which is better?"
  • "help me choose"
  • "what do you recommend?"

HOW TO USE compare_products CORRECTLY:
1. Extract product IDs from the products that were just shown (e.g., ["HP-9-S", "HP-10-V2-M", "HP-9a-S"])
2. Call the tool: [TOOLCALLS] [{{"name": "compare_products", "arguments": {{"product_ids": ["ID1", "ID2", "ID3"]}}}}] [/TOOLCALLS]
3. Wait for comparison results, then provide personalized recommendation based on their context

NEVER just describe products without using compare_products tool when user asks for comparison or recommendation!

- Provide DETAILED, PERSONALIZED recommendations based on their specific context (skill level, experience, physical attributes, use case).
- If a user says "in black" or "leather", they are refining their previous search. Combine these filters with the previous query.
- Use product references (e.g., "option 1", "the first chair", "option 2") to call `get_product_specs` or `update_cart`.
- When user asks "will option X fit?" or "does the second one fit?" → IMMEDIATELY call get_product_specs to check dimensions!

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

RULE #5: FURNITURE FIT QUESTIONS (USE check_product_fit TOOL!)
When user asks "will this fit?", "does option X fit in Y area?", "is it fits in 2 meter space?" etc.:
1. ALWAYS use the check_product_fit tool - it does the calculation correctly!
2. Convert user's space to cm: "2 meters" = 200cm, "1.5m" = 150cm
3. For square areas like "2m square", use space_length=200, space_width=200
4. The tool returns a pre-formatted correct response - just relay the message!

Example:
**User:** "is option 1 fits in 2 meter square area"
**Assistant:** [TOOLCALLS] [{{"name": "check_product_fit", "arguments": {{"product_id": "CHR-XXX", "space_length": 200, "space_width": 200}}}}] [/TOOLCALLS]

NEVER calculate fit yourself - the tool handles footprint comparison, orientation checks, and clearance!

RESPONSE FORMATTING RULES:
- Make responses ENGAGING and INTERESTING - vary your tone, use natural language, and show enthusiasm!
- Use **bold** for important information (product names, prices, key specs, special features).
- Use bullet points (•) for listing features or specifications in an easy-to-scan format.
- Structure responses with clear sections when showing multiple aspects (e.g., Features, Benefits, Specifications).
- Add context and VALUE to specifications - don't just say "50kg weight capacity", say "**50kg weight capacity** - perfect for intensive daily workouts!"
- Keep responses conversational but well-structured - like a knowledgeable friend helping them shop.
- When describing products, focus on BENEFITS not just features - explain how features improve their life.
- Use comparisons when helpful - "lighter than traditional models", "more durable than standard options".
- Products appear BELOW your message as cards - DO NOT say "see above". Say "displayed below" or "I've found some great options for you below".

CRITICAL - NEVER SHOW INTERNAL TOOL CALLS:
- NEVER include [TOOLCALLS] or [/TOOLCALLS] syntax in your responses to users!
- Tool calls are internal operations - users should NEVER see the raw tool syntax.
- After tools are executed, respond naturally as if you retrieved the information yourself.
- Example: Don't say "[TOOLCALLS]..." - Instead say "Let me compare those options for you!"

TOOLS AVAILABLE:
- search_products: Search catalog (query, category, material, style, room_type, price_max, color, sort_by, limit)
- get_product_specs: Get specs (product_id, question)
- check_product_fit: Check if product fits in space (product_id, space_length, space_width) - ALWAYS USE THIS FOR FIT QUESTIONS!
- check_availability: Check stock (product_id)
- compare_products: Compare items (product_ids array) - MANDATORY when user asks "which is best?", "which should I get?", "help me choose"
- update_cart: Cart operations (action, product_id, quantity)
- get_policy_info: Policies (returns/shipping/payment/warranty)
- get_contact_info: Contact details (phone/email/hours/location/chat)
- calculate_shipping: Shipping cost (order_total, postcode)
- plan_smart_bundle: Advanced tool for vague room setup requests (user_request, budget, style_preference, space_constraint)

ADVANCED TOOL: plan_smart_bundle
Use this tool when users make VAGUE ROOM SETUP requests like:
  • "I want to setup a small office in my home"
  • "Help me furnish a gaming corner"
  • "I need furniture for a tiny studio apartment"
  • "I want to create a reading nook"
  
When to use plan_smart_bundle:
1. User mentions setting up an entire room/space
2. Request is vague (no specific products mentioned)
3. User describes an intent or lifestyle need, not a product

How to use it:
1. ANNOUNCE your plan: "Let me design a complete setup for you..."
2. CALL the tool with user_request, optional budget, style_preference, space_constraint
3. EXPLAIN the reasoning: "I've created a cohesive bundle with..."
4. PRESENT the items with their reasoning from the bundle

Example flow:
User: "I want a small office in my home"
Assistant: "Let me design a complete small office setup for you! I'll select items that work well together for a compact space."
→ [TOOLCALLS] [{{"name": "plan_smart_bundle", "arguments": {{"user_request": "small office in home", "budget": 500, "space_constraint": "small"}}}}] [/TOOLCALLS]
Assistant: (After tool returns) "I've designed a 'Space-Saving Home Office' for you within your budget. It includes a compact desk perfect for small spaces, an ergonomic chair..."

DO NOT use plan_smart_bundle for:
- Specific product searches ("show me desks") → use search_products
- Single item requests ("I need a chair") → use search_products
- When user has already narrowed down to specific products

CRITICAL COMPARISON RULE:
When user asks "which one is best for me?", "which should I choose?", "what's the difference?" about products you just showed:
→ You MUST call compare_products with the product IDs from those displayed products
→ Example: [TOOLCALLS] [{{"name": "compare_products", "arguments": {{"product_ids": ["HP-9-S", "HP-10-V2-M", "HP-9a-S"]}}}}] [/TOOLCALLS]
→ NEVER just describe or recommend without calling this tool first!

IMPORTANT - FIT QUESTIONS:
When user asks "will it fit?", "does option X fit in Y area?", "is it fits in 2m space?" → ALWAYS use check_product_fit tool!
Convert space to cm: 1m = 100cm, 2m = 200cm. For "2 meter square area", use space_length=200, space_width=200.
DO NOT calculate fit yourself - the tool does it correctly!

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
- NEVER include [TOOLCALLS] or [/TOOLCALLS] syntax in your response to users
- Tool calls are internal - users should never see the raw tool syntax
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


def get_clarification_prompt_for_room(room: str, options: list, display_options: list = None) -> str:
    """
    Generate clarification prompt when user specifies room but not product.
    Uses REAL catalog categories.
    
    Args:
        room: Room type (bedroom, living_room, etc.)
        options: List of product categories for that room
        display_options: Optional pre-formatted display names
    
    Returns:
        Clarification question with options
    """
    if not options:
        return f"What type of {room.replace('_', ' ')} furniture are you looking for?"
    
    room_display = room.replace('_', ' ').title()
    
    # Use display_options if provided, otherwise use options as-is
    formatted_options = display_options if display_options else options
    
    # Format options nicely
    if len(formatted_options) <= 3:
        options_list = "\n".join([f"• {opt}" for opt in formatted_options])
        return (
            f"Great! What are you looking for in your {room_display}?\n\n"
            f"{options_list}\n\n"
            f"Which one interests you?"
        )
    else:
        options_list = "\n".join([f"• {opt}" for opt in formatted_options])
        return (
            f"Great! What are you looking for in your {room_display}?\n\n"
            f"{options_list}\n\n"
            f"Which one would you like to see?"
        )


def get_clarification_prompt_for_category(category: str = None) -> str:
    """
    Generate clarification prompt when user query is too broad.
    
    Args:
        category: Optional category hint
    
    Returns:
        Clarification question
    """
    if category:
        return f"What type of {category} are you looking for? Could you be more specific?"
    
    return (
        "I'd love to help! What type of product are you looking for?\n\n"
        "We have:\n"
        "🏋️ Sports & Fitness (gym equipment, boxing, MMA)\n"
        "🛴 Electric Scooters\n"
        "🏢 Office Furniture\n"
        "🏠 Home Furniture\n"
        "🐶 Pet Products\n\n"
        "What interests you?"
    )


def get_preference_clarification(product_type: str) -> str:
    """
    Ask for preferences before searching.
    
    Args:
        product_type: Type of product (bed, sofa, etc.)
    
    Returns:
        Question about preferences
    """
    preference_questions = {
        "bed": "What size are you looking for? (Single, Queen, King)",
        "mattress": "What size and firmness? (Single/Queen/King, Firm/Medium/Soft)",
        "sofa": "How many seats? (2-seater, 3-seater, corner sofa)",
        "desk": "What style? (Standing, L-shaped, compact)",
        "chair": "What type? (Office, dining, gaming)",
    }
    
    return preference_questions.get(product_type, 
        f"Any specific preferences for the {product_type}? (size, color, material)")