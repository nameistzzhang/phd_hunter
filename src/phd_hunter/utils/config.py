"""Configuration loader and management."""

import os
from pathlib import Path
from typing import Any, Dict, Optional
import yaml
from pydantic import BaseModel, Field, ConfigDict


class LLMConfig(BaseModel):
    """LLM configuration."""
    model_config = ConfigDict(extra="allow")
    provider: str = "openai"
    api_key: Optional[str] = None
    model: str = "gpt-4o"
    temperature: float = 0.3
    max_tokens: int = 4096


class CrawlerConfig(BaseModel):
    """Crawler configuration."""
    model_config = ConfigDict(extra="allow")
    headless: bool = True
    timeout: int = 30
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


class CacheConfig(BaseModel):
    """Cache configuration."""
    model_config = ConfigDict(extra="allow")
    enabled: bool = True
    ttl: int = 86400
    dir: str = "./cache"


class OutputConfig(BaseModel):
    """Output configuration."""
    model_config = ConfigDict(extra="allow")
    reports_dir: str = "./reports"
    papers_dir: str = "./papers"
    cache_dir: str = "./cache"
    default_format: str = "html"


class ReportsConfig(BaseModel):
    """Report configuration."""
    model_config = ConfigDict(extra="allow")
    template: str = "default"
    format: str = "html"
    include: list = Field(default_factory=lambda: [
        "executive_summary", "professor_profile", "research_analysis",
        "fit_assessment", "application_strategy", "risk_factors"
    ])
    scoring: Dict[str, float] = Field(default_factory=lambda: {
        "research_alignment": 0.40,
        "recent_activity": 0.20,
        "collaboration_network": 0.15,
        "student_mentorship": 0.15,
        "funding_potential": 0.10,
    })


class AgentsConfig(BaseModel):
    """Agent configuration."""
    model_config = ConfigDict(extra="allow")
    max_parallel: int = 5
    timeout: int = 300
    retry_attempts: int = 3
    batch_size: int = 10


class Settings(BaseModel):
    """Main settings object."""
    model_config = ConfigDict(extra="allow")
    llm: LLMConfig = Field(default_factory=LLMConfig)
    crawlers: Dict[str, Any] = Field(default_factory=dict)
    output: OutputConfig = Field(default_factory=OutputConfig)
    reports: ReportsConfig = Field(default_factory=ReportsConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    logging: Dict[str, Any] = Field(default_factory=dict)


def load_config(config_path: Optional[str] = None) -> Settings:
    """Load configuration from file.

    Args:
        config_path: Path to config file. If None, searches in standard locations.

    Returns:
        Settings object
    """
    config_data: Dict[str, Any] = {}

    # Default search paths
    if config_path is None:
        search_paths = [
            Path("config/settings.yaml"),
            Path("config/settings.yml"),
            Path.home() / ".phd_hunter/config.yaml",
            Path.cwd() / "settings.yaml",
        ]
        for path in search_paths:
            if path.exists():
                config_path = str(path)
                break

    if config_path and Path(config_path).exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f) or {}

    # Apply environment variable overrides
    _apply_env_overrides(config_data)

    return Settings(**config_data)


def _apply_env_overrides(config_data: Dict[str, Any]) -> None:
    """Apply environment variable overrides."""
    env_prefix = "PHD_HUNTER_"

    # LLM config overrides
    if api_key := os.environ.get(f"{env_prefix}LLM_API_KEY"):
        config_data.setdefault("llm", {})["api_key"] = api_key
    if provider := os.environ.get(f"{env_prefix}LLM_PROVIDER"):
        config_data.setdefault("llm", {})["provider"] = provider
    if model := os.environ.get(f"{env_prefix}LLM_MODEL"):
        config_data.setdefault("llm", {})["model"] = model

    # Output overrides
    if reports_dir := os.environ.get(f"{env_prefix}REPORTS_DIR"):
        config_data.setdefault("output", {})["reports_dir"] = reports_dir


def save_config(settings: Settings, path: str) -> None:
    """Save configuration to file."""
    config_dict = settings.model_dump()
    with open(path, 'w', encoding='utf-8') as f:
        yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get global settings instance."""
    global _settings
    if _settings is None:
        _settings = load_config()
    return _settings


def set_settings(settings: Settings) -> None:
    """Set global settings instance."""
    global _settings
    _settings = settings
