"""
Intelligent Context Handler using LLM for understanding
Instead of hardcoded patterns, use the LLM to intelligently understand:
- Is a query a follow-up to previous context?
- Is a response asking for clarification or showing products?
- Should previous context be applied to current query?
"""

import json
import asyncio
from typing import Dict, Any, Optional, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from app.core.config import get_settings


class IntelligentContextHandler:
    """
    Use LLM to intelligently analyze context and query relationships
    instead of relying on hardcoded patterns.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.llm = ChatOpenAI(
            api_key=self.settings.OPENAI_API_KEY,
            model=self.settings.OPENAI_MODEL or self.settings.LLM_MODEL,
            base_url=self.settings.OPENAI_BASE_URL,
            temperature=0.0,  # Deterministic for analysis
            timeout=10,
            max_tokens=500,
        )
    
    async def should_apply_previous_context(
        self, 
        current_message: str, 
        previous_shopping_context: Optional[str],
        recent_conversation: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Use LLM to determine if current message needs previous shopping context.
        
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
        
        # Get last few exchanges for context
        recent_history = ""
        if recent_conversation:
            last_exchanges = recent_conversation[-4:]  # Last 2 exchanges
            for msg in last_exchanges:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")[:200]  # Truncate long messages
                recent_history += f"{role}: {content}\n\n"
        
        analysis_prompt = f"""Analyze if the user's current message is incomplete and needs previous shopping context.

RECENT CONVERSATION:
{recent_history if recent_history else "No previous conversation"}

PREVIOUS SHOPPING CONTEXT:
"{previous_shopping_context}"

CURRENT USER MESSAGE:
"{current_message}"

Task: Determine if the current message is:
1. A continuation/follow-up that references the previous context (e.g., "yes", "you choose", "give me that", "go ahead")
2. Too vague without previous context (e.g., "bundle", "just pick", "make one")
3. A NEW independent query that doesn't need previous context (e.g., "show me office chairs")

If it needs context, combine them naturally. Otherwise, keep the current message as-is.

Respond with ONLY valid JSON (no markdown, no explanation):
{{
    "needs_context": true/false,
    "combined_query": "combined query if needs_context=true, otherwise current message",
    "reasoning": "brief explanation"
}}"""
        
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content="You are a context analysis assistant. Respond with ONLY valid JSON, no markdown formatting."),
                HumanMessage(content=analysis_prompt)
            ])
            
            result_text = response.content.strip()
            
            # Clean up markdown if present
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            
            # Validate result structure
            if "needs_context" in result and "combined_query" in result:
                return result
            else:
                raise ValueError("Invalid JSON structure")
                
        except Exception as e:
            # Fallback to safe default
            return {
                "needs_context": False,
                "combined_query": current_message,
                "reasoning": f"Analysis failed: {str(e)}, using original message"
            }
    
    async def analyze_response_type(
        self,
        assistant_response: str,
        user_query: str
    ) -> Dict[str, Any]:
        """
        Use LLM to determine if assistant's response is:
        - Asking for clarification
        - Showing product listings
        - Both (which shouldn't happen per our rules)
        
        Returns: {
            "is_clarification": bool,
            "is_showing_products": bool,
            "reasoning": str
        }
        """
        
        # Quick heuristic check first to avoid LLM call when obvious
        has_numbered_products = any(marker in assistant_response for marker in ["\n1.", "\n2.", "\n3."])
        has_price_symbols = "$" in assistant_response and any(price_pattern in assistant_response for price_pattern in ["$", "–", "-", "Price:"])
        
        # If has numbered list with prices, it's clearly showing products
        if has_numbered_products and has_price_symbols:
            return {
                "is_clarification": False,
                "is_showing_products": True,
                "reasoning": "Response has numbered product list with prices"
            }
        
        analysis_prompt = f"""Analyze an assistant's response to determine its type.

USER QUERY:
"{user_query}"

ASSISTANT RESPONSE:
"{assistant_response[:500]}"

Task: Determine if the response is:
1. CLARIFICATION: Asking user to specify/clarify something (e.g., "Which items do you need?", "What color?", "What size?")
2. SHOWING PRODUCTS: Displaying specific product listings with names/prices (e.g., "Here are chairs: 1. Chair A - $100, 2. Chair B - $200")

Rules:
- Numbered product listings with prices = showing_products
- Questions asking which/what items without showing actual products = clarification
- A polite question at the END of products ("Would you like more details?") still counts as showing_products

Respond with ONLY valid JSON (no markdown, no explanation):
{{
    "is_clarification": true/false,
    "is_showing_products": true/false,
    "reasoning": "brief explanation"
}}"""
        
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content="You are a response type analyzer. Respond with ONLY valid JSON, no markdown formatting."),
                HumanMessage(content=analysis_prompt)
            ])
            
            result_text = response.content.strip()
            
            # Clean up markdown if present
            if "```json" in result_text:
                result_text = result_text.split("```json")[1].split("```")[0].strip()
            elif "```" in result_text:
                result_text = result_text.split("```")[1].split("```")[0].strip()
            
            result = json.loads(result_text)
            
            # Validate result structure
            if "is_clarification" in result and "is_showing_products" in result:
                return result
            else:
                raise ValueError("Invalid JSON structure")
                
        except Exception as e:
            # Fallback to heuristic
            return {
                "is_clarification": not has_numbered_products,
                "is_showing_products": has_numbered_products,
                "reasoning": f"Analysis failed: {str(e)}, using heuristic fallback"
            }


_intelligent_context_handler: Optional[IntelligentContextHandler] = None


def get_intelligent_context_handler() -> IntelligentContextHandler:
    """Get or create singleton intelligent context handler."""
    global _intelligent_context_handler
    if _intelligent_context_handler is None:
        _intelligent_context_handler = IntelligentContextHandler()
    return _intelligent_context_handler
