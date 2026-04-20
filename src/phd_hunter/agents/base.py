"""Base classes for agents."""

from abc import ABC, abstractmethod
from typing import Any, Optional, Dict, List
from dataclasses import dataclass, field
from datetime import datetime
import asyncio


@dataclass
class AgentMessage:
    """Message passed between agents."""
    sender: str
    recipient: str
    task: str
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    priority: int = 1  # 1=normal, 2=high, 3=urgent


@dataclass
class AgentResult:
    """Result from an agent operation."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseAgent(ABC):
    """Base class for all agents."""

    def __init__(self, name: str):
        """Initialize agent.

        Args:
            name: Unique agent identifier
        """
        self.name = name
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._running = False

    @abstractmethod
    async def process(self, message: AgentMessage) -> AgentResult:
        """Process a message. Must be implemented by subclasses."""
        pass

    async def send(self, recipient: str, task: str, data: Dict[str, Any]) -> AgentResult:
        """Send message to another agent."""
        message = AgentMessage(
            sender=self.name,
            recipient=recipient,
            task=task,
            data=data
        )
        # In a full implementation, this would route to the recipient's queue
        return AgentResult(success=True, data={"message_sent": True})

    async def receive(self) -> AgentMessage:
        """Receive next message from queue."""
        return await self._message_queue.get()

    def start(self) -> None:
        """Start agent message loop."""
        self._running = True
        # Would normally start background task here

    def stop(self) -> None:
        """Stop agent."""
        self._running = False

    def log(self, message: str, level: str = "info") -> None:
        """Log message with agent name prefix."""
        from phd_hunter.utils.logger import get_logger
        logger = get_logger(self.name)
        getattr(logger, level)(f"[{self.name}] {message}")
