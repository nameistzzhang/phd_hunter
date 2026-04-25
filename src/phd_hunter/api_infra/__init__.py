"""api_infra: A robust infrastructure for calling closed-source AI APIs."""

from .core.client import ModelClient, Response
from .context.manager import ContextManager
from .tools.decorator import tool, ToolRegistry, get_global_registry

__version__ = "0.1.0"
__all__ = ["ModelClient", "ContextManager", "tool", "ToolRegistry", "get_global_registry"]
