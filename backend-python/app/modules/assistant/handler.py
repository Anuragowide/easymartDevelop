"""
Easymart Assistant Handler

Main orchestrator for the conversational AI assistant.
Coordinates LLM, tools, intent detection, and session management.
"""

import json
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel

# Import components
from .hf_llm_client import HuggingFaceLLMClient, Message, LLMResponse
from .tools import EasymartAssistantTools, TOOL_DEFINITIONS, execute_tool
from .intent_detector import IntentDetector
from .intents import IntentType
from .session_store import SessionStore, SessionContext, get_session_store
from .prompts import (
    get_system_prompt,
    get_greeting_message,
    get_clarification_prompt,
    get_empty_results_prompt,
    get_spec_not_found_prompt
)

# Import observability
from ..observability.logging_config import get_logger
from ..observability.events import EventTracker


logger = get_logger(__name__)


class AssistantRequest(BaseModel):
    """Request to assistant"""
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None


class AssistantResponse(BaseModel):
    """Response from assistant"""
    message: str
    session_id: str
    products: List[Dict[str, Any]] = []
    cart_summary: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = {}


class EasymartAssistantHandler:
    """
    Main handler for Easymart conversational assistant.
    
    Orchestrates:
    - Session management
    - Intent detection
    - LLM inference with function calling
    - Tool execution
    - Response formatting
    """
    
    def __init__(
        self,
        llm_client: Optional[HuggingFaceLLMClient] = None,
        session_store: Optional[SessionStore] = None  # ✅ Correct
    ):
        """
        Initialize assistant handler.
        
        Args:
            llm_client: Optional HF LLM client (creates new if not provided)
            session_store: Optional session store (uses global if not provided)
        """
        self.llm_client = llm_client
        self.session_store = session_store or get_session_store()
        self.tools = EasymartAssistantTools()
        self.intent_detector = IntentDetector()
        self.event_tracker = EventTracker()
        
        # System prompt
        self.system_prompt = get_system_prompt()
        
        logger.info("Easymart Assistant Handler initialized")
    
    async def handle_message(
        self,
        request: AssistantRequest
    ) -> AssistantResponse:
        """
        Handle user message and generate response.
        
        Main conversation flow:
        1. Get or create session
        2. Add message to history
        3. Detect intent (optional, for analytics)
        4. Call LLM with conversation history and tools
        5. Execute any function calls
        6. Format and return response
        
        Args:
            request: AssistantRequest with message and session info
        
        Returns:
            AssistantResponse with assistant message and metadata
        
        Example:
            >>> handler = EasymartAssistantHandler()
            >>> request = AssistantRequest(message="Show me office chairs")
            >>> response = await handler.handle_message(request)
            >>> print(response.message)
        """
        # Track event
        await self.event_tracker.track(
            "assistant_request",
            session_id=request.session_id,
            properties={
                "message_length": len(request.message),
                "has_session": bool(request.session_id)
            }
        )
        
        try:
            logger.info(f"[HANDLER] Starting message handling for session: {request.session_id}")
            
            # Get or create session
            logger.info(f"[HANDLER] Getting session...")
            session = self.session_store.get_or_create_session(
                session_id=request.session_id,
                user_id=request.user_id
            )
            logger.info(f"[HANDLER] Session retrieved: {session.session_id}")
            
            # Add user message to history
            logger.info(f"[HANDLER] Adding user message to history...")
            session.add_message("user", request.message)
            
            # VALIDATION: Check if query is off-topic (not related to e-commerce/shopping)
            off_topic_patterns = [
                # Programming/coding
                r'\b(python|javascript|java|code|programming|function|class|variable|algorithm|debug)\s+(code|snippet|program|script)',
                r'\b(write|create|make|generate)\s+(a|an|the)?\s*(code|program|script|function)',
                r'\bstar pattern\b|\bdiamond pattern\b|\bpyramid pattern\b',
                r'\bhow to (code|program|write code|make a program)',
                # Math/calculations (not pricing)
                r'\bsolve\s+(the|this)?\s*(equation|problem|math)',
                r'\bcalculate\s+(?!shipping|price|cost|total)',
                r'\bwhat is\s+\d+\s*[\+\-\*\/]\s*\d+',
                # General knowledge/trivia
                r'\b(who is|what is|when did|where is|why did)\s+(?!the (price|cost|shipping|delivery|return policy))',
                r'\b(capital of|president of|population of|history of)\b',
                # Creative/entertainment
                r'\b(write|tell|create)\s+(a|an|the)?\s*(story|poem|joke|song|essay)',
                r'\bwrite me (a|an)\b',
            ]
            
            message_lower = request.message.lower()
            
            # Check if message matches any off-topic pattern
            is_off_topic = any(re.search(pattern, message_lower) for pattern in off_topic_patterns)
            
            # Additional check: if message contains none of the shopping keywords
            shopping_keywords = [
                'chair', 'table', 'desk', 'sofa', 'bed', 'furniture', 'product', 'item',
                'buy', 'purchase', 'order', 'cart', 'price', 'cost', 'shipping', 'delivery',
                'return', 'policy', 'warranty', 'available', 'stock', 'show', 'find', 'search',
                'compare', 'recommend', 'looking for', 'need', 'want', 'locker', 'cabinet',
                'storage', 'drawer', 'office', 'home', 'bedroom', 'living room', 'kitchen'
            ]
            
            has_shopping_context = any(keyword in message_lower for keyword in shopping_keywords)
            
            # CHECK FOR RESET/CLEAR COMMANDS
            reset_keywords = ['clear chat', 'reset chat', 'start over', 'clear history', 'clear session', 'reset session', 'clear all', 'restart chat']
            is_reset = any(keyword in message_lower for keyword in reset_keywords)
            
            if is_reset:
                logger.info(f"[HANDLER] Reset command detected: {request.message}")
                reset_message = "I've cleared our conversation history. How can I help you with your shopping today?"
                
                # We return a specific metadata flag that frontend will use to clear UI
                return AssistantResponse(
                    message=reset_message,
                    session_id=session.session_id, # Frontend will generate new one
                    products=[],
                    cart_summary=self._build_cart_summary(session),
                    metadata={
                        "intent": "system_reset",
                        "reset_session": True,
                        "entities": {},
                        "function_calls_made": 0
                    }
                )
            
            if is_off_topic and not has_shopping_context:
                logger.warning(f"[HANDLER] Off-topic query detected: {request.message}")
                assistant_message = (
                    "I'm EasyMart's shopping assistant, specialized in helping you find furniture and home products. "
                    "I can help you search for chairs, tables, desks, storage solutions, and more. "
                    "What products are you looking for today?"
                )
                
                session.add_message("assistant", assistant_message)
                
                await self.event_tracker.track(
                    "assistant_response_success",
                    session_id=session.session_id,
                    properties={
                        "intent": "off_topic_rejected",
                        "response_length": len(assistant_message)
                    }
                )
                
                return AssistantResponse(
                    message=assistant_message,
                    session_id=session.session_id,
                    products=[],
                    cart_summary=self._build_cart_summary(session),
                    metadata={
                        "intent": "off_topic_rejected",
                        "entities": {},
                        "function_calls_made": 0
                    }
                )
            
            # Detect intent (for analytics/logging)
            logger.info(f"[HANDLER] Detecting intent...")
            intent = self.intent_detector.detect(request.message)
            logger.info(f"[HANDLER] Intent detected: {intent}, type: {type(intent)}")
            
            entities = self.intent_detector.extract_entities(request.message, intent)
            logger.info(f"[HANDLER] Entities extracted: {entities}")
            
            # Convert intent to string safely
            try:
                if isinstance(intent, str):
                    intent_str = intent
                    logger.info(f"[HANDLER] Intent is string: {intent_str}")
                else:
                    intent_str = intent.value
                    logger.info(f"[HANDLER] Intent enum converted to string: {intent_str}")
            except AttributeError as e:
                logger.error(f"[HANDLER] Error converting intent to string. Intent type: {type(intent)}, value: {intent}")
                logger.error(f"[HANDLER] Full traceback:", exc_info=True)
                raise
            
            logger.info(f"Detected intent: {intent_str}, entities: {entities}")
            
            # SHORTCUT: If intent is greeting, return static greeting
            if intent_str == "greeting":
                logger.info("[HANDLER] Greeting intent detected, returning static greeting")
                assistant_message = get_greeting_message()
                
                # Add assistant response to history
                session.add_message("assistant", assistant_message)
                
                # Build response
                response = AssistantResponse(
                    message=assistant_message,
                    session_id=session.session_id,
                    products=session.last_shown_products,
                    cart_summary=self._build_cart_summary(session),
                    metadata={
                        "intent": intent_str,
                        "entities": entities,
                        "function_calls_made": 0
                    }
                )
                
                # Track success
                await self.event_tracker.track(
                    "assistant_response_success",
                    session_id=request.session_id,
                    properties={
                        "intent": intent_str,
                        "response_length": len(assistant_message)
                    }
                )
                
                return response
            
            # FORCE product_search intent for furniture-related queries
            # BUT: Reject vague single-word queries that need clarification
            furniture_keywords = [
                "chair", "table", "desk", "sofa", "bed", "shelf", "locker", "stool",
                "cabinet", "storage", "furniture", "office", "bedroom", "living",
                "dining", "wardrobe", "drawer", "bench", "ottoman"
            ]
            
            # Check if query is too vague (single word without context)
            vague_queries = ["show", "find", "search", "get", "display", "list"]
            is_vague = (
                request.message.lower().strip() in vague_queries or
                len(request.message.strip().split()) == 1 and request.message.lower().strip() in vague_queries
            )
            
            if is_vague:
                logger.info(f"[HANDLER] Vague query detected: '{request.message}', asking for clarification")
                assistant_message = (
                    "To help you better, please provide a specific furniture query such as "
                    "\"show me office chairs\" or \"search for dining tables\". "
                    "This will enable me to provide accurate results."
                )
                
                session.add_message("assistant", assistant_message)
                
                return AssistantResponse(
                    message=assistant_message,
                    session_id=session.session_id,
                    products=[],
                    cart_summary=self._build_cart_summary(session),
                    metadata={
                        "intent": "clarification_needed",
                        "entities": {},
                        "function_calls_made": 0
                    }
                )

            # CHECK FOR ROOM REDO (vague furnishing requests)
            room_redo_patterns = [
                r'i am (redoing|furnishing|fixing up|updating|renovating) my (living room|bedroom|kitchen|office|dining room|room)',
                r'i need (some )?furniture for my (living room|bedroom|kitchen|office|dining room|room)'
            ]
            
            is_room_redo = any(re.search(pattern, message_lower) for pattern in room_redo_patterns)
            # Check if any specific furniture items are mentioned
            specific_items = ["chair", "table", "sofa", "desk", "bed", "shelf", "cabinet", "locker", "stool", "bench", "drawer", "wardrobe"]
            mentions_specific_item = any(item in message_lower for item in specific_items)
            
            if is_room_redo and not mentions_specific_item:
                logger.info(f"[HANDLER] Room redo detected without specific items: {request.message}")
                # Extract room name
                room_match = re.search(r'(living room|bedroom|kitchen|office|dining room|room)', message_lower)
                room_name = room_match.group(0) if room_match else "room"
                
                assistant_message = f"tell me what furniture do you want for your {room_name} tell me i will assist you with what you want"
                
                session.add_message("assistant", assistant_message)
                
                return AssistantResponse(
                    message=assistant_message,
                    session_id=session.session_id,
                    products=[],
                    cart_summary=self._build_cart_summary(session),
                    metadata={
                        "intent": "clarification_needed_room_redo",
                        "entities": {"room": room_name},
                        "function_calls_made": 0
                    }
                )
            
            if any(keyword in request.message.lower() for keyword in furniture_keywords):
                if intent not in [IntentType.PRODUCT_SEARCH, IntentType.PRODUCT_SPEC_QA]:
                    logger.info(f"[HANDLER] Overriding intent from {intent} to PRODUCT_SEARCH for furniture query")
                    intent = IntentType.PRODUCT_SEARCH
            
            # Detect if this is a refinement query and inject context
            original_message = request.message  # Save original before modification
            refined_message = self._apply_context_refinement(request.message, session)
            if refined_message != request.message:
                logger.info(f"[HANDLER] Applied context refinement: '{request.message}' → '{refined_message}'")
                # Temporarily update the message for search
                request.message = refined_message
            
            # Build conversation messages for LLM
            logger.info(f"[HANDLER] Building conversation messages...")
            messages = self._build_messages(session)
            logger.info(f"[HANDLER] Built {len(messages)} messages")
            
            # Create LLM client if not exists
            if not self.llm_client:
                logger.info(f"[HANDLER] Creating LLM client...")
                from .hf_llm_client import create_llm_client
                self.llm_client = await create_llm_client()
            
            # Call LLM with function calling
            logger.info(f"[HANDLER] Calling LLM with query: '{request.message}'")
            llm_response = await self.llm_client.chat(
                messages=messages,
                tools=TOOL_DEFINITIONS,
                temperature=0.3,
                max_tokens=256
            )
            
            # Process function calls if any
            if llm_response.function_calls:
                tool_results = await self._execute_function_calls(
                    llm_response.function_calls,
                    session
                )
                
                # Add tool results to conversation
                for tool_name, result in tool_results.items():
                    messages.append(Message(
                        role="user",
                        content=f"[TOOL_RESULTS] {json.dumps(result)} [/TOOL_RESULTS]"
                    ))
                
                # Generate final response with tool results
                final_response = await self.llm_client.chat(
                    messages=messages,
                    temperature=0.3,
                    max_tokens=512
                )
                assistant_message = final_response.content
            else:
                assistant_message = llm_response.content
            
            # Final cleanup
            assistant_message = re.sub(r'\[TOOL_?CALLS\].*?\[/TOOL_?CALLS\]', '', assistant_message, flags=re.IGNORECASE | re.DOTALL).strip()
            
            # Add assistant response to history
            session.add_message("assistant", assistant_message)
            
            # Build response
            response = AssistantResponse(
                message=assistant_message,
                session_id=session.session_id,
                products=session.last_shown_products,
                cart_summary=self._build_cart_summary(session),
                metadata={
                    "intent": intent_str,
                    "entities": entities,
                    "function_calls_made": len(llm_response.function_calls) if llm_response.function_calls else 0
                }
            )
            
            # Track success
            await self.event_tracker.track(
                "assistant_response_success",
                session_id=request.session_id,
                properties={
                    "intent": intent_str,
                    "response_length": len(assistant_message)
                }
            )
            
            return response
        
        except Exception as e:
            logger.error(f"Error handling message: {str(e)}", exc_info=True)
            await self.event_tracker.track("assistant_error", properties={"error": str(e)})
            
            # Return error response
            return AssistantResponse(
                message="I'm sorry, I encountered an error processing your request. Please try again or contact support.",
                session_id=request.session_id or "error",
                metadata={"error": str(e)}
            )
    
    def _apply_context_refinement(self, message: str, session: SessionContext) -> str:
        """
        Detect if the current message is a refinement of a previous query
        and combine it with context from conversation history.
        Handles both adding new filters and replacing conflicting filters.
        
        Args:
            message: Current user message
            session: Session context with conversation history
        
        Returns:
            Refined message with context applied, or original if not a refinement
        """
        message_lower = message.lower().strip()
        
        # Attribute categories for filter replacement
        attribute_groups = {
            'color': ['black', 'white', 'brown', 'grey', 'gray', 'blue', 'red', 'green', 'yellow', 'pink', 'purple', 'orange', 'beige', 'navy', 'silver', 'gold'],
            'age_group': ['kids', 'children', 'child', 'toddler', 'baby', 'infant', 'teen', 'teenager', 'adult'],
            'size': ['small', 'large', 'big', 'huge', 'tiny', 'medium', 'tall', 'short', 'wide', 'narrow', 'compact', 'spacious'],
            'material': ['wooden', 'wood', 'metal', 'plastic', 'fabric', 'leather', 'glass', 'steel', 'oak', 'pine', 'velvet', 'cotton'],
            'price': ['cheap', 'expensive', 'affordable', 'budget', 'luxury', 'premium', 'economy', 'high-end', 'low-cost'],
        }
        
        # Refinement patterns: short queries that modify previous search
        refinement_patterns = [
            r'^(for|in|with)\s+',  # "for kids", "in black", "with storage"
            r'^(show|find|get)\s+(me\s+)?(some|the|a|an)?\s*$',  # "show me some", "find the"
        ]
        
        import re
        is_refinement = any(re.match(pattern, message_lower) for pattern in refinement_patterns)
        
        # Also check if message is very short (likely a refinement)
        words = message_lower.split()
        all_refinement_keywords = [keyword for keywords in attribute_groups.values() for keyword in keywords]
        
        if len(words) <= 3 and not is_refinement:
            if any(keyword in message_lower for keyword in all_refinement_keywords):
                is_refinement = True
        
        if not is_refinement:
            return message  # Not a refinement, return as-is
        
        # Extract context from recent conversation
        # Look for the last product search query that's NOT a refinement
        last_search_query = None
        for msg in reversed(session.messages[-10:]):  # Check last 10 messages
            if msg["role"] == "user":
                user_msg = msg["content"]
                user_msg_lower = user_msg.lower()
                
                # Skip if it's a question about a specific product
                if any(word in user_msg_lower for word in ['option', 'number', 'tell me about', 'what is', 'describe']):
                    continue
                
                # Skip if it's a pure refinement query (short queries starting with for/in/with)
                words = user_msg_lower.split()
                if len(words) <= 3:
                    # Check if it starts with refinement patterns
                    if any(user_msg_lower.startswith(prefix) for prefix in ['for ', 'in ', 'with ']):
                        logger.info(f"[CONTEXT] Skipping refinement query: '{user_msg}'")
                        continue
                
                # This is a full search query - use it as base
                last_search_query = user_msg
                logger.info(f"[CONTEXT] Found last full search query: '{last_search_query}'")
                break
        
        if not last_search_query:
            logger.info(f"[CONTEXT] No previous full search found for refinement of: '{message}'")
            return message  # No previous search found, return as-is
        
        # Clean up the last search query - extract just the product/subject
        # Remove common action phrases to get the core search term
        last_query_clean = last_search_query.lower()
        for prefix in ['show me ', 'find me ', 'get me ', 'search for ', 'looking for ', 'i want ', 'i need ']:
            if last_query_clean.startswith(prefix):
                last_query_clean = last_query_clean[len(prefix):]
                break
        
        # Remove common suffixes
        for suffix in [' please', ' thanks', ' thank you']:
            if last_query_clean.endswith(suffix):
                last_query_clean = last_query_clean[:-len(suffix)]
                break
        
        last_query_clean = last_query_clean.strip()
        
        # CRITICAL: Remove any attributes that may have been hallucinated by LLM
        # Only keep attributes that were explicitly in the original user query
        # This prevents "show me lockers" → LLM says "in black" → next query picks up "black"
        original_had_attributes = {}
        for category, keywords in attribute_groups.items():
            for keyword in keywords:
                if keyword in last_search_query.lower():  # Check ORIGINAL user message
                    original_had_attributes[category] = keyword
                    break
        
        # Remove any attribute words that weren't in the original query
        for category, keywords in attribute_groups.items():
            if category not in original_had_attributes:
                # This category wasn't in original query - remove all its keywords
                for keyword in keywords:
                    if keyword in last_query_clean:
                        last_query_clean = last_query_clean.replace(keyword, '').strip()
                        logger.info(f"[CONTEXT] Removed hallucinated attribute '{keyword}' from context")
        
        # Clean up multiple spaces
        last_query_clean = ' '.join(last_query_clean.split())
        logger.info(f"[CONTEXT] Cleaned base query: '{last_query_clean}'")
        
        # Remove common prefixes from current message
        clean_message = message_lower
        for prefix in ['for ', 'in ', 'with ', 'show me ', 'find me ', 'get me ']:
            if clean_message.startswith(prefix):
                clean_message = clean_message[len(prefix):]
                break
        
        # Remove common suffixes (including "colour" and "color" as they're redundant)
        for suffix in [' colour', ' color', ' please', ' thanks', ' thank you']:
            if clean_message.endswith(suffix):
                clean_message = clean_message[:-len(suffix)].strip()
        
        clean_message = clean_message.strip()
        logger.info(f"[CONTEXT] Cleaned current message: '{clean_message}'")
        
        # Detect what attribute category the new refinement belongs to
        new_attribute_category = None
        new_attribute_value = None
        for category, keywords in attribute_groups.items():
            for keyword in keywords:
                if keyword in clean_message:
                    new_attribute_category = category
                    new_attribute_value = keyword
                    break
            if new_attribute_category:
                break
        
        # If we detected a new attribute, check if we need to REPLACE an existing one
        if new_attribute_category and new_attribute_value:
            # Check if the last query contains an attribute from the same category
            for existing_keyword in attribute_groups[new_attribute_category]:
                if existing_keyword in last_query_clean and existing_keyword != new_attribute_value:
                    # Found a conflicting attribute - REPLACE it
                    refined_query = last_query_clean.replace(existing_keyword, new_attribute_value)
                    logger.info(f"[CONTEXT] Filter replacement detected. Replacing '{existing_keyword}' with '{new_attribute_value}' in '{last_query_clean}' → '{refined_query}'")
                    return refined_query
        
        # No conflict found - ADD the new filter to existing context
        # Put base query first, then the refinement for better search results
        refined_query = f"{last_query_clean} {clean_message}"
        logger.info(f"[CONTEXT] Filter addition detected. Base: '{last_query_clean}', Addition: '{clean_message}', Combined: '{refined_query}'")
        
        return refined_query
    
    def _build_messages(self, session: SessionContext) -> List[Message]:
        """
        Build message list for LLM from session history.
        Injects system prompt ONLY once at the start.
        """
        messages = [
            Message(role="system", content=self.system_prompt)
        ]
        
        # Add conversation history (last 10 messages)
        # We don't repeat the system prompt or add extra instructions here
        for msg in session.messages[-10:]:
            messages.append(Message(
                role=msg["role"],
                role_type=msg.get("role_type", "text"), # Keep role type if present
                content=msg["content"]
            ))
        
        return messages
    
    def _validate_response(
        self, 
        response: str, 
        had_tool_calls: bool,
        tool_results: Dict[str, Any],
        original_query: str = "",
        search_query: str = ""
    ) -> str:
        """
        Validate response to prevent hallucinated product listings and attributes.
        
        Args:
            response: LLM response text
            had_tool_calls: Whether tools were called
            tool_results: Results from tool execution
            original_query: Original user query (before context refinement)
            search_query: Actual search query used (after context refinement)
        
        Returns:
            Validated (possibly modified) response
        """
        import re
        
        # Check if response mentions wrong product type
        # Extract important nouns from search query
        if search_query and had_tool_calls:
            important_nouns = {'chair', 'chairs', 'table', 'tables', 'desk', 'desks', 'sofa', 'sofas',
                              'bed', 'beds', 'locker', 'lockers', 'cabinet', 'cabinets', 'shelf', 'shelves',
                              'storage', 'stool', 'stools', 'bench', 'benches', 'wardrobe', 'wardrobes'}
            
            search_nouns = set(search_query.lower().split()) & important_nouns
            response_lower = response.lower()
            
            if search_nouns:
                # Check if response mentions WRONG product type
                # E.g., search for "lockers" but response says "desks"
                for search_noun in search_nouns:
                    # Normalize to singular
                    base_noun = search_noun.rstrip('s')
                    
                    # Check if response mentions this noun or its plural
                    has_correct_noun = base_noun in response_lower or (base_noun + 's') in response_lower
                    
                    if not has_correct_noun:
                        # Response doesn't mention the searched product type at all!
                        # Check if it mentions a DIFFERENT product type
                        wrong_nouns = important_nouns - {base_noun, base_noun + 's'}
                        mentioned_wrong = [noun for noun in wrong_nouns if noun in response_lower]
                        
                        if mentioned_wrong:
                            logger.warning(f"[VALIDATION] ⚠️ Response mentions wrong product type!")
                            logger.warning(f"[VALIDATION] Searched for: {search_noun}, Response mentions: {mentioned_wrong}")
                            # Replace with generic response
                            return f"I found several options that match your search."
        
        # Check if response contains product listings
        # Note: Removed 'Artiss' pattern - it's OK to mention product names in specs responses
        listing_patterns = [
            r'\d+\.\s+[A-Z].*\$\d+',          # "1. Product Name - $99"
            r'Here are (five|\d+) (chairs|desks|tables|products|items)',
            r'\$\d+\.\d+\)',                  # Prices in parentheses
            r'(Black|White|Blue|Red|Green)\s+\(\$',  # Color with price
        ]
        
        has_product_listing = any(re.search(p, response) for p in listing_patterns)
        
        if has_product_listing:
            if had_tool_calls and 'search_products' in tool_results:
                # LLM listed products after search_products tool call - replace with short intro
                product_count = len(tool_results['search_products'].get('products', []))
                if product_count > 0:
                    logger.warning(f"[VALIDATION] Blocked product listing, replacing with short intro")
                    return f"I found {product_count} great options for you!"
                else:
                    return "I couldn't find any products matching that search."
            elif had_tool_calls and 'get_product_specs' in tool_results:
                # For get_product_specs, mentioning the product name is EXPECTED and correct
                # Only block if it's listing MULTIPLE products with numbers (1. Product $99, 2. Product $99)
                numbered_list = re.search(r'\d+\.\s+[A-Z].*\$\d+', response)
                if numbered_list:
                    logger.error(f"[VALIDATION] Blocked hallucinated product listing in specs response!")
                    return "Let me provide you with the details from our database."
                # Single product mention is fine - don't block
            elif not had_tool_calls:
                # LLM tried to hallucinate products without any tool call
                logger.error(f"[VALIDATION] Blocked hallucinated product listing!")
                return "Let me search our catalog for you."
        
        # Block hallucinated attributes in response that weren't in user's query
        # Common attributes: colors, materials, sizes, age groups
        # Define synonym groups to avoid blocking equivalent terms
        synonym_groups = [
            {'kids', 'children', 'child'},
            {'grey', 'gray'},
            {'wood', 'wooden'},
        ]
        
        attribute_keywords = {
            'colors': ['black', 'white', 'brown', 'grey', 'gray', 'blue', 'red', 'green', 'yellow', 'pink', 'purple', 'orange', 'beige', 'navy', 'silver', 'gold'],
            'materials': ['wooden', 'wood', 'metal', 'plastic', 'fabric', 'leather', 'glass', 'steel'],
            'sizes': ['small', 'large', 'big', 'tiny', 'medium', 'compact'],
            'age_groups': ['kids', 'children', 'child', 'baby', 'adult', 'teen']
        }
        
        def is_synonym(word1: str, word2: str) -> bool:
            """Check if two words are synonyms."""
            for group in synonym_groups:
                if word1 in group and word2 in group:
                    return True
            return False
        
        if had_tool_calls and original_query:
            query_lower = original_query.lower()
            response_lower = response.lower()
            
            # Check if response mentions attributes that weren't in the query
            for attr_type, keywords in attribute_keywords.items():
                for keyword in keywords:
                    # If attribute is in response but NOT in original query
                    if keyword in response_lower and keyword not in query_lower:
                        # Check if a synonym is in the query
                        has_synonym_in_query = any(is_synonym(keyword, word) for word in query_lower.split())
                        
                        if has_synonym_in_query:
                            # Don't block - it's a synonym of what user asked
                            continue
                        
                        # Check if it's in a meaningful context (not just "in black")
                        attr_patterns = [
                            rf'\bin {keyword}\b',           # "in black"
                            rf'\b{keyword} \w+',            # "black lockers"  
                            rf'\w+ {keyword}\b',            # "office black"
                        ]
                        if any(re.search(p, response_lower) for p in attr_patterns):
                            logger.warning(f"[VALIDATION] ⚠️ Blocked hallucinated attribute '{keyword}' not in query!")
                            logger.warning(f"[VALIDATION] Query: '{original_query}', Response mentioned: '{keyword}'")
                            # Remove the hallucinated attribute mention
                            response = re.sub(rf'\s*in {keyword}', '', response, flags=re.IGNORECASE)
                            response = re.sub(rf'{keyword} ', '', response, flags=re.IGNORECASE, count=1)
                            response = response.strip()
        
        # Block hallucinated product specifications (dimensions, materials, colors)
        # These should ONLY come from get_product_specs tool, not LLM imagination
        spec_hallucination_patterns = [
            r'\b\d+\s*cm\s*\(width\)|\b\d+\s*cm\s*\(height\)|\b\d+\s*cm\s*\(depth\)',  # Specific dimensions
            r'\bmade of\s+(plastic|wood|metal|fabric|leather)',  # Material claims
            r'\bcomes in\s+(various|vibrant|different)\s+colors?',  # Color variety claims
            r'\bapproximately\s+\d+\s*cm',  # "approximately X cm"
            r'\bseat is (comfortable|padded|cushioned)',  # Comfort claims
            r'\bbackrest provides (adequate|good|excellent) support',  # Support claims
            r'\bperfect for (a kid|children|kids)',  # Usage claims
        ]
        
        # Only validate if NO tool calls were made (LLM is making things up)
        if not had_tool_calls:
            for pattern in spec_hallucination_patterns:
                if re.search(pattern, response, re.IGNORECASE):
                    logger.warning(f"[VALIDATION] ⚠️ Blocked hallucinated product specification!")
                    logger.warning(f"[VALIDATION] Spec pattern matched: {pattern}")
                    return "I need to look up the specific details for that product. Could you specify which product number you're asking about?"
        
        # Strict Spec Verification for Colors (Post-Generation Safety)
        if had_tool_calls and 'get_product_specs' in tool_results:
            spec_result = tool_results['get_product_specs']
            # Flatten specs to check what's actually in the data
            specs_text = str(spec_result.get('product_name', '')).lower()
            if 'specs' in spec_result:
                for val in spec_result['specs'].values():
                    specs_text += f" {str(val).lower()}"
            if 'description' in spec_result:
                specs_text += f" {str(spec_result.get('description', '')).lower()}"
                
            # Check colors
            for color in attribute_keywords['colors']:
                # If color is in response ...
                if color in response.lower(): 
                    # ... but NOT in the actual product data
                    if color not in specs_text:
                        # Check for affirmative claims (hallucination risk)
                        affirmative_patterns = [
                            rf"available in [^.]*{color}",
                            rf"comes in [^.]*{color}",
                            rf"offer [^.]*{color}",
                            rf"have [^.]*{color}",
                            rf"{color} (is|are) available",
                            rf"{color} option",
                        ]
                        
                        is_affirmative = any(re.search(p, response, re.IGNORECASE) for p in affirmative_patterns)
                        
                        # Check for negation (allow "not available in green")
                        is_negated = re.search(rf"not (available|come|offered|have).*?{color}", response, re.IGNORECASE)
                        
                        if is_affirmative and not is_negated:
                            logger.warning(f"[VALIDATION] ⚠️ Strict color check failed! Hallucinated: '{color}'")
                            
                            # Build safe fallback response
                            valid_colors = [c for c in attribute_keywords['colors'] if c in specs_text]
                            if valid_colors:
                                valid_str = ", ".join(valid_colors).title()
                                return f"I checked the product details, and the available colors listed are: {valid_str}. I don't see {color} as an option."
                            else:
                                return f"I checked the product specifications, but I don't see {color} mentioned in the current options."

        return response
    
    async def _execute_function_calls(
        self,
        function_calls: List[Any],
        session: SessionContext
    ) -> Dict[str, Any]:
        """
        Execute function calls from LLM and format results properly.
        """
        results = {}
        
        for func_call in function_calls:
            tool_name = func_call.name
            arguments = func_call.arguments
            
            logger.info(f"Executing tool: {tool_name}")
            
            result = await execute_tool(tool_name, arguments, self.tools)
            
            # FIX: Format products with actual names before sending to LLM
            if tool_name == "search_products" and "products" in result:
                for product in result["products"]:
                    # Ensure name is set from title, not product_X
                    if not product.get("name") or product.get("name").startswith("product_"):
                        product["name"] = product.get("title", product.get("description", "Product"))
                
                # Store in session for reference
                session.update_shown_products(result["products"])
            
            results[tool_name] = result
        
        return results
    
    def _build_cart_summary(self, session: SessionContext) -> Optional[Dict[str, Any]]:
        """
        Build cart summary from session.
        
        Args:
            session: Session context
        
        Returns:
            Cart summary dict or None if empty
        """
        if not session.cart_items:
            return None
        
        return {
            "item_count": len(session.cart_items),
            "items": session.cart_items,
            "total": sum(item.get("quantity", 0) for item in session.cart_items)
        }
    
    async def get_greeting(self, session_id: Optional[str] = None) -> AssistantResponse:
        """
        Get greeting message for new conversation.
        
        Args:
            session_id: Optional session ID
        
        Returns:
            Greeting response
        """
        session = self.session_store.get_or_create_session(session_id=session_id)
        greeting = get_greeting_message()
        session.add_message("assistant", greeting)
        
        return AssistantResponse(
            message=greeting,
            session_id=session.session_id,
            metadata={"type": "greeting"}
        )
    
    async def clear_session(self, session_id: str):
        """
        Clear session (for testing or reset).
        
        Args:
            session_id: Session ID to clear
        """
        self.session_store.delete_session(session_id)
        logger.info(f"Cleared session: {session_id}")


# Singleton handler instance
_handler = None


def get_assistant_handler() -> EasymartAssistantHandler:
    """
    Get global assistant handler instance (singleton).
    
    Returns:
        Global EasymartAssistantHandler instance
    
    Example:
        >>> handler = get_assistant_handler()
        >>> response = await handler.handle_message(request)
    """
    global _handler
    if _handler is None:
        _handler = EasymartAssistantHandler()
    return _handler
