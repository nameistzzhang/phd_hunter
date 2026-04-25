"""Simple integration test for api_infra LLM calling."""

import asyncio
import json
from pathlib import Path

from api_infra import ModelClient, ContextManager


CONFIG_PATH = Path(__file__).parent / ".." / "src" / "phd_hunter" / "frontend" / "hound_config.json"


def load_key() -> str:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)["api_key"]


API_KEY = load_key()
MODEL = "deepseek-v3.2"


async def test_basic_chat():
    """Test basic chat with deepseek-v3.2."""
    print("=" * 60)
    print("Test: Basic Chat with deepseek-v3.2")
    print("=" * 60)

    client = ModelClient(
        provider="yunwu",
        model=MODEL,
        api_keys=[API_KEY],
        temperature=0.7,
        max_tokens=500,
    )

    context = ContextManager()
    context.set_system_prompt("You are a helpful assistant. Be concise.")
    context.add_user_message("What is the capital of France? Answer in one sentence.")

    response = await client.generate(
        messages=context.build(),
        track_cost=True,
    )

    print(f"Response: {response.content}")
    print(f"Prompt tokens: {response.metadata.prompt_tokens}")
    print(f"Completion tokens: {response.metadata.completion_tokens}")
    print(f"Total cost: ${response.metadata.total_cost:.6f}")
    print()

    await client.close()


async def test_context_conversation():
    """Test multi-turn conversation."""
    print("=" * 60)
    print("Test: Multi-turn Conversation")
    print("=" * 60)

    client = ModelClient(
        provider="yunwu",
        model=MODEL,
        api_keys=[API_KEY],
        temperature=0.7,
        max_tokens=500,
    )

    context = ContextManager()
    context.set_system_prompt("You are a PhD application advisor. Give concise advice.")

    # Turn 1
    context.add_user_message("I'm interested in NLP research. What are hot topics in 2025? List 3.")
    response1 = await client.generate(messages=context.build(), track_cost=True)
    print(f"User: I'm interested in NLP research. What are hot topics in 2025?")
    print(f"Assistant: {response1.content}")
    context.add_assistant_message(response1.content)
    print()

    # Turn 2 - should remember context
    context.add_user_message("Which of these would be best for a beginner PhD student? Just the name.")
    response2 = await client.generate(messages=context.build(), track_cost=True)
    print(f"User: Which of these would be best for a beginner PhD student?")
    print(f"Assistant: {response2.content}")
    print()

    await client.close()


async def main():
    print("\n" + "=" * 60)
    print("LLM Integration Test")
    print(f"Model: {MODEL}")
    print("=" * 60 + "\n")

    try:
        await test_basic_chat()
        await test_context_conversation()

        print("=" * 60)
        print("All tests passed!")
        print("=" * 60)

    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    asyncio.run(main())
