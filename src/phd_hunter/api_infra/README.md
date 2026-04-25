# API Infrastructure

A robust Python package for calling closed-source AI APIs with advanced features including context management, few-shot learning, RAG, and tool calling.

## 🚀 Features

- ✨ **Simple API** - Easy to use, intuitive interface
- 🎯 **Context Management** - Manage conversation history seamlessly
- 📚 **Few-shot Learning** - Teach AI with examples
- 🗄️ **RAG Integration** - Inject knowledge from documents
- 🔧 **Tool Calling** - Let AI execute Python functions
- 💰 **Cost Tracking** - Monitor token usage and costs
- 🔄 **Multi-model Support** - Switch between different AI models
- ⚡ **Async Support** - Built-in async/await for high performance

## 📦 Installation

### Prerequisites

- Python 3.8 or higher
- `uv` package manager (recommended) or `pip`

### Install with uv (Recommended)

```bash
# Install the package in editable mode
uv pip install -e src/api_infra

# Or install directly
uv pip install api-infra
```

### Install with pip

```bash
# Install the package in editable mode
pip install -e src/api_infra

# Or install directly
pip install api-infra
```

## 🎓 Quick Start

### 1. Basic Chat

```python
from api_infra import ModelClient

# Create client
client = ModelClient(
    provider="yunwu",
    model="glm-5",
    api_keys=["your-api-key"]
)

# Send message
response = await client.generate(
    messages=[{"role": "user", "content": "Hello!"}],
    track_cost=True
)

print(response.content)
print(f"Cost: ${response.metadata.total_cost:.6f}")

# Cleanup
await client.close()
```

### 2. Context Management

```python
from api_infra import ModelClient, ContextManager

client = ModelClient(provider="yunwu", model="glm-5", api_keys=[API_KEY])
context = ContextManager()

# Set system prompt
context.set_system_prompt("You are a helpful assistant.")

# Build conversation
context.add_user_message("What is 2+2?")
context.add_assistant_message("2+2=4")

# Add follow-up question
context.add_user_message("And 3+3?")

# Generate response with context
response = await client.generate(messages=context.build(), track_cost=True)

print(response.content)
```

### 3. Few-shot Learning

```python
from api_infra import ModelClient, ContextManager

client = ModelClient(provider="yunwu", model="glm-5", api_keys=[API_KEY])
context = ContextManager()

# Set system prompt
context.set_system_prompt("You are a math tutor.")

# Add few-shot examples
context.add_few_shot([
    {"user": "5 + 3 = ?", "assistant": "8"},
    {"user": "10 - 4 = ?", "assistant": "6"},
    {"user": "7 * 8 = ?", "assistant": "56"},
])

# Ask a new question
context.add_user_message("12 / 3 = ?")

# Generate response
response = await client.generate(messages=context.build(), track_cost=True)
```

### 4. RAG Knowledge Injection

```python
from api_infra import ModelClient, ContextManager

client = ModelClient(provider="yunwu", model="glm-5", api_keys=[API_KEY])
context = ContextManager()

# Set system prompt with knowledge
context.set_system_prompt("You are a research assistant with the following documents:")

# Inject documents
documents = [
    {"content": "Paris is the capital of France with 2.1 million people.", "source": "doc1"},
    {"content": "The Eiffel Tower was built in 1889.", "source": "doc2"},
]
context.inject_rag_knowledge(documents)

# Ask a question based on the documents
context.add_user_message("What do you know about Paris?")

response = await client.generate(messages=context.build(), track_cost=True)
```

### 5. Tool Calling

```python
from api_infra import ModelClient, ContextManager, tool

# Define tools
@tool(description="Get weather information")
def get_weather(location: str) -> str:
    """Get weather for a location"""
    return f"{location}: 22°C, Sunny"

@tool(description="Search database")
def search_database(query: str) -> str:
    """Search the database"""
    return f"Found {len(query)} results"

# Create client
client = ModelClient(provider="yunwu", model="glm-5", api_keys=[API_KEY])

# Generate with tools
response = await client.generate(
    messages=[{"role": "user", "content": "What's the weather in Beijing?"}],
    tools=[get_weather, search_database],
    track_cost=True
)

print(response.content)
```

## 📚 API Reference

### ModelClient

Main class for interacting with AI models.

**Parameters:**
- `provider` (str): AI provider (currently supports "yunwu")
- `model` (str): Model name (e.g., "glm-5", "deepseek-v3.2")
- `api_keys` (List[str]): List of API keys for routing
- `temperature` (float): Sampling temperature (default: 0.7)
- `max_tokens` (int): Maximum tokens to generate (default: 2000)
- `timeout` (float): Request timeout in seconds (default: 60.0)
- `enable_routing` (bool): Enable API key routing (default: True)

**Methods:**
- `generate(messages, tools=None, temperature=None, max_tokens=None, track_cost=False)` - Generate response
- `close()` - Close client connection
- `__aenter__()` / `__aexit__()` - Context manager support

### ContextManager

Manages conversation context with various context engineering techniques.

**Methods:**
- `set_system_prompt(prompt)` - Set system prompt
- `add_user_message(message)` - Add user message
- `add_assistant_message(message)` - Add assistant message
- `add_few_shot(examples)` - Add few-shot examples
- `inject_rag_knowledge(documents)` - Inject RAG knowledge
- `build(include_few_shot=True, include_rag=True)` - Build final message list
- `clear()` - Clear all context
- `reset()` - Reset conversation while preserving configuration

### Tool Decorator

Convert Python functions into LLM-callable tools.

```python
@tool(description="Tool description")
def my_function(param: str) -> str:
    """Function docstring"""
    return result
```

## 🎮 Demo

Run the interactive demo to learn all features:

```bash
# Make sure api_infra is installed
uv pip install -e src/api_infra

# Run the demo
python -m integration_tests.demo_integration
```

The demo includes 7 interactive lessons covering:
1. Basic chat
2. Context management
3. Few-shot learning
4. RAG knowledge injection
5. Tool calling
6. Multi-model support
7. Complete workflow

## 🏗️ Project Structure

```
src/api_infra/
├── __init__.py           # Main package exports
├── setup.py             # Package setup configuration
├── README.md            # This file
├── core/
│   ├── __init__.py
│   └── client.py        # ModelClient, Provider, API calls
├── context/
│   ├── __init__.py
│   └── manager.py       # ContextManager, Message, FewShotExample
└── tools/
    ├── __init__.py
    └── decorator.py     # Tool decorator, ToolRegistry
```

## 🔧 Configuration

### API Configuration

```python
from api_infra.core.client import Provider

# Define available providers
provider = Provider.YUNWU  # or other providers

# Available models
models = [
    "glm-5",
    "deepseek-v3.2",
    "qwen3.5-397b-a17b",
    "gemini-3.1-pro-preview",
    "gpt-5.2",
    "claude-sonnet-4-6",
]
```

### Logging

The package uses Python's logging module. Configure it as needed:

```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Options: DEBUG, INFO, WARNING, ERROR
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Output to file
logging.basicConfig(
    level=logging.INFO,
    filename='api_infra.log',
    filemode='a'
)
```

## 💰 Cost Tracking

Track token usage and costs:

```python
response = await client.generate(
    messages=[{"role": "user", "content": "Hello!"}],
    track_cost=True
)

print(f"Prompt tokens: {response.metadata.prompt_tokens}")
print(f"Completion tokens: {response.metadata.completion_tokens}")
print(f"Total tokens: {response.metadata.total_tokens}")
print(f"Total cost: ${response.metadata.total_cost:.6f}")
```

## 🌟 Supported Models

- **glm-5**: General purpose model
- **deepseek-v3.2**: DeepSeek model
- **qwen3.5-397b-a17b**: Qwen model
- **gemini-3.1-pro-preview**: Gemini model
- **gpt-5.2**: GPT model
- **claude-sonnet-4-6**: Claude model

## 📝 Examples

See more examples in the `integration_tests/` directory:

- `demo_integration.py` - Interactive tutorial with 7 lessons
- `api_infra_demo.py` - Complete demonstration of all features
- `api_infra_usage.py` - Simple usage examples

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License - feel free to use in your projects.

## 🙏 Acknowledgments

Built for easy integration with closed-source AI APIs with powerful context engineering capabilities.
