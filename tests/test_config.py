"""Tests for configuration module."""

import os
import tempfile
import yaml
import pytest
from phd_hunter.utils.config import load_config, Settings, LLMConfig, _settings


def test_load_default_config():
    """Test loading default configuration."""
    # Should not raise even without config file
    settings = load_config()
    assert isinstance(settings, Settings)
    assert settings.llm.provider == "openai"


def test_load_config_from_file():
    """Test loading configuration from file."""
    config_data = {
        "llm": {
            "provider": "anthropic",
            "model": "claude-3-sonnet",
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = f.name

    try:
        settings = load_config(config_path)
        assert settings.llm.provider == "anthropic"
        assert settings.llm.model == "claude-3-sonnet"
    finally:
        os.unlink(config_path)


def test_env_override(monkeypatch):
    """Test environment variable override."""
    monkeypatch.setenv("PHD_HUNTER_LLM_PROVIDER", "anthropic")
    # Clear global settings cache
    import phd_hunter.utils.config as config_module
    config_module._settings = None

    settings = load_config()
    assert settings.llm.provider == "anthropic"
