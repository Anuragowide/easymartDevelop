"""
Hugging Face LLM Client

Client for Mistral-7B-Instruct-v0.2 via Hugging Face Inference API.
Supports function calling in native Mistral format.
"""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from huggingface_hub import AsyncInferenceClient


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
    Client for Hugging Face Inference API with Mistral-7B-Instruct-v0.2.
    
    Supports:
    - Text generation
    - Function calling (Mistral native format)
    - Conversation history
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "mistralai/Mistral-7B-Instruct-v0.2",
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
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Initialize AsyncInferenceClient
        # If base_url is the default router, we don't pass it to avoid conflict with model
        if not base_url or "router.huggingface.co" in base_url or "api-inference.huggingface.co" in base_url:
            self.client = AsyncInferenceClient(model=model, token=self.api_key)
        else:
            # Custom endpoint
            self.client = AsyncInferenceClient(base_url=base_url, token=self.api_key)
    
    async def chat(
        self,
        messages: List[Message],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 512
    ) -> LLMResponse:
        """
        Send chat request to Mistral-7B via HF Inference API.
        
        Args:
            messages: Conversation history
            tools: Available functions (OpenAI format)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
        
        Returns:
            LLMResponse with content and optional function calls
        """
        # Convert messages to format expected by AsyncInferenceClient
        hf_messages = []
        
        # Handle tools injection if needed
        # Mistral-7B-Instruct-v0.2 doesn't support native tools in API, so we inject into prompt
        # We'll add tool definitions to the first user message or system message
        
        tool_prompt = ""
        if tools:
            tool_def = self._format_tools(tools)
            tool_prompt = f"[AVAILABLE_TOOLS] {tool_def} [/AVAILABLE_TOOLS]\n\n"
        
        # Process messages
        for i, msg in enumerate(messages):
            content = msg.content
            
            # Inject tools into the first message (system or user)
            if i == 0 and tool_prompt:
                content = f"{tool_prompt}{content}"
            
            # Map role 'tool' to 'user' or handle appropriately
            # Mistral usually expects tool outputs in a specific format, but here we just pass content
            role = msg.role
            if role == "tool":
                # For now, treat tool outputs as user messages with special marker if needed
                # Or just user messages
                role = "user"
                content = f"[TOOL_RESULTS] {content} [/TOOL_RESULTS]"
            
            hf_messages.append({"role": role, "content": content})
            
        try:
            response = await self.client.chat_completion(
                messages=hf_messages,
                max_tokens=max_tokens,
                temperature=temperature,
                seed=42 # Optional, for reproducibility
            )
            
            generated_text = response.choices[0].message.content
            
            # Parse function calls if tools provided
            return self._parse_response(generated_text, tools)
            
        except Exception as e:
            raise Exception(f"LLM request failed: {str(e)}")
    
    def _format_tools(self, tools: List[Dict[str, Any]]) -> str:
        """
        Format tools into Mistral function calling format.
        
        Args:
            tools: Tool definitions (OpenAI format)
        
        Returns:
            JSON string of tools
        """
        # Convert OpenAI format to simpler format for Mistral
        mistral_tools = []
        for tool in tools:
            if tool.get("type") == "function":
                func = tool.get("function", {})
                mistral_tools.append({
                    "name": func.get("name"),
                    "description": func.get("description"),
                    "parameters": func.get("parameters", {})
                })
        
        return json.dumps(mistral_tools)
    
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
                    # FIX: Use more robust extraction to handle multiple occurrences or messy text
                    content = re.sub(rf'\\?{re.escape(marker)}.*?\\?{re.escape(end_marker)}', '', text_normalized, flags=re.IGNORECASE | re.DOTALL).strip()
                    
                    # Also strip any leftover markers that might be escaped or repeated
                    content = re.sub(r'\\?\[/?TOOL_?CALLS\]', '', content, flags=re.IGNORECASE).strip()
                
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
