"""
LLM Provider Selection and Fallback

Creates primary and fallback LLM clients based on settings.
"""

from typing import Optional, List, Dict, Any
from app.core.config import get_settings
from .hf_llm_client import HuggingFaceLLMClient, Message, LLMResponse
from .llm_client import OpenAILLMClient
from ..observability.logging_config import get_logger


logger = get_logger(__name__)


class CompositeLLMClient:
    """
    Primary + fallback LLM client wrapper.
    """
    
    def __init__(
        self,
        primary: Any,
        fallback: Optional[Any],
        primary_name: str,
        fallback_name: Optional[str]
    ):
        self.primary = primary
        self.fallback = fallback
        self.primary_name = primary_name
        self.fallback_name = fallback_name
    
    async def chat(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 512
    ) -> LLMResponse:
        try:
            return await self.primary.chat(
                messages=messages,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens
            )
        except Exception as error:
            logger.warning(
                f"[LLM_PROVIDER] Primary '{self.primary_name}' failed: {error}"
            )
            if not self.fallback:
                raise
            logger.info(
                f"[LLM_PROVIDER] Falling back to '{self.fallback_name}'"
            )
            return await self.fallback.chat(
                messages=messages,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens
            )


def _create_provider_client(provider: str):
    settings = get_settings()
    normalized = (provider or "").strip().lower()
    
    if normalized in {"openai", "gpt", "gpt-4", "gpt-4.1"}:
        return OpenAILLMClient(
            api_key=settings.OPENAI_API_KEY,
            model=settings.OPENAI_MODEL or settings.LLM_MODEL,
            base_url=settings.OPENAI_BASE_URL,
            timeout=settings.OPENAI_TIMEOUT
        )
    
    if normalized in {"mistral", "huggingface", "hf"}:
        return HuggingFaceLLMClient(
            api_key=settings.HUGGINGFACE_API_KEY,
            model=settings.HUGGINGFACE_MODEL,
            base_url=settings.HUGGINGFACE_BASE_URL,
            timeout=settings.HUGGINGFACE_TIMEOUT,
            max_retries=settings.HUGGINGFACE_MAX_RETRIES
        )
    
    raise ValueError(f"Unknown LLM provider: {provider}")


async def create_llm_client(
    primary_provider: Optional[str] = None,
    fallback_provider: Optional[str] = None
) -> CompositeLLMClient:
    settings = get_settings()
    primary = (primary_provider or settings.LLM_PROVIDER_PRIMARY or "openai").lower()
    fallback = (fallback_provider or settings.LLM_PROVIDER_FALLBACK or "").lower()
    
    primary_client = _create_provider_client(primary)
    fallback_client = _create_provider_client(fallback) if fallback else None
    
    return CompositeLLMClient(
        primary=primary_client,
        fallback=fallback_client,
        primary_name=primary,
        fallback_name=fallback or None
    )
