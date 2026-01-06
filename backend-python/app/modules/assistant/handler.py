"""
Easymart Assistant Handler

Main orchestrator for the conversational AI assistant.
Coordinates LLM, tools, intent detection, and session management.
"""

import json
import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from datetime import datetime, timedelta

# Import components
from .hf_llm_client import HuggingFaceLLMClient, Message, LLMResponse
from .tools import EasymartAssistantTools, TOOL_DEFINITIONS, execute_tool
from .intent_detector import IntentDetector
from .intents import IntentType
from .session_store import SessionStore, SessionContext, get_session_store
from .filter_validator import FilterValidator
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
        from .context_analyzer import get_context_analyzer
        self.llm_client = llm_client
        self.session_store = session_store or get_session_store()
        self.tools = get_assistant_tools()
        self.intent_detector = IntentDetector()
        self.filter_validator = FilterValidator()
        self.event_tracker = EventTracker()
        self.context_analyzer = get_context_analyzer()
        
        # System prompt
        self.system_prompt = get_system_prompt()
        
        logger.info("Easymart Assistant Handler initialized with context analyzer and filter validator")
    
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
            
            # Analyze context for better topic understanding
            logger.info(f"[HANDLER] Analyzing conversation context...")
            conversation_history = [{"role": msg["role"], "content": msg["content"]} for msg in session.messages[-10:]]
            topic_context = self.context_analyzer.analyze(request.message, conversation_history)
            logger.info(f"[HANDLER] Context analyzed - Topic: {topic_context.topic.value}, Intent: {topic_context.intent.value}, Confidence: {topic_context.confidence:.2f}")
            
            # Store topic context in session metadata for tracking
            if "topic_history" not in session.metadata:
                session.metadata["topic_history"] = []
            if "user_preferences" not in session.metadata:
                session.metadata["user_preferences"] = {}
            
            # Track topic changes
            current_topic = topic_context.topic.value
            if not session.metadata["topic_history"] or session.metadata["topic_history"][-1] != current_topic:
                session.metadata["topic_history"].append(current_topic)
                logger.info(f"[HANDLER] Topic changed to: {current_topic}")
            
            # Update user preferences
            if topic_context.extracted_preferences:
                session.metadata["user_preferences"].update(topic_context.extracted_preferences)
                logger.info(f"[HANDLER] Updated preferences: {topic_context.extracted_preferences}")
            
            # Add user message to history
            logger.info(f"[HANDLER] Adding user message to history...")
            session.add_message("user", request.message)
            
            # CRITICAL: Apply context refinement IMMEDIATELY after adding message
            # This must happen BEFORE vague query detection so single-word refinements
            # like "wooden" get merged with previous search context ("desks" → "wooden desks")
            # BUT: Don't apply to attribute questions about current products
            original_message = request.message
            
            # Check if this is an attribute question about current product
            has_product_context = (
                session.current_product is not None or 
                (session.last_shown_products and len(session.last_shown_products) > 0)
            )
            
            attribute_question_patterns = [
                r'\b(is this|does this|does it|is it)\b.*\b(come|available|have)\b',
                r'\b(what|which)\s+(colors?|colours?|materials?|sizes?)\b',
                r'\b(available in|comes in)\b',
            ]
            
            is_attribute_question = has_product_context and any(
                re.search(pattern, original_message.lower()) 
                for pattern in attribute_question_patterns
            )
            
            # Only apply context refinement if NOT an attribute question
            if not is_attribute_question:
                refined_message = self._apply_context_refinement(request.message, session)
                if refined_message != original_message:
                    logger.info(f"[HANDLER] ✅ Applied context refinement: '{original_message}' → '{refined_message}'")
                    # Update the request message for all subsequent processing
                    request.message = refined_message
            else:
                logger.info(f"[HANDLER] Skipping context refinement - attribute question about current product")
            
            # VALIDATION: Check if query is off-topic (not related to e-commerce/shopping)
            message_lower = request.message.lower()
            
            # Check if message matches any pre-compiled off-topic pattern
            is_off_topic = any(pattern.search(message_lower) for pattern in self.OFF_TOPIC_PATTERNS)
            
            # Additional check: if message contains none of the shopping keywords
            has_shopping_context = any(keyword in message_lower for keyword in self.SHOPPING_KEYWORDS)
            
            # CRITICAL: Skip off-topic check if message is a context refinement
            # Single-word attributes like "grey", "wooden", "small" should NOT be flagged as off-topic
            is_likely_refinement = False
            if len(original_message.split()) <= 3:  # Short messages
                refinement_indicators = [
                    # Colors
                    r'\b(red|blue|green|yellow|black|white|brown|grey|gray|orange|purple|pink|beige|cream)\b',
                    # Materials
                    r'\b(wooden|wood|metal|leather|fabric|plastic|glass|steel)\b',
                    # Sizes
                    r'\b(small|large|big|compact|mini|huge|medium)\b',
                    # Styles  
                    r'\b(modern|classic|vintage|contemporary|rustic|industrial)\b',
                    # Contexts
                    r'\b(for|in|with)\s+\w+',
                ]
                is_likely_refinement = any(re.search(pattern, message_lower) for pattern in refinement_indicators)
                if is_likely_refinement:
                    logger.info(f"[HANDLER] Detected likely refinement in '{original_message}' - skipping off-topic check")
            
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
                        "function_calls_made": 0,
                        "context": topic_context.to_dict(),
                        "user_preferences": session.metadata.get("user_preferences", {}),
                        "topic_history": session.metadata.get("topic_history", [])
                    }
                )
            
            if is_off_topic and not has_shopping_context and not is_likely_refinement:
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
                        "function_calls_made": 0,
                        "context": topic_context.to_dict(),
                        "user_preferences": session.metadata.get("user_preferences", {}),
                        "topic_history": session.metadata.get("topic_history", [])
                    }
                )
            
            # VAGUE QUERY DETECTION (EARLY) - Check BEFORE calling LLM to save API calls
            # Step 1: Check if we have pending clarification from previous turn
            pending = session.get_pending_clarification()
            
            if pending:
                logger.info(f"[HANDLER] Found pending clarification: {pending['vague_type']}")
                logger.info(f"[HANDLER] Pending entities: {pending.get('partial_entities', {})}")
                logger.info(f"[HANDLER] Current message: '{request.message}'")
                
                # Check if clarification expired (>3 minutes)
                clarification_age = datetime.now() - pending["timestamp"]
                if clarification_age > timedelta(minutes=3):
                    logger.info("[HANDLER] Clarification expired (>3 min), clearing pending state")
                    session.clear_pending_clarification()
                    pending = None
                # Check if user changed topic (different intent)
                else:
                    current_intent = self.intent_detector.detect(request.message).value
                    logger.info(f"[HANDLER] Current message intent: {current_intent}")
                    
                    # Short messages (< 4 words) are likely clarification answers, not topic changes
                    word_count = len(request.message.split())
                    is_short_response = word_count <= 4
                    
                    # Allow these intents to continue clarification flow
                    allowed_intents = ["product_search", "general_help", "out_of_scope", "vague_query", "clarification_needed"]
                    
                    if not is_short_response and current_intent not in allowed_intents:
                        logger.info(f"[HANDLER] User changed topic to {current_intent}, clearing pending clarification")
                        session.clear_pending_clarification()
                        pending = None
                    else:
                        if is_short_response:
                            logger.info(f"[HANDLER] Short response ({word_count} words), treating as clarification answer")
                        logger.info(f"[HANDLER] Intent is {current_intent}, continuing with clarification merge")
                        # Check for bypass phrases
                        bypass_phrases = [
                            "just show me anything", "show me anything", "surprise me",
                            "whatever you recommend", "any is fine", "anything is fine",
                            "you choose", "no preference", "doesn't matter"
                        ]
                        is_bypass = any(phrase in request.message.lower() for phrase in bypass_phrases)
                        
                        if is_bypass:
                            logger.info("[HANDLER] Bypass phrase detected, showing popular items")
                            session.clear_pending_clarification()
                            partial = pending["partial_entities"]
                            if partial.get("category"):
                                request.message = f"popular {partial['category']}s"
                            elif partial.get("room_type"):
                                request.message = f"popular furniture for {partial['room_type']}"
                            else:
                                request.message = "popular furniture"
                        else:
                            # Merge clarification response with original entities
                            logger.info(f"[HANDLER] Merging clarification response: '{request.message}'")
                            logger.info(f"[HANDLER] Original entities: {pending['partial_entities']}")
                            
                            # Check for bypass phrases using filter validator
                            if self.filter_validator.is_bypass_phrase(request.message):
                                logger.info("[HANDLER] Bypass phrase detected via filter validator")
                                session.clear_pending_clarification()
                                partial = pending["partial_entities"]
                                if partial.get("category"):
                                    request.message = f"popular {partial['category']}s"
                                elif partial.get("room_type"):
                                    request.message = f"popular furniture for {partial['room_type']}"
                                else:
                                    request.message = "popular furniture"
                                    
                                # Track bypass event
                                self.event_tracker.track_event(
                                    "clarification_bypass",
                                    session_id=session.session_id,
                                    metadata={
                                        "bypass_phrase": request.message.lower(),
                                        "vague_type": pending["vague_type"],
                                        "filter_count": len(partial)
                                    }
                                )
                            else:
                                # Merge clarification response
                                merged_entities = self.intent_detector.merge_clarification_response(
                                    pending["partial_entities"],
                                    request.message,
                                    pending["vague_type"]
                                )
                                logger.info(f"[HANDLER] ✅ Successfully merged entities: {merged_entities}")
                                
                                # Validate filter count using FilterValidator
                                is_valid, weight, validation_msg = self.filter_validator.validate_filter_count(
                                    merged_entities,
                                    request.message
                                )
                                logger.info(f"[HANDLER] Filter validation: valid={is_valid}, weight={weight:.1f}")
                                
                                # Check for contradictions
                                contradiction = self.filter_validator.detect_contradictions(
                                    merged_entities,
                                    request.message
                                )
                                
                                if contradiction:
                                    term1, term2, contradiction_msg = contradiction
                                    logger.info(f"[HANDLER] Contradiction detected: {term1} vs {term2}")
                                    session.add_message("assistant", contradiction_msg)
                                    
                                    return AssistantResponse(
                                        message=contradiction_msg,
                                        session_id=session.session_id,
                                        products=[],
                                        cart_summary=self._build_cart_summary(session),
                                        metadata={
                                            "intent": "contradiction_detected",
                                            "contradiction": {"term1": term1, "term2": term2},
                                            "context": topic_context.to_dict()
                                        }
                                    )
                                
                                clarification_count = pending["clarification_count"]
                                
                                # Proceed with search only if filter validation passes
                                if is_valid or clarification_count >= 2:
                                    if clarification_count >= 2:
                                        logger.info("[HANDLER] Max clarifications reached (2), proceeding anyway")
                                    else:
                                        logger.info("[HANDLER] Sufficient filters collected, proceeding with search")
                                    
                                    session.clear_pending_clarification()
                                    if merged_entities.get("query"):
                                        request.message = merged_entities["query"]
                                else:
                                    # Need more clarification
                                    logger.info(f"[HANDLER] Insufficient filters (weight={weight:.1f}), asking for more")
                                    session.increment_clarification_count()
                                    
                                    from .prompts import generate_clarification_prompt
                                    assistant_message = f"{validation_msg}\n\n"
                                    assistant_message += generate_clarification_prompt(
                                        pending["vague_type"],
                                        merged_entities,
                                        clarification_count=clarification_count + 1
                                    )
                                    
                                    pending["partial_entities"] = merged_entities
                                    session.add_message("assistant", assistant_message)
                                    
                                    return AssistantResponse(
                                        message=assistant_message,
                                        session_id=session.session_id,
                                        products=[],
                                        cart_summary=self._build_cart_summary(session),
                                        metadata={
                                            "intent": "clarification_needed",
                                            "clarification_count": clarification_count + 1,
                                            "vague_type": pending["vague_type"],
                                            "filter_weight": weight,
                                            "validation_message": validation_msg,
                                            "context": topic_context.to_dict(),
                                            "user_preferences": session.metadata.get("user_preferences", {}),
                                            "topic_history": session.metadata.get("topic_history", [])
                                        }
                                    )
            
            # Step 2: If no pending clarification, check if current query is vague
            # BUT: Skip vague detection if user is asking about attributes of shown products
            if not pending:
                # Check if user is asking about attributes of current/shown products
                has_product_context = (
                    session.current_product is not None or 
                    (session.last_shown_products and len(session.last_shown_products) > 0)
                )
                
                # Questions about product attributes when products are shown
                attribute_questions = [
                    r'\b(is this|does this|does it|is it|can this|can it)\b.*\b(come|available|have)\b.*\b(in|with)\b',  # "is this come in blue"
                    r'\b(what|which)\s+(colors?|colours?|materials?|sizes?)\b',  # "what colors"
                    r'\b(available in|comes in|have in|offer in)\b',  # "available in blue"
                    r'\b(tell me (about|more)|information|details|specs)\b',  # "tell me about"
                ]
                
                is_attribute_question = has_product_context and any(
                    re.search(pattern, original_message.lower()) 
                    for pattern in attribute_questions
                )
                
                if is_attribute_question:
                    logger.info(f"[HANDLER] Skipping vague detection - user asking about product attributes with context")
                    vague_result = None
                else:
                    vague_result = self.intent_detector.detect_vague_patterns(request.message)
                
                if vague_result:
                    logger.info(f"[HANDLER] Vague query detected: {vague_result['vague_type']}")
                    
                    bypass_phrases = [
                        "just show me anything", "show me anything", "surprise me",
                        "whatever you recommend", "anything is fine"
                    ]
                    is_bypass = any(phrase in request.message.lower() for phrase in bypass_phrases)
                    
                    if is_bypass:
                        logger.info("[HANDLER] Bypass in initial query, showing popular items")
                        request.message = "popular furniture"
                    else:
                        session.set_pending_clarification(
                            vague_result["vague_type"],
                            vague_result["partial_entities"],
                            request.message
                        )
                        
                        from .prompts import generate_clarification_prompt
                        assistant_message = generate_clarification_prompt(
                            vague_result["vague_type"],
                            vague_result["partial_entities"],
                            clarification_count=0
                        )
                        
                        session.add_message("assistant", assistant_message)
                        
                        return AssistantResponse(
                            message=assistant_message,
                            session_id=session.session_id,
                            products=[],
                            cart_summary=self._build_cart_summary(session),
                            metadata={
                                "intent": "clarification_needed",
                                "vague_type": vague_result["vague_type"],
                                "partial_entities": vague_result["partial_entities"],
                                "context": topic_context.to_dict(),
                                "user_preferences": session.metadata.get("user_preferences", {}),
                                "topic_history": session.metadata.get("topic_history", [])
                            }
                        )
            
            # Detect intent (for analytics/logging)
            logger.info(f"[HANDLER] Detecting intent...")
            intent = self.intent_detector.detect(
                request.message,
                current_product=session.current_product,
                last_shown_products=session.last_shown_products
            )
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
                        "function_calls_made": 0,
                        "context": topic_context.to_dict(),
                        "user_preferences": session.metadata.get("user_preferences", {}),
                        "topic_history": session.metadata.get("topic_history", [])
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
                        "function_calls_made": 0,
                        "context": topic_context.to_dict(),
                        "user_preferences": session.metadata.get("user_preferences", {}),
                        "topic_history": session.metadata.get("topic_history", [])
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
                    metadata={
                        "intent": "promotions",
                        "entities": entities,
                        "context": topic_context.to_dict(),
                        "user_preferences": session.metadata.get("user_preferences", {}),
                        "topic_history": session.metadata.get("topic_history", [])
                    }
                )
            
            # SHORTCUT: Handle cart view/show intent - no need for LLM
            if intent_str == "cart_show" or (intent == IntentType.CART_SHOW):
                logger.info("[HANDLER] Cart show intent detected, returning cart summary directly")
                
                # Use the tools to get cart state with full product details
                from .tools import get_assistant_tools
                tools = get_assistant_tools()
                cart_result = await tools.update_cart(
                    action="view",
                    session_id=session.session_id
                )
                
                cart_state = cart_result.get("cart", {})
                cart_items = cart_state.get("items", [])
                
                if cart_items:
                    total = cart_state.get("total", 0)
                    item_lines = []
                    for item in cart_items:
                        name = item.get('name') or item.get('title') or item.get('product_id', 'Item')
                        qty = item.get('quantity', 1)
                        price = item.get('price', 0)
                        item_total = item.get('item_total', price * qty)
                        item_lines.append(f"• **{name}** × {qty} = ${item_total:.2f}")
                    
                    assistant_message = f"**Your Cart ({len(cart_items)} item{'s' if len(cart_items) > 1 else ''}):**\n"
                    assistant_message += "\n".join(item_lines)
                    assistant_message += f"\n\n**Total: ${total:.2f}**\n\nWould you like to continue shopping or proceed to checkout?"
                else:
                    assistant_message = "Your cart is currently empty. Would you like to browse some products?"
                
                session.add_message("assistant", assistant_message)
                
                return AssistantResponse(
                    message=assistant_message,
                    session_id=session.session_id,
                    products=[],
                    cart_summary=self._build_cart_summary(session),
                    metadata={
                        "intent": "cart_show",
                        "entities": entities,
                        "context": topic_context.to_dict(),
                        "user_preferences": session.metadata.get("user_preferences", {}),
                        "topic_history": session.metadata.get("topic_history", [])
                    }
                )
            
            # SHORTCUT: Handle cart clear intent - no need for LLM
            if intent_str == "cart_clear" or (intent == IntentType.CART_CLEAR):
                logger.info("[HANDLER] Cart clear intent detected, clearing cart directly")
                
                # Use the tools to clear cart (skip_sync=False to sync with Node.js)
                from .tools import get_assistant_tools
                tools = get_assistant_tools()
                clear_result = await tools.update_cart(
                    action="clear",
                    session_id=session.session_id,
                    skip_sync=False
                )
                
                if clear_result.get("success"):
                    assistant_message = "Your cart has been cleared. Would you like to start fresh and browse some products?"
                else:
                    assistant_message = "I had trouble clearing your cart. Please try again."
                
                session.add_message("assistant", assistant_message)
                
                # Track cart action for frontend
                session.metadata["last_cart_action"] = {"type": "clear_cart"}
                
                return AssistantResponse(
                    message=assistant_message,
                    session_id=session.session_id,
                    products=[],
                    cart_summary=self._build_cart_summary(session),
                    metadata={
                        "intent": "cart_clear",
                        "entities": entities,
                        "context": topic_context.to_dict(),
                        "cart_action": {"type": "clear_cart"},
                        "user_preferences": session.metadata.get("user_preferences", {}),
                        "topic_history": session.metadata.get("topic_history", [])
                    }
                )
            
            # SHORTCUT: Handle find similar intent - no need for LLM clarification
            if intent_str == "find_similar" or (intent == IntentType.FIND_SIMILAR):
                logger.info("[HANDLER] Find similar intent detected, calling find_similar_products directly")
                
                # Determine which product to find similar items for
                product_id = None
                if session.current_product:
                    product_id = session.current_product.get('id')
                    logger.info(f"[HANDLER] Using current_product for similar search: {product_id}")
                elif session.last_shown_products:
                    product_id = session.last_shown_products[0].get('id')
                    logger.info(f"[HANDLER] Using first shown product for similar search: {product_id}")
                
                if not product_id:
                    # No product context, ask for clarification
                    assistant_message = "I'd be happy to find similar products! Please specify which product you'd like alternatives for, or search for a product first."
                    session.add_message("assistant", assistant_message)
                    
                    return AssistantResponse(
                        message=assistant_message,
                        session_id=session.session_id,
                        products=[],
                        cart_summary=self._build_cart_summary(session),
                        metadata={
                            "intent": "find_similar",
                            "entities": entities,
                            "context": topic_context.to_dict(),
                            "user_preferences": session.metadata.get("user_preferences", {}),
                            "topic_history": session.metadata.get("topic_history", [])
                        }
                    )
                
                # Collect all IDs to exclude
                exclude_ids = []
                if session.last_shown_products:
                    exclude_ids = [p.get('id') for p in session.last_shown_products if p.get('id')]
                
                # Call find_similar_products tool directly
                from .tools import get_assistant_tools
                tools = get_assistant_tools()
                similar_result = await tools.find_similar_products(
                    product_id=product_id,
                    exclude_ids=exclude_ids,
                    limit=5
                )
                
                products = similar_result.get('products', [])
                source_name = similar_result.get('source_product', 'this item')
                
                if products:
                    # Update session with similar products
                    session.last_shown_products = products
                    session.current_product = None
                    
                    assistant_message = f"Here are {len(products)} similar products to {source_name} that you might like!"
                else:
                    assistant_message = f"I couldn't find any similar products to {source_name} at the moment. Try searching for a different category!"
                
                session.add_message("assistant", assistant_message)
                
                return AssistantResponse(
                    message=assistant_message,
                    session_id=session.session_id,
                    products=products,
                    cart_summary=self._build_cart_summary(session),
                    metadata={
                        "intent": "find_similar",
                        "entities": entities,
                        "context": topic_context.to_dict(),
                        "user_preferences": session.metadata.get("user_preferences", {}),
                        "topic_history": session.metadata.get("topic_history", [])
                    }
                )
            
            # FORCE product_search intent for furniture-related queries
            furniture_keywords = [
                "chair", "table", "desk", "sofa", "bed", "shelf", "locker", "stool",
                "cabinet", "storage", "furniture", "office", "bedroom", "living",
                "dining", "wardrobe", "drawer", "bench", "ottoman"
            ]
            
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
                        metadata={
                            "intent": "clarification_needed",
                            "reason": "no_products_in_session",
                            "context": topic_context.to_dict(),
                            "user_preferences": session.metadata.get("user_preferences", {}),
                            "topic_history": session.metadata.get("topic_history", [])
                        }
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
                        metadata={
                            "intent": "clarification_needed",
                            "reason": "index_out_of_range",
                            "max_index": len(session.last_shown_products),
                            "context": topic_context.to_dict(),
                            "user_preferences": session.metadata.get("user_preferences", {}),
                            "topic_history": session.metadata.get("topic_history", [])
                        }
                    )

            # PRE-LLM FILTER VALIDATION - Check if query has sufficient filters before calling LLM
            # This prevents wasting LLM calls on queries that will need clarification anyway
            if intent == IntentType.PRODUCT_SEARCH:
                entities = self.intent_detector.extract_entities(request.message, intent)
                is_valid, weight, validation_msg = self.filter_validator.validate_filter_count(
                    entities,
                    request.message
                )
                
                # Check for bypass phrases
                if self.filter_validator.is_bypass_phrase(request.message):
                    logger.info("[HANDLER] Bypass phrase detected, allowing search with available filters")
                    bypass_disclaimer = "Here are some popular options based on your request. You can refine by mentioning specific preferences anytime."
                    session.metadata["bypass_disclaimer"] = bypass_disclaimer
                elif not is_valid:
                    logger.info(f"[HANDLER] Insufficient filters before LLM call (weight={weight:.1f})")
                    logger.info(f"[HANDLER] Triggering clarification to avoid wasting LLM resources")
                    
                    # Detect vague type for proper clarification, or use generic if no pattern matched
                    vague_result = self.intent_detector.detect_vague_patterns(request.message)
                    
                    if not vague_result:
                        # No specific vague pattern matched, but still insufficient filters
                        # Create a generic clarification based on what we have
                        logger.info("[HANDLER] No vague pattern matched, creating generic clarification")
                        
                        # Determine vague type based on entities
                        if entities.get("category"):
                            vague_type = "category_only"
                            partial_entities = {"category": entities["category"]}
                        elif entities.get("color"):
                            vague_type = "attribute_only"
                            partial_entities = {"color": entities["color"]}
                        elif entities.get("material"):
                            vague_type = "attribute_only"
                            partial_entities = {"material": entities["material"]}
                        elif entities.get("room_type"):
                            vague_type = "room_purpose_only"
                            partial_entities = {"room_type": entities["room_type"]}
                        else:
                            vague_type = "ultra_vague"
                            partial_entities = {}
                        
                        vague_result = {
                            "vague_type": vague_type,
                            "partial_entities": partial_entities
                        }
                    
                    session.set_pending_clarification(
                        vague_result["vague_type"],
                        vague_result["partial_entities"],
                        request.message
                    )
                    
                    from .prompts import generate_clarification_prompt
                    assistant_message = f"{validation_msg}\n\n"
                    assistant_message += generate_clarification_prompt(
                        vague_result["vague_type"],
                        vague_result["partial_entities"],
                        clarification_count=0
                    )
                    
                    session.add_message("assistant", assistant_message)
                    
                    return AssistantResponse(
                        message=assistant_message,
                        session_id=session.session_id,
                        products=[],
                        cart_summary=self._build_cart_summary(session),
                        metadata={
                            "intent": "insufficient_filters",
                            "filter_weight": weight,
                            "validation_message": validation_msg,
                            "vague_type": vague_result["vague_type"],
                            "context": topic_context.to_dict()
                        }
                    )
                else:
                    logger.info(f"[HANDLER] Filter validation passed (weight={weight:.1f}), proceeding to LLM")
            
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
                # Note: Vague queries are now handled BEFORE LLM call, so no need to check for clarification here
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
            
            # SAFETY CHECK: If product spec Q&A intent but WRONG tool or NO tool → force get_product_specs!
            if intent == IntentType.PRODUCT_SPEC_QA:
                # Check if LLM called search_products instead of get_product_specs
                wrong_tool_called = llm_response.function_calls and any(fc.name == 'search_products' for fc in llm_response.function_calls)
                no_tool_called = not llm_response.function_calls
                
                if wrong_tool_called or no_tool_called:
                    # Extract product reference from query using patterns
                    product_num = None
                    query_lower = request.message.lower()
                    
                    # Check for contextual references like "this chair", "that one", "these chairs"
                    contextual_refs = ['this', 'that', 'it', 'these', 'those', 'them', 'the chair', 'the product']
                    has_contextual_ref = any(ref in query_lower for ref in contextual_refs)
                    
                    # Try to extract explicit number
                    for pattern in self.PRODUCT_REF_PATTERNS:
                        match = pattern.search(request.message)
                        if match:
                            product_num = int(match.group(1))
                            break
                    
                    if not product_num:
                        # Try ordinal numbers
                        for ordinal, num in self.ORDINAL_MAP.items():
                            if ordinal in query_lower:
                                product_num = num
                                break
                    
                    # If no explicit number but has contextual reference, use last shown product
                    if not product_num and has_contextual_ref and session.last_shown_products:
                        product_num = 1  # Default to first/last shown
                        logger.info(f"[HANDLER] Contextual reference detected: '{request.message}', using first shown product")
                    
                    if product_num:
                        # Get product from session (1-indexed in user query, 0-indexed in list)
                        if session.last_shown_products and 0 < product_num <= len(session.last_shown_products):
                            product = session.last_shown_products[product_num - 1]
                            product_id = product.get('id')
                            
                            if product_id:
                                if wrong_tool_called:
                                    logger.warning(f"[HANDLER] ⚠️ SAFETY CATCH: Product Q&A intent but LLM called search_products instead of get_product_specs!")
                                    logger.warning(f"[HANDLER] Correcting to get_product_specs for product: {product.get('name', 'Unknown')}")
                                else:
                                    logger.warning(f"[HANDLER] ⚠️ SAFETY CATCH: Product Q&A but LLM didn't call tool!")
                                
                                from .hf_llm_client import FunctionCall
                                llm_response.function_calls = [
                                    FunctionCall(
                                        name="get_product_specs",
                                        arguments={"product_id": product_id, "question": request.message}
                                    )
                                ]
                                llm_response.content = ""
                        else:
                            logger.warning(f"[HANDLER] Product spec Q&A but product #{product_num} not in session (only {len(session.last_shown_products)} products)")
            
            # SAFETY CHECK: If cart add intent but NO tool calls → force update_cart!
            if intent == IntentType.CART_ADD and not llm_response.function_calls:
                query_lower = request.message.lower()
                
                # Look for product reference (number, ordinal, or contextual)
                product_num = None
                for pattern in self.PRODUCT_REF_PATTERNS:
                    match = pattern.search(query_lower)
                    if match:
                        product_num = int(match.group(1))
                        break
                
                if not product_num:
                    for ordinal, num in self.ORDINAL_MAP.items():
                        if ordinal in query_lower:
                            product_num = num
                            break
                
                # If only one product shown, assume "add it" refers to that
                if not product_num and session.last_shown_products and len(session.last_shown_products) == 1:
                    context_refs = ['this', 'it', 'the product', 'that', 'chair', 'table', 'desk', 
                                   'this one', 'buy', 'purchase', 'want to buy', 'want this', 'get this']
                    if any(ref in query_lower for ref in context_refs):
                        product_num = 1
                
                if product_num and session.last_shown_products and 0 < product_num <= len(session.last_shown_products):
                    product = session.last_shown_products[product_num - 1]
                    product_id = product.get('id') or product.get('product_id')
                    
                    if product_id:
                        logger.warning(f"[HANDLER] ⚠️ SAFETY CATCH: Cart add intent but LLM didn't call tool!")
                        from .hf_llm_client import FunctionCall
                        
                        # Extract quantity if mentioned (e.g., "add 2 of this", "add 3 units")
                        # CRITICAL: Don't match product references like "option 1", "product 2", "add option 2"
                        qty = 1
                        # Match patterns like: "2 of", "3 units", "5 items", "4x", but NOT "option 1" or "product 2"
                        # IMPORTANT: Exclude patterns that look like product selection (e.g., "add option 2", "add product 2")
                        qty_match = re.search(r'\b(\d+)\s*(?:x|units?|items?|pcs?|pieces?|of\s+(?:these|them|this|it))', query_lower)
                        
                        # Ensure we didn't capture a product reference number
                        if qty_match:
                            potential_qty = int(qty_match.group(1))
                            # Check if this number is preceded by "option", "product", "item", "number"
                            product_ref_check = re.search(r'\b(option|product|item|number|choice)\s+' + str(potential_qty), query_lower)
                            if not product_ref_check:
                                qty = potential_qty
                                logger.info(f"[HANDLER] Extracted quantity: {qty} from query: {query_lower}")
                            else:
                                logger.info(f"[HANDLER] Number {potential_qty} detected but appears to be a product reference, not quantity. Using qty=1")
                        
                        logger.info(f"[HANDLER] SAFETY CATCH creating update_cart call: product_id={product_id}, quantity={qty}")
                        llm_response.function_calls = [
                            FunctionCall(
                                name="update_cart",
                                arguments={"action": "add", "product_id": product_id, "quantity": qty}
                            )
                        ]
                        llm_response.content = ""

            # Process function calls if any
            if llm_response.function_calls:
                logger.info(f"[HANDLER] Processing {len(llm_response.function_calls)} function calls")
                logger.info(f"[HANDLER] Products in session BEFORE tool execution: {len(session.last_shown_products)}")
                
                # VALIDATION: Fix product IDs for spec/availability/comparison/cart tools
                for func_call in llm_response.function_calls:
                    if func_call.name in ['get_product_specs', 'check_availability', 'update_cart']:
                        product_id = func_call.arguments.get('product_id', '')
                        
                        # For update_cart: Validate quantity - default to 1 unless explicitly specified
                        if func_call.name == 'update_cart':
                            llm_qty = func_call.arguments.get('quantity', 1)
                            msg_lower = original_message.lower()
                            
                            # Check if user explicitly mentioned a quantity number
                            # IMPORTANT: Must NOT match "option 2", "item 3", "product 2" etc. - those are product references!
                            explicit_qty_patterns = [
                                # "2 units", "3 items", "5 pieces", "2 of these"
                                r'\b(\d+)\s*(?:units?|items?|pcs?|pieces?|of\s+(?:these|them|this|it))',
                                # "add 2 of" but NOT "add option 2" or "add 2 to cart" (where 2 is option number)
                                r'(?:add|get|want|need|order)\s+(\d+)\s+(?:of|copies|more)',
                                # "quantity 3", "qty: 2"
                                r'(?:quantity|qty)[:\s]*(\d+)',
                            ]
                            explicit_qty = None
                            for pattern in explicit_qty_patterns:
                                match = re.search(pattern, msg_lower)
                                if match:
                                    potential_qty = int(match.group(1))
                                    # Verify this isn't a product reference
                                    product_ref_check = re.search(r'\b(option|product|item|number|choice)\s+' + str(potential_qty), msg_lower)
                                    if not product_ref_check:
                                        explicit_qty = potential_qty
                                        logger.info(f"[HANDLER] Found explicit quantity: {explicit_qty} in '{original_message}'")
                                        break
                                    else:
                                        logger.info(f"[HANDLER] Number {potential_qty} appears to be product reference, not quantity")
                            
                            # ALWAYS force quantity to 1 unless explicit quantity phrase found
                            # This prevents "option 2", "this one", "add 2 to cart" confusion
                            if explicit_qty is None:
                                func_call.arguments['quantity'] = 1
                                if llm_qty != 1:
                                    logger.warning(f"[HANDLER] Corrected cart quantity from {llm_qty} to 1 (no explicit qty phrase in: '{original_message}')")
                            else:
                                # Double-check: if LLM extracted a different quantity, log it for debugging
                                if llm_qty != explicit_qty:
                                    logger.warning(f"[HANDLER] LLM extracted qty={llm_qty} but we found qty={explicit_qty}, using our extraction")
                                func_call.arguments['quantity'] = explicit_qty
                                logger.info(f"[HANDLER] Using explicit quantity: {explicit_qty}")
                        
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
                        
                        # Fix reference to "it", "this one", or generic detail requests if only 1 product shown
                        if product_num is None and session.last_shown_products and len(session.last_shown_products) == 1:
                            context_refs = ['this one', 'add it', 'add this', 'the product', 'that one', 
                                           'tell me', 'more info', 'details', 'detail', 'specs', 'specifications',
                                           'about it', 'about this', 'more about', 'is this in stock', 
                                           'in stock', 'available', 'availability', 'this to cart']
                            if any(ref in original_message.lower() for ref in context_refs):
                                product_num = 1
                                logger.info(f"[HANDLER] Inferred product_num=1 from generic request with single product in session")
                        
                        # NEW: If user is asking about current product (from specs view)
                        if product_num is None and session.current_product:
                            context_refs = ['this one', 'add it', 'add this', 'the product', 'that one',
                                           'is this in stock', 'in stock', 'available', 'availability', 
                                           'this to cart', 'add this', 'it to cart']
                            if any(ref in original_message.lower() for ref in context_refs):
                                # Use current product directly
                                current_id = session.current_product.get('id')
                                if current_id:
                                    func_call.arguments['product_id'] = current_id
                                    logger.info(f"[HANDLER] Using current_product ID: '{current_id}' for {func_call.name}")
                                    product_num = -1  # Mark as resolved via current_product
                        
                        # If still no product_num but multiple products shown and user wants details
                        if product_num is None and session.last_shown_products and len(session.last_shown_products) > 1:
                            detail_refs = ['tell me', 'more info', 'details', 'detail', 'specs', 'specifications', 
                                          'about it', 'about this', 'more about', 'describe']
                            if any(ref in original_message.lower() for ref in detail_refs):
                                # Need clarification - return early
                                logger.info(f"[HANDLER] User asked for details but {len(session.last_shown_products)} products shown - asking for clarification")
                                assistant_message = f"I'd be happy to give you more details! Which product are you interested in? Just say 'option 1', 'option 2', etc. (I have {len(session.last_shown_products)} products shown)."
                                session.add_message("assistant", assistant_message)
                                return AssistantResponse(
                                    message=assistant_message,
                                    session_id=session.session_id,
                                    products=[],
                                    cart_summary=self._build_cart_summary(session),
                                    metadata={
                                        "intent": "clarification_needed",
                                        "reason": "ambiguous_product_reference"
                                    }
                                )
                        
                        # Correct product_id if we have a valid number (skip if already resolved via current_product)
                        if product_num != -1 and session.last_shown_products and product_num and 0 < product_num <= len(session.last_shown_products):
                            correct_product = session.last_shown_products[product_num - 1]
                            correct_product_id = correct_product.get('id')
                            if correct_product_id:
                                func_call.arguments['product_id'] = correct_product_id
                                logger.info(f"[HANDLER] Corrected product_id to '{correct_product_id}' (option {product_num})")
                            else:
                                logger.error(f"[ERROR] Product #{product_num} has no ID in session!")
                        elif product_num == -1:
                            pass  # Already resolved via current_product
                        elif not session.last_shown_products and not session.current_product:
                            logger.error(f"[ERROR] No products in session - cannot correct ID")
                        elif not product_num and not session.current_product:
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
                    
                    elif func_call.name == 'find_similar_products':
                        # For similar products: auto-populate product_id and exclude already-shown products
                        product_id = func_call.arguments.get('product_id', '')
                        
                        # If no product_id or invalid, use current_product or first from last_shown
                        if not product_id or product_id in ['', 'unknown', 'UNKNOWN']:
                            if session.current_product:
                                product_id = session.current_product.get('id', '')
                                logger.info(f"[HANDLER] Using current_product for similar search: {product_id}")
                            elif session.last_shown_products:
                                product_id = session.last_shown_products[0].get('id', '')
                                logger.info(f"[HANDLER] Using first shown product for similar search: {product_id}")
                        
                        func_call.arguments['product_id'] = product_id
                        
                        # Collect all IDs to exclude (products already shown to user)
                        exclude_ids = []
                        if session.last_shown_products:
                            exclude_ids = [p.get('id') for p in session.last_shown_products if p.get('id')]
                        
                        # Also exclude current_product if it's not in the list
                        if session.current_product:
                            curr_id = session.current_product.get('id')
                            if curr_id and curr_id not in exclude_ids:
                                exclude_ids.append(curr_id)
                        
                        func_call.arguments['exclude_ids'] = exclude_ids
                        logger.info(f"[HANDLER] find_similar_products: product_id={product_id}, excluding {len(exclude_ids)} IDs")
                
                # Execute tools and get results
                tool_results = await self._execute_function_calls(
                    llm_response.function_calls,
                    session
                )
                
                logger.info(f"[HANDLER] Tool results: {list(tool_results.keys())}")
                logger.info(f"[HANDLER] Products in session AFTER tool execution: {len(session.last_shown_products)}")
                if session.last_shown_products:
                    logger.info(f"[HANDLER] First product: {session.last_shown_products[0].get('name', 'NO NAME')} (id: {session.last_shown_products[0].get('id', 'NO ID')})")
                else:
                    logger.warning(f"[HANDLER] ⚠️ No products in session after tool execution!")
                
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
                    
                    elif tool_name == 'find_similar_products':
                        # Format similar products like search results
                        products = result.get('products', [])
                        source_name = result.get('source_product_name', 'the selected product')
                        if products:
                            product_list = []
                            for idx, p in enumerate(products):
                                p_name = p.get('name') or p.get('title') or "Unknown Product"
                                p_price = p.get('price', 0)
                                p_id = p.get('id')
                                product_list.append(f"{idx+1}. {p_name} (${p_price}) [ID: {p_id}]")
                            
                            result_str = f"Found {len(products)} products similar to {source_name}:\n" + "\n".join(product_list)
                            
                            # Update session with new products (FIX: use update_shown_products)
                            session.update_shown_products(products)
                            logger.info(f"[HANDLER] Updated session with {len(products)} similar products")
                        else:
                            result_str = f"No similar products found for {source_name}."
                    
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
                            "Respond with well-formatted product information using this structure:\n"
                            "1. Start with **Product Name** in bold\n"
                            "2. Give a 1-sentence description\n"
                            "3. Use bullet points (•) for key specs like:\n"
                            "   • **Dimensions**: width x depth x height\n"
                            "   • **Material**: material type\n"
                            "   • **Weight**: if available\n"
                            "   • **Key Features**: important features\n"
                            "Keep it concise - 3-5 bullet points max. Only include data from the tool result."
                        )
                elif 'calculate_shipping' in tool_names:
                    post_tool_instruction = (
                        "Format shipping information clearly:\n"
                        "• **Standard Shipping**: $X (Y-Z business days)\n"
                        "• **Express Shipping**: $X if available\n"
                        "Keep it brief and helpful."
                    )
                elif 'check_availability' in tool_names:
                    avail_result = tool_results.get('check_availability', {})
                    if avail_result.get('in_stock'):
                        post_tool_instruction = (
                            "Confirm the product is **in stock**. Use the exact message from the tool result. "
                            "Mention contact info for customization if relevant."
                        )
                    else:
                        post_tool_instruction = (
                            "Inform that the product is **currently out of stock**. "
                            "Use the exact message from the tool result. Suggest contacting support for restock dates."
                        )
                elif 'compare_products' in tool_names:
                    post_tool_instruction = (
                        "Format the comparison clearly using this structure:\n"
                        "**Comparison Summary:**\n"
                        "• **Price**: Product A ($X) vs Product B ($Y)\n"
                        "• **Key Difference 1**: brief comparison\n"
                        "• **Key Difference 2**: brief comparison\n"
                        "• **Recommendation**: based on user's needs\n"
                        "Use bullet points and bold for key info."
                    )
                elif 'find_similar_products' in tool_names:
                    similar_result = tool_results.get('find_similar_products', {})
                    products = similar_result.get('products', [])
                    if products:
                        post_tool_instruction = (
                            "Now respond to the user with ONLY a brief, professional 1-2 sentence intro about the similar products found. "
                            "DO NOT list products - they will be displayed below your message as cards. "
                            "DO NOT mention 'UI', 'screen', 'list', or 'display'. "
                            "Example: 'Here are some similar products you might like!' or 'I found X more options in the same category.'"
                        )
                    else:
                        post_tool_instruction = (
                            "Apologize that no similar products were found. Suggest the user try a different search."
                        )
                else:
                    post_tool_instruction = "Respond briefly and professionally based on the tool results. Use **bold** for important info."

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
                try:
                    final_response = await self.llm_client.chat(
                        messages=messages,
                        temperature=response_temperature,
                        max_tokens=max_response_tokens
                    )
                    
                    # Let LLM generate natural, conversational response
                    # Products are already stored in session from tool execution
                    assistant_message = final_response.content if final_response and final_response.content else ""
                    
                except Exception as e:
                    logger.error(f"[HANDLER] Final LLM call failed: {e}", exc_info=True)
                    # Generate fallback message based on tool results
                    if 'search_products' in tool_results and tool_results['search_products'].get('products'):
                        product_count = len(tool_results['search_products']['products'])
                        assistant_message = f"I found {product_count} {'option' if product_count == 1 else 'options'} for you!"
                    else:
                        assistant_message = "I've processed your request."
                
                if not assistant_message:
                    logger.error(f"[HANDLER] Empty message after final LLM call, generating fallback")
                    if 'search_products' in tool_results and tool_results['search_products'].get('products'):
                        product_count = len(tool_results['search_products']['products'])
                        assistant_message = f"I found {product_count} options matching your search."
                    else:
                        assistant_message = "Here's what I found for you."
                
                # Strip any leaked markers or internal prefixes (MORE AGGRESSIVE)
                assistant_message = re.sub(r'\[/?TOOL[_\s]?CALLS?\]', '', assistant_message, flags=re.IGNORECASE)
                assistant_message = re.sub(r'\[/?TOOL[_\s]?RESULTS?\]', '', assistant_message, flags=re.IGNORECASE)
                assistant_message = re.sub(r'\[Tool result from .*?\]', '', assistant_message, flags=re.IGNORECASE)
                
                # Remove raw JSON tool call structures that leaked into response
                assistant_message = re.sub(r'\[\s*\{["\']name["\']:\s*["\']tool_name["\'].*?\}\s*\]', '', assistant_message, flags=re.DOTALL)
                assistant_message = re.sub(r'\{["\']name["\']:\s*["\'][^"\']+["\'],\s*["\']arguments["\']:\s*\{.*?\}\}', '', assistant_message, flags=re.DOTALL)
                
                # Remove common internal markers
                assistant_message = re.sub(r'Found \d+ products? matching the search\.', '', assistant_message, flags=re.IGNORECASE)
                assistant_message = re.sub(r'INTERNAL INSTRUCTION:.*', '', assistant_message, flags=re.IGNORECASE | re.DOTALL)
                
                # Strip common LLM prefixes
                assistant_message = re.sub(r'^(Assistant|User|System|Bot):\s*', '', assistant_message, flags=re.IGNORECASE)
                assistant_message = re.sub(r'\n(Assistant|User|System|Bot):\s*', '\n', assistant_message, flags=re.IGNORECASE)
                
                # Strip any repeated prompts
                assistant_message = re.sub(r'Now respond to the user.*', '', assistant_message, flags=re.IGNORECASE | re.DOTALL)
                
                # Strip tool result debugging text
                assistant_message = re.sub(r'\{"name".*?"price".*?\}', '', assistant_message)
                
                # Clean up multiple newlines and spaces
                assistant_message = re.sub(r'\n\s*\n\s*\n+', '\n\n', assistant_message)
                assistant_message = assistant_message.strip()

                
                # ADDITIONAL VALIDATION: Block hallucinations after tool errors
                if 'get_product_specs' in tool_results:
                    spec_result = tool_results['get_product_specs']
                    
                    # Set current product when user views specs (for follow-up questions)
                    if not spec_result.get('error'):
                        product_id = spec_result.get('product_id')
                        product_name = spec_result.get('product_name')
                        if product_id:
                            session.current_product = {
                                'id': product_id,
                                'name': product_name,
                                'price': spec_result.get('price'),
                            }
                            logger.info(f"[HANDLER] Set current_product to: {product_name} ({product_id})")
                    
                    if 'error' in spec_result:
                        # Tool failed - check if LLM hallucinated anyway
                        has_price = re.search(r'\$\d+', assistant_message)
                        has_dimensions = re.search(r'\d+\s*[x×]\s*\d+|\d+\s*(cm|mm|kg|inches)', assistant_message)
                        has_materials = any(word in assistant_message.lower() for word in ['wood', 'metal', 'leather', 'fabric', 'plastic'])
                        
                        if has_price or has_dimensions or has_materials:
                            logger.warning(f"[BLOCKED] LLM hallucinated specs despite tool error!")
                            logger.warning(f"Blocked hallucination: {assistant_message[:100]}...")
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
                    
                    # Don't validate noun matching here - trust the search results
                    # The hybrid search already handles relevance scoring
                
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
            
            # CRITICAL: Ensure message is never empty
            if not assistant_message or assistant_message.strip() == "":
                logger.error(f"[HANDLER] ❌ EMPTY MESSAGE DETECTED! Generating fallback")
                if session.last_shown_products:
                    assistant_message = f"I found {len(session.last_shown_products)} options for you. Let me know if you'd like more details on any of them!"
                else:
                    assistant_message = "I'm sorry, I couldn't find any products matching that search. Could you try a different search term?"
                session.add_message("assistant", assistant_message)
            
            # CRITICAL FIX: Validate product discovery claims match actual products
            # Never say "I found products" without actually having products to show
            assistant_message = self._validate_product_claims(
                assistant_message,
                session.last_shown_products,
                original_message
            )
            
            # CRITICAL FIX: Only include product cards when it's a NEW SEARCH
            # Don't return product cards for spec queries, availability checks, etc.
            should_include_products = False
            if llm_response.function_calls:
                tool_names = [fc.name for fc in llm_response.function_calls]
                # Only include products if search_products was called
                if 'search_products' in tool_names:
                    should_include_products = True
                # For compare_products, include only the compared products
                elif 'compare_products' in tool_names:
                    should_include_products = True
                # For find_similar_products, include the similar products found
                elif 'find_similar_products' in tool_names:
                    should_include_products = True
            
            products_to_return = session.last_shown_products[:] if should_include_products else []
            
            # Build response
            logger.info(f"[HANDLER] Building response - should_include_products: {should_include_products}")
            logger.info(f"[HANDLER] Products to return: {len(products_to_return)}")
            response = AssistantResponse(
                message=assistant_message,
                session_id=session.session_id,
                products=products_to_return,
                cart_summary=self._build_cart_summary(session),
                metadata={
                    "intent": intent_str,
                    "entities": entities,
                    "function_calls_made": len(llm_response.function_calls) if llm_response.function_calls else 0,
                    "context": topic_context.to_dict(),
                    "user_preferences": session.metadata.get("user_preferences", {}),
                    "topic_history": session.metadata.get("topic_history", [])
                }
            )
            logger.info(f"[HANDLER] ✅ Response created with {len(response.products) if response.products else 0} products")
            
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
            
            # Get session for error response
            try:
                session = self.session_store.get_or_create_session(
                    session_id=request.session_id,
                    user_id=request.user_id
                )
            except:
                session = None
            
            # Return error response with minimal context
            error_metadata = {
                "error": str(e),
                "context": {
                    "topic": "general",
                    "intent": "statement",
                    "confidence": 0,
                    "preferences": {}
                }
            }
            
            if session:
                error_metadata["user_preferences"] = session.metadata.get("user_preferences", {})
                error_metadata["topic_history"] = session.metadata.get("topic_history", [])
            
            return AssistantResponse(
                message="I'm sorry, I encountered an error processing your request. Please try again or contact support.",
                session_id=request.session_id or "error",
                metadata=error_metadata
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
        
        # Validate the refined query has sufficient filters
        from .intents import IntentType
        entities = self.intent_detector.extract_entities(refined_query, IntentType.PRODUCT_SEARCH)
        is_valid, weight, validation_msg = self.filter_validator.validate_filter_count(
            entities,
            refined_query
        )
        
        if not is_valid:
            logger.warning(f"[CONTEXT] Refined query has insufficient filters (weight={weight:.1f})")
            logger.warning(f"[CONTEXT] Will trigger clarification instead of progressive refinement")
            # Return original message to allow clarification flow to handle it
            return message
        else:
            logger.info(f"[CONTEXT] Refined query validated (weight={weight:.1f}), proceeding")
        
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
        
        # Add conversation history (last 20 messages for context window)
        for msg in session.messages[-20:]:
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
        
        # Check if response mentions wrong product type (just warn, don't block)
        if search_query and had_tool_calls:
            important_nouns = {'chair', 'chairs', 'table', 'tables', 'desk', 'desks', 'sofa', 'sofas',
                              'bed', 'beds', 'locker', 'lockers', 'cabinet', 'cabinets', 'shelf', 'shelves',
                              'storage', 'stool', 'stools', 'bench', 'benches', 'wardrobe', 'wardrobes'}
            
            search_nouns = set(search_query.lower().split()) & important_nouns
            response_lower = response.lower()
            
            if search_nouns:
                for search_noun in search_nouns:
                    base_noun = search_noun.rstrip('s')
                    has_correct_noun = base_noun in response_lower or (base_noun + 's') in response_lower
                    
                    if not has_correct_noun:
                        wrong_nouns = important_nouns - {base_noun, base_noun + 's'}
                        mentioned_wrong = [noun for noun in wrong_nouns if noun in response_lower]
                        
                        if mentioned_wrong:
                            logger.warning(f"[VALIDATION] ⚠️ Response mentions: {mentioned_wrong}, searched for: {search_noun}")
                            # Just log, don't replace - trust search results
        
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
            if not had_tool_calls:
                # LLM tried to hallucinate products without any tool call - BLOCK THIS
                logger.error(f"[VALIDATION] Blocked hallucinated product listing!")
                return "Let me search our catalog for you."
            # If we HAD tool calls, trust the response - products are real
        
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
            
            try:
                result = await execute_tool(tool_name, arguments, self.tools)
                logger.info(f"[EXECUTE_TOOLS] Tool {tool_name} completed successfully")
            except Exception as e:
                logger.error(f"[EXECUTE_TOOLS] Tool {tool_name} failed: {e}", exc_info=True)
                result = {"error": str(e), "products": [] if tool_name == "search_products" else None}
            
            # FIX: Format products with actual names before sending to LLM
            if tool_name == "search_products":
                if "error" in result:
                    logger.error(f"[EXECUTE_TOOLS] search_products error: {result['error']}")
                    result["products"] = []
                elif "products" not in result:
                    logger.error(f"[EXECUTE_TOOLS] search_products returned no 'products' key! Result keys: {result.keys()}")
                    result["products"] = []
                elif not result["products"]:
                    logger.warning(f"[EXECUTE_TOOLS] search_products returned empty products list")
                else:
                    logger.info(f"[EXECUTE_TOOLS] search_products returned {len(result['products'])} products")
                
                # Process products if we have any
                if result.get("products"):
                    for product in result["products"]:
                        # Ensure name is set from title, not product_X
                        if not product.get("name") or product.get("name").startswith("product_"):
                            product["name"] = product.get("title", product.get("description", "Product"))
                    
                    # Store in session for reference
                    logger.info(f"[EXECUTE_TOOLS] Storing {len(result['products'])} products in session")
                    logger.info(f"[EXECUTE_TOOLS] Product names: {[p.get('name', 'NO NAME') for p in result['products'][:3]]}")
                    session.update_shown_products(result["products"])
                    logger.info(f"[EXECUTE_TOOLS] ✅ Session now has {len(session.last_shown_products)} products")
                    if session.last_shown_products:
                        logger.info(f"[EXECUTE_TOOLS] Session products: {[p.get('name', 'NO NAME') for p in session.last_shown_products[:3]]}")
                else:
                    logger.error(f"[EXECUTE_TOOLS] ❌ No products to store in session")
            
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
            
                    # NEW: Also update shown products for find_similar_products
                    if tool_name == "find_similar_products" and result.get("products"):
                        logger.info(f"[EXECUTE_TOOLS] Storing {len(result['products'])} similar products in session")
                        session.update_shown_products(result["products"])
            
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
    
    def _validate_product_claims(
        self,
        message: str,
        products: List[Dict[str, Any]],
        original_query: str
    ) -> str:
        """
        Validate that product discovery claims in the message match actual products.
        If the message says "I found X products" but products list is empty, 
        either generate a text fallback or fix the message.
        
        Args:
            message: The assistant's response message
            products: List of products to be displayed
            original_query: Original user query
        
        Returns:
            Validated/corrected message
        """
        # Patterns that indicate product discovery claims
        product_claim_patterns = [
            r'I found (\d+|several|some|a few|multiple)',
            r'Here are (\d+|several|some|the|a few)',
            r'I\'ve found (\d+|several|some)',
            r'showing you (\d+|several|some)',
            r'(\d+) (options?|products?|items?|chairs?|sofas?|desks?|tables?|beds?) (for you|matching|that)',
            r'displayed (below|above)',
            r'take a look at',
        ]
        
        has_product_claim = any(re.search(p, message, re.IGNORECASE) for p in product_claim_patterns)
        
        if has_product_claim and not products:
            # LLM claimed to find products but we have none - this is the hollow response issue!
            logger.error(f"[VALIDATION] ❌ HOLLOW RESPONSE: Message claims products but none available!")
            logger.error(f"[VALIDATION] Message: {message[:100]}...")
            
            # Generate a proper "no results" message
            query_terms = original_query.lower()
            
            # Extract product type from query
            product_types = ['sofa', 'chair', 'desk', 'table', 'bed', 'locker', 'cabinet', 'stool', 'shelf', 'storage', 'wardrobe']
            found_type = 'products'
            for ptype in product_types:
                if ptype in query_terms:
                    found_type = ptype + 's' if not ptype.endswith('s') else ptype
                    break
            
            message = f"I couldn't find any {found_type} matching your search. Would you like to try a different search term or browse our categories?"
            logger.info(f"[VALIDATION] ✅ Replaced hollow response with: {message}")
        
        elif products and not has_product_claim:
            # We have products but message doesn't acknowledge them
            # This can happen if LLM generates a generic response
            message_lower = message.lower()
            
            # Check if message is too generic or doesn't mention products
            generic_patterns = [
                r'^(sure|okay|yes|of course)[,!.]?\s*$',
                r'^(let me|i\'ll|i will)\s+(help|search|look)',
                r'^searching',
            ]
            
            is_generic = any(re.match(p, message_lower) for p in generic_patterns) or len(message) < 30
            
            if is_generic:
                logger.warning(f"[VALIDATION] ⚠️ Generic message with products available, enhancing...")
                # Generate a proper product acknowledgment
                count = len(products)
                
                # Get product type from first product
                first_product = products[0]
                product_name = first_product.get('name', '').lower()
                
                product_type = 'options'
                for ptype in ['sofa', 'chair', 'desk', 'table', 'bed', 'locker', 'cabinet', 'stool', 'shelf']:
                    if ptype in product_name:
                        product_type = ptype + 's' if count > 1 else ptype
                        break
                
                message = f"I found {count} {product_type} for you. Let me know if you'd like more details on any of them!"
        
        # If we have products, also append a text fallback list for accessibility
        if products and len(products) > 0:
            # Check if message already contains product list
            if not re.search(r'\d+\.\s+', message):  # No numbered list
                # Add a brief text summary as fallback (hidden or shown based on UI)
                # This ensures products are ALWAYS visible even if UI cards fail
                pass  # Products are in response.products, UI will handle display
        
        return message
    
    def _generate_text_product_list(self, products: List[Dict[str, Any]], limit: int = 5) -> str:
        """
        Generate a text-based product list as fallback.
        Used when UI cards cannot render or for accessibility.
        
        Args:
            products: List of products
            limit: Max products to list
        
        Returns:
            Formatted text list
        """
        if not products:
            return ""
        
        lines = []
        for idx, product in enumerate(products[:limit], 1):
            name = product.get('name') or product.get('title', 'Product')
            price = product.get('price', 0)
            currency = product.get('currency', 'AUD')
            
            lines.append(f"{idx}. **{name}** - ${price:.2f} {currency}")
        
        if len(products) > limit:
            lines.append(f"... and {len(products) - limit} more")
        
        return "\n".join(lines)

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
