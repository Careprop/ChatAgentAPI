from abc import ABC, abstractmethod
from collections.abc import Sequence

from app.agent.schemas import AgentMessage, AgentResponse, ToolDefinition


class AgentBackend(ABC):
    """Provider-agnostic interface for a chat completion model."""

    @abstractmethod
    async def generate(
        self,
        messages: Sequence[AgentMessage],
        *,
        instructions: str | None = None,
        temperature: float | None = None,
        tools: list[ToolDefinition] | None = None,
    ) -> AgentResponse:
        """Produce a single assistant reply for the given conversation."""
        raise NotImplementedError
