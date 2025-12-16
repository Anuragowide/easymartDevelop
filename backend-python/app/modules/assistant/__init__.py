"""
Easymart Assistant Module

Conversational AI assistant for furniture shopping with:
- Intent detection and entity extraction
- LLM-based conversation (Mistral-7B via Hugging Face)
- Function calling (8 tools)
- Session management
- Product search, specs, cart, policies, contact

Main entry point:
    from app.modules.assistant import get_assistant_handler
    
    handler = get_assistant_handler()
    response = await handler.handle_message(request)
"""

# Core components
from .handler import (
    EasymartAssistantHandler,
    get_assistant_handler,
    AssistantRequest,
    AssistantResponse
)

from .session_store import (
    SessionStore,
    SessionContext,
    get_session_store
)

# LLM and tools
from .hf_llm_client import (
    HuggingFaceLLMClient,
    create_llm_client,
    Message,
    LLMResponse
)

from .tools import (
    EasymartAssistantTools,
    TOOL_DEFINITIONS,
    execute_tool
)

# Intent detection
from .intents import (
    IntentType,
    ProductSearchIntent,
    ProductSpecQAIntent,
    CartAddIntent,
    CartRemoveIntent,
    CartShowIntent,
    ReturnPolicyIntent,
    ShippingInfoIntent,
    ContactInfoIntent
)

from .intent_detector import IntentDetector

# Prompts and config
from .prompts import (
    STORE_INFO,
    POLICIES,
    get_system_prompt,
    get_policy_text,
    get_contact_text,
    get_greeting_message,
    get_clarification_prompt,
    get_empty_results_prompt,
    get_spec_not_found_prompt
)

__all__ = [
    # Main handler
    "EasymartAssistantHandler",
    "get_assistant_handler",
    "AssistantRequest",
    "AssistantResponse",
    
    # Session management
    "SessionStore",
    "SessionContext",
    "get_session_store",
    
    # LLM
    "HuggingFaceLLMClient",
    "create_llm_client",
    "Message",
    "LLMResponse",
    
    # Tools
    "EasymartAssistantTools",
    "TOOL_DEFINITIONS",
    "execute_tool",
    
    # Intents
    "IntentType",
    "ProductSearchIntent",
    "ProductSpecQAIntent",
    "CartAddIntent",
    "CartRemoveIntent",
    "CartShowIntent",
    "ReturnPolicyIntent",
    "ShippingInfoIntent",
    "ContactInfoIntent",
    "IntentDetector",
    
    # Prompts
    "STORE_INFO",
    "POLICIES",
    "get_system_prompt",
    "get_policy_text",
    "get_contact_text",
    "get_greeting_message",
    "get_clarification_prompt",
    "get_empty_results_prompt",
    "get_spec_not_found_prompt",
]
