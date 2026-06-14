from collections.abc import Sequence

import anthropic
from anthropic import AsyncAnthropic

from app.agent.base import AgentBackend
from app.agent.exceptions import AgentAuthError, AgentProviderError, AgentRateLimitError, AgentTimeoutError
from app.agent.schemas import AgentMessage, AgentResponse, Role
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
    ) -> AgentResponse:
        # Anthropic separates system prompt from the messages list.
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

        return AgentResponse(
            content=response.content[0].text,
            model=response.model,
            raw=response,
        )
