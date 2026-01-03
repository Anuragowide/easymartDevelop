"""
Context Analyzer for better topic understanding and long conversation handling.
Analyzes user messages to detect topics, intents, entities, and user preferences.
"""

import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class TopicType(Enum):
    """Conversation topic types"""
    PRODUCTS = "products"
    ORDERS = "orders"
    ACCOUNT = "account"
    PAYMENT = "payment"
    SUPPORT = "support"
    RECOMMENDATIONS = "recommendations"
    CART = "cart"
    SHIPPING = "shipping"
    RETURNS = "returns"
    GENERAL = "general"


class IntentCategory(Enum):
    """Intent categories for user messages"""
    QUESTION = "question"
    REQUEST = "request"
    COMPLAINT = "complaint"
    CONFIRMATION = "confirmation"
    NEGATION = "negation"
    STATEMENT = "statement"


@dataclass
class TopicContext:
    """Context information about current conversation topic"""
    topic: TopicType
    entities: List[str]
    intent: IntentCategory
    confidence: float
    extracted_preferences: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic.value,
            "entities": self.entities,
            "intent": self.intent.value,
            "confidence": self.confidence,
            "preferences": self.extracted_preferences
        }


class ContextAnalyzer:
    """
    Analyzes conversation context for better topic understanding.
    Detects topics, intents, entities, and user preferences.
    """
    
    # Topic detection keywords
    TOPIC_KEYWORDS = {
        TopicType.PRODUCTS: [
            'product', 'item', 'furniture', 'chair', 'table', 'desk', 
            'sofa', 'bed', 'cabinet', 'storage', 'locker', 'drawer',
            'buy', 'purchase', 'looking for', 'need', 'want', 'show me',
            'find', 'search', 'available', 'stock', 'price', 'cost'
        ],
        TopicType.CART: [
            'cart', 'add to cart', 'remove from cart', 'basket', 
            'shopping cart', 'my cart', 'checkout', 'in my cart'
        ],
        TopicType.ORDERS: [
            'order', 'delivery', 'shipping', 'track', 'tracking',
            'status', 'cancel', 'my order', 'order number', 'when will'
        ],
        TopicType.PAYMENT: [
            'payment', 'pay', 'card', 'checkout', 'invoice', 
            'refund', 'transaction', 'billing', 'charge'
        ],
        TopicType.SHIPPING: [
            'shipping', 'delivery', 'ship', 'deliver', 'arrive',
            'shipping cost', 'delivery time', 'free shipping'
        ],
        TopicType.RETURNS: [
            'return', 'exchange', 'refund', 'send back', 
            'return policy', 'money back', 'warranty'
        ],
        TopicType.SUPPORT: [
            'help', 'issue', 'problem', 'complaint', 'support',
            'contact', 'customer service', 'assistance'
        ],
        TopicType.RECOMMENDATIONS: [
            'suggest', 'recommend', 'best', 'top', 'popular',
            'similar', 'alternative', 'what do you recommend'
        ],
    }
    
    # Intent detection patterns
    INTENT_PATTERNS = {
        IntentCategory.QUESTION: [
            'what', 'when', 'where', 'how', 'why', 'which', 
            'can', 'do', 'is', 'are', 'does', 'will', 'would'
        ],
        IntentCategory.REQUEST: [
            'please', 'need', 'want', 'would like', 'looking for',
            'show me', 'find', 'get me', 'i need', 'i want'
        ],
        IntentCategory.COMPLAINT: [
            'not working', 'broken', 'issue', 'problem', 'wrong',
            'error', 'disappointed', 'unhappy', 'terrible'
        ],
        IntentCategory.CONFIRMATION: [
            'yes', 'correct', 'right', 'confirm', 'proceed',
            'go ahead', 'sure', 'okay', 'ok', 'yep', 'yeah'
        ],
        IntentCategory.NEGATION: [
            'no', 'cancel', 'stop', 'never mind', 'forget',
            'don\'t', 'not', 'nope', 'nah'
        ],
    }
    
    def __init__(self):
        """Initialize context analyzer"""
        self.preference_extractors = {
            'budget': self._extract_budget,
            'size': self._extract_size,
            'color': self._extract_color,
            'material': self._extract_material,
            'room': self._extract_room,
        }
    
    def analyze(self, message: str, conversation_history: Optional[List[Dict]] = None) -> TopicContext:
        """
        Analyze message to detect topic, intent, and entities.
        
        Args:
            message: User message to analyze
            conversation_history: Previous messages for context
            
        Returns:
            TopicContext with detected information
        """
        message_lower = message.lower()
        
        # Detect topic
        topic, topic_confidence = self._detect_topic(message_lower)
        
        # Detect intent
        intent = self._detect_intent(message_lower)
        
        # Extract entities
        entities = self._extract_entities(message)
        
        # Extract preferences
        preferences = self._extract_preferences(message)
        
        # Calculate overall confidence
        confidence = self._calculate_confidence(topic_confidence, entities, preferences)
        
        return TopicContext(
            topic=topic,
            entities=entities,
            intent=intent,
            confidence=confidence,
            extracted_preferences=preferences
        )
    
    def _detect_topic(self, message_lower: str) -> tuple[TopicType, float]:
        """Detect conversation topic from message"""
        topic_scores: Dict[TopicType, int] = {}
        
        # Score each topic based on keyword matches
        for topic, keywords in self.TOPIC_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in message_lower)
            if score > 0:
                topic_scores[topic] = score
        
        if not topic_scores:
            return TopicType.GENERAL, 0.3
        
        # Get topic with highest score
        detected_topic = max(topic_scores, key=topic_scores.get)
        max_score = topic_scores[detected_topic]
        
        # Calculate confidence (normalize to 0-1)
        confidence = min(max_score / 3, 1.0)
        
        return detected_topic, confidence
    
    def _detect_intent(self, message_lower: str) -> IntentCategory:
        """Detect user intent from message"""
        for intent, patterns in self.INTENT_PATTERNS.items():
            if any(pattern in message_lower for pattern in patterns):
                return intent
        
        return IntentCategory.STATEMENT
    
    def _extract_entities(self, message: str) -> List[str]:
        """Extract entities like order IDs, SKUs, prices"""
        entities = []
        
        # Extract order IDs (#12345, ORD-123, order 123)
        order_matches = re.findall(r'#\d+|ORD-\d+|order\s+\d+', message, re.IGNORECASE)
        entities.extend(order_matches)
        
        # Extract SKUs (e.g., CHAIR-001)
        sku_matches = re.findall(r'\b[A-Z]+-\d+\b', message)
        entities.extend(sku_matches)
        
        # Extract prices ($XX.XX, $XX)
        price_matches = re.findall(r'\$\d+(?:\.\d{2})?', message)
        entities.extend(price_matches)
        
        # Extract product references (product 1, item 2)
        product_refs = re.findall(r'(?:product|item|option|number)\s+\d+', message, re.IGNORECASE)
        entities.extend(product_refs)
        
        return entities
    
    def _extract_preferences(self, message: str) -> Dict[str, Any]:
        """Extract user preferences from message"""
        preferences = {}
        
        for pref_name, extractor in self.preference_extractors.items():
            value = extractor(message)
            if value:
                preferences[pref_name] = value
        
        return preferences
    
    def _extract_budget(self, message: str) -> Optional[float]:
        """Extract budget/price preference"""
        # Match patterns like "under $500", "less than $1000", "budget of $300"
        patterns = [
            r'(?:under|less than|below|max|maximum|budget of)\s*\$(\d+)',
            r'\$(\d+)\s*(?:or less|max|maximum)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                return float(match.group(1))
        
        return None
    
    def _extract_size(self, message: str) -> Optional[str]:
        """Extract size preference"""
        size_pattern = r'\b(small|medium|large|xl|xxl|compact|big|tiny)\b'
        match = re.search(size_pattern, message, re.IGNORECASE)
        return match.group(1).lower() if match else None
    
    def _extract_color(self, message: str) -> Optional[str]:
        """Extract color preference"""
        color_pattern = r'\b(red|blue|green|black|white|brown|gray|grey|beige|yellow|orange|purple|pink|wooden|natural)\b'
        match = re.search(color_pattern, message, re.IGNORECASE)
        return match.group(1).lower() if match else None
    
    def _extract_material(self, message: str) -> Optional[str]:
        """Extract material preference"""
        material_pattern = r'\b(wood|wooden|metal|leather|fabric|plastic|glass|steel)\b'
        match = re.search(material_pattern, message, re.IGNORECASE)
        return match.group(1).lower() if match else None
    
    def _extract_room(self, message: str) -> Optional[str]:
        """Extract room type"""
        room_pattern = r'\b(bedroom|living room|office|kitchen|bathroom|dining room|study)\b'
        match = re.search(room_pattern, message, re.IGNORECASE)
        return match.group(1).lower() if match else None
    
    def _calculate_confidence(
        self, 
        topic_confidence: float, 
        entities: List[str], 
        preferences: Dict[str, Any]
    ) -> float:
        """Calculate overall confidence score"""
        # Base confidence from topic detection
        confidence = topic_confidence * 0.6
        
        # Boost for extracted entities (up to +0.2)
        entity_boost = min(len(entities) * 0.1, 0.2)
        confidence += entity_boost
        
        # Boost for extracted preferences (up to +0.2)
        pref_boost = min(len(preferences) * 0.1, 0.2)
        confidence += pref_boost
        
        return min(confidence, 1.0)
    
    def build_context_prompt(
        self,
        topic_context: TopicContext,
        conversation_history: List[Dict[str, str]],
        user_preferences: Dict[str, Any]
    ) -> str:
        """
        Build enhanced context prompt for LLM.
        
        Args:
            topic_context: Detected topic context
            conversation_history: Recent conversation messages
            user_preferences: Accumulated user preferences
            
        Returns:
            Enhanced context prompt string
        """
        recent_messages = conversation_history[-5:] if len(conversation_history) > 5 else conversation_history
        
        prompt = f"""You are an AI assistant for EasyMart, an e-commerce furniture platform.

CURRENT CONTEXT:
- Topic: {topic_context.topic.value}
- User Intent: {topic_context.intent.value}
- Confidence: {topic_context.confidence:.0%}
"""
        
        if topic_context.entities:
            prompt += f"- Mentioned Items: {', '.join(topic_context.entities)}\n"
        
        if topic_context.extracted_preferences:
            prompt += f"- Current Preferences: {topic_context.extracted_preferences}\n"
        
        if user_preferences:
            prompt += f"- Known User Preferences: {user_preferences}\n"
        
        prompt += f"\nRECENT CONVERSATION:\n"
        for msg in recent_messages:
            prompt += f"{msg['role']}: {msg['content']}\n"
        
        prompt += self._get_topic_guidance(topic_context.topic)
        
        return prompt
    
    def _get_topic_guidance(self, topic: TopicType) -> str:
        """Get topic-specific guidance for the LLM"""
        guidance = {
            TopicType.PRODUCTS: """
FOCUS ON:
- Providing accurate product information
- Highlighting features, specifications, and benefits
- Mentioning availability, pricing, and stock status
- Suggesting related or similar products when appropriate
- Being helpful and consultative in recommendations""",
            
            TopicType.CART: """
FOCUS ON:
- Clear cart operations (add, remove, view)
- Confirming cart actions taken
- Showing current cart summary when relevant
- Guiding towards checkout when appropriate""",
            
            TopicType.ORDERS: """
FOCUS ON:
- Order tracking and status updates
- Clear delivery timelines and expectations
- Return and cancellation policies
- Being empathetic about order concerns
- Providing accurate order information""",
            
            TopicType.PAYMENT: """
FOCUS ON:
- Payment security and trust
- Available payment methods
- Clear refund and billing policies
- Never asking for sensitive payment details directly
- Directing to secure checkout pages""",
            
            TopicType.SHIPPING: """
FOCUS ON:
- Clear shipping costs and timelines
- Delivery options available
- Tracking information
- Addressing delivery concerns empathetically""",
            
            TopicType.RETURNS: """
FOCUS ON:
- Clear return and exchange policies
- Step-by-step return process
- Refund timelines and methods
- Being understanding about return reasons""",
            
            TopicType.SUPPORT: """
FOCUS ON:
- Active listening and empathy
- Clear troubleshooting steps
- Offering to escalate to human support when needed
- Following up on reported issues""",
            
            TopicType.RECOMMENDATIONS: """
FOCUS ON:
- Personalized suggestions based on conversation context
- Explaining why recommendations fit the user's needs
- Considering preferences mentioned earlier
- Offering alternatives and comparisons""",
        }
        
        return guidance.get(topic, "\nProvide helpful and accurate information.")


# Global instance
_context_analyzer = None


def get_context_analyzer() -> ContextAnalyzer:
    """Get global context analyzer instance"""
    global _context_analyzer
    if _context_analyzer is None:
        _context_analyzer = ContextAnalyzer()
    return _context_analyzer
