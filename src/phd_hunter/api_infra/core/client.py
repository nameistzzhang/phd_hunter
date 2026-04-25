"""ModelClient: Handles API calls to AI models with retry logic and routing."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple, TypeVar, Union
from urllib.parse import urljoin
from datetime import datetime

import httpx
from pydantic import BaseModel, Field, ValidationError

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Provider(Enum):
    """Supported AI providers."""
    YUNWU = "yunwu"

    @classmethod
    def _missing_(cls, value: str):
        """Handle case-insensitive provider names."""
        for member in cls:
            if member.value.lower() == value.lower():
                return member
        return None


class ModelType(Enum):
    """Supported model types."""
    GLM_5 = "glm-5"
    DEEPSEEK_V3_2 = "deepseek-v3.2"
    QWEN_3_5_397B = "qwen3.5-397b-a17b"
    GEMINI_3_1_PRO = "gemini-3.1-pro-preview"
    GPT_5_2 = "gpt-5.2"
    CLAUDE_SONNET_4_6 = "claude-sonnet-4-6"


# YUNWU API configuration
YUNWU_BASE_URL = "https://yunwu.ai/v1"
DEFAULT_TIMEOUT = 120.0
MAX_RETRIES = 5
RETRY_BACKOFF = 3.0  # seconds


class ModelConfig(BaseModel):
    """Configuration for a model."""
    provider: Provider = Provider.YUNWU
    model_name: str
    api_keys: List[str] = Field(default_factory=list)
    temperature: float = 0.7
    max_tokens: int = 2000
    timeout: float = DEFAULT_TIMEOUT
    enable_routing: bool = True
    base_url: str = YUNWU_BASE_URL

    def __init__(self, **data):
        if "api_keys" not in data or not data.get("api_keys"):
            # Default YUNWU API key
            raise ValueError("At least one API key must be provided in the configuration")
        # Set default base_url if not provided
        if "base_url" not in data or not data.get("base_url"):
            data["base_url"] = YUNWU_BASE_URL
        super().__init__(**data)

    class Config:
        arbitrary_types_allowed = True


class APIKeyMetadata(BaseModel):
    """Metadata for tracking API key usage."""
    key_index: int = Field(description="Index of the API key in rotation")
    request_count: int = Field(default=0, description="Number of requests made with this key")
    success_count: int = Field(default=0, description="Number of successful requests")
    failure_count: int = Field(default=0, description="Number of failed requests")
    last_used: Optional[str] = Field(default=None, description="ISO timestamp of last use")
    consecutive_failures: int = Field(default=0, description="Consecutive failure count")


class GenerationMetadata(BaseModel):
    """Metadata about a generation request."""
    model: str
    provider: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    total_cost: float = Field(default=0.0, description="Total cost in USD")
    cache_hit: bool = Field(default=False)
    routing_key_used: Optional[str] = Field(default=None)
    api_key_metadata: Optional[APIKeyMetadata] = Field(default=None)

    class Config:
        use_enum_values = True


class Response(BaseModel):
    """Model response."""
    content: str = Field(description="Generated response content")
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: GenerationMetadata

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "content": self.content,
            "tool_calls": self.tool_calls,
            "metadata": self.metadata.dict()
        }


class ErrorDetail(BaseModel):
    """Error detail from API response."""
    message: str
    type: str
    code: Optional[str] = None


class APIError(Exception):
    """Base API error."""

    def __init__(self, message: str, status_code: int = None, error_details: List[ErrorDetail] = None):
        self.message = message
        self.status_code = status_code
        self.error_details = error_details or []
        super().__init__(self.message)


class RateLimitError(APIError):
    """Rate limit error."""

    def __init__(self, retry_after: Optional[int] = None):
        message = f"Rate limit exceeded. Retry after {retry_after} seconds." if retry_after else "Rate limit exceeded"
        super().__init__(message, status_code=429)
        self.retry_after = retry_after


class AuthenticationError(APIError):
    """Authentication error."""

    def __init__(self):
        super().__init__("Invalid or expired API key", status_code=401)


class ServerError(APIError):
    """Server error."""

    def __init__(self):
        super().__init__("Internal server error", status_code=500)


class APIProvider(Protocol):
    """Protocol for API provider implementations."""

    async def generate(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> Response:
        """Generate response from API."""
        ...


class YUNWUProvider:
    """YUNWU API provider implementation."""

    def __init__(self, config: ModelConfig):
        self.config = config

        # Disable proxy to avoid issues
        self.client = httpx.AsyncClient(
            timeout=config.timeout,
            trust_env=False,
        )
        self.api_keys: List[str] = config.api_keys
        self.key_metadata: List[APIKeyMetadata] = [
            APIKeyMetadata(key_index=i) for i in range(len(self.api_keys))
        ]
        self.current_key_index = 0
        self.lock = asyncio.Lock()

    async def _get_key(self) -> Tuple[str, APIKeyMetadata]:
        """Get the next API key with routing logic."""
        if len(self.api_keys) == 1:
            key, meta = self.api_keys[0], self.key_metadata[0]
            meta.request_count += 1
            meta.last_used = datetime.now().isoformat()
            return key, meta

        # If routing is disabled, use the same key
        if not self.config.enable_routing:
            key, meta = self.api_keys[self.current_key_index], self.key_metadata[self.current_key_index]
            meta.request_count += 1
            meta.last_used = datetime.now().isoformat()
            return key, meta

        # Use the key with the lowest failure rate
        # Rotate through keys based on failure count
        best_key_idx = 0
        best_failure_count = float('inf')

        for i, meta in enumerate(self.key_metadata):
            if meta.consecutive_failures == 0:
                # Prefer keys that haven't failed recently
                return self.api_keys[i], self.key_metadata[i]

            if meta.consecutive_failures < best_failure_count:
                best_failure_count = meta.consecutive_failures
                best_key_idx = i

        # Rotate to next key
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        key, meta = self.api_keys[self.current_key_index], self.key_metadata[self.current_key_index]

        meta.request_count += 1
        meta.last_used = datetime.now().isoformat()

        # If the best key has 0 consecutive failures, use that instead
        if self.key_metadata[best_key_idx].consecutive_failures == 0:
            key = self.api_keys[best_key_idx]
            meta = self.key_metadata[best_key_idx]
            self.current_key_index = best_key_idx

        return key, meta

    async def _should_retry(self, error: APIError, attempt: int) -> bool:
        """Determine if we should retry based on error type."""
        if attempt >= MAX_RETRIES:
            return False

        # Don't retry on client errors (4xx)
        if error.status_code and 400 <= error.status_code < 500:
            return False

        # Retry on rate limits, server errors, and unknown errors
        return True

    async def _backoff(self, attempt: int):
        """Implement exponential backoff."""
        delay = RETRY_BACKOFF * (2 ** (attempt - 1))
        logger.info(f"Retry attempt {attempt}/{MAX_RETRIES}, waiting {delay}s before retry")
        await asyncio.sleep(delay)

    async def _handle_rate_limit(self, error: RateLimitError):
        """Handle rate limit error."""
        logger.warning(f"Rate limit hit: {error.message}")
        await self._backoff(1)
        # Rotate to next key on rate limit
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)

    async def generate(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]] = None,
        temperature: float = None,
        max_tokens: int = None,
    ) -> Response:
        """Generate response from YUNWU API."""
        temp = temperature if temperature is not None else self.config.temperature
        max_tok = max_tokens if max_tokens is not None else self.config.max_tokens

        # Get current API key
        key, meta = await self._get_key()

        for attempt in range(MAX_RETRIES):
            try:
                # Prepare request
                url = urljoin(self.config.base_url, "v1/chat/completions")
                logger.info(f"Request URL: {url}")

                headers = {
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                }

                payload = {
                    "model": self.config.model_name,
                    "messages": messages,
                    "temperature": temp,
                    "max_tokens": max_tok,
                    "stream": False,
                }

                if tools:
                    payload["tools"] = tools

                logger.info(f"Making request to {url} with model {self.config.model_name}")
                logger.info(f"Using API key index: {meta.key_index}")

                response = await self.client.post(url, json=payload, headers=headers)

                logger.info(f"Response status: {response.status_code}")
                logger.info(f"Response text length: {len(response.text)}")
                logger.info(f"Response text preview: {response.text[:200] if response.text else 'EMPTY'}")

                # Check response status
                if response.status_code == 401:
                    raise AuthenticationError()

                elif response.status_code == 429:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "Rate limit exceeded")
                    retry_after = error_data.get("error", {}).get("retry_after")
                    meta.consecutive_failures += 1
                    meta.failure_count += 1
                    raise RateLimitError(retry_after)

                elif response.status_code >= 500:
                    raise ServerError()

                elif response.status_code >= 400:
                    error_data = response.json()
                    error_msg = error_data.get("error", {}).get("message", "API request failed")
                    meta.consecutive_failures += 1
                    meta.failure_count += 1
                    raise APIError(error_msg, response.status_code)

                # Parse success response
                try:
                    data = response.json()
                except Exception as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    logger.error(f"Raw response text: {response.text}")
                    raise APIError(f"Invalid JSON response: {e}")

                # Handle potential empty response
                if not data or "choices" not in data or not data["choices"]:
                    logger.error(f"Invalid response data structure: {data}")
                    raise APIError("Invalid response format from API")

                choice = data["choices"][0]
                message = choice["message"]

                # Extract metadata with fallback values
                usage = data.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens") or usage.get("input_tokens") or 0
                completion_tokens = usage.get("completion_tokens") or usage.get("output_tokens") or 0
                total_tokens = prompt_tokens + completion_tokens

                # Calculate cost (approximate)
                cost = self._calculate_cost(
                    self.config.model_name,
                    prompt_tokens,
                    completion_tokens
                )

                # Update metadata
                meta.consecutive_failures = 0
                meta.success_count += 1
                meta.last_used = datetime.now().isoformat()

                metadata = GenerationMetadata(
                    model=self.config.model_name,
                    provider=self.config.provider.value,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    total_cost=cost,
                    routing_key_used=key[:10] + "..." if key else None,
                    api_key_metadata=meta,
                )

                tool_calls = []
                if message.get("tool_calls"):
                    tool_calls = message["tool_calls"]

                # Some models return content=None when the assistant only emits tool calls.
                # Normalize to string to satisfy Response schema.
                raw_content = message.get("content")
                if raw_content is None:
                    content = ""
                elif isinstance(raw_content, str):
                    content = raw_content
                elif isinstance(raw_content, list):
                    text_parts: List[str] = []
                    for item in raw_content:
                        if isinstance(item, dict):
                            text = item.get("text")
                            if isinstance(text, str):
                                text_parts.append(text)
                    content = "\n".join(text_parts)
                else:
                    content = str(raw_content)

                return Response(
                    content=content,
                    tool_calls=tool_calls,
                    metadata=metadata,
                )

            except RateLimitError as e:
                if await self._should_retry(e, attempt):
                    await self._handle_rate_limit(e)
                    continue
                raise

            except APIError as e:
                if await self._should_retry(e, attempt):
                    await self._backoff(attempt + 1)
                    continue
                raise

            except httpx.HTTPStatusError as e:
                meta.consecutive_failures += 1
                meta.failure_count += 1
                raise APIError(e.response.text, e.response.status_code)

            except Exception as e:
                meta.consecutive_failures += 1
                meta.failure_count += 1
                raise APIError(f"Unexpected error: {str(e)}")

        # Should not reach here
        raise APIError("Max retries exceeded")

    def _calculate_cost(self, model: str, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate estimated cost based on model."""
        # Approximate cost per token (USD)
        cost_rates = {
            "glm-5": (0.0001, 0.0003),      # 0.1¢/1k for prompt, 0.3¢/1k for completion
            "deepseek-v3.2": (0.0001, 0.0002),  # DeepSeek pricing
            "qwen3.5-397b-a17b": (0.0002, 0.0004),  # Qwen pricing
            "gemini-3.1-pro-preview": (0.00005, 0.00015),  # Gemini pricing
            "gpt-5.2": (0.0001, 0.0003),  # GPT pricing
            "claude-sonnet-4-6": (0.000003, 0.000015),  # Claude pricing
        }

        rate = cost_rates.get(model, (0.0001, 0.0002))  # Default rate
        prompt_cost = (prompt_tokens / 1000) * rate[0]
        completion_cost = (completion_tokens / 1000) * rate[1]
        return prompt_cost + completion_cost

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# Type variable for generic decorator
F = TypeVar("F", bound=Callable)


class ModelClient:
    """Main client for interacting with AI models."""

    def __init__(
        self,
        provider: str = "openai",
        model: str = "gpt-4o",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        api_keys: List[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        enable_routing: bool = True,
        base_url: str = None,
    ):
        """
        Initialize ModelClient.

        Args:
            provider: Provider name (currently only "yunwu" is supported)
            model: Model name
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            api_keys: List of API keys for routing
            timeout: Request timeout in seconds
            enable_routing: Enable API key routing
            base_url: Custom API base URL (defaults to YUNWU_BASE_URL)
        """
        config = ModelConfig(
            provider=Provider(provider.upper()),
            model_name=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_keys=api_keys,
            timeout=timeout,
            enable_routing=enable_routing,
            base_url=base_url,
        )

        self.config = config
        self._provider: Optional[APIProvider] = None

    async def _get_provider(self) -> APIProvider:
        """Get or create provider instance."""
        if self._provider is None:
            if self.config.provider == Provider.YUNWU:
                self._provider = YUNWUProvider(self.config)
            else:
                raise ValueError(f"Unsupported provider: {self.config.provider}")
        return self._provider

    async def generate(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]] = None,
        temperature: float = None,
        max_tokens: int = None,
        track_cost: bool = False,
        max_iterations: int = 5,
    ) -> Response:
        """
        Generate response from model with optional tool calling.

        Args:
            messages: List of message dictionaries with "role" and "content"
            tools: List of tool definitions
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            track_cost: Track cost metrics
            max_iterations: Maximum number of tool calling iterations

        Returns:
            Response object with content and metadata
        """
        provider = await self._get_provider()

        if track_cost:
            logger.info(f"Generating response with model {self.config.model_name}")

        messages = messages.copy()  # Don't modify original messages

        # Retry logic for rate limiting
        max_retries = 3
        for retry in range(max_retries):
            try:
                for iteration in range(max_iterations):
                    logger.info(f"[Tool Call] Iteration {iteration + 1}/{max_iterations}")
                    response = await provider.generate(
                        messages=messages,
                        tools=tools,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )

                    # Check if the model wants to use tools
                    if not response.tool_calls or not response.tool_calls[0].get("function"):
                        # No tool calls, return response
                        logger.info(f"[Tool Call] No tool calls in iteration {iteration + 1}")
                        return response

                    logger.info(f"[Tool Call] Model called {len(response.tool_calls)} tools:")
                    for tool_call in response.tool_calls:
                        logger.info(f"  - {tool_call['function']['name']}")

                    # Execute tool calls
                    tool_results = []
                    for tool_call in response.tool_calls:
                        tool_name = tool_call["function"]["name"]
                        tool_args = json.loads(tool_call["function"]["arguments"])

                        logger.info(f"Executing tool: {tool_name} with args {tool_args}")

                        # Find the tool definition
                        tool_def = None
                        if tools:
                            for t in tools:
                                if t["function"]["name"] == tool_name:
                                    tool_def = t
                                    break

                        # Execute the tool
                        if tool_def:
                            try:
                                # Import here to avoid circular dependency
                                from api_infra.tools.decorator import _global_registry
                                tool_registered = _global_registry.get(tool_name)
                                if tool_registered:
                                    result = tool_registered.function(**tool_args)
                                    result_str = str(result)
                                else:
                                    result_str = f"Tool '{tool_name}' executed with args {tool_args}"

                            except Exception as e:
                                result_str = f"Error executing tool '{tool_name}': {str(e)}"
                        else:
                            result_str = f"Unknown tool: {tool_name}"

                        tool_results.append({
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": result_str,
                        })

                    # Add tool results to messages
                    logger.info(f"[Tool Call] Added {len(tool_results)} tool results to messages")
                    assistant_msg = response.to_dict()
                    assistant_msg["role"] = "assistant"
                    messages.append(assistant_msg)
                    messages.extend(tool_results)

                    # Add delay between iterations if rate limited
                    if retry < max_retries - 1:
                        import asyncio
                        await asyncio.sleep(0.5)

                # If we reach here, all iterations completed without hitting rate limit
                break

            except Exception as e:
                if retry == max_retries - 1:
                    raise
                logger.warning(f"[Tool Call] Retry {retry + 1}/{max_retries} due to: {e}")
                import asyncio
                await asyncio.sleep(1 * (retry + 1))  # Exponential backoff

        # If max iterations reached, return the last response
        logger.warning(f"Max iterations ({max_iterations}) reached, returning last response")
        return response

    async def close(self):
        """Close the provider connection."""
        if self._provider:
            await self._provider.close()

    async def __aenter__(self):
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()
