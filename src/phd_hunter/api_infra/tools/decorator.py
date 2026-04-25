"""Tool decorator to convert Python functions into LLM-callable tools."""

from __future__ import annotations

import inspect
import json
import logging
import functools
from typing import Any, Callable, Dict, List, Optional, Protocol, TypeVar, Union, get_args, get_origin, get_type_hints

from pydantic import BaseModel, create_model, ValidationError

logger = logging.getLogger(__name__)

# Type variable for generic function
F = TypeVar("F", bound=Callable)


class ToolDefinition:
    """Represents a tool definition for LLM."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: Dict[str, Any],
        function: Callable,
    ):
        """
        Initialize tool definition.

        Args:
            name: Tool name
            description: Tool description
            parameters: Tool parameters schema
            function: Actual function to call
        """
        self.name = name
        self.description = description
        self.parameters = parameters
        self.function = function

    def to_dict(self) -> Dict[str, Any]:
        """Convert to tool schema dictionary."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": [],
                },
            },
        }


class ToolRegistry:
    """Registry for managing tools."""

    def __init__(self):
        """Initialize tool registry."""
        self._tools: Dict[str, ToolDefinition] = {}

    def register(self, name: str, description: str, func: Callable, parameters: Dict[str, Any] = None):
        """
        Register a tool.

        Args:
            name: Tool name
            description: Tool description
            func: Function to register
            parameters: Optional parameters schema
        """
        if name in self._tools:
            logger.warning(f"Tool '{name}' already registered. Overwriting.")

        self._tools[name] = ToolDefinition(
            name=name,
            description=description,
            function=func,
            parameters=parameters or {},
        )
        logger.debug(f"Registered tool: {name}")

    def get(self, name: str) -> Optional[ToolDefinition]:
        """Get tool by name."""
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """Get list of all registered tools."""
        return [tool.to_dict() for tool in self._tools.values()]

    def list_tool_names(self) -> List[str]:
        """Get list of all tool names."""
        return list(self._tools.keys())

    def has_tool(self, name: str) -> bool:
        """Check if tool exists."""
        return name in self._tools

    def unregister(self, name: str) -> bool:
        """Unregister a tool."""
        if name in self._tools:
            del self._tools[name]
            logger.debug(f"Unregistered tool: {name}")
            return True
        return False

    def clear(self):
        """Clear all tools."""
        self._tools.clear()
        logger.debug("Cleared all tools")


class Tool:
    """Metadata about a tool."""

    def __init__(self, name: str, description: str):
        """
        Initialize tool metadata.

        Args:
            name: Tool name
            description: Tool description
        """
        self.name = name
        self.description = description


class ToolInvocation:
    """Represents a tool invocation result."""

    def __init__(self, name: str, arguments: Dict[str, Any], result: Any, error: str = None):
        """
        Initialize tool invocation.

        Args:
            name: Tool name
            arguments: Tool arguments
            result: Tool execution result
            error: Error message if execution failed
        """
        self.name = name
        self.arguments = arguments
        self.result = result
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "arguments": self.arguments,
            "result": self.result,
            "error": self.error,
        }


class ToolHandler(Protocol):
    """Protocol for tool handler."""

    async def handle_tool_call(
        self,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> ToolInvocation:
        """Handle a tool call."""
        ...


class ToolExecutor:
    """Executes tool calls."""

    def __init__(self, handler: ToolHandler = None):
        """
        Initialize tool executor.

        Args:
            handler: Optional tool handler
        """
        self.handler = handler

    async def execute_tool(
        self,
        tool_definition: ToolDefinition,
        arguments: Dict[str, Any],
    ) -> ToolInvocation:
        """
        Execute a tool call.

        Args:
            tool_definition: Tool definition
            arguments: Tool arguments

        Returns:
            ToolInvocation result
        """
        try:
            logger.debug(f"Executing tool: {tool_definition.name} with arguments {arguments}")

            # Validate arguments using Pydantic if available
            if self.handler and hasattr(self.handler, 'validate_args'):
                validated_args = await self.handler.validate_args(tool_definition.name, arguments)
            else:
                validated_args = arguments

            # Execute the function
            result = tool_definition.function(**validated_args)

            return ToolInvocation(
                name=tool_definition.name,
                arguments=arguments,
                result=result,
            )

        except ValidationError as e:
            error_msg = f"Validation error: {str(e)}"
            logger.error(error_msg)
            return ToolInvocation(
                name=tool_definition.name,
                arguments=arguments,
                error=error_msg,
            )

        except TypeError as e:
            error_msg = f"Function error: {str(e)}"
            logger.error(error_msg)
            return ToolInvocation(
                name=tool_definition.name,
                arguments=arguments,
                error=error_msg,
            )

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            logger.error(error_msg)
            return ToolInvocation(
                name=tool_definition.name,
                arguments=arguments,
                error=error_msg,
            )


def tool(
    name: str = None,
    description: str = None,
    parameters: Dict[str, Any] = None,
):
    """
    Decorator to convert a Python function into an LLM-callable tool.

    Args:
        name: Tool name (defaults to function name)
        description: Tool description (defaults to function docstring)
        parameters: Optional parameters schema

    Returns:
        Decorator function

    Example:
        .. code-block:: python

            @tool(description="Search the database")
            def search_database(query: str) -> str:
                return db.query(query)

            # With type hints, parameters are automatically inferred
            @tool
            def add_numbers(a: int, b: int) -> int:
                \"\"\"Add two numbers.\"\"\"
                return a + b
    """
    def decorator(func: F) -> F:
        logger.debug(f"decorator() called for function {func.__name__}")

        # Set defaults using func's own attributes
        func_name = name or func.__name__
        func_description = description or (func.__doc__ or "").strip()

        logger.debug(f"Tool: name={func_name}, description={func_description}")

        # Extract parameters from type hints
        extracted_params = _extract_parameters_from_function(func)

        # Use provided parameters or extracted ones
        final_params = parameters if parameters else extracted_params

        # Register the tool in global registry
        logger.debug(f"Registering tool: {func_name}")
        _global_registry.register(func_name, func_description, func, final_params)
        logger.debug(f"Tool registered: {func_name}")

        # Preserve the original function's metadata
        @functools.wraps(func)
        def wrapped_func(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapped_func

    # If name, description, and parameters are all None, apply decorator immediately
    if name is None and description is None and parameters is None:
        logger.debug("No parameters provided, applying decorator immediately")
        return decorator(func)
    return decorator


def _extract_parameters_from_function(func: Callable) -> Dict[str, Any]:
    """
    Extract parameters from function signature and type hints.

    Args:
        func: Python function

    Returns:
        Dictionary of parameter schemas
    """
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)
    parameters = {}

    for param_name, param in sig.parameters.items():
        if param_name == "self" or param_name == "cls":
            continue

        resolved_annotation = type_hints.get(param_name, param.annotation)
        param_schema = _python_annotation_to_schema(resolved_annotation)
        param_schema["description"] = _get_param_description(func, param_name)

        # Don't mark as required for None default or unused defaults
        # The 'required' field in JSON schema will be handled separately
        # during schema generation for tool calls

        parameters[param_name] = param_schema

    return parameters


def _python_type_to_json_type(annotation) -> str:
    """
    Convert Python type to JSON schema type.

    Args:
        annotation: Python type annotation

    Returns:
        JSON schema type string
    """
    type_mapping = {
        str: "string",
        int: "integer",
        float: "number",
        bool: "boolean",
        list: "array",
        dict: "object",
        Any: "string",  # Default to string for Any
    }

    # Handle typing module types
    if hasattr(annotation, "__origin__"):
        if annotation.__origin__ is list:
            return "array"
        elif annotation.__origin__ is dict:
            return "object"

    # Handle Union types
    if hasattr(annotation, "__origin__") and annotation.__origin__ is Union:
        return "string"

    return type_mapping.get(annotation, "string")


def _python_annotation_to_schema(annotation) -> Dict[str, Any]:
    """Convert Python annotation to a JSON schema fragment."""
    origin = get_origin(annotation)
    args = get_args(annotation)

    if annotation in (str, int, float, bool):
        return {"type": _python_type_to_json_type(annotation)}

    if annotation is Any:
        return {"type": "string"}

    if origin in (list, List):
        item_annotation = args[0] if args else Any
        return {
            "type": "array",
            "items": _python_annotation_to_schema(item_annotation),
        }

    if origin in (dict, Dict):
        if len(args) == 2:
            return {
                "type": "object",
                "additionalProperties": _python_annotation_to_schema(args[1]),
            }
        return {"type": "object"}

    if origin is Union:
        non_none_args = [arg for arg in args if arg is not type(None)]
        if len(non_none_args) == 1:
            return _python_annotation_to_schema(non_none_args[0])
        return {"type": "string"}

    return {"type": _python_type_to_json_type(annotation)}


def _get_param_description(func: Callable, param_name: str) -> str:
    """
    Get parameter description from function docstring.

    Args:
        func: Python function
        param_name: Parameter name

    Returns:
        Parameter description
    """
    docstring = func.__doc__
    if not docstring:
        return f"Parameter: {param_name}"

    # Try to extract from docstring
    lines = docstring.strip().split('\n')
    for line in lines:
        if f":{param_name}:" in line:
            parts = line.split(":")
            if len(parts) >= 3:
                return parts[2].strip()
            elif len(parts) >= 2:
                return parts[1].strip()

    return f"Parameter: {param_name}"


# Global tool registry
_global_registry = ToolRegistry()

def get_global_registry() -> ToolRegistry:
    """Get the global tool registry."""
    return _global_registry


def get_tool(name: str) -> Optional[ToolDefinition]:
    """Get a tool from the global registry."""
    return _global_registry.get(name)


def register_tool(
    name: str,
    func: Callable,
    description: str = None,
    parameters: Dict[str, Any] = None,
) -> ToolDefinition:
    """
    Register a tool in the global registry.

    Args:
        name: Tool name
        func: Function to register
        description: Tool description
        parameters: Optional parameters schema

    Returns:
        ToolDefinition
    """
    if description is None:
        description = func.__doc__ or ""
    if parameters is None:
        parameters = _extract_parameters_from_function(func)

    _global_registry.register(name, description, func, parameters)
    return _global_registry.get(name)


def list_global_tools() -> List[Dict[str, Any]]:
    """List all globally registered tools."""
    return _global_registry.list_tools()
