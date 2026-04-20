"""LLM client for interacting with OpenAI and Anthropic APIs."""

from typing import Any, Dict, Optional, Union, List
import os
from dataclasses import dataclass
import tiktoken
from openai import OpenAI, AsyncOpenAI
from anthropic import Anthropic, AsyncAnthropic
from pydantic import BaseModel
import json


@dataclass
class LLMConfig:
    """Configuration for LLM client."""
    provider: str = "openai"  # "openai" or "anthropic"
    api_key: Optional[str] = None
    model: str = "gpt-4o"
    temperature: float = 0.3
    max_tokens: int = 4096
    timeout: int = 60


class LLMClient:
    """Unified client for LLM providers."""

    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize LLM client.

        Args:
            config: LLM configuration
        """
        self.config = config or LLMConfig()
        self._init_clients()

    def _init_clients(self) -> None:
        """Initialize API clients based on provider."""
        api_key = self.config.api_key or self._get_env_key()

        if self.config.provider == "openai":
            self.client = OpenAI(api_key=api_key)
            self.async_client = AsyncOpenAI(api_key=api_key)
        elif self.config.provider == "anthropic":
            self.client = Anthropic(api_key=api_key)
            self.async_client = AsyncAnthropic(api_key=api_key)
        else:
            raise ValueError(f"Unsupported provider: {self.config.provider}")

    def _get_env_key(self) -> str:
        """Get API key from environment."""
        if self.config.provider == "openai":
            key = os.environ.get("OPENAI_API_KEY")
        else:
            key = os.environ.get("ANTHROPIC_API_KEY")

        if not key:
            raise ValueError(
                f"No API key found for {self.config.provider}. "
                f"Set {self.config.provider.upper()}_API_KEY environment variable "
                f"or pass api_key to LLMClient."
            )
        return key

    def complete(
        self,
        system: str,
        user: str,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Get text completion from LLM.

        Args:
            system: System prompt
            user: User prompt/query
            temperature: Override config temperature
            max_tokens: Override config max_tokens

        Returns:
            Generated text response
        """
        temperature = temperature or self.config.temperature
        max_tokens = max_tokens or self.config.max_tokens

        if self.config.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=self.config.timeout,
            )
            return response.choices[0].message.content

        else:  # anthropic
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "user", "content": user}
                ],
                system=system,
                temperature=temperature,
                timeout=self.config.timeout,
            )
            return response.content[0].text

    def structured(
        self,
        system: str,
        user: str,
        schema: Union[Dict, type[BaseModel]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Union[Dict, BaseModel]:
        """Get structured JSON output from LLM.

        Args:
            system: System prompt
            user: User prompt/query
            schema: JSON schema dict or Pydantic model class
            temperature: Override config temperature
            max_tokens: Override config max_tokens

        Returns:
            Parsed JSON object or Pydantic model instance
        """
        temperature = temperature or self.config.temperature
        max_tokens = max_tokens or self.config.max_tokens

        if isinstance(schema, type) and issubclass(schema, BaseModel):
            schema_dict = schema.model_json_schema()
            is_pydantic = True
        else:
            schema_dict = schema
            is_pydantic = False

        json_prompt = f"{user}\n\nOutput must be valid JSON matching this schema:\n{json.dumps(schema_dict, indent=2)}"

        if self.config.provider == "openai":
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "system", "content": system + "\n\nReturn only JSON."},
                    {"role": "user", "content": json_prompt}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=self.config.timeout,
                response_format={"type": "json_object"}
            )
            result = json.loads(response.choices[0].message.content)

        else:  # anthropic
            response = self.client.messages.create(
                model=self.config.model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "user", "content": json_prompt}
                ],
                system=system + "\n\nReturn only JSON.",
                temperature=temperature,
                timeout=self.config.timeout,
            )
            result = json.loads(response.content[0].text)

        if is_pydantic:
            return schema(**result)
        return result

    def embed(self, texts: List[str]) -> List[List[float]]:
        """Get embeddings for texts.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        if self.config.provider == "openai":
            response = self.client.embeddings.create(
                model="text-embedding-3-small",
                input=texts
            )
            return [item.embedding for item in response.data]
        else:
            # Anthropic doesn't have embeddings API yet, use OpenAI
            # In production, you'd use a separate embedding model
            client = OpenAI()
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=texts
            )
            return [item.embedding for item in response.data]

    def count_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        try:
            if self.config.provider == "openai":
                encoding = tiktoken.encoding_for_model(self.config.model)
            else:
                encoding = tiktoken.encoding_for_model("gpt-4o")
            return len(encoding.encode(text))
        except Exception:
            # Fallback: rough estimate (4 chars per token)
            return len(text) // 4

    def estimate_cost(
        self,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Estimate cost for token usage.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        # Pricing as of 2026 (update as needed)
        pricing = {
            "openai": {
                "gpt-4o": {"input": 2.50, "output": 10.00},  # per 1M tokens
                "gpt-4o-mini": {"input": 0.15, "output": 0.60},
                "gpt-4-turbo": {"input": 10.00, "output": 30.00},
            },
            "anthropic": {
                "claude-3-opus": {"input": 15.00, "output": 75.00},
                "claude-3-sonnet": {"input": 3.00, "output": 15.00},
                "claude-3-haiku": {"input": 0.25, "output": 1.25},
            }
        }

        provider_pricing = pricing.get(self.config.provider, {})
        model_pricing = provider_pricing.get(self.config.model, {"input": 0, "output": 0})

        input_cost = (input_tokens / 1_000_000) * model_pricing["input"]
        output_cost = (output_tokens / 1_000_000) * model_pricing["output"]

        return input_cost + output_cost
