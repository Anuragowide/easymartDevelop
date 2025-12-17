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
        session_store: Optional[SessionStore] = None
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
            
            # Call LLM with function calling (LOW temperature for factual responses)
            logger.info(f"[HANDLER] Calling LLM...")
            llm_response = await self.llm_client.chat(
                messages=messages,
                tools=TOOL_DEFINITIONS,
                temperature=0.1,
                max_tokens=512
            )
            logger.info(f"[HANDLER] LLM response received, function_calls: {len(llm_response.function_calls) if llm_response.function_calls else 0}")
            
            # SAFETY CHECK: If product search intent but NO tool calls → LLM hallucinated!
            # Force a tool call to prevent fake products
            if intent == IntentType.PRODUCT_SEARCH and not llm_response.function_calls:
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
                for tool_name, result in tool_results.items():
                    result_str = json.dumps(result)
                    messages.append(Message(
                        role="tool",
                        content=result_str,
                        name=tool_name
                    ))
                
                # Call LLM again to generate final response with tool results
                final_response = await self.llm_client.chat(
                    messages=messages,
                    temperature=0.7,
                    max_tokens=512
                )
                
                # Let LLM generate natural, conversational response
                # Products are already stored in session from tool execution
                assistant_message = final_response.content
                
                logger.info(f"[HANDLER] LLM generated response (length: {len(assistant_message)})")
                logger.info(f"[HANDLER] Tool results: {list(tool_results.keys())}")
            else:
                # No function calls, use content directly
                assistant_message = llm_response.content
            
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
        
        # Add conversation history (last 10 messages for context window)
        for msg in session.messages[-10:]:
            messages.append(Message(
                role=msg["role"],
                content=msg["content"]
            ))
        
        return messages
    
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
