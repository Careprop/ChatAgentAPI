from openai import AsyncOpenAI

from app.agent.embedding.base import EmbeddingBackend
from app.config.settings import settings


class OpenAIEmbeddingBackend(EmbeddingBackend):
    """:class:`EmbeddingBackend` backed by the OpenAI Embeddings API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        client: AsyncOpenAI | None = None,
    ):
        self._model = model or settings.openai_embedding_model
        self._client = client or AsyncOpenAI(api_key=api_key or settings.openai_api_key)

    @property
    def model_name(self) -> str:
        return self._model

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = await self._client.embeddings.create(
            model=self._model,
            input=texts,
            dimensions=settings.embedding_dimensions,
        )
        # API guarantees same order as input
        return [item.embedding for item in response.data]
