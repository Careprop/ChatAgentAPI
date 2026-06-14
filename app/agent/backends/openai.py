from collections.abc import Sequence

import openai
from openai import AsyncOpenAI

from app.agent.base import AgentBackend
from app.agent.exceptions import AgentAuthError, AgentProviderError, AgentRateLimitError, AgentTimeoutError
from app.agent.schemas import AgentMessage, AgentResponse
from app.config.settings import settings


class OpenAIBackend(AgentBackend):
    """:class:`AgentBackend` backed by the OpenAI Responses API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        client: AsyncOpenAI | None = None,
    ):
        self._model = model or settings.openai_model
        self._client = client or AsyncOpenAI(
            api_key=api_key or settings.openai_api_key
        )

    async def generate(
        self,
        messages: Sequence[AgentMessage],
        *,
        instructions: str | None = None,
        temperature: float | None = None,
    ) -> AgentResponse:
        params: dict = {
            "model": self._model,
            "input": [
                {"role": message.role.value, "content": message.content}
                for message in messages
            ],
            "store": False,
        }

        if instructions is not None:
            params["instructions"] = instructions

        if temperature is not None:
            params["temperature"] = temperature

        try:
            response = await self._client.responses.create(**params)
        except (openai.AuthenticationError, openai.PermissionDeniedError) as exc:
            raise AgentAuthError(f"OpenAI authentication failed: {exc.message}") from exc
        except openai.RateLimitError as exc:
            raise AgentRateLimitError(f"OpenAI rate limit exceeded: {exc.message}") from exc
        except openai.APITimeoutError as exc:
            raise AgentTimeoutError("OpenAI request timed out") from exc
        except openai.APIError as exc:
            raise AgentProviderError(f"OpenAI error: {exc.message}") from exc

        return AgentResponse(
            content=response.output_text,
            model=response.model,
            raw=response,
        )
