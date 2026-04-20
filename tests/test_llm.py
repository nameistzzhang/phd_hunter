"""Tests for LLM client."""

import pytest
from unittest.mock import MagicMock, patch
from phd_hunter.llm.client import LLMClient, LLMConfig
from phd_hunter.models import Professor


def test_llm_client_init_openai():
    """Test LLM client initialization with OpenAI."""
    config = LLMConfig(provider="openai", api_key="test-key")
    client = LLMClient(config)
    assert client.config.provider == "openai"


def test_llm_client_count_tokens():
    """Test token counting."""
    config = LLMConfig(provider="openai", api_key="test-key")
    client = LLMClient(config)
    tokens = client.count_tokens("Hello world")
    assert tokens > 0


@patch("phd_hunter.llm.client.OpenAI")
def test_llm_client_complete(mock_openai):
    """Test LLM completion."""
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Test response"
    mock_openai.return_value.chat.completions.create.return_value = mock_response

    config = LLMConfig(provider="openai", api_key="test-key")
    client = LLMClient(config)
    result = client.complete(system="Test", user="Hello")

    assert result == "Test response"


def test_llm_client_estimate_cost():
    """Test cost estimation."""
    config = LLMConfig(provider="openai", model="gpt-4o", api_key="test-key")
    client = LLMClient(config)
    cost = client.estimate_cost(input_tokens=1000, output_tokens=500)
    assert cost > 0
