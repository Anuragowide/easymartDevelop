"""
Conversation State Manager

Manages conversation state and determines message intent for context refinement.
This is the root fix for context refinement issues - a proper state machine.
"""

from typing import Optional, Dict, List
from dataclasses import dataclass, field
from enum import Enum
import re

from ..observability.logging_config import get_logger

logger = get_logger(__name__)


class ConversationPhase(Enum):
    INITIAL = "initial"
    SEARCHING = "searching"
    REFINING = "refining"
    PRODUCT_DETAIL = "product_detail"
    GENERAL_QUESTION = "general_question"


@dataclass
class SearchContext:
    """Tracks the current search context"""
    base_query: str  # Original search: "chairs"
    refinements: List[str] = field(default_factory=list)  # ["modern", "wooden", "under $500"]
    category: Optional[str] = None  # "chairs"
    attributes: Dict[str, str] = field(default_factory=dict)  # {"style": "modern", "material": "wooden"}
    price_constraint: Optional[str] = None  # "under $500"
    room: Optional[str] = None  # "office"
    
    def get_full_query(self) -> str:
        """Construct the complete search query"""
        parts = [self.base_query]
        
        # Add refinements in order
        for refinement in self.refinements:
            if refinement not in parts:
                parts.append(refinement)
        
        return " ".join(parts)
    
    def add_refinement(self, refinement: str) -> None:
        """Add a new refinement to the context"""
        if refinement not in self.refinements:
            self.refinements.append(refinement)
            
            # Parse and update attributes
            self._parse_refinement(refinement)
    
    def _parse_refinement(self, refinement: str) -> None:
        """Extract structured attributes from refinement"""
        refinement_lower = refinement.lower()
        
        # Color
        colors = ['red', 'blue', 'green', 'black', 'white', 'grey', 'gray', 'brown', 
                  'beige', 'navy', 'pink', 'yellow', 'orange', 'purple']
        for color in colors:
            if color in refinement_lower:
                self.attributes['color'] = color
        
        # Material
        materials = ['wooden', 'wood', 'metal', 'plastic', 'leather', 'fabric', 
                     'glass', 'steel', 'oak', 'pine', 'marble']
        for material in materials:
            if material in refinement_lower:
                self.attributes['material'] = material
        
        # Style
        styles = ['modern', 'contemporary', 'traditional', 'rustic', 'minimalist', 
                  'industrial', 'vintage', 'classic']
        for style in styles:
            if style in refinement_lower:
                self.attributes['style'] = style
        
        # Room
        rooms = ['office', 'bedroom', 'living room', 'kitchen', 'dining', 'kids']
        for room in rooms:
            if room in refinement_lower:
                self.room = room
        
        # Price
        price_match = re.search(r'(under|below|less than|max|maximum|cheaper than)\s*\$?(\d+)', refinement_lower)
        if price_match:
            self.price_constraint = f"under ${price_match.group(2)}"


class ConversationStateManager:
    """Manages conversation state and determines message intent"""
    
    # Product categories
    CATEGORIES = [
        'chair', 'chairs', 'table', 'tables', 'desk', 'desks', 'sofa', 'sofas',
        'bed', 'beds', 'shelf', 'shelves', 'cabinet', 'cabinets', 'storage',
        'locker', 'lockers', 'furniture', 'couch', 'dresser', 'nightstand'
    ]
    
    # Refinement keywords
    REFINEMENT_KEYWORDS = {
        'colors': ['red', 'blue', 'green', 'black', 'white', 'grey', 'gray', 'brown', 
                   'beige', 'navy', 'pink', 'yellow', 'orange', 'purple'],
        'materials': ['wooden', 'wood', 'metal', 'plastic', 'leather', 'fabric', 
                      'glass', 'steel', 'oak', 'pine', 'marble', 'canvas'],
        'styles': ['modern', 'contemporary', 'traditional', 'rustic', 'minimalist',
                   'industrial', 'vintage', 'classic', 'scandinavian'],
        'rooms': ['office', 'bedroom', 'living room', 'kitchen', 'dining', 'kids',
                  'bathroom', 'outdoor', 'patio'],
        'features': ['storage', 'adjustable', 'foldable', 'portable', 'ergonomic',
                     'reclining', 'swivel', 'wheels', 'cushioned']
    }
    
    def __init__(self):
        self.current_phase = ConversationPhase.INITIAL
        self.search_context: Optional[SearchContext] = None
        self.last_product_id: Optional[str] = None
    
    def analyze_message(self, message: str, conversation_history: List[Dict]) -> Dict:
        """
        Analyze message and return structured intent
        
        Returns:
            {
                'phase': ConversationPhase,
                'intent': str,  # 'new_search', 'refinement', 'product_question', 'general'
                'processed_message': str,  # Message to use for search/response
                'context': Optional[SearchContext]
            }
        """
        message_lower = message.lower().strip()
        
        logger.info(f"[STATE] Analyzing message: '{message}'")
        logger.info(f"[STATE] Current phase: {self.current_phase}")
        logger.info(f"[STATE] Has search context: {self.search_context is not None}")
        
        # Check for product-specific questions
        if self._is_product_question(message_lower):
            logger.info(f"[STATE] Detected as PRODUCT_QUESTION")
            return {
                'phase': ConversationPhase.PRODUCT_DETAIL,
                'intent': 'product_question',
                'processed_message': message,
                'context': None
            }
        
        # Check if it's a refinement
        if self._is_refinement(message_lower):
            if self.search_context:
                # Add refinement to existing context
                self.search_context.add_refinement(message)
                self.current_phase = ConversationPhase.REFINING
                
                full_query = self.search_context.get_full_query()
                logger.info(f"[STATE] Detected as REFINEMENT")
                logger.info(f"[STATE] Added refinement: '{message}'")
                logger.info(f"[STATE] Full query: '{full_query}'")
                
                return {
                    'phase': ConversationPhase.REFINING,
                    'intent': 'refinement',
                    'processed_message': full_query,
                    'context': self.search_context
                }
            else:
                # No context - treat as incomplete search
                logger.info(f"[STATE] Detected as INCOMPLETE_SEARCH (refinement without context)")
                return {
                    'phase': ConversationPhase.INITIAL,
                    'intent': 'incomplete_search',
                    'processed_message': message,
                    'context': None
                }
        
        # Check if it's a new search
        if self._is_new_search(message_lower):
            # Create new search context
            category = self._extract_category(message_lower)
            self.search_context = SearchContext(
                base_query=message,
                refinements=[],
                category=category,
                attributes={},
                price_constraint=None,
                room=None
            )
            self.current_phase = ConversationPhase.SEARCHING
            
            logger.info(f"[STATE] Detected as NEW_SEARCH")
            logger.info(f"[STATE] Category: {category}")
            
            return {
                'phase': ConversationPhase.SEARCHING,
                'intent': 'new_search',
                'processed_message': message,
                'context': self.search_context
            }
        
        # General question
        logger.info(f"[STATE] Detected as GENERAL question")
        self.current_phase = ConversationPhase.GENERAL_QUESTION
        return {
            'phase': ConversationPhase.GENERAL_QUESTION,
            'intent': 'general',
            'processed_message': message,
            'context': None
        }
    
    def _is_refinement(self, message: str) -> bool:
        """Check if message is a refinement"""
        words = message.split()
        
        # Very short messages with refinement keywords
        if len(words) <= 5:
            for keywords in self.REFINEMENT_KEYWORDS.values():
                if any(keyword in message for keyword in keywords):
                    logger.info(f"[STATE] Refinement match: keyword found in '{message}'")
                    return True
            
            # Price constraints
            if re.search(r'(under|below|less than|max|maximum)\s*\$?\d+', message):
                logger.info(f"[STATE] Refinement match: price constraint in '{message}'")
                return True
            
            # Common refinement prefixes
            if re.match(r'^(for|in|with|under|over)\s+', message):
                logger.info(f"[STATE] Refinement match: prefix pattern in '{message}'")
                return True
        
        return False
    
    def _is_new_search(self, message: str) -> bool:
        """Check if message is a new product search"""
        # Contains a product category
        if any(category in message for category in self.CATEGORIES):
            return True
        
        # Search intent keywords with category-like words
        search_keywords = ['find', 'show', 'search', 'looking for', 'need', 'want', 'get me']
        if any(keyword in message for keyword in search_keywords):
            return True
        
        return False
    
    def _is_product_question(self, message: str) -> bool:
        """Check if asking about specific product"""
        product_question_patterns = [
            r'(option|number|product)\s*\d+',
            r'tell me (about|more)',
            r'what (is|are) (the|this|that)',
            r'(does|is) (this|it|that)',
            r'show me (option|product|number)',
            r'(available|comes?) in'
        ]
        
        return any(re.search(pattern, message) for pattern in product_question_patterns)
    
    def _extract_category(self, message: str) -> Optional[str]:
        """Extract product category from message"""
        for category in self.CATEGORIES:
            if category in message:
                return category.rstrip('s')  # Singular form
        return None
    
    def reset_context(self):
        """Reset search context"""
        self.search_context = None
        self.current_phase = ConversationPhase.INITIAL
        logger.info(f"[STATE] Context reset")
