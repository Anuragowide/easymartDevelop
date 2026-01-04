"""
Error Recovery System
Handles errors gracefully with user-friendly alternatives.
"""

from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class ErrorRecovery:
    """Handle errors gracefully with user-friendly alternatives"""
    
    ERROR_RESPONSES = {
        "product_not_found": {
            "message": "I couldn't find that exact product. Could you tell me more about what you're looking for?",
            "followups": ["Search for similar items", "Browse categories", "Get help"],
        },
        "search_empty": {
            "message": "I couldn't find products matching your exact criteria. Let me suggest some alternatives.",
            "followups": ["Try different keywords", "Browse all products", "Adjust filters"],
        },
        "tool_failure": {
            "message": "I'm having a bit of trouble with that request. Let me try to help differently.",
            "followups": ["Try again", "Search products", "Contact support"],
        },
        "llm_timeout": {
            "message": "I'm taking longer than usual to think. Let me give you a quick response.",
            "followups": ["View popular items", "Browse categories", "Try simpler question"],
        },
        "inventory_error": {
            "message": "I couldn't verify the stock status. Please contact our team at 1300 327 962 for real-time availability.",
            "followups": ["Contact support", "View product details", "Continue shopping"],
        },
        "cart_error": {
            "message": "I had trouble updating your cart. Please try again or contact support if the issue persists.",
            "followups": ["Try again", "View cart", "Contact support"],
        },
        "session_error": {
            "message": "Your session may have expired. Let me help you start fresh.",
            "followups": ["Start new session", "Search products", "Get help"],
        },
    }
    
    RECOVERY_FOLLOWUPS = {
        "default": [
            "Try a different search",
            "Browse categories", 
            "Contact support"
        ],
        "after_search_error": [
            "Search for chairs",
            "Search for desks",
            "Browse all products"
        ],
        "after_cart_error": [
            "View my cart",
            "Continue shopping",
            "Contact support"
        ]
    }
    
    def handle_error(
        self,
        error_type: str,
        context: Dict = None
    ) -> Dict:
        """Handle error with graceful recovery"""
        
        recovery = self.ERROR_RESPONSES.get(error_type, {
            "message": "Something went wrong. Let me help you differently.",
            "followups": self.RECOVERY_FOLLOWUPS["default"]
        })
        
        response = {
            "message": recovery["message"],
            "followups": recovery.get("followups", self.RECOVERY_FOLLOWUPS["default"]),
            "recovered": True,
            "error_type": error_type
        }
        
        # Add context-specific suggestions
        if context:
            if context.get("query"):
                response["original_query"] = context["query"]
            if context.get("intent"):
                response["intent"] = context["intent"]
        
        logger.info(f"[ERROR_RECOVERY] Handled {error_type}, returning recovery response")
        
        return response
    
    def get_fallback_message(self, intent: str = None) -> str:
        """Get a fallback message when all else fails"""
        
        fallbacks = {
            "product_search": "I'm having trouble with that search. Try browsing our categories or contact us for help!",
            "product_spec_qa": "I couldn't get those product details right now. Try asking about a different product or contact support.",
            "cart_add": "I couldn't add that to your cart. Please try using the 'Add to Cart' button on the product card.",
            "default": "I'm here to help! You can search for products, ask about specifications, or contact our support team."
        }
        
        return fallbacks.get(intent, fallbacks["default"])
    
    def suggest_alternatives(self, failed_query: str) -> List[str]:
        """Suggest alternative queries when search fails"""
        
        # Extract potential category from query
        categories = ["chair", "desk", "sofa", "table", "bed", "storage"]
        found_category = None
        
        for cat in categories:
            if cat in failed_query.lower():
                found_category = cat
                break
        
        if found_category:
            return [
                f"Show me all {found_category}s",
                f"Popular {found_category}s",
                f"Budget {found_category}s under $500"
            ]
        
        return [
            "Show me office chairs",
            "Browse sofas",
            "View popular products"
        ]


# Global error recovery instance
error_recovery = ErrorRecovery()


def get_error_recovery() -> ErrorRecovery:
    """Get the global error recovery instance"""
    return error_recovery
