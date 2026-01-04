"""
Smart Follow-up Question Generator
Generates contextual follow-up chips based on conversation context.
"""

from typing import Dict, List, Optional
import random


class FollowupGenerator:
    """Generate contextual follow-up suggestions as chips"""
    
    # Follow-up templates based on intent
    # All chips should be clear, actionable queries the LLM can understand
    FOLLOWUPS_BY_INTENT = {
        "product_search": {
            "with_results": [
                "Tell me about option 1",
                "Is option 1 in stock?",
                "Add option 1 to cart",
            ],
            "no_results": [
                "Search for office chairs",
                "Search for sofas",
                "Search for desks",
            ]
        },
        "product_spec_qa": [
            "Add this product to my cart",
            "Check stock for this product",
            "Find similar products",
        ],
        "check_availability": [
            "Add this product to my cart",
            "Find similar products",
            "Search for office chairs",
        ],
        "cart_add": [
            "Show my cart",
            "Search for more products",
            "What's in my cart?",
        ],
        "cart_show": [
            "Search for office chairs",
            "Search for sofas",
            "Clear my cart",
        ],
        "comparison": [
            "Add option 1 to cart",
            "Add option 2 to cart",
            "Tell me about option 1",
        ],
        "return_policy": [
            "What is the shipping policy?",
            "How do I contact support?",
            "Search for office chairs",
        ],
        "shipping_info": [
            "What is the return policy?",
            "How do I contact support?",
            "Search for sofas",
        ],
        "contact_info": [
            "Search for office chairs",
            "What is the return policy?",
            "What is the shipping policy?",
        ],
        "vague_query": [
            "Search for office chairs",
            "Search for sofas", 
            "Search for desks",
        ],
        "clarification_needed": [
            "Search for office chairs",
            "Search for sofas",
            "Search for bedroom furniture",
        ],
        "general": [
            "Search for office chairs",
            "Search for sofas",
            "Search for desks",
        ],
        "greeting": [
            "Search for office chairs",
            "Search for sofas",
            "Search for desks",
        ],
        "out_of_scope": [
            "Search for office chairs",
            "Search for sofas",
            "Search for desks",
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
        
        # Deduplicate followups (case-insensitive)
        seen = set()
        unique_followups = []
        for f in followups:
            f_lower = f.lower()
            if f_lower not in seen:
                seen.add(f_lower)
                unique_followups.append(f)
        followups = unique_followups
        
        # Ensure we have exactly 3 followups with actionable suggestions
        defaults = ["Search for office chairs", "Search for sofas", "Search for desks"]
        while len(followups) < 3:
            for d in defaults:
                if d.lower() not in seen and len(followups) < 3:
                    followups.append(d)
                    seen.add(d.lower())
                    break
            else:
                break  # No more defaults to add
        
        return followups[:3]  # Return max 3 followups
    
    def get_welcome_followups(self, is_returning: bool = False, cart_count: int = 0) -> List[str]:
        """Get follow-ups for welcome message"""
        
        if is_returning and cart_count > 0:
            return [
                "Show my cart",
                "Search for office chairs",
                "Search for sofas",
            ]
        else:
            return [
                "Search for office chairs",
                "Search for sofas",
                "Search for desks",
            ]
    
    def get_error_followups(self, error_type: str) -> List[str]:
        """Get follow-ups after an error"""
        
        error_followups = {
            "search_empty": ["Search for office chairs", "Search for sofas", "Search for desks"],
            "product_not_found": ["Search for office chairs", "Search for sofas", "Search for desks"],
            "cart_error": ["Show my cart", "Search for office chairs", "How do I contact support?"],
            "default": ["Search for office chairs", "Search for sofas", "Search for desks"],
        }
        
        return error_followups.get(error_type, error_followups["default"])


# Global followup generator instance
followup_generator = FollowupGenerator()


def get_followup_generator() -> FollowupGenerator:
    """Get the global followup generator instance"""
    return followup_generator
