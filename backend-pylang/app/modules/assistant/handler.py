"""
LangChain-based Easymart Assistant Handler
"""

import time
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
from app.modules.assistant.session_store import SessionStore, get_session_store
from app.modules.assistant.prompts import get_system_prompt, get_greeting_message
from app.modules.assistant.tools import get_langchain_tools, CURRENT_SESSION_ID


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

            session.add_message("user", request.message)
            session.add_message("assistant", response_text)

            products = self._extract_products(tool_steps, session)

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
        return {
            "item_count": len(session.cart_items),
            "items": session.cart_items,
            "total": sum(item.get("quantity", 0) for item in session.cart_items)
        }

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


_handler: Optional[EasymartAssistantHandler] = None


def get_assistant_handler() -> EasymartAssistantHandler:
    global _handler
    if _handler is None:
        _handler = EasymartAssistantHandler()
    return _handler
