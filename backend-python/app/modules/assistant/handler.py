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
    """
    
    # Pre-compiled off-topic patterns for efficiency
    OFF_TOPIC_PATTERNS = [
        re.compile(p, re.IGNORECASE) for p in [
            r'\b(python|javascript|java|code|programming|function|class|variable|algorithm|debug)\s+(code|snippet|program|script)',
            r'\b(write|create|make|generate)\s+(a|an|the)?\s*(code|program|script|function)',
            r'\bstar pattern\b|\bdiamond pattern\b|\bpyramid pattern\b',
            r'\bhow to (code|program|write code|make a program)',
            r'\bsolve\s+(the|this)?\s*(equation|problem|math)',
            r'\bcalculate\s+(?!shipping|price|cost|total)',
            r'\bwhat is\s+\d+\s*[\+\-\*\/]\s*\d+',
            r'\b(who is|what is|when did|where is|why did)\s+(?!the (price|cost|shipping|delivery|return policy))',
            r'\b(capital of|president of|population of|history of)\b',
            r'\b(write|tell|create)\s+(a|an|the)?\s*(story|poem|joke|song|essay)',
            r'\bwrite me (a|an)\b',
        ]
    ]
    
    # Common shopping keywords for quick validation
    SHOPPING_KEYWORDS = {
        'chair', 'table', 'desk', 'sofa', 'bed', 'furniture', 'product', 'item',
        'buy', 'purchase', 'order', 'cart', 'price', 'cost', 'shipping', 'delivery',
        'return', 'policy', 'warranty', 'available', 'stock', 'show', 'find', 'search',
        'compare', 'recommend', 'looking for', 'need', 'want', 'locker', 'cabinet',
        'storage', 'drawer', 'office', 'home', 'bedroom', 'living room', 'kitchen'
    }
    
    RESET_KEYWORDS = {'clear chat', 'reset chat', 'start over', 'clear history', 'clear session', 'reset session', 'clear all', 'restart chat'}
    
    ORDINAL_MAP = {
        'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fifth': 5,
        'sixth': 6, 'seventh': 7, 'eighth': 8, 'ninth': 9, 'tenth': 10,
        '1st': 1, '2nd': 2, '3rd': 3, '4th': 4, '5th': 5,
        '6th': 6, '7th': 7, '8th': 8, '9th': 9, '10th': 10
    }
    
    PRODUCT_REF_PATTERNS = [
        re.compile(r'\b(?:option|product|number|item|choice)\s+(\d+)', re.IGNORECASE),
        re.compile(r'(\d+)\s+(?:option|product|number|item|choice)', re.IGNORECASE),
        re.compile(r'^(\d+)\s*$', re.IGNORECASE)
    ]

    def __init__(
        self,
        llm_client: Optional[HuggingFaceLLMClient] = None,
        session_store: Optional[SessionStore] = None
    ):
        """
        Initialize assistant handler.
        
        Args:
            llm_client: Optional HF LLM client (creates new if not provided)
            session_store: Optional session store (uses global if not provided)
        """
        from .tools import get_assistant_tools
        self.llm_client = llm_client
        self.session_store = session_store or get_session_store()
        self.tools = get_assistant_tools()
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
            message_lower = request.message.lower()
            
            # Check if message matches any pre-compiled off-topic pattern
            is_off_topic = any(pattern.search(message_lower) for pattern in self.OFF_TOPIC_PATTERNS)
            
            # Additional check: if message contains none of the shopping keywords
            has_shopping_context = any(keyword in message_lower for keyword in self.SHOPPING_KEYWORDS)
            
            # CHECK FOR RESET/CLEAR COMMANDS
            is_reset = any(keyword in message_lower for keyword in self.RESET_KEYWORDS)
            
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
                
                # Check for joke specifically
                if re.search(r'\bjoke\b', message_lower):
                    assistant_message = "I'm here to help you find furniture and home products, but I don't really have a sense of humor for jokes! Is there any furniture I can help you search for today?"
                else:
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
            
            # SHORTCUT: Handle OUT_OF_SCOPE queries
            if intent_str == "out_of_scope":
                logger.info("[HANDLER] Out-of-scope intent detected, returning polite redirect")
                assistant_message = (
                    "I'm EasyMart's furniture shopping assistant, and I specialize in helping you find the perfect furniture! "
                    "I can help you search for chairs, tables, sofas, beds, storage solutions, and more. "
                    "I can also answer questions about shipping, returns, and our policies. "
                    "How can I assist you with your furniture needs today?"
                )
                
                # Add assistant response to history
                session.add_message("assistant", assistant_message)
                
                # Track out-of-scope query
                await self.event_tracker.track(
                    "assistant_out_of_scope",
                    session_id=request.session_id,
                    properties={
                        "query": request.message,
                        "query_length": len(request.message)
                    }
                )
                
                return AssistantResponse(
                    message=assistant_message,
                    session_id=session.session_id,
                    products=[],
                    cart_summary=self._build_cart_summary(session),
                    metadata={
                        "intent": intent_str,
                        "entities": {},
                        "function_calls_made": 0
                    }
                )
            
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
            
            # SHORTCUT: Handle PROMOTIONS intent
            if intent_str == "promotions":
                logger.info("[HANDLER] Promotions intent detected")
                assistant_message = (
                    "We currently have great deals across our furniture range! "
                    "You can find clearance items in our 'Sale' section, and we often have seasonal promotions. "
                    "Is there a specific type of furniture you're looking for a deal on?"
                )
                session.add_message("assistant", assistant_message)
                return AssistantResponse(
                    message=assistant_message,
                    session_id=session.session_id,
                    products=[],
                    cart_summary=self._build_cart_summary(session),
                    metadata={"intent": "promotions", "entities": entities}
                )
            
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
            
            # Overrides for furniture queries
            if any(keyword in request.message.lower() for keyword in furniture_keywords):
                if intent not in [IntentType.PRODUCT_SEARCH, IntentType.PRODUCT_SPEC_QA, IntentType.CART_ADD, IntentType.PRODUCT_AVAILABILITY]:
                    logger.info(f"[HANDLER] Overriding intent from {intent} to PRODUCT_SEARCH for furniture query")
                    intent = IntentType.PRODUCT_SEARCH
            
            # AMBIGUITY CHECK: Handle references like "option 1", "product 2"
            original_message = request.message
            message_lower = original_message.lower()
            
            # Extract potential product number reference
            product_num = None
            product_ref_match = re.search(r'\b(?:option|product|number|item|choice)\s+(\d+)', message_lower)
            if not product_ref_match:
                product_ref_match = re.search(r'(\d+)\s+(?:option|product|number|item|choice)', message_lower)
            
            if product_ref_match:
                product_num = int(product_ref_match.group(1))
            else:
                ordinal_map = {
                    'first': 1, 'second': 2, 'third': 3, 'fourth': 4, 'fifth': 5,
                    'sixth': 6, 'seventh': 7, 'eighth': 8, 'ninth': 9, 'tenth': 10,
                    '1st': 1, '2nd': 2, '3rd': 3, '4th': 4, '5th': 5
                }
                for ordinal, num in ordinal_map.items():
                    if f"{ordinal} " in message_lower or message_lower.endswith(ordinal):
                        product_num = num
                        break
            
            # If user referred to a product by number but we don't have enough products shown
            if product_num:
                if not session.last_shown_products:
                    logger.warning(f"[HANDLER] Ambiguous reference: option {product_num} but no products in session")
                    assistant_message = f"I'm not sure which product you're referring to as 'option {product_num}'. I haven't shown you any products in this session yet. What are you looking for?"
                    session.add_message("assistant", assistant_message)
                    return AssistantResponse(
                        message=assistant_message,
                        session_id=session.session_id,
                        products=[],
                        cart_summary=self._build_cart_summary(session),
                        metadata={"intent": "clarification_needed", "reason": "no_products_in_session"}
                    )
                elif product_num > len(session.last_shown_products):
                    logger.warning(f"[HANDLER] Ambiguous reference: option {product_num} but only {len(session.last_shown_products)} products shown")
                    assistant_message = f"I've only shown you {len(session.last_shown_products)} options so far. Which one of those (1-{len(session.last_shown_products)}) were you referring to, or would you like to see more?"
                    session.add_message("assistant", assistant_message)
                    return AssistantResponse(
                        message=assistant_message,
                        session_id=session.session_id,
                        products=session.last_shown_products,
                        cart_summary=self._build_cart_summary(session),
                        metadata={"intent": "clarification_needed", "reason": "index_out_of_range", "max_index": len(session.last_shown_products)}
                    )

            # Detect if this is a refinement query and inject context
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
                # Lazy initialization
                from .hf_llm_client import create_llm_client
                self.llm_client = await create_llm_client()
                logger.info(f"[HANDLER] LLM client created")
            
            # Call LLM with function calling
            logger.info(f"[HANDLER] Calling LLM with query: '{request.message}'")
            llm_response = await self.llm_client.chat(
                messages=messages,
                tools=TOOL_DEFINITIONS,
                temperature=0.5,  # Increased to 0.5 for better tool calling
                max_tokens=200    # Reduced - we just need tool call or short response
            )
            logger.info(f"[HANDLER] LLM response received, function_calls: {len(llm_response.function_calls) if llm_response.function_calls else 0}")
            
            # Store tool call in session history for context retention
            if llm_response.function_calls:
                tool_call_msg = f"[TOOLCALLS] {json.dumps([{'name': f.name, 'arguments': f.arguments} for f in llm_response.function_calls])} [/TOOLCALLS]"
                session.add_message("assistant", tool_call_msg)
            
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
                # Check if it's a contextual question about already-displayed products
                query_lower = request.message.lower()
                
                # Expanded contextual detection
                contextual_words = ['this', 'that', 'it', 'these', 'those', 'them', 'they', 'the one', 'option']
                question_patterns = ['how', 'why', 'are they', 'is this', 'is that', 'does it', 'do they', 'can it', 'will it']
                
                is_contextual = any(word in query_lower for word in contextual_words)
                is_question_about_existing = any(pattern in query_lower for pattern in question_patterns)
                has_products_in_session = session.last_shown_products and len(session.last_shown_products) > 0
                
                # Check if it's an out-of-scope query
                is_out_of_scope = any(keyword in query_lower for keyword in out_of_scope_keywords)
                
                # Allow LLM response if: contextual, question about existing products, or out of scope
                if is_out_of_scope or (is_contextual and has_products_in_session) or (is_question_about_existing and has_products_in_session):
                    # Let LLM's response stand (out-of-scope or contextual follow-up)
                    logger.info(f"[HANDLER] Contextual/question about existing products detected: '{request.message}', skipping safety catch")
                else:
                    # Furniture-related but LLM didn't call tool - force it
                    logger.warning(f"[HANDLER] ⚠️ SAFETY CATCH: Product search intent but LLM didn't call tool!")
                    logger.warning(f"[HANDLER] Forcing search_products call to prevent hallucination")
                    logger.warning(f"[HANDLER] Using query: '{refined_message}'")
                    
                    # Create forced tool call using the refined message (after context applied)
                    from .hf_llm_client import FunctionCall
                    llm_response.function_calls = [
                        FunctionCall(
                            name="search_products",
                            arguments={"query": refined_message}
                        )
                    ]
                    # Clear the hallucinated content
                    llm_response.content = ""
            
            # SAFETY CHECK: If product spec Q&A intent but NO tool calls → force get_product_specs!
            if intent == IntentType.PRODUCT_SPEC_QA and not llm_response.function_calls:
                # Extract product reference from query using patterns
                product_num = None
                for pattern in self.PRODUCT_REF_PATTERNS:
                    match = pattern.search(request.message)
                    if match:
                        product_num = int(match.group(1))
                        break
                
                if not product_num:
                    # Try ordinal numbers
                    for ordinal, num in self.ORDINAL_MAP.items():
                        if ordinal in request.message.lower():
                            product_num = num
                            break
                
                if product_num:
                    # Get product from session (1-indexed in user query, 0-indexed in list)
                    if session.last_shown_products and 0 < product_num <= len(session.last_shown_products):
                        product = session.last_shown_products[product_num - 1]
                        product_id = product.get('id')
                        
                        if product_id:
                            logger.warning(f"[HANDLER] ⚠️ SAFETY CATCH: Product Q&A but LLM didn't call tool!")
                            from .hf_llm_client import FunctionCall
                            llm_response.function_calls = [
                                FunctionCall(
                                    name="get_product_specs",
                                    arguments={"product_id": product_id}
                                )
                            ]
                            llm_response.content = ""
            
            # SAFETY CHECK: Removed aggressive forced cart operations to prevent "self-adding" issues.
            # The LLM should be trusted to call tools when explicitly requested by the user.

            # Process function calls if any
            if llm_response.function_calls:
                logger.info(f"[HANDLER] Processing {len(llm_response.function_calls)} function calls")
                
                # VALIDATION: Fix product IDs for spec/availability/comparison/cart tools
                for func_call in llm_response.function_calls:
                    if func_call.name in ['get_product_specs', 'check_availability', 'update_cart']:
                        product_id = func_call.arguments.get('product_id', '')
                        
                        # Try to extract number from user's message
                        product_num = None
                        for pattern in self.PRODUCT_REF_PATTERNS:
                            match = pattern.search(original_message)
                            if match:
                                product_num = int(match.group(1))
                                break
                        
                        if product_num is None:
                            for ordinal, num in self.ORDINAL_MAP.items():
                                if f"{ordinal} " in original_message.lower() or original_message.lower().endswith(ordinal):
                                    product_num = num
                                    break
                        
                        # Fix reference to "it", "this one" if only 1 product shown
                        if product_num is None and session.last_shown_products and len(session.last_shown_products) == 1:
                            context_refs = ['this one', 'add it', 'add this', 'the product', 'that one']
                            if any(ref in original_message.lower() for ref in context_refs):
                                product_num = 1
                        
                        # Correct product_id if we have a valid number
                        if session.last_shown_products and product_num and 0 < product_num <= len(session.last_shown_products):
                            correct_product = session.last_shown_products[product_num - 1]
                            correct_product_id = correct_product.get('id')
                            if correct_product_id:
                                func_call.arguments['product_id'] = correct_product_id
                            else:
                                logger.error(f"[ERROR] Product #{product_num} has no ID in session!")
                        elif not session.last_shown_products:
                            logger.error(f"[ERROR] No products in session - cannot correct ID")
                        elif not product_num:
                            logger.error(f"[ERROR] Could not extract product number - cannot correct ID")
                    
                    elif func_call.name == 'compare_products':
                        # Fix product_ids array for comparison and track position labels
                        product_ids = func_call.arguments.get('product_ids', [])
                        
                        # Try to extract numbers from message (compare 1 and 2, etc.)
                        numbers = re.findall(r'\b(?:option|product|item)?\s*(\d+)', original_message.lower())
                        
                        if numbers and session.last_shown_products:
                            corrected_ids = []
                            position_labels = []  # Track which option number maps to which product
                            for num_str in numbers:
                                product_num = int(num_str)
                                if 0 < product_num <= len(session.last_shown_products):
                                    correct_product = session.last_shown_products[product_num - 1]
                                    correct_id = correct_product.get('id')
                                    if correct_id:
                                        corrected_ids.append(correct_id)
                                        position_labels.append(f"Option {product_num}")
                            
                            if corrected_ids:
                                logger.warning(f"[HANDLER] ⚠️ CORRECTING COMPARISON IDs: {product_ids} → {corrected_ids}")
                                func_call.arguments['product_ids'] = corrected_ids
                                # Store position labels for later formatting
                                func_call.arguments['_position_labels'] = position_labels
                
                # Execute tools and get results
                tool_results = await self._execute_function_calls(
                    llm_response.function_calls,
                    session
                )
                
                logger.info(f"[HANDLER] Tool results: {list(tool_results.keys())}")
                
                # Add tool results to conversation with human-readable formatting
                # Note: HuggingFace doesn't support role="tool", so we use role="user"
                tool_results_content = []
                for tool_name, result in tool_results.items():
                    # Format result based on tool type for better LLM comprehension
                    if tool_name == 'get_product_specs':
                        # Format specs in readable way
                        product_name = result.get('product_name', 'Unknown')
                        price = result.get('price')
                        description = result.get('description', '')
                        specs = result.get('specs', {})
                        error = result.get('error')
                        message = result.get('message', '')
                        
                        if error:
                            # DON'T pass error to LLM - it causes hallucinations
                            # Instead, provide a safe message
                            logger.error(f"[TOOL ERROR] get_product_specs failed: {error}")
                            result_str = f"Product: {product_name}\nStatus: Information not available\nNote: This product's details could not be retrieved from the database."
                        elif specs:
                            # Format specs clearly with product name and structured info
                            spec_lines = [f"=== PRODUCT INFORMATION ==="]
                            spec_lines.append(f"Product Name: {product_name}")
                            if price:
                                spec_lines.append(f"Price: ${price}")
                            spec_lines.append("")
                            
                            # Add each spec section
                            for section, content in specs.items():
                                if content and str(content).strip():
                                    # Clean up content (remove "nan" values)
                                    content_str = str(content)
                                    if 'nan' not in content_str.lower():
                                        spec_lines.append(f"{section}: {content}")
                            
                            result_str = "\n".join(spec_lines)
                        else:
                            # No specs - show basic product info
                            result_str = f"Product: {product_name}\n"
                            if price:
                                result_str += f"Price: ${price}\n"
                            if description:
                                result_str += f"Description: {description[:200]}{'...' if len(description) > 200 else ''}\n"
                            result_str += message if message else "No detailed specifications available in database."
                    
                    elif tool_name == 'search_products':
                        # Include product details in result summary so LLM remembers them
                        products = result.get('products', [])
                        if products:
                            product_list = []
                            for idx, p in enumerate(products):
                                p_name = p.get('name') or p.get('title') or "Unknown Product"
                                p_price = p.get('price', 0)
                                p_id = p.get('id')
                                product_list.append(f"{idx+1}. {p_name} (${p_price}) [ID: {p_id}]")
                            
                            result_str = f"Found {len(products)} products:\n" + "\n".join(product_list)
                        else:
                            result_str = "Found 0 products matching the search."
                    
                    elif tool_name == 'compare_products':
                        # Format comparison with position labels to preserve context
                        products = result.get('products', [])
                        position_labels = result.get('position_labels', [])
                        
                        if products:
                            comparison_lines = ["=== PRODUCT COMPARISON ==="]
                            for idx, product in enumerate(products):
                                # Add position label if available
                                if idx < len(position_labels):
                                    comparison_lines.append(f"\n{position_labels[idx]}:")
                                else:
                                    comparison_lines.append(f"\nProduct {idx + 1}:")
                                
                                comparison_lines.append(f"  Name: {product.get('name', 'Unknown')}")
                                comparison_lines.append(f"  Price: ${product.get('price', 0):.2f}")
                                
                                # Add key specs if available
                                specs = product.get('specs', {})
                                for section, content in list(specs.items())[:3]:  # Limit to first 3 specs
                                    if content and 'nan' not in str(content).lower():
                                        comparison_lines.append(f"  {section}: {content}")
                            
                            # Add comparison summary if available
                            comparison = result.get('comparison', {})
                            if comparison.get('price_range'):
                                comparison_lines.append(f"\nPrice Range: {comparison['price_range']}")
                            
                            result_str = "\n".join(comparison_lines)
                        else:
                            result_str = json.dumps(result)
                    
                    else:
                        # Other tools - use JSON
                        result_str = json.dumps(result)
                    
                    tool_results_content.append(f"[Tool result from {tool_name}]:\n{result_str}")
                
                # Combine all tool results into one message
                combined_tool_results = "\n\n".join(tool_results_content)
                
                # Determine post-tool instruction based on which tool was called
                tool_names = list(tool_results.keys())
                
                if 'search_products' in tool_names:
                    post_tool_instruction = (
                        "Now respond to the user with ONLY a brief, professional 1-2 sentence intro. "
                        "DO NOT list products - they will be displayed below your message as cards. "
                        "DO NOT mention 'UI', 'screen', 'list', or 'display'. "
                        "Examples: 'I found 5 office chairs for you, displayed above.', 'I\\'ve found several red desks that might work perfectly.'"
                    )
                elif 'get_product_specs' in tool_names:
                    spec_result = tool_results.get('get_product_specs', {})
                    has_error = 'error' in spec_result or 'Information not available' in str(spec_result)
                    
                    if has_error:
                        post_tool_instruction = (
                            "CRITICAL: Tool error. Say exactly: 'I'm unable to retrieve detailed information for this product at the moment. Please try another option, or contact support.'"
                        )
                    else:
                        post_tool_instruction = (
                            "Respond naturally using ONLY the provided product data. Start with the product name. Be concise (2-3 sentences)."
                        )
                elif 'calculate_shipping' in tool_names:
                    post_tool_instruction = (
                        "Relay the shipping information naturally. Note: 'express_available' is a data field, not a tool. Just say if express is available and the cost."
                    )
                else:
                    post_tool_instruction = "Respond briefly and professionally based on the tool results."

                # Add combined message with results AND instruction to help LLM stay on track
                tool_results_msg = f"[TOOL_RESULTS] {combined_tool_results} [/TOOL_RESULTS]"
                session.add_message("user", tool_results_msg)
                
                messages.append(Message(
                    role="user",
                    content=f"{tool_results_msg}\n\nINTERNAL INSTRUCTION: {post_tool_instruction}"
                ))

                
                # Determine temperature based on tool type
                # Lower temp for factual responses (specs, availability, comparison)
                # Higher temp for conversational responses (search results, policies)
                if any(tool in tool_names for tool in ['get_product_specs', 'check_availability', 'compare_products']):
                    response_temperature = 0.3  # Factual, don't hallucinate
                    max_response_tokens = 300  # Increased to allow complete comparisons and specs
                else:
                    response_temperature = 0.7  # Conversational, friendly
                    max_response_tokens = 250  # Increased for fuller responses
                
                # Call LLM again to generate final response with tool results
                final_response = await self.llm_client.chat(
                    messages=messages,
                    temperature=response_temperature,
                    max_tokens=max_response_tokens
                )
                
                # Let LLM generate natural, conversational response
                # Products are already stored in session from tool execution
                assistant_message = final_response.content
                
                # Strip any leaked markers or internal prefixes (MORE AGGRESSIVE)
                assistant_message = re.sub(r'\[/?TOOL[_\s]?RESULTS?\]', '', assistant_message, flags=re.IGNORECASE)
                assistant_message = re.sub(r'\[Tool result from .*?\]', '', assistant_message, flags=re.IGNORECASE)
                assistant_message = re.sub(r'Found \d+ products? matching the search\.', '', assistant_message, flags=re.IGNORECASE)
                assistant_message = re.sub(r'INTERNAL INSTRUCTION:.*', '', assistant_message, flags=re.IGNORECASE | re.DOTALL)
                
                # Strip common LLM prefixes
                assistant_message = re.sub(r'^(Assistant|User|System|Bot):\s*', '', assistant_message, flags=re.IGNORECASE)
                assistant_message = re.sub(r'\n(Assistant|User|System|Bot):\s*', '\n', assistant_message, flags=re.IGNORECASE)
                
                # Strip any repeated prompts
                assistant_message = re.sub(r'Now respond to the user.*', '', assistant_message, flags=re.IGNORECASE | re.DOTALL)
                
                # Strip tool result debugging text
                assistant_message = re.sub(r'\{"name".*?"price".*?\}', '', assistant_message)
                
                assistant_message = assistant_message.strip()

                
                # ADDITIONAL VALIDATION: Block hallucinations after tool errors
                if 'get_product_specs' in tool_results:
                    spec_result = tool_results['get_product_specs']
                    if 'error' in spec_result:
                        # Tool failed - check if LLM hallucinated anyway
                        has_price = re.search(r'\$\d+', assistant_message)
                        has_dimensions = re.search(r'\d+\s*[x×]\s*\d+|\d+\s*(cm|mm|kg|inches)', assistant_message)
                        has_materials = any(word in assistant_message.lower() for word in ['wood', 'metal', 'leather', 'fabric', 'plastic'])
                        
                        if has_price or has_dimensions or has_materials:
                            logger.warning(f"[BLOCKED] LLM hallucinated specs despite tool error!")
                            print(f"[DEBUG] ✗ Blocked hallucination: {assistant_message[:100]}...")
                            assistant_message = "I'm unable to retrieve detailed information for this product at the moment. Please try another option from the list, or contact our support team for assistance."
                
                # Additional validation: Check if search results actually match the query
                if 'search_products' in tool_results:
                    products = tool_results['search_products'].get('products', [])\
                    
                    # Check if query had price constraint and no results
                    if len(products) == 0:
                        query_lower = request.message.lower()
                        price_patterns = [
                            r'under\s+\$?(\d+)',
                            r'less\s+than\s+\$?(\d+)',
                            r'below\s+\$?(\d+)',
                            r'cheaper\s+than\s+\$?(\d+)',
                        ]
                        
                        for pattern in price_patterns:
                            match = re.search(pattern, query_lower)
                            if match:
                                price_value = int(match.group(1))
                                # Suggest a higher price range
                                suggested_price = price_value * 2  # Double the price
                                
                                # Extract product type
                                product_types = ['chair', 'table', 'desk', 'sofa', 'bed', 'locker', 'cabinet']
                                product_type = "items"
                                for ptype in product_types:
                                    if ptype in query_lower:
                                        product_type = ptype + "s" if not ptype.endswith('s') else ptype
                                        break
                                
                                assistant_message = (
                                    f"I couldn't find any {product_type} under ${price_value}. "
                                    f"Would you like to see {product_type} under ${suggested_price} instead?"
                                )
                                logger.info(f"[VALIDATION] No results for price constraint ${price_value}, suggesting ${suggested_price}")
                                break
                    
                    elif products:
                        # Extract important nouns from query
                        query_lower = request.message.lower()
                        important_nouns = {'chair', 'chairs', 'table', 'tables', 'desk', 'desks', 'sofa', 'sofas',
                                          'bed', 'beds', 'locker', 'lockers', 'cabinet', 'cabinets', 'shelf', 'shelves',
                                          'storage', 'stool', 'stools', 'bench', 'benches', 'wardrobe', 'wardrobes'}
                        
                        query_nouns = set(query_lower.split()) & important_nouns
                        
                        if query_nouns:
                            # Normalize nouns to singular for more robust matching
                            normalized_query_nouns = {n.rstrip('s') for n in query_nouns}
                            
                            # Check if ANY product name contains the query nouns (singular or plural)
                            matching_products = []
                            for product in products:
                                product_name = product.get('name', '').lower()
                                if any(noun in product_name for noun in normalized_query_nouns):
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
                    original_query=original_message,
                    search_query=""
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
        
        Args:
            session: Session context
        
        Returns:
            List of Message objects
        """
        messages = [
            Message(role="system", content=self.system_prompt)
        ]
        
        # Add few-shot examples to teach LLM the correct format
        # These examples show BOTH tool calling AND post-tool responses
        # CRITICAL: Show COMPLETE format with [/TOOLCALLS] closing tag
        few_shot_examples = [
            # Example 1: Basic product search
            Message(role="user", content="show me office chairs"),
            Message(role="assistant", content='[TOOLCALLS] [{"name": "search_products", "arguments": {"query": "office chairs"}}] [/TOOLCALLS]'),
            Message(role="user", content="[TOOL_RESULTS] Found 5 office chairs: Executive Chair ($299), Ergonomic Chair ($349), Mesh Chair ($199), Leather Chair ($499), Adjustable Chair ($279) [/TOOL_RESULTS]"),
            Message(role="assistant", content="I found 5 office chairs for you, displayed above. Would you like details on any of them?"),
            
            # Example 2: Context refinement (adding attribute)
            Message(role="user", content="for kids"),
            Message(role="assistant", content='[TOOLCALLS] [{"name": "search_products", "arguments": {"query": "kids office chairs"}}] [/TOOLCALLS]'),
            Message(role="user", content="[TOOL_RESULTS] Found 2 office chairs: Kids Study Chair ($149), Junior Desk Chair ($129) [/TOOL_RESULTS]"),
            Message(role="assistant", content="I found 2 office chairs suitable for kids, shown above. Let me know if you'd like specifications for any of them."),
            
            # Example 3: Product specification query
            Message(role="user", content="tell me about option 1"),
            Message(role="assistant", content='[TOOLCALLS] [{"name": "get_product_specs", "arguments": {"product_id": "CHR-001"}}] [/TOOLCALLS]'),
            Message(role="user", content="[TOOL_RESULTS] Kids Study Chair: Dimensions 45x45x80cm, weight capacity 50kg, fabric upholstery, adjustable height, easy assembly [/TOOL_RESULTS]"),
            Message(role="assistant", content="The Kids Study Chair has dimensions of 45×45×80cm with a 50kg weight capacity. It features fabric upholstery and adjustable height, and is easy to assemble."),
            
            # Example 4: No results found
            Message(role="user", content="show me pink unicorn desks"),
            Message(role="assistant", content='[TOOLCALLS] [{"name": "search_products", "arguments": {"query": "pink unicorn desks"}}] [/TOOLCALLS]'),
            Message(role="user", content="[TOOL_RESULTS] Found 0 products matching query [/TOOL_RESULTS]"),
            Message(role="assistant", content="I couldn't find any products matching 'pink unicorn desks'. Would you like to try a different search?"),
            
            # Example 5: Filter replacement (color change)
            Message(role="user", content="show me desks in black"),
            Message(role="assistant", content='[TOOLCALLS] [{"name": "search_products", "arguments": {"query": "desks in black"}}] [/TOOLCALLS]'),
            Message(role="user", content="[TOOL_RESULTS] Found 3 desks [/TOOL_RESULTS]"),
            Message(role="assistant", content="I found 3 black desks for you, displayed above."),
            Message(role="user", content="in white"),
            Message(role="assistant", content='[TOOLCALLS] [{"name": "search_products", "arguments": {"query": "desks in white"}}] [/TOOLCALLS]'),
            
            # Example 6: Cart operation
            Message(role="user", content="add option 2 to cart"),
            Message(role="assistant", content='[TOOLCALLS] [{"name": "update_cart", "arguments": {"action": "add", "product_id": "DSK-002", "quantity": 1}}] [/TOOLCALLS]'),
            Message(role="user", content="[TOOL_RESULTS] Added Modern Desk to cart [/TOOL_RESULTS]"),
            Message(role="assistant", content="I've added the Modern Desk to your cart. Would you like to continue shopping or view your cart?"),
            
            # Example 7: Policy question (no tool needed)
            Message(role="user", content="what's your return policy?"),
            Message(role="assistant", content='[TOOLCALLS] [{"name": "get_policy_info", "arguments": {"policy_type": "returns"}}] [/TOOLCALLS]'),
            Message(role="user", content="[TOOL_RESULTS] 30 day return period, items must be unused and in original packaging [/TOOL_RESULTS]"),
            Message(role="assistant", content="We offer a 30-day return period. Items must be unused and in their original packaging to qualify for a return."),
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
            
            # Inject session_id for tools that need it
            if tool_name == "update_cart":
                arguments["session_id"] = session.session_id
            
            logger.info(f"Executing tool: {tool_name} with args: {arguments}")
            
            result = await execute_tool(tool_name, arguments, self.tools)
            
            # FIX: Format products with actual names before sending to LLM
            if tool_name == "search_products" and "products" in result:
                for product in result["products"]:
                    # Ensure name is set from title, not product_X
                    if not product.get("name") or product.get("name").startswith("product_"):
                        product["name"] = product.get("title", product.get("description", "Product"))
                
                # Store in session for reference
                session.update_shown_products(result["products"])
            
            # NEW: Also update shown products when getting specs for a single product
            # This allows "add it to cart" to work after asking about a specific product
            if tool_name == "get_product_specs" and "product_id" in result:
                # Create a mini product object for the session context
                product_id = result.get("product_id")
                product_name = result.get("product_name")
                
                if product_id:
                    session.update_shown_products([{
                        "id": product_id,
                        "product_id": product_id,
                        "name": product_name,
                        "title": product_name,
                        "price": result.get("price", 0)
                    }])
            
            # Track cart actions (FIX: Moved OUTSIDE search_products block)
            if tool_name == "update_cart" and result.get("success"):
                # Store cart action in session for later retrieval
                action_type = result.get("action")
                if action_type in ["add", "set"]:
                    session.metadata["last_cart_action"] = {
                        "type": "add_to_cart",
                        "product_id": result.get("product_id"),
                        "product_name": result.get("product_name"),
                        "quantity": result.get("quantity", 1)
                    }
                elif action_type == "remove":
                    session.metadata["last_cart_action"] = {
                        "type": "remove_from_cart",
                        "product_id": result.get("product_id")
                    }
                elif action_type == "view":
                    session.metadata["last_cart_action"] = {
                        "type": "view_cart"
                    }
                elif action_type == "clear":
                    session.metadata["last_cart_action"] = {
                        "type": "clear_cart"
                    }

            
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
