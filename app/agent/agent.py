from collections.abc import Sequence

from app.agent.base import AgentBackend
from app.agent.schemas import AgentMessage, AgentResponse

DEFAULT_INSTRUCTIONS = "You are a helpful assistant."


class Agent:
    """A chat agent: a backend model paired with system instructions."""

    def __init__(
        self,
        backend: AgentBackend,
        *,
        instructions: str = DEFAULT_INSTRUCTIONS,
    ):
        self._backend = backend
        self._instructions = instructions

    async def respond(
        self,
        messages: Sequence[AgentMessage],
        *,
        temperature: float | None = None,
        open_chains_context: str | None = None,
        memory_context: str | None = None,
    ) -> AgentResponse:
        instructions = self._instructions
        if open_chains_context:
            instructions = f"{instructions}\n\n{open_chains_context}"
        if memory_context:
            instructions = f"{instructions}\n\n{memory_context}"
        return await self._backend.generate(
            messages,
            instructions=instructions,
            temperature=temperature,
        )
