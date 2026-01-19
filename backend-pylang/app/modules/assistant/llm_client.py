"""
LLM Client

OpenAI GPT client with function calling support.
"""

from typing import List, Dict, Any, Optional
import json
import logging
from openai import AsyncOpenAI

from app.core.config import get_settings
from .hf_llm_client import Message, FunctionCall, LLMResponse


logger = logging.getLogger(__name__)


class OpenAILLMClient:
    """
    OpenAI GPT client with tool calling support.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: int = 2
    ):
        settings = get_settings()
        self.api_key = api_key or settings.OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY not found in environment or parameters")
        
        self.model = model or settings.OPENAI_MODEL or settings.LLM_MODEL
        self.timeout = timeout or settings.OPENAI_TIMEOUT or settings.LLM_TIMEOUT
        
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url=base_url or settings.OPENAI_BASE_URL,
            timeout=self.timeout,
            max_retries=max_retries
        )
    
    async def chat(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 512
    ) -> LLMResponse:
        oa_messages = []
        
        for msg in messages:
            role = msg.role
            content = msg.content
            
            # Treat tool results as user messages for compatibility with existing flow
            if role == "tool":
                role = "user"
            
            oa_messages.append({"role": role, "content": content})
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=oa_messages,
            tools=tools or None,
            tool_choice="auto" if tools else None,
            temperature=temperature,
            max_tokens=max_tokens
        )
        
        choice = response.choices[0]
        response_message = choice.message
        content = response_message.content or ""
        function_calls: List[FunctionCall] = []
        
        if response_message.tool_calls:
            for tool_call in response_message.tool_calls:
                if tool_call.type != "function":
                    continue
                args = {}
                if tool_call.function.arguments:
                    try:
                        args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        logger.warning("Failed to parse OpenAI tool arguments; using empty dict")
                        args = {}
                function_calls.append(
                    FunctionCall(name=tool_call.function.name, arguments=args)
                )
        
        return LLMResponse(
            content=content,
            function_calls=function_calls,
            finish_reason=choice.finish_reason or "stop"
        )


async def create_openai_client(
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> OpenAILLMClient:
    settings = get_settings()
    return OpenAILLMClient(
        api_key=api_key or settings.OPENAI_API_KEY,
        model=model or settings.OPENAI_MODEL or settings.LLM_MODEL,
        base_url=settings.OPENAI_BASE_URL,
        timeout=settings.OPENAI_TIMEOUT
    )
