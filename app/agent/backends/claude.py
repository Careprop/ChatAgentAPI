from collections.abc import Sequence

import anthropic
from anthropic import AsyncAnthropic

from app.agent.base import AgentBackend
from app.agent.exceptions import AgentAuthError, AgentProviderError, AgentRateLimitError, AgentTimeoutError
from app.agent.schemas import AgentMessage, AgentResponse, ToolCall, ToolDefinition, Role
from app.config.settings import settings


class ClaudeBackend(AgentBackend):
    """:class:`AgentBackend` backed by the Anthropic Claude messages API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        client: AsyncAnthropic | None = None,
    ):
        self._model = model or settings.anthropic_model
        self._client = client or AsyncAnthropic(
            api_key=api_key or settings.anthropic_api_key,
        )

    async def generate(
        self,
        messages: Sequence[AgentMessage],
        *,
        instructions: str | None = None,
        temperature: float | None = None,
        tools: list[ToolDefinition] | None = None,
    ) -> AgentResponse:
        chat_messages = [
            {"role": m.role.value, "content": m.content}
            for m in messages
            if m.role != Role.SYSTEM
        ]

        params: dict = {
            "model": self._model,
            "max_tokens": 8096,
            "messages": chat_messages,
        }
        if instructions:
            params["system"] = instructions
        if temperature is not None:
            params["temperature"] = temperature
        if tools:
            params["tools"] = [
                {
                    "name": t.name,
                    "description": t.description,
                    "input_schema": t.parameters,
                }
                for t in tools
            ]

        try:
            response = await self._client.messages.create(**params)
        except (anthropic.AuthenticationError, anthropic.PermissionDeniedError) as exc:
            raise AgentAuthError(f"Anthropic authentication failed: {exc.message}") from exc
        except anthropic.RateLimitError as exc:
            raise AgentRateLimitError(f"Anthropic rate limit exceeded: {exc.message}") from exc
        except anthropic.APITimeoutError as exc:
            raise AgentTimeoutError("Anthropic request timed out") from exc
        except anthropic.APIError as exc:
            raise AgentProviderError(f"Anthropic error: {exc.message}") from exc

        text = "".join(
            block.text for block in response.content
            if block.type == "text"
        )
        tool_calls = [
            ToolCall(name=block.name, arguments=block.input)
            for block in response.content
            if block.type == "tool_use"
        ]

        return AgentResponse(
            content=text,
            model=response.model,
            tool_calls=tool_calls,
            raw=response,
        )
