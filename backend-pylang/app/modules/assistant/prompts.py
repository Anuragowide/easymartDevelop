"""
System prompt and response templates for Easymart Assistant.

Optimized for OpenAI GPT-4.1 with tool calling via LangChain.
All enforcement/validation is handled in the backend.
"""

from typing import Dict, Any
from .categories import CATEGORY_MAPPING


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
            "Monday-Friday: 9:00 AM - 6:00 PM AEST, "
            "Saturday: 10:00 AM - 4:00 PM AEST, "
            "Sunday: Closed"
        ),
        "response_time": "24-48 hours for email inquiries",
        "live_chat": "Available during business hours via website"
    },
    "location": {
        "warehouse": "Sydney, NSW, Australia",
        "showroom": "Visit our showroom by appointment",
        "pickup": "Click & Collect available at our warehouse"
    }
}


# -------------------------------------------------------------------
# Policies (Returned via templates, NOT hard-coded in system prompt)
# -------------------------------------------------------------------

POLICIES: Dict = {
    "returns": {
        "period": "30 days",
        "condition": "Items must be unused and in original packaging",
        "exclusions": "Custom-made items, final sale items, mattresses",
        "refund": "Original payment method within 5-10 business days",
    },
    "shipping": {
        "free_threshold": 199.00,
        "standard_cost": 15.00,
        "delivery_time": "5-10 business days (metro), 10-15 (regional)",
        "express_available": True,
        "express_cost": 35.00,
        "express_time": "2-5 business days",
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
# SYSTEM PROMPT (OPTIMIZED FOR OPENAI GPT-4.1)
# -------------------------------------------------------------------


def _get_category_overview() -> str:
    overview = []
    for category, subcategories in CATEGORY_MAPPING.items():
        examples = subcategories[:4]
        if len(subcategories) > 4:
            examples_str = ", ".join(examples) + f" (+{len(subcategories) - 4} more)"
        else:
            examples_str = ", ".join(examples)
        overview.append(f"- {category}: {examples_str}")
    return "\n".join(overview)


def get_system_prompt() -> str:
    category_overview = _get_category_overview()

    return f"""
You are Easymart Shopping Assistant for Easymart (Australia's online store).

Product categories we offer:
{category_overview}

Scope:
- We sell furniture AND sports/fitness gear, boxing/MMA equipment, electric scooters, and pet products.
- We also carry office and retail accessories (power points, screens, whiteboards, CCTV, projectors, speakers, etc.).
- Always search for the exact category the customer requests.

Behavior:
- Be helpful, clear, and concise. Ask one question at a time when clarification is needed.
- Use tools for product data, specifications, availability, cart actions, and policies.
- Do NOT invent product details. If specs are needed, call the specs tool.
- When a user asks for comparisons or recommendations about shown products, use compare_products.
- If the user asks for "more options" or adds new constraints, refine the last shown results or bundle with the new constraint.
- Maintain a short shopping brief (budget, room, style, color, material). Reuse it unless the user changes it.

Clarification rule (CRITICAL - Ask OR Search, never both):
- If the user request is broad or vague, ask a clarifying question WITHOUT calling any search/bundle tools.
- NEVER call search_products, build_bundle, or any product tools while asking a clarification question.
- Example: "puppy starter supplies, $250" is vague - ask which specific items they need (bed, bowl, leash, etc.) WITHOUT searching.
- If the request is specific enough (explicit product types like "dog bed and food bowl"), then search immediately.
- If the user mentions a small/limited space for tables or desks, ask for the available length and width in cm.
- Rule: Either ask a question OR show products, NEVER both at the same time.

Product references:
- Resolve references like "option 1", "first one", "the second chair" using the shown products.

Tool usage:
- search_products for any product discovery.
- get_product_specs for questions about dimensions, materials, colors, weight capacity, etc.
- check_product_fit for any fit/space questions.
- search_small_space for product searches constrained by available space dimensions.
- update_cart for add/remove/update/view/clear cart actions.
- get_policy_info for returns/shipping/payment/warranty.
- get_contact_info for contact details.
- calculate_shipping for shipping cost questions.
- build_bundle for multi-item bundle requests with total budget (e.g., "5 tables and 6 chairs under $2000").
- Use build_bundle with strategy "closest_to_budget" when a total budget is given and the user wants the best mix.
- build_cheapest_bundle when the user wants the lowest possible total or says "cheapest".

Response rules:
- Answer only what was asked; do not dump full specs for a single-attribute question.
- Keep responses conversational and focused on shopping assistance.
- Prefer in-stock items; avoid recommending out-of-stock products.
- After showing a bundle, offer to refine it (color/material/style) or suggest another bundle.
""".strip()


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
        f"Welcome to {STORE_INFO['name']}!\n\n"
        "I can help you find:\n"
        "- Sports and Fitness equipment (gym, boxing, MMA, weights)\n"
        "- Electric scooters\n"
        "- Office furniture (desks, chairs, storage)\n"
        "- Home furniture (bedroom, living room, dining)\n"
        "- Pet products (kennels, cages, supplies)\n\n"
        "What are you looking for today?"
    )


def get_no_results_message(query: str) -> str:
    return f"I could not find any products matching \"{query}\" in our catalog."


def get_spec_not_available_message(product_name: str, spec_type: str) -> str:
    return (
        f"I do not have {spec_type} information for {product_name}. "
        f"You can check the product page on {STORE_INFO['website']} "
        f"or contact us on {STORE_INFO['contact']['phone']}."
    )


# -------------------------------------------------------------------
# BACKWARD COMPATIBILITY WRAPPERS
# -------------------------------------------------------------------


def get_policy_text(policy_type: str) -> str:
    if policy_type == "returns":
        return get_returns_policy_text()
    if policy_type == "shipping":
        return get_shipping_policy_text()
    if policy_type == "payment":
        return get_payment_policy_text()
    if policy_type == "warranty":
        return get_warranty_policy_text()
    return f"Unknown policy type: {policy_type}"


def get_clarification_prompt(ambiguity: str) -> str:
    return (
        "Can you please tell me more about what you want? "
        "This will help me find exactly what you are looking for."
    )


def get_empty_results_prompt(query: str) -> str:
    return get_no_results_message(query)


def get_spec_not_found_prompt(product_name: str, spec_type: str) -> str:
    return get_spec_not_available_message(product_name, spec_type)


TOOL_CALL_FORMAT = "tool_name(arguments)"

RESPONSE_RULES = """
After receiving tool results:
- Provide a short intro (1-2 sentences)
- Do not list products exhaustively; the UI shows cards
- Never expose tool syntax to users
"""


def generate_clarification_prompt(
    vague_type: str,
    partial_entities: Dict[str, Any],
    clarification_count: int = 0
) -> str:
    bypass_hint = ""
    if clarification_count >= 1:
        bypass_hint = " Or I can show popular options if you prefer."

    if vague_type == "ultra_vague":
        return (
            "I can help with furniture, fitness gear, scooters, and pet products. "
            "What type of item are you looking for?"
            f"{bypass_hint}"
        )

    if vague_type == "attribute_only":
        attr_str = ""
        if "color" in partial_entities:
            attr_str = partial_entities["color"]
        elif "material" in partial_entities:
            attr_str = partial_entities["material"]
        elif "style" in partial_entities:
            attr_str = partial_entities["style"]

        return (
            f"I can help you find {attr_str} products. "
            "What type are you looking for?"
            f"{bypass_hint}"
        )

    if vague_type == "room_setup":
        room = partial_entities.get("room_type", "room")
        return (
            f"Great! What type of furniture do you need for your {room}?"
            f"{bypass_hint}"
        )

    if vague_type == "category_only":
        category = partial_entities.get("category", "furniture")
        if clarification_count == 0:
            return (
                f"I can help you find {category}s. Any preferences (size, color, material, budget)?"
                f"{bypass_hint}"
            )
        return (
            f"What is your budget range or preferred style for the {category}?"
            f"{bypass_hint}"
        )

    if vague_type == "quality_only":
        quality = partial_entities.get("quality", "quality")
        category = partial_entities.get("category")
        if category:
            return (
                f"What room or purpose is this {quality} {category} for?"
                f"{bypass_hint}"
            )
        return (
            f"What type of {quality} furniture are you looking for?"
            f"{bypass_hint}"
        )

    if vague_type == "room_purpose_only":
        room = partial_entities.get("room_type", "room")
        return (
            f"What type of furniture do you need for your {room}?"
            f"{bypass_hint}"
        )

    if vague_type == "use_case_only":
        category = partial_entities.get("category", "furniture")
        if clarification_count == 0:
            return (
                f"Great choice. Any style or budget preferences for this {category}?"
                f"{bypass_hint}"
            )
        return (
            f"Any color or material preference for the {category}?"
            f"{bypass_hint}"
        )

    if vague_type == "size_only":
        size = partial_entities.get("size", "compact")
        return (
            f"What type of {size} furniture are you looking for?"
            f"{bypass_hint}"
        )

    if vague_type == "aesthetic_only":
        aesthetic = partial_entities.get("aesthetic", "stylish")
        return (
            f"What type of {aesthetic} furniture would you like?"
            f"{bypass_hint}"
        )

    if vague_type == "multi_product":
        products = partial_entities.get("requested_products", [])
        if len(products) >= 2:
            return (
                f"Which would you like to see first: {products[0]}s or {products[1]}s?"
            )
        return "Which item would you like to start with?"

    if vague_type == "comparison_no_context":
        return (
            "I can recommend the best options. First, what type of product are you interested in?"
            f"{bypass_hint}"
        )

    return (
        "Could you tell me more about what you are looking for?"
        f"{bypass_hint}"
    )


def get_clarification_prompt_for_room(room: str, options: list, display_options: list = None) -> str:
    if not options:
        return f"What type of {room.replace('_', ' ')} furniture are you looking for?"

    room_display = room.replace('_', ' ').title()
    formatted_options = display_options if display_options else options

    options_list = "\n".join([f"- {opt}" for opt in formatted_options])
    return (
        f"Great! What are you looking for in your {room_display}?\n\n"
        f"{options_list}\n\n"
        "Which one interests you?"
    )


def get_clarification_prompt_for_category(category: str = None) -> str:
    if category:
        return f"What type of {category} are you looking for? Could you be more specific?"

    return (
        "I would love to help. What type of product are you looking for?\n\n"
        "We have:\n"
        "- Sports and Fitness\n"
        "- Electric Scooters\n"
        "- Office Furniture\n"
        "- Home Furniture\n"
        "- Pet Products\n\n"
        "What interests you?"
    )


def get_preference_clarification(product_type: str) -> str:
    preference_questions = {
        "bed": "What size are you looking for? (Single, Queen, King)",
        "mattress": "What size and firmness? (Single/Queen/King, Firm/Medium/Soft)",
        "sofa": "How many seats? (2-seater, 3-seater, corner sofa)",
        "desk": "What style? (Standing, L-shaped, compact)",
        "chair": "What type? (Office, dining, gaming)",
    }

    return preference_questions.get(
        product_type,
        f"Any specific preferences for the {product_type}? (size, color, material)"
    )
