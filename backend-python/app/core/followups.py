"""
Smart Follow-up Question Generator
Generates contextual follow-up chips based on conversation context.
"""

from typing import Dict, List, Optional
import random


class FollowupGenerator:
    """Generate contextual follow-up suggestions as chips"""
    
    # Follow-up templates based on intent
    FOLLOWUPS_BY_INTENT = {
        "product_search": {
            "with_results": [
                "Tell me about option 1",
                "Check availability",
                "Add option 1 to cart",
                "Show similar products",
            ],
            "no_results": [
                "Show me office chairs",
                "Browse sofas",
                "View desks",
            ]
        },
        "product_spec_qa": [
            "Add to cart",
            "Check if in stock",
            "Show similar products",
        ],
        "check_availability": [
            "Add to cart",
            "Show similar products",
            "View product details",
        ],
        "cart_add": [
            "View my cart",
            "Continue shopping",
            "Proceed to checkout",
        ],
        "cart_show": [
            "Proceed to checkout",
            "Continue shopping",
        ],
        "comparison": [
            "Add option 1 to cart",
            "Add option 2 to cart",
            "Show more options",
        ],
        "return_policy": [
            "Shipping info",
            "Contact support",
            "Browse products",
        ],
        "shipping_info": [
            "Return policy",
            "Contact support",
            "Browse products",
        ],
        "contact_info": [
            "Browse products",
            "Return policy",
            "Shipping info",
        ],
        "vague_query": [
            "Show me office chairs",
            "Browse sofas", 
            "View desks",
        ],
        "clarification_needed": [
            "Office chairs",
            "Living room furniture",
            "Bedroom furniture",
        ],
        "general": [
            "Show me office chairs",
            "Browse sofas",
            "View desks",
        ],
        "greeting": [
            "Show me office chairs",
            "Browse sofas",
            "I need a desk",
        ],
        "out_of_scope": [
            "Show me office chairs",
            "Browse sofas",
            "View desks",
        ],
    }
    
    def generate_followups(
        self,
        intent: str,
        products_count: int = 0,
        cart_count: int = 0,
        context: Dict = None
    ) -> List[str]:
        """Generate contextual follow-up suggestions"""
        
        followups = []
        
        # Get intent-specific followups
        intent_followups = self.FOLLOWUPS_BY_INTENT.get(intent, self.FOLLOWUPS_BY_INTENT["general"])
        
        # Handle search with/without results
        if intent == "product_search":
            if products_count > 0:
                followups = list(intent_followups.get("with_results", []))[:3]
            else:
                followups = list(intent_followups.get("no_results", []))[:3]
        elif isinstance(intent_followups, list):
            followups = list(intent_followups)[:3]
        else:
            followups = list(intent_followups.get("with_results", self.FOLLOWUPS_BY_INTENT["general"]))[:3]
        
        # Add cart-related followup if items in cart
        if cart_count > 0 and "View my cart" not in followups:
            if intent not in ["cart_add", "cart_show"]:
                followups = followups[:2] + [f"View cart ({cart_count})"]
        
        # Add product-specific followups if products shown
        if products_count > 0 and intent == "product_search":
            # Replace generic with specific
            specific_followups = []
            for i, f in enumerate(followups):
                if "option 1" in f.lower() or "about option" in f.lower():
                    specific_followups.append(f"Tell me about option 1")
                else:
                    specific_followups.append(f)
            followups = specific_followups
        
        # Ensure we have exactly 3 followups with actionable suggestions
        defaults = ["Show me office chairs", "Browse sofas", "View desks"]
        while len(followups) < 3:
            for d in defaults:
                if d not in followups and len(followups) < 3:
                    followups.append(d)
                    break
        
        return followups[:3]  # Return max 3 followups
    
    def get_welcome_followups(self, is_returning: bool = False, cart_count: int = 0) -> List[str]:
        """Get follow-ups for welcome message"""
        
        if is_returning and cart_count > 0:
            return [
                f"View my cart ({cart_count})",
                "Show me office chairs",
                "Browse sofas",
            ]
        else:
            return [
                "Show me office chairs",
                "Browse sofas",
                "I need a desk",
            ]
    
    def get_error_followups(self, error_type: str) -> List[str]:
        """Get follow-ups after an error"""
        
        error_followups = {
            "search_empty": ["Show me office chairs", "Browse sofas", "View desks"],
            "product_not_found": ["Show me office chairs", "Browse sofas", "View desks"],
            "cart_error": ["Try again", "View cart", "Contact support"],
            "default": ["Show me office chairs", "Browse sofas", "View desks"],
        }
        
        return error_followups.get(error_type, error_followups["default"])


# Global followup generator instance
followup_generator = FollowupGenerator()


def get_followup_generator() -> FollowupGenerator:
    """Get the global followup generator instance"""
    return followup_generator
