"""
Hugging Face LLM Client

Client for Vicuna-7B via Hugging Face Inference API.
Supports function calling in chat-completion format.
"""

import os
import json
import asyncio
import aiohttp
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class Message(BaseModel):
    """Chat message"""
    role: str  # "system", "user", "assistant", "tool"
    content: str
    name: Optional[str] = None  # For tool calls


class FunctionCall(BaseModel):
    """Function call from LLM"""
    name: str
    arguments: Dict[str, Any]


class LLMResponse(BaseModel):
    """Response from LLM"""
    content: str
    function_calls: List[FunctionCall] = []
    finish_reason: str = "stop"  # "stop", "length", "function_call"


class HuggingFaceLLMClient:
    """
    Client for Hugging Face Inference API with Vicuna-7B.
    
    Supports:
    - Text generation
    - Function calling
    - Conversation history
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "lmsys/vicuna-7b-v1.5",
        base_url: str = "https://router.huggingface.co",
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize HF LLM client.
        
        Args:
            api_key: Hugging Face API key (or from HUGGINGFACE_API_KEY env)
            model: Model identifier
            base_url: HF Inference API base URL
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
        """
        self.api_key = api_key or os.getenv("HUGGINGFACE_API_KEY")
        if not self.api_key:
            raise ValueError("HUGGINGFACE_API_KEY not found in environment or parameters")
        
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Determine API URL
        if "router.huggingface.co" in base_url or "api-inference.huggingface.co" in base_url:
            # Use standard inference API URL for the model (updated to router)
            self.api_url = f"https://router.huggingface.co/hf-inference/models/{model}"
        else:
            # Custom endpoint
            self.api_url = base_url
            
        self.session = None
    
    async def _get_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=aiohttp.ClientTimeout(total=self.timeout)
            )
        return self.session
    
    async def chat(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 512
    ) -> LLMResponse:
        """
        Send chat request to Vicuna-7B via HF Inference API.
        
        Args:
            messages: Conversation history
            tools: Available functions (OpenAI format)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
        
        Returns:
            LLMResponse with content and optional function calls
        """
        # Handle tools injection if needed
        tool_prompt = ""
        if tools:
            tool_def = self._format_tools(tools)
            tool_prompt = f"Available tools:\n{tool_def}\n\nTo call a tool, use: [TOOLCALLS] [{{\"name\": \"tool_name\", \"arguments\": {{...}}}}] [/TOOLCALLS]\n\n"
        
        # Manual prompt construction for Vicuna
        prompt = "A chat between a curious user and an artificial intelligence assistant. The assistant gives helpful, detailed, and polite answers to the user's questions.\n\n"
        
        for i, msg in enumerate(messages):
            content = msg.content
            
            # Inject tools into the first message (system or user)
            if i == 0 and tool_prompt:
                content = f"{tool_prompt}{content}"
            
            role = msg.role
            if role == "tool":
                role = "user"
                content = f"[TOOL_RESULTS] {content} [/TOOL_RESULTS]"
            
            if role == "system":
                prompt += f"{content}\n\n"
            elif role == "user":
                prompt += f"USER: {content}\n"
            elif role == "assistant":
                prompt += f"ASSISTANT: {content}\n"
        
        prompt += "ASSISTANT:"
        
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": max_tokens,
                "temperature": temperature,
                "return_full_text": False,
                "stop": ["USER:"]
            }
        }
        
        session = await self._get_session()
        
        for attempt in range(self.max_retries):
            try:
                async with session.post(self.api_url, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        # If model is loading, wait and retry
                        if "loading" in error_text.lower():
                            await asyncio.sleep(2 * (attempt + 1))
                            continue
                        raise Exception(f"HF API Error {response.status}: {error_text}")
                    
                    result = await response.json()
                    
                    # Result is usually a list of dicts: [{"generated_text": "..."}]
                    if isinstance(result, list) and len(result) > 0:
                        generated_text = result[0].get("generated_text", "")
                    elif isinstance(result, dict):
                        generated_text = result.get("generated_text", "")
                    else:
                        generated_text = str(result)
                    
                    # Parse function calls if tools provided
                    return self._parse_response(generated_text, tools)
                    
            except Exception as e:
                if attempt == self.max_retries - 1:
                    raise Exception(f"LLM request failed after {self.max_retries} retries: {str(e)}")
                await asyncio.sleep(1)
    
    def _format_tools(self, tools: List[Dict[str, Any]]) -> str:
        """
        Format tools into a readable JSON string.
        """
        formatted_tools = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool.get("function", {})
                formatted_tools.append({
                    "name": func.get("name"),
                    "description": func.get("description"),
                    "parameters": func.get("parameters", {})
                })
        
        return json.dumps(formatted_tools)
    
    def _parse_response(
        self,
        text: str,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> LLMResponse:
        """
        Parse LLM response text, extracting function calls if present.
        
        Function call format (Mistral):
        [TOOL_CALLS] [{"name": "function_name", "arguments": {...}}] [/TOOL_CALLS]
        
        Args:
            text: Generated text
            tools: Available tools (to validate calls)
        
        Returns:
            Parsed LLMResponse
        """
        # Check for tool calls (handle both escaped and unescaped versions)
        # LLM may output [TOOL\_CALLS] with escaped underscores due to Markdown
        text_normalized = text.replace("\\_", "_")  # Unescape underscores
        
        # Support both [TOOLCALLS] and [TOOL_CALLS] formats for backward compatibility
        has_toolcalls_open = "[TOOLCALLS]" in text_normalized
        has_tool_calls_open = "[TOOL_CALLS]" in text_normalized
        
        if has_toolcalls_open or has_tool_calls_open:
            marker = "[TOOLCALLS]" if has_toolcalls_open else "[TOOL_CALLS]"
            end_marker = "[/TOOLCALLS]" if has_toolcalls_open else "[/TOOL_CALLS]"
            
            # Check if closing tag exists
            has_closing = end_marker in text_normalized
            
            if has_closing:
                print(f"[DEBUG HF] Found {marker} markers in LLM response")
                # Extract tool calls with proper closing
                try:
                    start = text_normalized.index(marker) + len(marker)
                    end = text_normalized.index(end_marker)
                    tool_calls_str = text_normalized[start:end].strip()
                    
                    print(f"[DEBUG HF] Extracted tool_calls_str: {tool_calls_str[:200]}")
                    
                    # Extract content (everything not in tool calls)
                    content_before = text_normalized[:text_normalized.index(marker)].strip()
                    content_after = text_normalized[end + len(end_marker):].strip()
                    content = f"{content_before}\n{content_after}".strip()
                
                    tool_calls_json = json.loads(tool_calls_str)
                    if not isinstance(tool_calls_json, list):
                        tool_calls_json = [tool_calls_json]
                    
                    print(f"[DEBUG HF] Successfully parsed {len(tool_calls_json)} tool calls")
                    
                    function_calls = [
                        FunctionCall(
                            name=call.get("name", ""),
                            arguments=call.get("arguments", {})
                        )
                        for call in tool_calls_json
                    ]
                    
                    print(f"[DEBUG HF] Returning LLMResponse with {len(function_calls)} function_calls")
                    
                    return LLMResponse(
                        content=content,
                        function_calls=function_calls,
                        finish_reason="function_call"
                    )
                except (ValueError, json.JSONDecodeError) as e:
                    print(f"[DEBUG HF] PARSING FAILED: {e}")
                    print(f"[DEBUG HF] Falling back to incomplete tool call extraction")
            
            # FALLBACK: No closing tag or parsing failed - try to extract JSON array manually
            print(f"[DEBUG HF] WARNING: {marker} found but no {end_marker} - attempting recovery")
            try:
                start_idx = text_normalized.index(marker) + len(marker)
                remaining_text = text_normalized[start_idx:].strip()
                
                # Try to find the JSON array - look for [{ ... }]
                if remaining_text.startswith('['):
                    # Find matching closing bracket for array
                    bracket_count = 0
                    end_idx = 0
                    for i, char in enumerate(remaining_text):
                        if char == '[':
                            bracket_count += 1
                        elif char == ']':
                            bracket_count -= 1
                            if bracket_count == 0:
                                end_idx = i + 1
                                break
                    
                    if end_idx > 0:
                        tool_calls_str = remaining_text[:end_idx]
                        print(f"[DEBUG HF] Recovered tool_calls_str: {tool_calls_str[:200]}")
                        
                        tool_calls_json = json.loads(tool_calls_str)
                        if not isinstance(tool_calls_json, list):
                            tool_calls_json = [tool_calls_json]
                        
                        print(f"[DEBUG HF] Successfully recovered {len(tool_calls_json)} tool calls")
                        
                        function_calls = [
                            FunctionCall(
                                name=call.get("name", ""),
                                arguments=call.get("arguments", {})
                            )
                            for call in tool_calls_json
                        ]
                        
                        return LLMResponse(
                            content="",  # Ignore any text, tool call is what matters
                            function_calls=function_calls,
                            finish_reason="function_call"
                        )
            except (ValueError, json.JSONDecodeError, IndexError) as e:
                print(f"[DEBUG HF] RECOVERY FAILED: {e}")
                print(f"[DEBUG HF] Returning raw text as content")
                return LLMResponse(content=text, finish_reason="stop")
        
        # No function calls, regular response
        print(f"[DEBUG HF] No [TOOLCALLS] markers found, returning text as-is")
        print(f"[DEBUG HF] Raw LLM output (first 300 chars): {text[:300]}")
        return LLMResponse(content=text.strip(), finish_reason="stop")
    
    async def close(self):
        """Close HTTP client"""
        # AsyncInferenceClient doesn't strictly need closing if used as context manager, 
        # but we can't easily close the underlying session if we don't own it fully.
        # However, it doesn't expose a close method directly in all versions.
        # We'll just pass.
        pass
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()


# Convenience function
async def create_llm_client(
    api_key: Optional[str] = None,
    model: str = "mistralai/Mistral-7B-Instruct-v0.2"
) -> HuggingFaceLLMClient:
    """
    Create and return HF LLM client.
    
    Args:
        api_key: Optional API key (uses settings if not provided)
        model: Model identifier
    
    Returns:
        Initialized HuggingFaceLLMClient
    
    Example:
        >>> async with create_llm_client() as client:
        ...     response = await client.chat(messages)
    """
    # Get API key and config from settings if not provided
    from ...core.config import get_settings
    settings = get_settings()
    
    if not api_key:
        api_key = settings.HUGGINGFACE_API_KEY
    
    if not model or model == "mistralai/Mistral-7B-Instruct-v0.2":
        model = settings.HUGGINGFACE_MODEL
    
    return HuggingFaceLLMClient(
        api_key=api_key,
        model=model,
        base_url=settings.HUGGINGFACE_BASE_URL,
        timeout=settings.HUGGINGFACE_TIMEOUT,
        max_retries=settings.HUGGINGFACE_MAX_RETRIES
    )
