"""
Intent Detection

Detects user intent from messages to route to appropriate tools.
Extended for Easymart furniture store with policy and contact intents.
"""

import re
from typing import Optional, Dict, Any
from .intents import IntentType


class IntentDetector:
    """
    Rule-based intent detection for Easymart furniture assistant.
    TODO: Replace with ML-based intent classification for better accuracy.
    """
    
    # Intent patterns for Easymart
    PATTERNS = {
        IntentType.PRODUCT_SEARCH: [
            r'\b(show|find|search|looking for|want|need|browse)\b.*\b(chairs?|tables?|desks?|sofas?|beds?|shelves|shelving|lockers?|stools?|furniture)\b',
            r'\b(office|bedroom|living room|dining)\b.*\b(furniture|chairs?|tables?)\b',
            r'\bdo you have\b.*\b(any|some)\b',
            # NEW: "Tell me about" and information queries
            r'\b(tell me about|what is|what are|information about|info about|details about|describe)\b.*\b(chairs?|tables?|desks?|sofas?|beds?|shelves|shelving|lockers?|stools?|furniture|storage|cabinet)\\b',
            r'\b(tell me about|what is|what are)\b.*\b(police|office|dining|bedroom|living|kitchen)\b',
            r'\b(modern|industrial|rustic|scandinavian|contemporary|minimalist|classic)\b',
            r'\b(wood|metal|leather|fabric|glass|rattan|plastic)\b',
            r'\b(red|blue|green|yellow|black|white|brown|gray|orange|purple|pink)\b',
            r'\b(cheap|expensive|under|over|less than|more than)\b',
            r'\b(show|find)\s+(me|us)\b',
            r'\b(something|anything|something)\s+(red|blue|green|yellow|black|white|brown|gray|orange|purple|pink)\b',
        ],
        IntentType.PRODUCT_SPEC_QA: [
            r'\b(dimensions?|sizes?|width|height|depth|weight|material|color|specifications?|specs?|details?)\b',
            r'\bhow (big|large|small|heavy|long|wide|tall|deep)\b',
            r'\bwhat (is|are) (the|its)\b.*\b(dimensions?|sizes?|material|color|weight)\b',
            r'\b(made of|assembly|care instruction|warranty)\b',
            r'\b(seat|weight capacity|load)\b',
            r'\btell me (about|more about)\s+(product|option|number|item|the)\s+\d+',
            r'\b(product|option|number|item)\s+\d+',
        ],
        IntentType.CART_ADD: [
            r'\b(add|put)\b.*\b(to|in|into)\b.*\b(cart|basket)\b',
            r'\b(buy|purchase|get|order)\b.*\b(this|that|the|it)\b',
            r'\b(i\'ll take)\b.*\b(this|that|the|it|one)\b',
            r'\b(also|too|as well)\s+(add|get|put)\b',
            r'\badd.*\b(also|too|as well)\b',
            r'\bput.*\b(also|too|as well)\b',
            r'\bget.*\b(also|too|as well)\b',
        ],
        IntentType.CART_REMOVE: [
            r'\b(remove|delete|take out|discard)\b.*\b(from|out of)\b.*\b(cart|basket)\b',
            r'\bdon\'t want\b.*\b(anymore|this|that|it)\b',
            r'\bcancel\b.*\b(option|product|item)\b',
        ],
        IntentType.CART_SHOW: [
            r'\b(show|view|see|check|open|display)\b.*\b(cart|basket|items)\b',
            r'\bwhat\'s in\b.*\b(cart|basket|my list)\b',
            r'\b(my cart|my basket|cart contents|view list)\b',
            r'^view cart',  # Matches "view cart", "view cart (1)", etc.
            r'^show cart',  # Matches "show cart", "show cart (2)", etc.
            r'^cart$',
            r'view.*cart',  # General view cart pattern
            r'show.*my.*cart',
            r'what.*in.*cart',
        ],
        IntentType.CART_CLEAR: [
            r'\b(empty|clear|reset|delete|wipe)\b.*\b(cart|basket)\b',
            r'^empty my cart$',
            r'^clear cart$',
        ],
        IntentType.RETURN_POLICY: [
            r'\b(return|refund|exchange)\b.*\b(policy|process|procedure)\b',
            r'\bcan i return\b',
            r'\bhow (long|many days)\b.*\b(return|refund)\b',
            r'\breturn.*\b(period|policy|window)\b',
        ],
        IntentType.SHIPPING_INFO: [
            r'\b(shipping|delivery|freight|postage)\b.*\b(cost|price|fee|charge)\b',
            r'\b(free shipping|delivery fee)\b',
            r'\bhow long\b.*\b(deliver|shipping|delivery)\b',
            r'\b(delivery time|shipping time|arrive)\b',
            r'\bship to\b.*\b(postcode|suburb|location)\b',
        ],
        IntentType.PAYMENT_OPTIONS: [
            r'\b(payment|pay|paying)\b.*\b(method|option|way)\b',
            r'\bdo you accept\b.*\b(card|paypal|afterpay|zip)\b',
            r'\b(afterpay|zip pay|buy now pay later)\b',
        ],
        IntentType.PROMOTIONS: [
            r'\b(discount|offer|sale|promo|promotion|coupon|deal|clearance)\b',
            r'\bany\s+(deals|offers|discounts)\b',
            r'\bis there a sale\b',
        ],
        IntentType.WARRANTY_INFO: [
            r'\b(warranty|guarantee)\b',
            r'\bhow long\b.*\b(warranty|covered)\b',
            r'\bwhat\'s covered\b.*\b(warranty)\b',
        ],
        IntentType.CONTACT_INFO: [
            r'\b(contact|call|phone|email|reach)\b.*\b(you|customer service|support)\b',
            r'\b(phone number|email address|contact details)\b',
            r'\bhow (can|do) i contact\b',
            r'\b(live chat|speak to|talk to)\b.*\b(someone|person|representative)\b',
        ],
        IntentType.STORE_HOURS: [
            r'\b(open|opening|store)\b.*\b(hour|time)\b',
            r'\b(when|what time)\b.*\b(open|close)\b',
            r'\bare you open\b',
        ],
        IntentType.STORE_LOCATION: [
            r'\b(where|location|address|store location)\b',
            r'\b(physical store|warehouse|pickup)\b',
            r'\bcan i visit\b',
        ],
        IntentType.GREETING: [
            r'^\s*(hello|hi|hey|g\'day|greetings|good morning|good afternoon|good evening)\s*$',
            r'^\s*(hi|hey|hello)\s+(there|everyone|guys)?\s*$',
            r'^\s*how\s+are\s+you\s*\??$',
            r'^\s*what\'?s\s+up\s*\??$',
            r'^\s*howdy\s*$',
            # Flexible patterns for greetings
            r'^hi+$',           # hi, hii, hiii
            r'^hey+$',          # hey, heyy, heyyy
            r'^hello+$',        # hello, hellooo
            r'^h[ie]+y*$',      # hi, hii, hey, heyyy
        ],
        IntentType.GENERAL_HELP: [
            r'\b(help|assist|support)\b',
            r'\bwhat can you\b',
            r'\bhow does.*work\b',
        ],
    }
    
    def detect(self, message: str) -> IntentType:
        """
        Detect intent from user message.
        
        Args:
            message: User message text
        
        Returns:
            Detected IntentType enum
        
        Example:
            >>> detector = IntentDetector()
            >>> intent = detector.detect("Show me office chairs")
            >>> print(intent)
            IntentType.PRODUCT_SEARCH
        """
        message_lower = message.lower().strip()
        
        # PRIORITY 0: Check for out-of-scope queries FIRST
        # These are clearly not furniture-related and should not be forced into product search
        out_of_scope_keywords = [
            # Programming & Tech
            r'\b(python|java|javascript|code|programming|coding|function|script|algorithm)\b',
            r'\b(html|css|react|vue|angular|node|npm|git|github)\b',
            r'\b(sql|database|query|api|server|backend|frontend)\b',
            # Vehicles & Transportation
            r'\b(car|cars|vehicle|automobile|motorcycle|bike|truck|van)\b',
            # Electronics (non-furniture)
            r'\b(laptop|computer|pc|mac|tablet|ipad|iphone|smartphone|phone|mobile)\b',
            r'\b(tv|television|camera|watch|headphone|speaker|gaming console)\b',
            # Clothing & Fashion
            r'\b(clothing|clothes|shirt|pants|dress|shoes|jacket|coat|hat)\b',
            # Food & Drinks
            r'\b(food|drink|recipe|cooking|restaurant|meal|dinner|lunch)\b',
            # Health & Medical
            r'\b(doctor|hospital|medicine|health|disease|symptom|treatment)\b',
            # General Knowledge / Educational
            r'\b(math|mathematics|physics|chemistry|biology|history|geography)\b',
            r'\b(definition of|what is the capital|who invented|when did)\b',
            # Entertainment
            r'\b(movie|film|music|song|video game|tv show|netflix|joke)\b',
            # Sports
            r'\b(football|soccer|basketball|tennis|cricket|sports)\b',
            # Weather
            r'\b(weather|temperature|forecast|rain|snow)\b',
            # Travel
            r'\b(flight|hotel|vacation|travel|tourist|trip)\b',
        ]
        
        # If message matches any out-of-scope pattern, return OUT_OF_SCOPE immediately
        if any(re.search(pattern, message_lower) for pattern in out_of_scope_keywords):
            return IntentType.OUT_OF_SCOPE
        
        # PRIORITY 1: Check greetings FIRST (exact matches before pattern matching)
        # This prevents "hi" from being caught by other patterns
        greeting_exact = ['hi', 'hello', 'hey', "g'day", 'greetings', 
                         'good morning', 'good afternoon', 'good evening', 
                         'howdy', 'hi there', 'hello there', 'hey there']
        if message_lower in greeting_exact:
            return IntentType.GREETING
        
        # PRIORITY 2: Check for BROAD product search patterns (catch vague queries)
        # This must come before specific patterns to catch "something for kids", etc.
        broad_product_patterns = [
            r'\b(show|find|search|looking for|want|need|get me)\b',  # Action verbs
            r'\b(something|anything|items|products|furniture)\b',     # Generic nouns
            r'\b(chairs?|tables?|desks?|sofas?|beds?|shelves|shelving|lockers?|stools?)\s+(available|in stock|options|list)\b', # Furniture availability
            r'^(chairs?|tables?|desks?|sofas?|beds?|shelves|shelving|lockers?|stools?)\??$', # Single word furniture?
            r'\bfor\s+(kids|children|baby|toddler|adult|teen|gaming|office|home|bedroom|living room|kitchen|dining|study|outdoor)\b',  # Context - expanded!
            r'\bin\s+(black|white|red|blue|green|brown|grey|gray|wood|metal|leather|fabric)\b',  # Colors/materials with "in"
            r'\bwith\s+(storage|drawers|wheels|cushion|armrest)\b',  # Features with "with"
            r'\b(cheap|affordable|expensive|best|good|quality|nice|premium|luxury|budget)\b',  # Adjectives
            r'\bunder\s+\$?\d+\b',  # Price queries
            r'\b(small|large|big|compact|modern|classic|vintage|contemporary)\b',  # Size/style
        ]
        
        # If ANY broad pattern matches, assume PRODUCT_SEARCH
        if any(re.search(pattern, message_lower) for pattern in broad_product_patterns):
            return IntentType.PRODUCT_SEARCH
        
        # PRIORITY 2.5: Check for potential context refinement words
        # These are single words/short phrases that could refine a previous search
        # Examples: "bedroom", "office", "blue", "metal", "modern"
        refinement_keywords = [
            # Rooms and contexts
            r'^(bedroom|office|living room|dining room|kitchen|bathroom|hallway|garage|outdoor|patio|balcony)s?$',
            # Colors
            r'^(black|white|red|blue|green|yellow|brown|grey|gray|pink|purple|orange|beige|navy|teal|cream|ivory|silver|gold)$',
            # Materials
            r'^(wood|wooden|metal|leather|fabric|glass|plastic|rattan|wicker|bamboo|steel|iron|oak|pine|walnut|marble)$',
            # Styles
            r'^(modern|contemporary|classic|vintage|rustic|industrial|scandinavian|minimalist|traditional|bohemian|mid[\s-]?century)$',
            # Sizes
            r'^(small|large|big|compact|mini|tiny|huge|oversized|extra[\s-]?large|xl|medium)$',
            # Age groups / target users
            r'^(kids|children|adult|baby|toddler|teen|elderly|senior)s?$',
            # Use cases
            r'^(gaming|study|work|storage|dining|sleeping)$',
        ]
        
        # Check if message is a single refinement word
        if any(re.search(pattern, message_lower) for pattern in refinement_keywords):
            return IntentType.PRODUCT_SEARCH  # Treat as product search (will be refined via context)
        
        # PRIORITY 3: Check for context-dependent questions (referring to previously shown products)
        # These should be PRODUCT_SPEC_QA, not PRODUCT_SEARCH
        context_references = [
            r'\btell me (about|more about)\s+(product|option|number|item)',  # "tell me about product 3"
            r'\b(product|option|number|item)\s+\d+',  # "product 3", "option 1"
            r'\b(this|that|the|it)\s+(one|chair|table|desk|sofa|bed|product|item)',
            r'\b(first|second|third|last|option)\s+(one|chair|table|product)',
            r'\b(the|this|that)\s+\$?\d+',
            r'\bmore (info|information|details|about)\s+(this|that|the|it)',
            r'\b(feature|spec|dimension|detail)s?\s+of\s+(this|that|the|it)',
        ]
        for pattern in context_references:
            if re.search(pattern, message_lower):
                return IntentType.PRODUCT_SPEC_QA
        
        # PRIORITY 3: Check greeting patterns
        if IntentType.GREETING in self.PATTERNS:
            for pattern in self.PATTERNS[IntentType.GREETING]:
                if re.search(pattern, message_lower):
                    return IntentType.GREETING
        
        # PRIORITY 4: Check other intent patterns
        for intent, patterns in self.PATTERNS.items():
            if intent == IntentType.GREETING:  # Already checked
                continue
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    return intent
        
        # Default to general help if no specific intent matched
        if len(message.split()) > 3:
            return IntentType.GENERAL_HELP
        
        return IntentType.OUT_OF_SCOPE
    
    def extract_entities(self, message: str, intent: IntentType) -> Dict[str, Any]:
        """
        Extract entities based on detected intent for Easymart furniture.
        
        Args:
            message: User message
            intent: Detected intent
        
        Returns:
            Dictionary of extracted entities
        """
        entities = {}
        message_lower = message.lower()
        
        if intent == IntentType.PRODUCT_SEARCH:
            entities["query"] = message
            
            # Extract category
            categories = {
                "chair": ["chair", "chairs", "seating"],
                "table": ["table", "tables", "desk", "desks"],
                "sofa": ["sofa", "sofas", "couch", "couches"],
                "bed": ["bed", "beds", "mattress"],
                "shelf": ["shelf", "shelves", "shelving", "bookcase"],
                "stool": ["stool", "stools", "bar stool"],
                "locker": ["locker", "lockers", "cabinet", "cabinets"],
                "storage": ["storage", "wardrobe", "dresser"]
            }
            
            for cat, keywords in categories.items():
                if any(kw in message_lower for kw in keywords):
                    entities["category"] = cat
                    break
            
            # Extract price range
            price_under = re.search(r'under\s*\$?(\d+)', message_lower)
            price_below = re.search(r'below\s*\$?(\d+)', message_lower)
            price_max = re.search(r'max(?:imum)?\s*\$?(\d+)', message_lower)
            
            if price_under:
                entities["price_max"] = float(price_under.group(1))
            elif price_below:
                entities["price_max"] = float(price_below.group(1))
            elif price_max:
                entities["price_max"] = float(price_max.group(1))
            
            # Extract color
            colors = ["red", "blue", "green", "yellow", "black", "white", "brown", "gray", "grey", 
                      "orange", "purple", "pink", "beige", "cream", "navy", "silver", "gold"]
            for color in colors:
                if color in message_lower:
                    entities["color"] = color
                    break
            
            # Extract material
            materials = ["wood", "metal", "leather", "fabric", "glass", "rattan", "plastic"]
            for material in materials:
                if material in message_lower:
                    entities["material"] = material
                    break
            
            # Extract style
            styles = ["modern", "contemporary", "industrial", "minimalist", "rustic", "scandinavian", "classic"]
            for style in styles:
                if style in message_lower:
                    entities["style"] = style
                    break
            
            # Extract room type
            rooms = {
                "office": ["office", "workspace", "study"],
                "bedroom": ["bedroom", "bed room"],
                "living_room": ["living room", "lounge"],
                "dining_room": ["dining room", "dining"],
                "outdoor": ["outdoor", "patio", "garden"]
            }
            
            for room, keywords in rooms.items():
                if any(kw in message_lower for kw in keywords):
                    entities["room_type"] = room
                    break
        
        elif intent == IntentType.PRODUCT_SPEC_QA:
            # Extract product reference
            index_match = re.search(r'\b(first|second|third|fourth|fifth|1st|2nd|3rd|4th|5th|\d+)\b.*\bone\b', message_lower)
            if index_match:
                index_word = index_match.group(1)
                index_map = {"first": "1", "second": "2", "third": "3", "fourth": "4", "fifth": "5",
                           "1st": "1", "2nd": "2", "3rd": "3", "4th": "4", "5th": "5"}
                entities["product_reference"] = index_map.get(index_word, index_word)
                entities["reference_type"] = "index"
            
            # Extract SKU if mentioned
            sku_match = re.search(r'\b([A-Z]+-\d+)\b', message)
            if sku_match:
                entities["product_reference"] = sku_match.group(1)
                entities["reference_type"] = "sku"
            
            entities["question"] = message
        
        elif intent == IntentType.CART_ADD:
            # Extract product reference and quantity
            # Try patterns like "option 1", "number 2", "first one", etc.
            index_match = re.search(r'\b(?:option|product|number|item|choice)\s+(\d+)\b', message_lower)
            if not index_match:
                index_match = re.search(r'\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|1st|2nd|3rd|4th|5th|6th|7th|8th|9th|10th)\b', message_lower)
            
            if index_match:
                index_val = index_match.group(1)
                ordinal_map = {
                    "first": "1", "second": "2", "third": "3", "fourth": "4", "fifth": "5",
                    "sixth": "6", "seventh": "7", "eighth": "8", "ninth": "9", "tenth": "10",
                    "1st": "1", "2nd": "2", "3rd": "3", "4th": "4", "5th": "5",
                    "6th": "6", "7th": "7", "8th": "8", "9th": "9", "10th": "10"
                }
                entities["product_reference"] = ordinal_map.get(index_val, index_val)
                entities["reference_type"] = "index"
            
            # Extract SKU if mentioned
            sku_match = re.search(r'\b([A-Z]+-\d+)\b', message)
            if sku_match and not entities.get("product_reference"):
                entities["product_reference"] = sku_match.group(1)
                entities["reference_type"] = "sku"
            
            # Extract quantity
            qty_match = re.search(r'\b(\d+)\s+(?:units?|items?|of|quantity)\b', message_lower)
            if not qty_match:
                qty_match = re.search(r'\b(?:qty|quantity|add)\s+(\d+)\b', message_lower)
            
            if qty_match:
                entities["quantity"] = int(qty_match.group(1))
            else:
                entities["quantity"] = 1
        
        elif intent == IntentType.CART_REMOVE:
            # Extract product reference
            index_match = re.search(r'\b(?:option|product|number|item|choice)\s+(\d+)\b', message_lower)
            if not index_match:
                index_match = re.search(r'\b(first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|1st|2nd|3rd|4th|5th|6th|7th|8th|9th|10th)\b', message_lower)
            
            if index_match:
                index_val = index_match.group(1)
                ordinal_map = {
                    "first": "1", "second": "2", "third": "3", "fourth": "4", "fifth": "5",
                    "sixth": "6", "seventh": "7", "eighth": "8", "ninth": "9", "tenth": "10",
                    "1st": "1", "2nd": "2", "3rd": "3", "4th": "4", "5th": "5"
                }
                entities["product_reference"] = ordinal_map.get(index_val, index_val)
                entities["reference_type"] = "index"
            
            # Extract SKU if mentioned
            sku_match = re.search(r'\b([A-Z]+-\d+)\b', message)
            if sku_match and not entities.get("product_reference"):
                entities["product_reference"] = sku_match.group(1)
                entities["reference_type"] = "sku"
            
            # Extract quantity
            qty_match = re.search(r'\b(need|want|get|buy)\s+(\d+)', message_lower)
            if qty_match:
                entities["quantity"] = int(qty_match.group(2))
            else:
                entities["quantity"] = 1
        
        elif intent == IntentType.SHIPPING_INFO:
            # Extract postcode
            postcode_match = re.search(r'\b(\d{4})\b', message)
            if postcode_match:
                entities["postcode"] = postcode_match.group(1)
        
        return entities
    
    def detect_vague_patterns(self, message: str) -> Optional[Dict[str, Any]]:
        """
        Detect vague query patterns that require clarification.
        
        Returns:
            Dict with 'vague_type' and 'partial_entities' if vague, None otherwise
        """
        message_lower = message.lower().strip()
        partial_entities = {}
        
        # Category 1: Ultra-vague queries
        ultra_vague_patterns = [
            r'^(i\s+)?(want|need|looking for|show me|find me|get me)\s+(something|anything)\s*$',
            r'^(something|anything)\s+(good|nice|cool|great|best)\s*$',
            r'^(help me\s+)?(choose|decide|select|pick)\s*$',
            r'^what\s+(should i|do you)\s+(buy|recommend|suggest)\s*\??$',
            r'^(suggest|recommend)\s+something\s*$',
            r'^what\s+do\s+you\s+have\s*\??$',
        ]
        
        for pattern in ultra_vague_patterns:
            if re.search(pattern, message_lower):
                return {"vague_type": "ultra_vague", "partial_entities": {}}
        
        # Category 2: Attribute-only (color/material only)
        # BUT: Skip if query contains furniture category (e.g., "blue chairs" is NOT vague)
        furniture_categories = ['chair', 'table', 'desk', 'sofa', 'bed', 'shelf', 'locker', 'stool', 'cabinet', 'furniture']
        has_category = any(cat in message_lower for cat in furniture_categories)
        
        if not has_category:
            attribute_only_patterns = [
                (r'^(something|anything|i\s+want\s+something|show me\s+something)\s+(blue|white|red|black|green|brown|grey|gray|yellow|pink|purple|orange|beige)\s*$', 'color'),
                (r'^(something|anything|i\s+want\s+something|show me\s+something)\s+(wooden|wood|metal|leather|fabric|glass|plastic|rattan)\s*$', 'material'),
                (r'^(something|anything|i\s+want\s+something|show me\s+something)\s+(modern|contemporary|minimalist|minimal|aesthetic|classic|industrial|rustic|scandinavian)\s*$', 'style'),
                (r'^(something|anything|i\s+want\s+something|show me\s+something)\s+(dark|light\s+colored|bright)\s*$', 'appearance'),
            ]
            
            for pattern, attr_type in attribute_only_patterns:
                match = re.search(pattern, message_lower)
                if match:
                    # Extract the attribute value
                    attr_value = match.group(2) if match.lastindex >= 2 else None
                    if attr_value:
                        if attr_type == 'color':
                            partial_entities['color'] = attr_value
                        elif attr_type == 'material':
                            partial_entities['material'] = attr_value
                        elif attr_type == 'style':
                            partial_entities['style'] = attr_value
                        elif attr_type == 'appearance':
                            partial_entities['appearance'] = attr_value
                    return {"vague_type": "attribute_only", "partial_entities": partial_entities}
        
        # Category 3: Room setup queries
        room_setup_patterns = [
            r'(i\s+am\s+|i\'m\s+)?(redoing|setting up|renovating|upgrading|furnishing)\s+(my\s+)?(room|bedroom|office|living room|apartment|place|home)\s*$',
            r'^(my\s+)?(room|bedroom|office|living room)\s+(looks\s+empty|needs\s+furniture)\s*$',
            r'^(moving\s+into|just\s+moved\s+to)\s+(a\s+)?(new\s+)?(place|apartment|house|home)\s*$',
        ]
        
        for pattern in room_setup_patterns:
            match = re.search(pattern, message_lower)
            if match:
                # Try to extract room type
                room_match = re.search(r'(bedroom|living room|office|kitchen|dining room)', message_lower)
                if room_match:
                    partial_entities['room_type'] = room_match.group(1)
                return {"vague_type": "room_setup", "partial_entities": partial_entities}
        
        # Category 4: Category-only without specifics
        category_only_patterns = [
            r'^(i\s+)?(want|need|looking for|show me|find me)\s+(a\s+)?(chair|table|desk|sofa|bed|shelf|locker|stool)s?\s*$',
        ]
        
        for pattern in category_only_patterns:
            match = re.search(pattern, message_lower)
            if match:
                # Extract category
                cat_match = re.search(r'(chair|table|desk|sofa|bed|shelf|locker|stool)s?', message_lower)
                if cat_match:
                    category = cat_match.group(1)
                    partial_entities['category'] = category
                return {"vague_type": "category_only", "partial_entities": partial_entities}
        
        # Category 5: Quality-only queries
        quality_only_patterns = [
            r'^(best|top|good|premium|quality|affordable|cheap|budget)\s+(furniture|chair|table|desk|sofa|bed)s?\s*$',
            r'^(furniture|chair|table|desk|sofa|bed)s?\s+(that\s+is\s+)?(best|good|quality|premium|affordable)\s*$',
        ]
        
        for pattern in quality_only_patterns:
            match = re.search(pattern, message_lower)
            if match:
                # Extract quality and category if present
                quality_match = re.search(r'(best|top|good|premium|quality|affordable|cheap|budget)', message_lower)
                cat_match = re.search(r'(furniture|chair|table|desk|sofa|bed)', message_lower)
                if quality_match:
                    partial_entities['quality'] = quality_match.group(1)
                if cat_match:
                    partial_entities['category'] = cat_match.group(1).rstrip('s')
                return {"vague_type": "quality_only", "partial_entities": partial_entities}
        
        # Category 6: Room-purpose-only
        room_purpose_patterns = [
            r'^(furniture|items|something)\s+for\s+(my\s+)?(room|home|bedroom|living room|office|kitchen|dining room)\s*$',
        ]
        
        for pattern in room_purpose_patterns:
            match = re.search(pattern, message_lower)
            if match:
                room_match = re.search(r'(bedroom|living room|office|kitchen|dining room|home|room)', message_lower)
                if room_match:
                    partial_entities['room_type'] = room_match.group(1)
                return {"vague_type": "room_purpose_only", "partial_entities": partial_entities}
        
        # Category 7: Use-case-only
        use_case_patterns = [
            r'^(chair|table|desk|furniture)s?\s+for\s+(work|home|office|kids|guests|gaming|study)\s*$',
        ]
        
        for pattern in use_case_patterns:
            match = re.search(pattern, message_lower)
            if match:
                cat_match = re.search(r'(chair|table|desk|furniture)', message_lower)
                use_match = re.search(r'for\s+(work|home|office|kids|guests|gaming|study)', message_lower)
                if cat_match:
                    partial_entities['category'] = cat_match.group(1).rstrip('s')
                if use_match:
                    partial_entities['use_case'] = use_match.group(1)
                return {"vague_type": "use_case_only", "partial_entities": partial_entities}
        
        # Category 8: Size-only
        size_only_patterns = [
            r'^(something|anything|furniture)\s+(compact|small|big|large|space\s+saving)\s*$',
            r'^(not\s+too\s+big|compact|space\s+saving)\s+(furniture)\s*$',
            r'^furniture\s+for\s+(small\s+)?(room|space|apartment)\s*$',
        ]
        
        for pattern in size_only_patterns:
            match = re.search(pattern, message_lower)
            if match:
                size_match = re.search(r'(compact|small|big|large|space\s+saving|not\s+too\s+big)', message_lower)
                if size_match:
                    partial_entities['size'] = size_match.group(1)
                return {"vague_type": "size_only", "partial_entities": partial_entities}
        
        # Category 9: Aesthetic-only
        aesthetic_only_patterns = [
            r'^(something|anything)\s+(cozy|comfortable|classy|luxurious|trendy|elegant|stylish)\s*$',
        ]
        
        for pattern in aesthetic_only_patterns:
            match = re.search(pattern, message_lower)
            if match:
                aesthetic_match = re.search(r'(cozy|comfortable|classy|luxurious|trendy|elegant|stylish)', message_lower)
                if aesthetic_match:
                    partial_entities['aesthetic'] = aesthetic_match.group(1)
                return {"vague_type": "aesthetic_only", "partial_entities": partial_entities}
        
        # Category 10: Comparison without context
        comparison_patterns = [
            r'^(which\s+one\s+is\s+best|what\s+do\s+you\s+recommend|top\s+options|best\s+option\s+for\s+me)\s*\??$',
        ]
        
        for pattern in comparison_patterns:
            if re.search(pattern, message_lower):
                return {"vague_type": "comparison_no_context", "partial_entities": {}}
        
        # Not vague
        return None
    
    def merge_clarification_response(
        self,
        original_entities: Dict[str, Any],
        clarification_message: str,
        vague_type: str
    ) -> Dict[str, Any]:
        """
        Merge clarification response with original partial entities.
        
        Args:
            original_entities: Partial entities from vague query
            clarification_message: User's clarification response
            vague_type: Type of vague query detected
        
        Returns:
            Merged entities dict
        """
        merged = original_entities.copy()
        clarification_lower = clarification_message.lower().strip()
        
        # Extract category from clarification
        categories = {
            "chair": ["chair", "chairs", "seating"],
            "table": ["table", "tables", "desk", "desks"],
            "sofa": ["sofa", "sofas", "couch", "couches"],
            "bed": ["bed", "beds", "mattress"],
            "shelf": ["shelf", "shelves", "shelving", "bookcase"],
            "stool": ["stool", "stools", "bar stool"],
            "locker": ["locker", "lockers", "cabinet", "cabinets"],
            "storage": ["storage", "wardrobe", "dresser"]
        }
        
        for cat, keywords in categories.items():
            if any(kw in clarification_lower for kw in keywords):
                merged["category"] = cat
                break
        
        # Extract room type
        rooms = {
            "office": ["office", "workspace", "study"],
            "bedroom": ["bedroom", "bed room"],
            "living_room": ["living room", "lounge"],
            "dining_room": ["dining room", "dining"],
            "outdoor": ["outdoor", "patio", "garden"]
        }
        
        for room, keywords in rooms.items():
            if any(kw in clarification_lower for kw in keywords):
                merged["room_type"] = room
                break
        
        # Extract color from clarification
        colors = ["red", "blue", "green", "yellow", "black", "white", "brown", "gray", "grey",
                  "orange", "purple", "pink", "beige", "cream", "navy", "silver", "gold"]
        for color in colors:
            if color in clarification_lower:
                merged["color"] = color
                break
        
        # Extract material
        materials = ["wood", "metal", "leather", "fabric", "glass", "rattan", "plastic"]
        for material in materials:
            if material in clarification_lower:
                merged["material"] = material
                break
        
        # Extract price range
        price_under = re.search(r'under\s*\$?(\d+)', clarification_lower)
        price_below = re.search(r'below\s*\$?(\d+)', clarification_lower)
        price_max = re.search(r'max(?:imum)?\s*\$?(\d+)', clarification_lower)
        
        if price_under:
            merged["price_max"] = float(price_under.group(1))
        elif price_below:
            merged["price_max"] = float(price_below.group(1))
        elif price_max:
            merged["price_max"] = float(price_max.group(1))
        
        # Build combined query
        query_parts = []
        
        # Add category
        if "category" in merged:
            query_parts.append(merged["category"])
        
        # Add color
        if "color" in merged:
            query_parts.append(merged["color"])
        
        # Add material
        if "material" in merged:
            query_parts.append(merged["material"])
        
        # Add room type
        if "room_type" in merged:
            query_parts.append(f"for {merged['room_type']}")
        
        # Add use case
        if "use_case" in merged:
            query_parts.append(f"for {merged['use_case']}")
        
        # Build query string
        if query_parts:
            merged["query"] = " ".join(query_parts)
        else:
            merged["query"] = clarification_message
        
        return merged
