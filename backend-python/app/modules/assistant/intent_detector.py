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
        ],
        IntentType.CART_ADD: [
            r'\b(add|put)\b.*\b(to|in|into)\b.*\b(cart|basket)\b',
            r'\b(buy|purchase|get|order)\b.*\b(this|that|the|it)\b',
            r'\b(i\'ll take)\b.*\b(this|that|the|it|one)\b',
        ],
        IntentType.CART_REMOVE: [
            r'\b(remove|delete|take out)\b.*\b(from|out of)\b.*\b(cart|basket)\b',
            r'\bdon\'t want\b.*\b(anymore|this|that)\b',
        ],
        IntentType.CART_SHOW: [
            r'\b(show|view|see|check)\b.*\b(cart|basket)\b',
            r'\bwhat\'s in\b.*\b(cart|basket)\b',
            r'\b(my cart|my basket|cart contents)\b',
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
        
        # PRIORITY 1: Check greetings FIRST (exact matches before pattern matching)
        # This prevents "hi" from being caught by other patterns
        greeting_exact = ['hi', 'hello', 'hey', "g'day", 'greetings', 
                         'good morning', 'good afternoon', 'good evening', 
                         'howdy', 'hi there', 'hello there', 'hey there']
        if message_lower in greeting_exact:
            return IntentType.GREETING
        
        # PRIORITY 2: Check for context-dependent questions (referring to previously shown products)
        # These should be PRODUCT_SPEC_QA, not PRODUCT_SEARCH
        context_references = [
            r'\b(this|that|the|it)\s+(one|chair|table|desk|sofa|bed|product|item)',
            r'\b(first|second|third|last|option)\s+(one|chair|table|product)',
            r'\b(option|number)\s+\d+',
            r'\b(the|this|that)\s+\$?\d+',
            r'\bmore (info|information|details|about)\s+(this|that|the|it)',
            r'\b(feature|spec|dimension|detail)s?\s+of\s+(this|that|the|it)',
        ]
        for pattern in context_references:
            if re.search(pattern, message_lower):
                return IntentType.PRODUCT_SPEC_QA
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
            index_match = re.search(r'\b(first|second|third|fourth|fifth|1st|2nd|3rd|4th|5th|\d+)\b', message_lower)
            if index_match:
                index_word = index_match.group(1)
                index_map = {"first": "1", "second": "2", "third": "3", "fourth": "4", "fifth": "5",
                           "1st": "1", "2nd": "2", "3rd": "3", "4th": "4", "5th": "5"}
                entities["product_reference"] = index_map.get(index_word, index_word)
                entities["reference_type"] = "index"
            
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
