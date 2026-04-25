"""ContextManager: Manages conversation state and context engineering."""

from __future__ import annotations

import copy
import logging
from typing import Any, Dict, List, Optional, Protocol, Tuple

logger = logging.getLogger(__name__)


class Message:
    """Represents a conversation message."""

    def __init__(self, role: str, content: str, metadata: Dict[str, Any] = None):
        """
        Initialize a message.

        Args:
            role: Message role ("user", "assistant", "system", "tool")
            content: Message content
            metadata: Optional metadata
        """
        self.role = role
        self.content = content
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        msg = {
            "role": self.role,
            "content": self.content,
        }
        if self.metadata:
            msg["metadata"] = self.metadata
        return msg

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Message:
        """Create from dictionary."""
        return cls(
            role=data["role"],
            content=data["content"],
            metadata=data.get("metadata"),
        )


class FewShotExample:
    """Represents a few-shot example."""

    def __init__(
        self,
        user_message: str,
        assistant_message: str,
        metadata: Dict[str, Any] = None,
    ):
        """
        Initialize a few-shot example.

        Args:
            user_message: User message content
            assistant_message: Assistant message content
            metadata: Optional metadata
        """
        self.user_message = user_message
        self.assistant_message = assistant_message
        self.metadata = metadata or {}

    def to_messages(self) -> List[Dict[str, str]]:
        """Convert to messages."""
        return [
            {"role": "user", "content": self.user_message},
            {"role": "assistant", "content": self.assistant_message},
        ]


class ContextManager:
    """Manages conversation context with various context engineering techniques."""

    def __init__(self):
        """Initialize context manager."""
        self._messages: List[Message] = []
        self._system_prompt: Optional[str] = None
        self._few_shot_examples: List[FewShotExample] = []
        self._rag_contexts: List[str] = []
        self._rag_documents: List[str] = []

    def set_system_prompt(self, prompt: str) -> "ContextManager":
        """
        Set the system prompt.

        Args:
            prompt: System prompt content

        Returns:
            self for chaining
        """
        self._system_prompt = prompt
        logger.debug(f"System prompt set: {prompt[:50]}..." if len(prompt) > 50 else f"System prompt set: {prompt}")
        return self

    def add_system_prompt(self, prompt: str) -> "ContextManager":
        """
        Append to system prompt.

        Args:
            prompt: Additional system prompt content

        Returns:
            self for chaining
        """
        if self._system_prompt is None:
            self._system_prompt = prompt
        else:
            self._system_prompt += "\n\n" + prompt
        logger.debug(f"System prompt appended: {prompt[:50]}..." if len(prompt) > 50 else f"System prompt appended: {prompt}")
        return self

    def add_user_message(self, message: str) -> "ContextManager":
        """
        Add a user message to the context.

        Args:
            message: User message content

        Returns:
            self for chaining
        """
        self._messages.append(Message(role="user", content=message))
        logger.debug(f"Added user message: {message[:50]}..." if len(message) > 50 else f"Added user message: {message}")
        return self

    def add_assistant_message(self, message: str) -> "ContextManager":
        """
        Add an assistant message to the context.

        Args:
            message: Assistant message content

        Returns:
            self for chaining
        """
        self._messages.append(Message(role="assistant", content=message))
        logger.debug(f"Added assistant message: {message[:50]}..." if len(message) > 50 else f"Added assistant message: {message}")
        return self

    def add_tool_message(self, message: str, tool_call_id: str = None) -> "ContextManager":
        """
        Add a tool message to the context.

        Args:
            message: Tool message content
            tool_call_id: Optional tool call ID

        Returns:
            self for chaining
        """
        msg = Message(role="tool", content=message)
        if tool_call_id:
            msg.metadata["tool_call_id"] = tool_call_id
        self._messages.append(msg)
        logger.debug(f"Added tool message: {message[:50]}..." if len(message) > 50 else f"Added tool message: {message}")
        return self

    def add_few_shot(
        self,
        examples: List[Dict[str, str]] | List[FewShotExample],
    ) -> "ContextManager":
        """
        Add few-shot examples.

        Args:
            examples: List of examples as dictionaries or FewShotExample objects

        Returns:
            self for chaining
        """
        if not isinstance(examples[0], FewShotExample):
            examples = [
                FewShotExample(
                    user_message=ex["user"],
                    assistant_message=ex["assistant"],
                )
                for ex in examples
            ]

        self._few_shot_examples.extend(examples)
        logger.debug(f"Added {len(examples)} few-shot examples")
        return self

    def add_few_shot_example(
        self,
        user_message: str,
        assistant_message: str,
    ) -> "ContextManager":
        """
        Add a single few-shot example.

        Args:
            user_message: User message content
            assistant_message: Assistant message content

        Returns:
            self for chaining
        """
        self._few_shot_examples.append(
            FewShotExample(user_message=user_message, assistant_message=assistant_message)
        )
        logger.debug(f"Added few-shot example: user={user_message[:30]}..., assistant={assistant_message[:30]}...")
        return self

    def inject_rag_knowledge(self, documents: List[str] | List[Dict[str, Any]]) -> "ContextManager":
        """
        Inject RAG (Retrieval-Augmented Generation) knowledge.

        Args:
            documents: List of document contents or dictionaries with content and metadata

        Returns:
            self for chaining
        """
        if isinstance(documents[0], dict):
            self._rag_documents = [doc["content"] for doc in documents]
            self._rag_contexts = [
                f"Document {i+1}: {doc['content']}\nMetadata: {doc.get('metadata', {})}"
                for i, doc in enumerate(documents)
            ]
        else:
            self._rag_documents = documents
            self._rag_contexts = [f"Document {i+1}: {doc}" for i, doc in enumerate(documents)]

        logger.debug(f"Injected RAG knowledge for {len(documents)} documents")
        return self

    def add_rag_context(self, context: str) -> "ContextManager":
        """
        Add additional RAG context.

        Args:
            context: RAG context string

        Returns:
            self for chaining
        """
        self._rag_contexts.append(context)
        logger.debug(f"Added RAG context: {context[:50]}...")
        return self

    def clear(self) -> "ContextManager":
        """
        Clear all messages and context.

        Returns:
            self for chaining
        """
        self._messages.clear()
        self._system_prompt = None
        self._few_shot_examples.clear()
        self._rag_contexts.clear()
        self._rag_documents.clear()
        logger.debug("Cleared context")
        return self

    def reset(self) -> "ContextManager":
        """
        Reset to initial state while preserving configuration.

        Returns:
            self for chaining
        """
        self._messages.clear()
        logger.debug("Reset conversation")
        return self

    def _build_context_text(self) -> str:
        """
        Build context text from RAG documents.

        Returns:
            Formatted context text
        """
        if not self._rag_contexts:
            return ""

        context_parts = []
        for i, ctx in enumerate(self._rag_contexts, 1):
            context_parts.append(f"Context {i}: {ctx}")
        return "\n\n".join(context_parts)

    def build(
        self,
        include_few_shot: bool = True,
        include_rag: bool = True,
    ) -> List[Dict[str, str]]:
        """
        Build the final message list.

        Args:
            include_few_shot: Whether to include few-shot examples
            include_rag: Whether to include RAG context

        Returns:
            List of message dictionaries
        """
        messages: List[Dict[str, str]] = []

        # Add system prompt
        if self._system_prompt:
            messages.append({"role": "system", "content": self._system_prompt})

        # Add few-shot examples
        if include_few_shot and self._few_shot_examples:
            for example in self._few_shot_examples:
                messages.extend(example.to_messages())

        # Add RAG context
        if include_rag and self._rag_contexts:
            context_text = self._build_context_text()
            messages.append({
                "role": "system",
                "content": f"Relevant context:\n\n{context_text}"
            })

        # Add conversation messages
        messages.extend(msg.to_dict() for msg in self._messages)

        logger.debug(f"Built context with {len(messages)} messages")
        return messages

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """
        Get the conversation history without system prompt or examples.

        Returns:
            List of message dictionaries
        """
        return [msg.to_dict() for msg in self._messages]

    def get_message_count(self) -> int:
        """
        Get the number of messages in the context.

        Returns:
            Number of messages (including system prompt, few-shot, and RAG)
        """
        count = 0
        if self._system_prompt:
            count += 1  # System prompt
        if self._few_shot_examples:
            count += len(self._few_shot_examples)  # Few-shot examples
        if self._rag_contexts:
            count += len(self._rag_contexts)  # RAG contexts
        if self._messages:
            count += len(self._messages)  # Conversation messages
        return count

    def get_context_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the context.

        Returns:
            Dictionary with context statistics
        """
        role_counts = {}
        for msg in self._messages:
            role = msg.role
            role_counts[role] = role_counts.get(role, 0) + 1

        return {
            "total_messages": len(self._messages),
            "user_messages": role_counts.get("user", 0),
            "assistant_messages": role_counts.get("assistant", 0),
            "system_prompt": bool(self._system_prompt),
            "few_shot_examples": len(self._few_shot_examples),
            "rag_documents": len(self._rag_documents),
            "rag_contexts": len(self._rag_contexts),
        }

    def __len__(self) -> int:
        """Get the length of the message list."""
        return len(self._messages)

    def __repr__(self) -> str:
        """String representation."""
        stats = self.get_context_stats()
        return f"ContextManager(stats={stats})"
