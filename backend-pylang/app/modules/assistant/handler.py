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

            products = self._extract_products(tool_steps, session)
            if intent == "product_search" and not products:
                fallback_products = await self._fallback_search(request.message, session)
                if fallback_products:
                    products = fallback_products
                    lower_text = response_text.lower()
                    if "trouble" in lower_text or ("no" in lower_text and "found" in lower_text):
                        response_text = "Here are some options I found."
                        session.add_message("assistant", response_text)

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
        for name, observation in reversed(steps or []):
            if isinstance(observation, dict) and observation.get("products"):
                return observation.get("products")
        return session.last_shown_products or []

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
            result = await tools.update_cart(
                action="add",
                product_id=item.get("product_id"),
                quantity=item.get("quantity", 1),
                session_id=session.session_id,
                skip_sync=False,
                product_snapshot={
                    "title": item.get("name"),
                    "price": item.get("price"),
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


_handler: Optional[EasymartAssistantHandler] = None


def get_assistant_handler() -> EasymartAssistantHandler:
    global _handler
    if _handler is None:
        _handler = EasymartAssistantHandler()
    return _handler
