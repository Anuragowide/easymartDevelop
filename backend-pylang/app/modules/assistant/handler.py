"""
LangChain-based Easymart Assistant Handler
"""

import time
import re
from datetime import datetime
from typing import Dict, Any, List, Optional

from pydantic import BaseModel
import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage

from app.core.config import get_settings
from app.core.analytics import get_analytics
from app.core.error_recovery import get_error_recovery
from app.core.exceptions import EasymartException
from app.modules.assistant.intent_detector import IntentDetector
from app.modules.assistant.intents import IntentType
from app.modules.assistant.session_store import SessionStore, get_session_store
from app.modules.assistant.filter_validator import FilterValidator
from app.modules.assistant.prompts import get_system_prompt, get_greeting_message
from app.modules.assistant.tools import get_langchain_tools, CURRENT_SESSION_ID, get_assistant_tools
from app.modules.assistant.bundle_planner import parse_bundle_request
from app.modules.assistant.intelligent_context import get_intelligent_context_handler


class AssistantRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None


class AssistantResponse(BaseModel):
    message: str
    session_id: str
    products: List[Dict[str, Any]] = []
    cart_summary: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = {}
    actions: List[Dict[str, Any]] = []


class EasymartAssistantHandler:
    def __init__(self, session_store: Optional[SessionStore] = None):
        self.settings = get_settings()
        self.session_store = session_store or get_session_store()
        self.intent_detector = IntentDetector()
        self.filter_validator = FilterValidator()
        self.tools = get_langchain_tools()
        self.system_prompt = get_system_prompt()
        self.intelligent_context = get_intelligent_context_handler()

        self.llm = ChatOpenAI(
            api_key=self.settings.OPENAI_API_KEY,
            model=self.settings.OPENAI_MODEL or self.settings.LLM_MODEL,
            base_url=self.settings.OPENAI_BASE_URL,
            temperature=self.settings.LLM_TEMPERATURE,
            timeout=self.settings.OPENAI_TIMEOUT,
            max_tokens=self.settings.LLM_MAX_TOKENS,
        )
        self.tool_llm = self.llm.bind_tools(self.tools)
        self.tool_map = {tool.name: tool for tool in self.tools}

    async def handle_message(self, request: AssistantRequest) -> AssistantResponse:
        analytics = get_analytics()
        error_recovery = get_error_recovery()

        start_time = time.time()
        session = self.session_store.get_or_create_session(
            session_id=request.session_id,
            user_id=request.user_id
        )

        if self._is_bundle_confirm_message(request.message):
            response = await self._handle_bundle_confirmation(session)
            if response:
                return response

        if self._is_add_bundle_request(request.message):
            bundle_total = session.metadata.get("last_bundle_total")
            if bundle_total and bundle_total >= self.settings.BUNDLE_CONFIRM_THRESHOLD:
                session.set_pending_clarification(
                    vague_type="bundle_confirm",
                    partial_entities={"total": bundle_total},
                    original_query=request.message
                )
                response_text = f"This bundle totals about ${bundle_total:.2f}. Would you like me to add it to your cart?"
                session.add_message("assistant", response_text)
                return AssistantResponse(
                    message=response_text,
                    session_id=session.session_id,
                    products=[],
                    cart_summary=self._build_cart_summary(session),
                    metadata={"intent": "clarification_needed"}
                )

            response = await self._handle_bundle_add(session)
            if response:
                return response

        self._maybe_apply_bundle_context(session, request)
        self._update_shopping_brief(session, request.message)
        
        # INTELLIGENT CONTEXT RECOVERY: Use LLM to understand if this is a follow-up query
        request.message = await self._intelligent_context_recovery(session, request.message)
        
        # RESOLVE PRODUCT REFERENCES (option 1, first one, etc.)
        resolved_message = self._resolve_product_references(session, request.message)
        if resolved_message != request.message:
            request.message = resolved_message

        last_bundle = session.metadata.get("last_bundle_request")
        if last_bundle:
            message_lower = request.message.lower().strip()
            refinement_phrases = [
                "more option", "more options", "other option", "other options",
                "different option", "different options", "more choices", "another option",
                "another one", "show more", "more like this"
            ]
            if any(phrase in message_lower for phrase in refinement_phrases):
                request.message = f"{last_bundle.get('request', '')} {request.message}"

        # Space-aware clarification
        if self._needs_space_dimensions(request.message):
            session.set_pending_clarification(
                vague_type="space_required",
                partial_entities={"original_query": request.message},
                original_query=request.message
            )
            response_text = "What is the available space? Please share length and width in cm (e.g., 120 x 60 cm)."
            session.add_message("assistant", response_text)
            return AssistantResponse(
                message=response_text,
                session_id=session.session_id,
                products=[],
                cart_summary=self._build_cart_summary(session),
                metadata={"intent": "clarification_needed"}
            )

        # Vague query handling
        vague = self.intent_detector.detect_vague_patterns(request.message)
        if vague:
            session.set_pending_clarification(
                vague_type=vague["vague_type"],
                partial_entities=vague.get("partial_entities", {}),
                original_query=request.message
            )
            response_text = (
                "I can help with furniture, fitness gear, scooters, and pet products. "
                "What type of item are you looking for?"
            )
            session.add_message("assistant", response_text)
            return AssistantResponse(
                message=response_text,
                session_id=session.session_id,
                products=[],
                cart_summary=self._build_cart_summary(session),
                metadata={"intent": "clarification_needed"}
            )

        # Resolve pending clarification if present
        pending = session.get_pending_clarification()
        if pending:
            if pending.get("vague_type") == "space_required":
                dims = self._extract_space_dimensions(request.message)
                if dims:
                    request.message = f"{pending.get('original_query', '')} {dims['length']} x {dims['width']} cm"
                    session.clear_pending_clarification()
                else:
                    response_text = "Please share the space length and width in cm (e.g., 120 x 60 cm)."
                    session.add_message("assistant", response_text)
                    return AssistantResponse(
                        message=response_text,
                        session_id=session.session_id,
                        products=[],
                        cart_summary=self._build_cart_summary(session),
                        metadata={"intent": "clarification_needed"}
                    )

            if pending.get("vague_type") == "filter_clarification":
                original_query = pending.get("original_query", "")
                if original_query:
                    request.message = f"{original_query} {request.message}".strip()
                session.clear_pending_clarification()

            if pending.get("vague_type") == "bundle_confirm":
                if self._is_confirmation_response(request.message):
                    session.clear_pending_clarification()
                    response = await self._handle_bundle_add(session)
                    if response:
                        return response
                else:
                    session.clear_pending_clarification()
                    response_text = "No problem. Let me know if you want another bundle or changes."
                    session.add_message("assistant", response_text)
                    return AssistantResponse(
                        message=response_text,
                        session_id=session.session_id,
                        products=[],
                        cart_summary=self._build_cart_summary(session),
                        metadata={"intent": "clarification_needed"}
                    )

            merged = self.intent_detector.merge_clarification_response(
                pending.get("partial_entities", {}),
                request.message,
                pending.get("vague_type", "")
            )
            request.message = merged.get("query", request.message)
            session.clear_pending_clarification()

        # Off-topic guard
        intent = self.intent_detector.detect(
            request.message,
            current_product=session.current_product,
            last_shown_products=session.last_shown_products
        ).value
        if intent == "out_of_scope":
            response_text = (
                "I'm Easymart's shopping assistant. I can help you find furniture, fitness gear, scooters, or pet products. "
                "What are you shopping for today?"
            )
            session.add_message("assistant", response_text)
            return AssistantResponse(
                message=response_text,
                session_id=session.session_id,
                products=[],
                cart_summary=self._build_cart_summary(session),
                metadata={"intent": "out_of_scope"}
            )

        # Force bundle handling for multi-item requests
        bundle_items, _ = parse_bundle_request(request.message)
        if len(bundle_items) >= 2:
            request.message = f"Please use build_bundle. {request.message}"

        # Clarify if filters are too weak for product search
        if intent == "product_search":
            entities = self.intent_detector.extract_entities(request.message, IntentType.PRODUCT_SEARCH)
            is_valid, _, message = self.filter_validator.validate_filter_count(entities, request.message)
            if not is_valid and not self.filter_validator.is_bypass_phrase(request.message):
                session.set_pending_clarification(
                    vague_type="filter_clarification",
                    partial_entities=entities,
                    original_query=request.message
                )
                session.add_message("assistant", message)
                return AssistantResponse(
                    message=message,
                    session_id=session.session_id,
                    products=[],
                    cart_summary=self._build_cart_summary(session),
                    metadata={"intent": "clarification_needed"}
                )

        if self.settings.TEST_MODE:
            response_text = "Test mode is enabled. How can I help you shop today?"
            session.add_message("user", request.message)
            session.add_message("assistant", response_text)
            return AssistantResponse(
                session_id=session.session_id,
                message=response_text,
                products=[],
                actions=[],
                cart_summary=self._build_cart_summary(session),
                metadata={"intent": intent, "test_mode": True}
            )

        try:
            history = session.to_langchain_messages(limit=10)
            token = CURRENT_SESSION_ID.set(session.session_id)
            try:
                response_text, tool_steps = await self._run_tool_loop(request.message, history)
            finally:
                CURRENT_SESSION_ID.reset(token)

            response_text = (response_text or "").strip()
            if not response_text:
                response_text = error_recovery.get_fallback_message(intent=intent)

            bundle_feedback = self._summarize_bundle_feedback(tool_steps)
            if bundle_feedback:
                response_text = f"{response_text}\n\n{bundle_feedback}".strip()

            session.add_message("user", request.message)
            session.add_message("assistant", response_text)

            # INTELLIGENT CLARIFICATION DETECTION: Use LLM to understand if response is asking for clarification
            clarification_analysis = await self.intelligent_context.analyze_response_type(
                response_text, request.message
            )
            
            if clarification_analysis["is_clarification"] and not clarification_analysis["is_showing_products"]:
                # Don't extract or show products for clarification responses
                products = []
                # Save shopping context for follow-up recovery
                self._save_shopping_context(session, request.message)
            else:
                products = self._extract_products(tool_steps, session)
                # Clear shopping context when we have a successful non-clarification response
                self._clear_shopping_context(session)
                if intent == "product_search" and not products:
                    fallback_products = await self._fallback_search(request.message, session)
                    if fallback_products:
                        products = fallback_products
                        lower_text = response_text.lower()
                        if "trouble" in lower_text or ("no" in lower_text and "found" in lower_text):
                            response_text = "Here are some options I found."
                            session.add_message("assistant", response_text)
                
                # Deduplicate products to avoid showing similar items
                products = self._deduplicate_products(products)

            response_time_ms = (time.time() - start_time) * 1000

            return AssistantResponse(
                session_id=session.session_id,
                message=response_text,
                products=products if products else [],
                actions=[],
                cart_summary=self._build_cart_summary(session),
                metadata={
                    "intent": intent,
                    "processing_time_ms": round(response_time_ms, 2),
                    "timestamp": datetime.utcnow().isoformat(),
                    "function_calls_made": len(tool_steps)
                }
            )

        except EasymartException as e:
            analytics.track_error("easymart_exception", str(e))
            recovery = error_recovery.handle_error("tool_failure", {"query": request.message})
            return AssistantResponse(
                session_id=session.session_id,
                message=recovery.get("message"),
                products=[],
                cart_summary=self._build_cart_summary(session),
                metadata={"intent": "error", "error": e.message}
            )
        except Exception as e:
            analytics.track_error("internal_error", str(e))
            recovery = error_recovery.handle_error("tool_failure", {"query": request.message})
            return AssistantResponse(
                session_id=session.session_id,
                message=recovery.get("message"),
                products=[],
                cart_summary=self._build_cart_summary(session),
                metadata={"intent": "error", "error": str(e)}
            )

    async def get_greeting(self, session_id: Optional[str] = None) -> AssistantResponse:
        session = self.session_store.get_or_create_session(session_id=session_id)
        greeting = get_greeting_message()
        session.add_message("assistant", greeting)
        return AssistantResponse(
            message=greeting,
            session_id=session.session_id,
            metadata={"type": "greeting"}
        )

    async def clear_session(self, session_id: str):
        self.session_store.delete_session(session_id)

    def _extract_products(self, steps, session) -> List[Dict[str, Any]]:
        # Define non-product tools that should never show product cards
        NON_PRODUCT_TOOLS = {
            "get_policy_info",
            "get_contact_info", 
            "calculate_shipping",
            "update_cart"  # Cart operations show cart summary, not product cards
        }
        
        # If only non-product tools were called, don't show any products
        if steps:
            tool_names = [name for name, _ in steps]
            if tool_names and all(name in NON_PRODUCT_TOOLS for name in tool_names):
                return []
        
        # Special handling for single-product detail tools FIRST
        # When user asks about a specific product, return ONLY that product
        for name, observation in reversed(steps or []):
            if name == "get_product_specs" and isinstance(observation, dict):
                product_id = observation.get("product_id")
                if product_id and session.last_shown_products:
                    # Find and return only the specific product being asked about
                    for product in session.last_shown_products:
                        if product.get("sku") == product_id or product.get("id") == product_id:
                            return [product]  # Return ONLY this product
                # If not in last_shown, don't return any product cards
                return []
            
            # For compare_products, return only the products being compared
            if name == "compare_products" and isinstance(observation, dict):
                compared_products = observation.get("products", [])
                if compared_products:
                    return compared_products
                # Fall back to finding them in session
                product_ids = observation.get("product_ids", [])
                if product_ids and session.last_shown_products:
                    return [p for p in session.last_shown_products 
                           if p.get("sku") in product_ids or p.get("id") in product_ids]
                return []
        
        # Check for products in tool responses (search, similar, bundle, etc.)
        for name, observation in reversed(steps or []):
            if isinstance(observation, dict) and observation.get("products"):
                return observation.get("products")
        
        # If no tools were called or no product-specific results, don't show old products
        # Only return last_shown_products if there were actual product-related tool calls
        if not steps:
            return []
            
        return []

    def _build_cart_summary(self, session) -> Optional[Dict[str, Any]]:
        if not session.cart_items:
            return None
        total_price = 0.0
        for item in session.cart_items:
            price = item.get("price")
            qty = item.get("quantity", 0)
            if price is not None:
                total_price += float(price) * qty
        return {
            "item_count": len(session.cart_items),
            "items": session.cart_items,
            "total": total_price
        }

    def _summarize_bundle_feedback(self, steps) -> Optional[str]:
        for name, observation in reversed(steps or []):
            if name in ["build_bundle", "build_cheapest_bundle"] and isinstance(observation, dict):
                bundle = observation.get("bundle") or {}
                if not bundle:
                    continue
                if not bundle.get("feasible") and bundle.get("budget_total") is not None:
                    min_total = bundle.get("min_total_estimate")
                    budget = bundle.get("budget_total")
                    if min_total and min_total > budget:
                        return (
                            f"That budget looks too tight for the requested quantities. "
                            f"The lowest possible total I found is about ${min_total:.2f}."
                        )
                break
        return None

    def _needs_space_dimensions(self, message: str) -> bool:
        message_lower = message.lower()
        has_space = any(phrase in message_lower for phrase in [
            "small space", "limited space", "tight space", "small room", "compact space"
        ])
        wants_table = any(word in message_lower for word in ["table", "desk"])
        has_dimensions = self._extract_space_dimensions(message) is not None
        return has_space and wants_table and not has_dimensions

    def _extract_space_dimensions(self, message: str) -> Optional[Dict[str, float]]:
        match = re.search(
            r'(\d+(?:\.\d+)?)\s*(?:cm)?\s*(?:x|by)\s*(\d+(?:\.\d+)?)\s*cm',
            message.lower()
        )
        if not match:
            return None
        return {"length": float(match.group(1)), "width": float(match.group(2))}

    def _update_shopping_brief(self, session, message: str) -> None:
        intent = self.intent_detector.detect(
            message,
            current_product=session.current_product,
            last_shown_products=session.last_shown_products
        ).value
        entities = self.intent_detector.extract_entities(message, intent=intent) if message else {}
        brief = session.metadata.get("shopping_brief", {})

        for key in ["category", "color", "material", "style", "room_type", "price_max", "descriptor", "size"]:
            if entities.get(key):
                brief[key] = entities[key]

        if entities.get("query"):
            brief["last_query"] = entities["query"]
        if entities.get("space_length") and entities.get("space_width"):
            brief["space_length"] = entities["space_length"]
            brief["space_width"] = entities["space_width"]

        bundle_items, _ = parse_bundle_request(message)
        if len(bundle_items) >= 2:
            brief["bundle_items"] = [
                {"type": item.item_type, "quantity": item.quantity}
                for item in bundle_items
            ]

        if brief:
            session.metadata["shopping_brief"] = brief

    def _maybe_apply_bundle_context(self, session, request: AssistantRequest) -> None:
        brief = session.metadata.get("shopping_brief", {})
        bundle_items = brief.get("bundle_items")
        if not bundle_items:
            return

        message_lower = request.message.lower()
        has_budget = any(token in message_lower for token in ["under", "budget", "max", "maximum"])
        has_item_words = any(word in message_lower for word in ["chair", "table", "desk", "sofa", "bed"])
        if has_budget and not has_item_words:
            items_text = " and ".join(
                f"{item['quantity']} {item['type']}" for item in bundle_items
            )
            request.message = f"{items_text} {request.message}".strip()

        if self._is_bundle_refine_request(request.message):
            items_text = " and ".join(
                f"{item['quantity']} {item['type']}" for item in bundle_items
            )
            request.message = f"{items_text} {request.message}".strip()

    def _is_add_bundle_request(self, message: str) -> bool:
        message_lower = message.lower()
        bundle_phrases = [
            "add this bundle to cart",
            "add bundle to cart",
            "add the bundle to cart",
            "add this bundle",
            "add the bundle",
            "add bundle",
            "add all to cart",
            "add all items",
            # Handle common typos
            "add this bundell",
            "add this bundel",
            "add the bundell",
            "add the bundel",
            "add bundell",
            "add bundel",
        ]
        return any(phrase in message_lower for phrase in bundle_phrases)

    def _is_bundle_confirm_message(self, message: str) -> bool:
        return self._is_confirmation_response(message)

    def _is_confirmation_response(self, message: str) -> bool:
        message_lower = message.lower().strip()
        yes_phrases = ["yes", "yep", "yeah", "confirm", "ok", "okay", "please do", "go ahead"]
        no_phrases = ["no", "nope", "don't", "do not", "cancel", "stop"]
        if any(phrase == message_lower for phrase in yes_phrases):
            return True
        if any(phrase == message_lower for phrase in no_phrases):
            return False
        if any(phrase in message_lower for phrase in yes_phrases):
            return True
        return False

    async def _handle_bundle_confirmation(self, session) -> Optional[AssistantResponse]:
        pending = session.get_pending_clarification()
        if not pending or pending.get("vague_type") != "bundle_confirm":
            return None
        session.clear_pending_clarification()
        return await self._handle_bundle_add(session)

    async def _handle_bundle_add(self, session) -> Optional[AssistantResponse]:
        bundle_items = session.metadata.get("last_bundle_items") or []
        if not bundle_items:
            response_text = "I don’t have a recent bundle yet. Which bundle should I add to your cart?"
            session.add_message("assistant", response_text)
            return AssistantResponse(
                message=response_text,
                session_id=session.session_id,
                products=[],
                cart_summary=self._build_cart_summary(session),
                metadata={"intent": "clarification_needed"}
            )

        tools = get_assistant_tools()
        added = []
        failed = []
        for item in bundle_items:
            # Fix: bundle items store 'unit_price', not 'price'
            price = item.get("price") or item.get("unit_price")
            result = await tools.update_cart(
                action="add",
                product_id=item.get("product_id"),
                quantity=item.get("quantity", 1),
                session_id=session.session_id,
                skip_sync=False,
                product_snapshot={
                    "title": item.get("name"),
                    "price": price,
                    "image_url": item.get("image_url"),
                }
            )
            if result.get("success"):
                added.append(item)
            else:
                failed.append({
                    "product_id": item.get("product_id"),
                    "name": item.get("name"),
                    "quantity": item.get("quantity", 1),
                    "error": result.get("error")
                })

        response_text = f"Added {len(added)} bundle items to your cart."
        if failed:
            response_text += f" {len(failed)} items could not be added."
        if failed and len(failed) == len(bundle_items):
            response_text = "I couldn’t add the bundle items to your cart. Want me to try a different bundle?"
        session.add_message("assistant", response_text)
        return AssistantResponse(
            message=response_text,
            session_id=session.session_id,
            products=[],
            cart_summary=self._build_cart_summary(session),
            metadata={
                "intent": "cart_add_bundle",
                "bundle_add_results": {
                    "added": added,
                    "failed": failed
                }
            }
        )

    def _is_bundle_refine_request(self, message: str) -> bool:
        message_lower = message.lower()
        refine_phrases = [
            "make it", "prefer", "instead", "change to", "switch to",
            "in red", "in blue", "in black", "in white", "red", "blue", "black", "white",
            "more options", "another bundle", "different bundle", "new bundle"
        ]
        return any(phrase in message_lower for phrase in refine_phrases)

    def _is_clarification_response(self, response_text: str) -> bool:
        """
        Detect if the LLM response is asking a clarification question.
        If so, we should NOT show products alongside the question.
        """
        if not response_text:
            return False
        
        response_lower = response_text.lower()
        
        # Check if response has a numbered/bulleted product list (indicates it's showing products, not asking for clarification)
        has_product_listing = any(marker in response_text for marker in ["\n1.", "\n2.", "\n3."])
        
        # If it has a product listing, it's NOT a clarification
        if has_product_listing:
            return False
        
        # Common clarification question patterns
        clarification_patterns = [
            "could you specify",
            "could you tell me",
            "could you clarify",
            "which items",
            "which ones",
            "what type",
            "what kind",
            "what size",
            "what color",
            "what material",
            "what style",
            "let me know which",
            "please specify",
            "please tell me",
            "which essential items",
            "which of these",
            "do you want",
            "would you like",
            "do you prefer",
            "do you need",
            "are you looking for",
            "what are you looking for",
            "can you tell me more",
            "help me understand",
            "common starter supplies",
            "common items include",
            "things like",
        ]
        
        # Check for question mark + clarification patterns
        has_question = "?" in response_text
        has_clarification_phrase = any(pattern in response_lower for pattern in clarification_patterns)
        
        # CRITICAL FIX: Only treat as clarification if it has BOTH a question mark AND a clarification phrase
        # Product listings with numbered lists (1. Product A, 2. Product B) should NOT be treated as clarifications
        # even if they have a follow-up question like "Would you like to see more?"
        #
        # True clarifications: "Which items do you need? \n- Cat bed\n- Litter box"
        # NOT clarifications: "Here are some chairs:\n1. Chair A\n2. Chair B\nWould you like more?"
        return has_question and has_clarification_phrase
    
    def _save_shopping_context(self, session, user_message: str) -> None:
        """
        Save the user's shopping request as context for follow-up responses.
        Called when the assistant asks a clarification question.
        """
        # Don't overwrite if we already have context from this conversation
        existing_context = session.metadata.get("shopping_context")
        if existing_context:
            return
        
        # Store the original query that triggered clarification
        session.metadata["shopping_context"] = {
            "original_query": user_message,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _clear_shopping_context(self, session) -> None:
        """Clear shopping context after successful response."""
        if "shopping_context" in session.metadata:
            del session.metadata["shopping_context"]
    
    async def _intelligent_context_recovery(self, session, user_message: str) -> str:
        """
        Use LLM to intelligently determine if user message needs previous shopping context.
        This replaces hardcoded pattern matching with intelligent understanding.
        
        Examples:
        - "give me bundle" after "puppy supplies $250" → combines them
        - "show me office chairs" after "puppy supplies" → independent query, no combination
        - "yes" after asking which items → combines with previous context
        """
        shopping_context = session.metadata.get("shopping_context")
        if not shopping_context:
            return user_message
        
        original_query = shopping_context.get("original_query", "")
        if not original_query:
            return user_message
        
        # Get recent conversation for context
        recent_conversation = []
        if hasattr(session, 'messages'):
            recent_conversation = [
                {"role": msg.get("role"), "content": msg.get("content")}
                for msg in session.messages[-6:]  # Last 3 exchanges
            ]
        
        # Use intelligent context handler to analyze
        analysis = await self.intelligent_context.should_apply_previous_context(
            current_message=user_message,
            previous_shopping_context=original_query,
            recent_conversation=recent_conversation
        )
        
        if analysis.get("needs_context"):
            # Clear context after using it
            self._clear_shopping_context(session)
            return analysis.get("combined_query", user_message)
        
        return user_message
    
    def _recover_shopping_context(self, session, user_message: str) -> str:
        """
        DEPRECATED: Old hardcoded pattern-based context recovery.
        Kept for backward compatibility. Use _intelligent_context_recovery instead.
        
        Check if the user's message is a short follow-up response and recover
        the original shopping context if present.
        
        Examples of short follow-ups:
        - "give me bundle" → "puppy supplies $250, give me bundle"
        - "just pick for me" → "puppy supplies $250, just pick for me"
        - "you choose" → "puppy supplies $250, you choose"
        """
        shopping_context = session.metadata.get("shopping_context")
        if not shopping_context:
            return user_message
        
        original_query = shopping_context.get("original_query", "")
        if not original_query:
            return user_message
        
        # Check if current message is a short follow-up response
        message_lower = user_message.lower().strip()
        
        # Short follow-up patterns that indicate user wants to proceed with previous context
        follow_up_patterns = [
            "give me bundle",
            "give me a bundle", 
            "make me a bundle",
            "create a bundle",
            "build a bundle",
            "bundle please",
            "just bundle",
            "bundle it",
            "just pick",
            "pick for me",
            "just pick for me",
            "you pick",
            "you choose",
            "choose for me",
            "just choose",
            "surprise me",
            "your choice",
            "go ahead",
            "yes please",
            "yes",
            "yes bundle",
            "ok",
            "okay",
            "sure",
            "sounds good",
            "let's do it",
            "do it",
            "proceed",
            "all of them",
            "all of it",
            "everything",
            "the works",
            "whatever you think",
            "what you recommend",
            "your recommendation",
        ]
        
        # Check if current message matches any follow-up pattern
        is_follow_up = any(pattern in message_lower for pattern in follow_up_patterns)
        
        # Also check if it's a very short message (3 words or less) that could be a follow-up
        word_count = len(message_lower.split())
        is_short = word_count <= 4
        
        # Check for bundle-related keywords in short messages
        bundle_keywords = ["bundle", "pick", "choose", "yes", "ok", "sure", "go", "proceed"]
        has_bundle_keyword = any(kw in message_lower for kw in bundle_keywords)
        
        if is_follow_up or (is_short and has_bundle_keyword):
            # Combine original context with the follow-up response
            combined_message = f"{original_query}, {user_message}"
            # Clear context after using it
            self._clear_shopping_context(session)
            return combined_message
        
        return user_message
    
    def _deduplicate_products(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate/similar products to avoid showing essentially the same item multiple times.
        Products are considered duplicates if they have:
        - Same base name (ignoring quantity/size variations like '200pcs' vs '400pcs')
        - Same category
        """
        if not products:
            return []
        
        seen_base_names = set()
        unique_products = []
        
        for product in products:
            name = product.get("name") or product.get("title") or ""
            
            # Normalize the name: remove quantities, sizes, and common variations
            base_name = self._get_base_product_name(name)
            
            if base_name and base_name not in seen_base_names:
                seen_base_names.add(base_name)
                unique_products.append(product)
        
        return unique_products
    
    def _get_base_product_name(self, name: str) -> str:
        """
        Extract the base product name by removing quantity/size/variant variations.
        E.g., '200pcs Puppy Dog Pet Training Pads' -> 'puppy dog pet training pads'
        E.g., 'Dog Bed Large Orthopedic' -> 'dog bed orthopedic'
        E.g., 'Dog Bed Small Washable' -> 'dog bed washable' 
        Then further normalize to catch 'dog bed' as the core type.
        """
        import re
        
        name_lower = name.lower()
        
        # Remove quantity patterns like "200pcs", "400 pcs", "1 x", "2x", etc.
        name_lower = re.sub(r'\b\d+\s*(?:pcs?|pieces?|pack|count|x|units?)\b', '', name_lower)
        
        # Remove size patterns like "small", "medium", "large", "xl", "xxl", etc.
        name_lower = re.sub(r'\b(?:x?x?small|x?x?large|medium|mini|big|huge|tiny|xl|xxl|xs|xxs)\b', '', name_lower)
        
        # Remove standalone size letters only when they appear as size indicators
        name_lower = re.sub(r'\b[sml]\b', '', name_lower)
        
        # Remove dimension patterns like "60x90cm", "100cm", etc.
        name_lower = re.sub(r'\b\d+\s*x\s*\d+\s*(?:cm|mm|m|inch|in|ft)?\b', '', name_lower)
        name_lower = re.sub(r'\b\d+\s*(?:cm|mm|m|inch|in|ft)\b', '', name_lower)
        
        # Remove variant descriptors that don't change the core product type
        name_lower = re.sub(r'\b(?:orthopedic|washable|waterproof|foldable|portable|deluxe|premium|basic|standard|pro|plus)\b', '', name_lower)
        
        # Remove color patterns
        name_lower = re.sub(r'\b(?:black|white|red|blue|green|yellow|pink|purple|grey|gray|brown|beige|orange|navy|cream)\b', '', name_lower)
        
        # Remove leading/trailing whitespace and normalize spaces
        name_lower = re.sub(r'\s+', ' ', name_lower).strip()
        
        return name_lower

    async def _run_tool_loop(self, message: str, history):
        messages = [SystemMessage(content=self.system_prompt)] + history + [HumanMessage(content=message)]
        tool_steps = []

        for _ in range(3):
            ai_msg = await self.tool_llm.ainvoke(messages)
            messages.append(ai_msg)

            tool_calls = getattr(ai_msg, "tool_calls", None) or []
            if not tool_calls:
                return ai_msg.content, tool_steps

            for call in tool_calls:
                call_name = call.get("name") or call.get("function", {}).get("name")
                call_args = call.get("args") or call.get("function", {}).get("arguments") or {}
                call_id = call.get("id") or call.get("tool_call_id") or call.get("function", {}).get("id") or call_name

                if isinstance(call_args, str):
                    try:
                        call_args = json.loads(call_args)
                    except json.JSONDecodeError:
                        call_args = {}

                tool = self.tool_map.get(call_name)
                if tool is None:
                    result = {"error": f"Unknown tool: {call_name}"}
                else:
                    result = await tool.ainvoke(call_args)

                # DEBUG: Log tool results
                print(f"[DEBUG] Tool '{call_name}' args: {call_args}")
                if isinstance(result, dict):
                    if result.get("no_color_match"):
                        print(f"[DEBUG] no_color_match=True, available_colors={result.get('available_colors')}")
                    elif result.get("products"):
                        print(f"[DEBUG] Got {len(result['products'])} products")
                    else:
                        print(f"[DEBUG] Result keys: {result.keys()}")

                tool_steps.append((call_name, result))
                messages.append(ToolMessage(content=json.dumps(result), tool_call_id=call_id))

        return "", tool_steps

    async def _fallback_search(self, message: str, session) -> List[Dict[str, Any]]:
        entities = self.intent_detector.extract_entities(message, IntentType.PRODUCT_SEARCH)
        query = entities.get("query") or message
        token = CURRENT_SESSION_ID.set(session.session_id)
        try:
            result = await get_assistant_tools().search_products(
                query=query,
                category=entities.get("category"),
                material=entities.get("material"),
                style=entities.get("style"),
                room_type=entities.get("room_type"),
                color=entities.get("color"),
                price_max=entities.get("price_max"),
                limit=self.settings.SEARCH_LIMIT_DEFAULT
            )
        finally:
            CURRENT_SESSION_ID.reset(token)

        if isinstance(result, dict) and result.get("products"):
            return result.get("products")
        return []
    
    def _resolve_product_references(self, session, message: str) -> str:
        """
        Resolve product references like "option 1", "first one", "the second chair" 
        to actual product SKUs before sending to LLM.
        
        Examples:
        - "tell me about option 1" -> "tell me about product 'Artiss Office Chair' (SKU: SKU-CHAIR-001)"
        - "add the first one to cart" -> "add product 'Artiss Office Chair' (SKU: SKU-CHAIR-001) to cart"
        - "add 2 and 3 to cart" -> "add product 'X' (SKU: SKU-X) and product 'Y' (SKU: SKU-Y) to cart"
        """
        if not session.last_shown_products:
            return message
        
        # Patterns to detect product references (in priority order)
        patterns = [
            # "option 1", "item 2", "product 3"
            (r'\b(?:option|choice|item|product|number)\s+(\d+)', 'index'),
            # "first one", "second chair"
            (r'\b(first|second|third|fourth|fifth)\s+(?:one|option|choice|item|chair|table|desk|product)?', 'index'),
            # "1st one", "2nd option"
            (r'\b(1st|2nd|3rd|4th|5th)\s+(?:one|option|choice|item|chair|table|desk|product)?', 'index'),
            # "the 2nd one"
            (r'\b(?:the\s+)?(\d+)(?:st|nd|rd|th)\s+(?:one|option|chair|table|desk|product)?', 'index'),
            # Standalone numbers in cart/add context: "add 2 and 3", "2 and 3 to cart"
            # Match numbers that appear to be product references (not prices or quantities)
            (r'\badd\s+(\d+)\b(?!\s*(?:to|x|items?|of))', 'index'),
            (r'\b(\d+)\s+(?:and|,)\s*(\d+)\s+(?:option|to\s+cart|to\s+my\s+cart)', 'multi_index'),
            # "2 option" (number before option)
            (r'\b(\d+)\s+option', 'index'),
        ]
        
        # Find all matches with their positions and resolved values
        replacements = []
        
        for pattern, ref_type in patterns:
            for match in re.finditer(pattern, message, re.IGNORECASE):
                if ref_type == 'multi_index':
                    # Handle "2 and 3" pattern - resolve both numbers
                    ref1, ref2 = match.group(1), match.group(2)
                    
                    # Skip if this span overlaps with an existing match
                    if any(match.start() < r[1] and match.end() > r[0] for r in replacements):
                        continue
                    
                    product_id1 = session.resolve_product_reference(ref1, 'index')
                    product_id2 = session.resolve_product_reference(ref2, 'index')
                    
                    if product_id1 and product_id2:
                        product1 = next((p for p in session.last_shown_products if p.get('id') == product_id1 or p.get('sku') == product_id1), None)
                        product2 = next((p for p in session.last_shown_products if p.get('id') == product_id2 or p.get('sku') == product_id2), None)
                        
                        if product1 and product2:
                            name1 = product1.get('name') or product1.get('title', '')
                            name2 = product2.get('name') or product2.get('title', '')
                            replacement_text = f"product '{name1}' (SKU: {product_id1}) and product '{name2}' (SKU: {product_id2}) option"
                            replacements.append((match.start(), match.end(), replacement_text))
                else:
                    reference = match.group(1)
                    
                    # Skip if this span overlaps with an existing match
                    if any(match.start() < r[1] and match.end() > r[0] for r in replacements):
                        continue
                    
                    # Resolve the reference
                    product_id = session.resolve_product_reference(reference, 'index')
                    
                    if product_id:
                        # Find the product details
                        product = next(
                            (p for p in session.last_shown_products 
                             if p.get('id') == product_id or p.get('sku') == product_id),
                            None
                        )
                        
                        if product:
                            product_name = product.get('name') or product.get('title', '')
                            replacement_text = f"product '{product_name}' (SKU: {product_id})"
                            replacements.append((match.start(), match.end(), replacement_text))
        
        # Sort by position (reverse order) to replace from end to start
        replacements.sort(reverse=True)
        
        # Apply replacements
        resolved_message = message
        for start, end, replacement_text in replacements:
            resolved_message = resolved_message[:start] + replacement_text + resolved_message[end:]
        
        return resolved_message


_handler: Optional[EasymartAssistantHandler] = None


def get_assistant_handler() -> EasymartAssistantHandler:
    global _handler
    if _handler is None:
        _handler = EasymartAssistantHandler()
    return _handler
