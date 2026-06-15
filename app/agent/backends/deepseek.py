import json
from collections.abc import Sequence

import openai
from openai import AsyncOpenAI

from app.agent.base import AgentBackend
from app.agent.exceptions import AgentAuthError, AgentProviderError, AgentRateLimitError, AgentTimeoutError
from app.agent.schemas import AgentMessage, AgentResponse, ToolCall, ToolDefinition
from app.config.settings import settings

_DEEPSEEK_BASE_URL = "https://api.deepseek.com"


class DeepSeekBackend(AgentBackend):
    """:class:`AgentBackend` backed by the DeepSeek chat completions API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        client: AsyncOpenAI | None = None,
    ):
        self._model = model or settings.deepseek_model
        self._client = client or AsyncOpenAI(
            api_key=api_key or settings.deepseek_api_key,
            base_url=_DEEPSEEK_BASE_URL,
        )

    async def generate(
        self,
        messages: Sequence[AgentMessage],
        *,
        instructions: str | None = None,
        temperature: float | None = None,
        tools: list[ToolDefinition] | None = None,
    ) -> AgentResponse:
        all_messages: list[dict] = []
        if instructions:
            all_messages.append({"role": "system", "content": instructions})
        all_messages.extend(
            {"role": m.role.value, "content": m.content} for m in messages
        )

        params: dict = {"model": self._model, "messages": all_messages}
        if temperature is not None:
            params["temperature"] = temperature
        if tools:
            params["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in tools
            ]

        try:
            response = await self._client.chat.completions.create(**params)
        except (openai.AuthenticationError, openai.PermissionDeniedError) as exc:
            raise AgentAuthError(f"DeepSeek authentication failed: {exc.message}") from exc
        except openai.RateLimitError as exc:
            raise AgentRateLimitError(f"DeepSeek rate limit exceeded: {exc.message}") from exc
        except openai.APITimeoutError as exc:
            raise AgentTimeoutError("DeepSeek request timed out") from exc
        except openai.APIError as exc:
            raise AgentProviderError(f"DeepSeek error: {exc.message}") from exc

        message = response.choices[0].message
        tool_calls = [
            ToolCall(name=tc.function.name, arguments=json.loads(tc.function.arguments))
            for tc in (message.tool_calls or [])
        ]

        return AgentResponse(
            content=message.content or "",
            model=response.model,
            tool_calls=tool_calls,
            raw=response,
        )
