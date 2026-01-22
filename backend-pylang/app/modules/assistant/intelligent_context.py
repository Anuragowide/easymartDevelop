"""
Intelligent Context Handler - FAST heuristic-based understanding
Uses pattern matching instead of LLM calls for speed optimization.
- Is a query a follow-up to previous context?
- Is a response asking for clarification or showing products?
- Should previous context be applied to current query?
"""

from typing import Dict, Any, Optional, List


class IntelligentContextHandler:
    """
    FAST heuristic-based context analysis for speed.
    No LLM calls - pure pattern matching for instant responses.
    """
    
    def __init__(self):
        pass  # No LLM needed - using fast heuristics
    
    async def should_apply_previous_context(
        self, 
        current_message: str, 
        previous_shopping_context: Optional[str],
        recent_conversation: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        FAST heuristic-first approach to determine if current message needs previous shopping context.
        Only falls back to LLM for ambiguous cases.
        
        Returns: {
            "needs_context": bool,
            "combined_query": str (if needs_context=True),
            "reasoning": str
        }
        """
        
        if not previous_shopping_context:
            return {
                "needs_context": False,
                "combined_query": current_message,
                "reasoning": "No previous shopping context available"
            }
        
        message_lower = current_message.lower().strip()
        
        # FAST HEURISTIC 1: Short follow-up responses that CLEARLY need context
        short_follow_ups = [
            "yes", "yeah", "yep", "sure", "ok", "okay", "go ahead", 
            "you choose", "you pick", "just pick", "pick for me",
            "give me that", "i'll take it", "sounds good", "perfect",
            "bundle", "give me bundle", "create bundle", "make bundle",
            "go for it", "do it", "proceed", "continue"
        ]
        
        if message_lower in short_follow_ups or len(message_lower.split()) <= 3 and any(word in message_lower for word in ["bundle", "pick", "choose", "that"]):
            return {
                "needs_context": True,
                "combined_query": f"{previous_shopping_context}, {current_message}",
                "reasoning": "Short follow-up response detected (heuristic)"
            }
        
        # FAST HEURISTIC 2: Independent queries that DON'T need context
        # These are clearly new product searches
        independent_starters = [
            "show me", "find me", "search for", "look for", "i want", "i need",
            "looking for", "can you find", "do you have", "what about"
        ]
        
        if any(message_lower.startswith(starter) for starter in independent_starters):
            return {
                "needs_context": False,
                "combined_query": current_message,
                "reasoning": "Independent product search detected (heuristic)"
            }
        
        # FAST HEURISTIC 3: If message contains specific product terms, it's independent
        product_terms = ["chair", "desk", "table", "sofa", "bed", "lamp", "cabinet", "shelf", "couch", "aquarium", "recliner"]
        if any(term in message_lower for term in product_terms) and len(message_lower.split()) > 3:
            return {
                "needs_context": False,
                "combined_query": current_message,
                "reasoning": "Contains specific product terms (heuristic)"
            }
        
        # FAST HEURISTIC 4: For medium-length ambiguous messages, use simple logic
        # If it's under 6 words and doesn't look like a search, assume needs context
        word_count = len(message_lower.split())
        if word_count <= 5:
            return {
                "needs_context": True,
                "combined_query": f"{previous_shopping_context}, {current_message}",
                "reasoning": "Short/vague message, applying context (heuristic)"
            }
        
        # For longer messages, assume they're independent
        return {
            "needs_context": False,
            "combined_query": current_message,
            "reasoning": "Longer message treated as independent query (heuristic)"
        }
    
    async def analyze_response_type(
        self,
        assistant_response: str,
        user_query: str
    ) -> Dict[str, Any]:
        """
        FAST heuristic-only analysis (no LLM call) to determine if assistant's response is:
        - Asking for clarification
        - Showing product listings
        
        Returns: {
            "is_clarification": bool,
            "is_showing_products": bool,
            "reasoning": str
        }
        """
        response_lower = assistant_response.lower()
        
        # Check for product listings - numbered items (with or without prices)
        has_numbered_list = any(marker in assistant_response for marker in ["\n1.", "\n2.", "\n3.", "1. ", "2. "])
        has_price_symbols = "$" in assistant_response
        
        # Check for product name patterns (capitalized product names after numbers)
        import re
        has_product_names = bool(re.search(r'\d\.\s+[A-Z][a-zA-Z]+.*(?:–|-|:)', assistant_response))
        
        # Check for product structure patterns
        has_product_structure = any(pattern in response_lower for pattern in [
            "here are", "here's what", "found these", "options for you",
            "i found", "showing you", "take a look", "check out these",
            "available now", "available:", "options:"
        ])
        
        # Check for clarification-ONLY patterns (questions without products)
        clarification_only_patterns = [
            "what type", "which type", "what kind", "which kind",
            "what are you looking for", "can you tell me more",
            "do you have a preference", "any specific", "anything specific",
            "what size", "what color", "which color", "what style",
            "shall i show you", "would you like me to show",
            "we have a wide range", "we have a nice selection",
            "are you looking for something specific"
        ]
        is_pure_clarification = any(pattern in response_lower for pattern in clarification_only_patterns) and not has_numbered_list
        
        # If has numbered list with product names OR product structure, it's showing products
        if has_numbered_list and (has_price_symbols or has_product_names or has_product_structure):
            return {
                "is_clarification": False,
                "is_showing_products": True,
                "reasoning": "Response has numbered product listings"
            }
        
        # If it's a pure clarification question without product list, it's clarification
        if is_pure_clarification:
            return {
                "is_clarification": True,
                "is_showing_products": False,
                "reasoning": "Response is asking for clarification without products"
            }
        
        # Default: if it has numbered list, assume products; otherwise assume clarification
        if has_numbered_list:
            return {
                "is_clarification": False,
                "is_showing_products": True,
                "reasoning": "Response has numbered list"
            }
        
        return {
            "is_clarification": True,
            "is_showing_products": False,
            "reasoning": "No product indicators found, treating as clarification"
        }


_intelligent_context_handler: Optional[IntelligentContextHandler] = None


def get_intelligent_context_handler() -> IntelligentContextHandler:
    """Get or create singleton intelligent context handler."""
    global _intelligent_context_handler
    if _intelligent_context_handler is None:
        _intelligent_context_handler = IntelligentContextHandler()
    return _intelligent_context_handler
