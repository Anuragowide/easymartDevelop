"""
Easymart Assistant Handler

Main orchestrator for the conversational AI assistant.
Coordinates LLM, tools, intent detection, and session management.
"""

import json
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
            furniture_keywords = [
                "chair", "table", "desk", "sofa", "bed", "shelf", "locker", "stool",
                "cabinet", "storage", "furniture", "office", "bedroom", "living",
                "dining", "wardrobe", "drawer", "bench", "ottoman"
            ]
            if any(keyword in request.message.lower() for keyword in furniture_keywords):
                if intent not in [IntentType.PRODUCT_SEARCH, IntentType.PRODUCT_SPEC_QA]:
                    logger.info(f"[HANDLER] Overriding intent from {intent} to PRODUCT_SEARCH for furniture query")
                    intent = IntentType.PRODUCT_SEARCH
            
            # Detect if this is a refinement query and inject context
            refined_message = self._apply_context_refinement(request.message, session)
            if refined_message != request.message:
                logger.info(f"[HANDLER] Applied context refinement: '{request.message}' → '{refined_message}'")
                # Temporarily update the message for search
                original_message = request.message
                request.message = refined_message
            
            # Build conversation messages for LLM
            logger.info(f"[HANDLER] Building conversation messages...")
            messages = self._build_messages(session)
            logger.info(f"[HANDLER] Built {len(messages)} messages")
            
            # Create LLM client if not exists
            if not self.llm_client:
                logger.info(f"[HANDLER] Creating LLM client...")
                # Lazy initialization
                from .hf_llm_client import create_llm_client
                self.llm_client = await create_llm_client()
                logger.info(f"[HANDLER] LLM client created")
            
            # Call LLM with function calling
            logger.info(f"[HANDLER] Calling LLM...")
            llm_response = await self.llm_client.chat(
                messages=messages,
                tools=TOOL_DEFINITIONS,
                temperature=0.3,  # Increased to allow tool calling flexibility
                max_tokens=200    # Reduced - we just need tool call or short response
            )
            logger.info(f"[HANDLER] LLM response received, function_calls: {len(llm_response.function_calls) if llm_response.function_calls else 0}")
            
            # SAFETY CHECK: If product search intent but NO tool calls → LLM hallucinated!
            # Force a tool call to prevent fake products
            # BUT: Check if query is out-of-scope (non-furniture) first
            out_of_scope_keywords = [
                "car", "cars", "vehicle", "automobile", "motorcycle", "bike",
                "laptop", "computer", "pc", "mac", "tablet", "ipad",
                "phone", "mobile", "iphone", "smartphone", "cell",
                "clothing", "clothes", "shirt", "pants", "dress", "shoes",
                "electronics", "tv", "television", "camera", "watch",
                "food", "drink", "groceries", "book", "toy", "game"
            ]

            if intent == IntentType.PRODUCT_SEARCH and not llm_response.function_calls:
                # Check if it's an out-of-scope query
                query_lower = request.message.lower()
                is_out_of_scope = any(keyword in query_lower for keyword in out_of_scope_keywords)
                
                if is_out_of_scope:
                    # Out of scope - let LLM's "we don't sell X" response stand
                    logger.info(f"[HANDLER] Out-of-scope query detected: '{request.message}', skipping safety catch")
                else:
                    # Furniture-related but LLM didn't call tool - force it
                    logger.warning(f"[HANDLER] ⚠️ SAFETY CATCH: Product search intent but LLM didn't call tool!")
                    logger.warning(f"[HANDLER] Forcing search_products call to prevent hallucination")
                    print(f"[DEBUG] ⚠️ FORCING TOOL CALL - LLM tried to hallucinate products!")
                    
                    # Create forced tool call
                    from .hf_llm_client import FunctionCall
                    llm_response.function_calls = [
                        FunctionCall(
                            name="search_products",
                            arguments={"query": request.message}
                        )
                    ]
                    # Clear the hallucinated content
                    llm_response.content = ""
            
            # SAFETY CHECK: If product spec Q&A intent but NO tool calls → force get_product_specs!
            if intent == IntentType.PRODUCT_SPEC_QA and not llm_response.function_calls:
                # Extract product reference from query (option 5, product 3, etc.)
                import re
                product_ref_match = re.search(r'\b(option|product|number|item)\s+(\d+)', request.message.lower())
                
                if product_ref_match:
                    product_num = int(product_ref_match.group(2))
                    
                    # Get product from session (1-indexed in user query, 0-indexed in list)
                    if session.last_shown_products and 0 < product_num <= len(session.last_shown_products):
                        product = session.last_shown_products[product_num - 1]
                        product_id = product.get('id')
                        
                        if product_id:
                            logger.warning(f"[HANDLER] ⚠️ SAFETY CATCH: Product Q&A but LLM didn't call tool!")
                            logger.warning(f"[HANDLER] Forcing get_product_specs call for product {product_num} (ID: {product_id})")
                            print(f"[DEBUG] ⚠️ FORCING get_product_specs - LLM tried to hallucinate specs!")
                            
                            # Create forced tool call
                            from .hf_llm_client import FunctionCall
                            llm_response.function_calls = [
                                FunctionCall(
                                    name="get_product_specs",
                                    arguments={"product_id": product_id}
                                )
                            ]
                            # Clear the hallucinated content
                            llm_response.content = ""
                        else:
                            logger.error(f"[HANDLER] Product {product_num} has no ID, cannot fetch specs")
                    else:
                        logger.warning(f"[HANDLER] Product {product_num} not in session or out of range")
                else:
                    logger.warning(f"[HANDLER] Could not extract product number from: {request.message}")
            
            # Process function calls if any
            if llm_response.function_calls:
                logger.info(f"[HANDLER] Processing {len(llm_response.function_calls)} function calls")
                
                # Execute tools and get results
                tool_results = await self._execute_function_calls(
                    llm_response.function_calls,
                    session
                )
                
                logger.info(f"[HANDLER] Tool results: {list(tool_results.keys())}")
                
                # Add tool results to conversation
                # Note: HuggingFace doesn't support role="tool", so we use role="user"
                for tool_name, result in tool_results.items():
                    result_str = json.dumps(result)
                    messages.append(Message(
                        role="user",  # Changed from "tool" to "user" for HF compatibility
                        content=f"[Tool result from {tool_name}]: {result_str}"
                    ))
                
                # Add strict instruction for final response as user message
                # (HuggingFace doesn't support multiple system messages)
                messages.append(Message(
                    role="user",
                    content=(
                        "Now respond to the user with ONLY a brief, professional 1-2 sentence intro. "
                        "DO NOT list products - they will be displayed below your message. "
                        "DO NOT mention 'UI', 'screen', 'list', or 'display'. "
                        "Examples:\n"
                        "- 'I found 5 great office chairs for you!'\n"
                        "- 'Here are some excellent locker options that match your search.'\n"
                        "- 'I've found several red lockers that might work perfectly for you.'"
                    )
                ))
                
                # Call LLM again to generate final response with tool results
                final_response = await self.llm_client.chat(
                    messages=messages,
                    temperature=0.7,
                    max_tokens=150  # Short response only
                )
                
                # Let LLM generate natural, conversational response
                # Products are already stored in session from tool execution
                assistant_message = final_response.content
                
                # SAFETY: Strip any leaked tool call syntax from message
                # Remove [TOOL_CALLS], [TOOLCALLS], and their content
                import re
                assistant_message = re.sub(r'\[TOOL_?CALLS\].*?\[/TOOL_?CALLS\]', '', assistant_message, flags=re.IGNORECASE | re.DOTALL)
                assistant_message = assistant_message.strip()
                
                # VALIDATION: Block hallucinated product lists and check if results match query
                assistant_message = self._validate_response(
                    assistant_message, 
                    had_tool_calls=True,
                    tool_results=tool_results,
                    original_query=request.message
                )
                
                # Additional validation: Check if search results actually match the query
                if 'search_products' in tool_results:
                    products = tool_results['search_products'].get('products', [])
                    if products:
                        # Extract important nouns from query
                        query_lower = request.message.lower()
                        important_nouns = {'chair', 'chairs', 'table', 'tables', 'desk', 'desks', 'sofa', 'sofas',
                                          'bed', 'beds', 'locker', 'lockers', 'cabinet', 'cabinets', 'shelf', 'shelves',
                                          'storage', 'stool', 'stools', 'bench', 'benches', 'wardrobe', 'wardrobes'}
                        
                        query_nouns = set(query_lower.split()) & important_nouns
                        
                        if query_nouns:
                            # Check if ANY product name contains the query nouns
                            matching_products = []
                            for product in products:
                                product_name = product.get('name', '').lower()
                                if any(noun in product_name for noun in query_nouns):
                                    matching_products.append(product)
                            
                            # If NO products match the key nouns, update message
                            if len(matching_products) == 0:
                                # Extract attributes (colors, materials) from query
                                attributes = []
                                color_keywords = ['black', 'white', 'brown', 'grey', 'gray', 'blue', 'red', 'green', 'yellow']
                                for color in color_keywords:
                                    if color in query_lower:
                                        attributes.append(color)
                                
                                noun_str = ' '.join(query_nouns)
                                if attributes:
                                    attr_str = ' '.join(attributes)
                                    assistant_message = f"I couldn't find any {noun_str} in {attr_str}. Would you like to try a different color or see all available {noun_str}?"
                                else:
                                    assistant_message = f"I couldn't find any {noun_str} matching your search. Here are some related products that might interest you."
                                
                                logger.warning(f"[VALIDATION] ⚠️ No products matched query nouns: {query_nouns}")
                                logger.warning(f"[VALIDATION] Returned products were: {[p.get('name') for p in products[:3]]}")
                
                logger.info(f"[HANDLER] LLM generated response (length: {len(assistant_message)})")
                logger.info(f"[HANDLER] Tool results: {list(tool_results.keys())}")
            else:
                # No function calls, use content directly
                assistant_message = llm_response.content
                
                # VALIDATION: Block responses that list fake products without tool calls
                assistant_message = self._validate_response(
                    assistant_message,
                    had_tool_calls=False,
                    tool_results={},
                    original_query=request.message
                )
            
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
        # Look for the last product search query
        last_search_query = None
        for msg in reversed(session.messages[-10:]):  # Check last 10 messages
            if msg["role"] == "user":
                # Check if this was a product search (not Q&A or greeting)
                user_msg = msg["content"].lower()
                # Skip if it's a question about a specific product
                if any(word in user_msg for word in ['option', 'number', 'tell me about', 'what is', 'describe']):
                    continue
                # This is likely a search query
                last_search_query = msg["content"]
                break
        
        if not last_search_query:
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
        
        # Remove common prefixes from current message
        clean_message = message_lower
        for prefix in ['for ', 'in ', 'with ', 'show me ', 'find me ', 'get me ']:
            if clean_message.startswith(prefix):
                clean_message = clean_message[len(prefix):]
                break
        
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
        refined_query = f"{clean_message} {last_query_clean}"
        logger.info(f"[CONTEXT] Filter addition detected. Base: '{last_query_clean}', Addition: '{clean_message}', Combined: '{refined_query}'")
        
        return refined_query
    
    def _build_messages(self, session: SessionContext) -> List[Message]:
        """
        Build message list for LLM from session history.
        
        Args:
            session: Session context
        
        Returns:
            List of Message objects
        """
        messages = [
            Message(role="system", content=self.system_prompt)
        ]
        
        # Add few-shot examples to teach LLM the correct format
        # These examples show the LLM how to call tools properly AND handle context
        # CRITICAL: Show COMPLETE format with [/TOOLCALLS] closing tag
        few_shot_examples = [
            Message(role="user", content="show me office chairs"),
            Message(role="assistant", content='[TOOLCALLS] [{"name": "search_products", "arguments": {"query": "office chairs"}}] [/TOOLCALLS]'),
            Message(role="user", content="for kids"),
            Message(role="assistant", content='[TOOLCALLS] [{"name": "search_products", "arguments": {"query": "kids office chairs"}}] [/TOOLCALLS]'),
            Message(role="user", content="show me desks"),
            Message(role="assistant", content='[TOOLCALLS] [{"name": "search_products", "arguments": {"query": "desks"}}] [/TOOLCALLS]'),
            Message(role="user", content="in black"),
            Message(role="assistant", content='[TOOLCALLS] [{"name": "search_products", "arguments": {"query": "black desks"}}] [/TOOLCALLS]'),
        ]
        messages.extend(few_shot_examples)
        
        # Add conversation history (last 10 messages for context window)
        for msg in session.messages[-10:]:
            messages.append(Message(
                role=msg["role"],
                content=msg["content"]
            ))
        
        return messages
    
    def _validate_response(
        self, 
        response: str, 
        had_tool_calls: bool,
        tool_results: Dict[str, Any],
        original_query: str = ""
    ) -> str:
        """
        Validate response to prevent hallucinated product listings and attributes.
        
        Args:
            response: LLM response text
            had_tool_calls: Whether tools were called
            tool_results: Results from tool execution
            original_query: Original user query to check for attribute mentions
        
        Returns:
            Validated (possibly modified) response
        """
        import re
        
        # Check if response contains product listings
        listing_patterns = [
            r'\d+\.\s+[A-Z].*\$\d+',          # "1. Product Name - $99"
            r'Artiss\s+[A-Z][a-z]+',           # Brand name with product
            r'Here are (five|\d+) (chairs|desks|tables|products|items)',
            r'\$\d+\.\d+\)',                  # Prices in parentheses
            r'(Black|White|Blue|Red|Green)\s+\(\$',  # Color with price
        ]
        
        has_product_listing = any(re.search(p, response) for p in listing_patterns)
        
        if has_product_listing:
            if had_tool_calls and 'search_products' in tool_results:
                # LLM listed products after tool call - replace with short intro
                product_count = len(tool_results['search_products'].get('products', []))
                if product_count > 0:
                    logger.warning(f"[VALIDATION] Blocked product listing, replacing with short intro")
                    return f"I found {product_count} great options for you!"
                else:
                    return "I couldn't find any products matching that search."
            else:
                # LLM tried to hallucinate products without tool call
                logger.error(f"[VALIDATION] Blocked hallucinated product listing!")
                return "Let me search our catalog for you."
        
        # Block hallucinated attributes in response that weren't in user's query
        # Common attributes: colors, materials, sizes, age groups
        attribute_keywords = {
            'colors': ['black', 'white', 'brown', 'grey', 'gray', 'blue', 'red', 'green', 'yellow', 'pink', 'purple', 'orange', 'beige', 'navy', 'silver', 'gold'],
            'materials': ['wooden', 'wood', 'metal', 'plastic', 'fabric', 'leather', 'glass', 'steel'],
            'sizes': ['small', 'large', 'big', 'tiny', 'medium', 'compact'],
            'age_groups': ['kids', 'children', 'child', 'baby', 'adult', 'teen']
        }
        
        if had_tool_calls and original_query:
            query_lower = original_query.lower()
            response_lower = response.lower()
            
            # Check if response mentions attributes that weren't in the query
            for attr_type, keywords in attribute_keywords.items():
                for keyword in keywords:
                    # If attribute is in response but NOT in original query
                    if keyword in response_lower and keyword not in query_lower:
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
