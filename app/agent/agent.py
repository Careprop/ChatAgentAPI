from collections.abc import Sequence

from app.agent.base import AgentBackend
from app.agent.schemas import AgentMessage, AgentResponse
from app.agent.tools import make_save_chat_fact_tool, make_save_fact_tool

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
        memory_context: str | None = None,
        save_facts: bool = True,
        username: str | None = None,
        save_chat_facts: bool = True,
    ) -> AgentResponse:
        instructions = self._instructions
        if memory_context:
            instructions = f"{instructions}\n\n{memory_context}"

        kwargs = dict(instructions=instructions, temperature=temperature)
        tools: list | None = None
        if save_facts:
            tools = [make_save_fact_tool(username)]
            if save_chat_facts:
                tools.append(make_save_chat_fact_tool())
        response = await self._backend.generate(messages, **kwargs, tools=tools)

        # Some backends (e.g. Anthropic) stop after tool calls without a text reply.
        # Make a follow-up call without tools to get the actual response text.
        if not response.content and response.tool_calls:
            text_response = await self._backend.generate(messages, **kwargs)
            return AgentResponse(
                content=text_response.content,
                model=text_response.model,
                tool_calls=response.tool_calls,
            )

        return response
