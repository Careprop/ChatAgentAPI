import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.agent.embedding.base import EmbeddingBackend

_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="st-embed")


class SentenceTransformersBackend(EmbeddingBackend):
    """Local embedding backend powered by sentence-transformers (no API key needed)."""

    def __init__(self, model_name: str):
        self._model_name = model_name
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)

    @property
    def model_name(self) -> str:
        return self._model_name

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        loop = asyncio.get_running_loop()

        def _encode() -> list[list[float]]:
            self._load()
            return self._model.encode(texts, normalize_embeddings=True).tolist()

        return await loop.run_in_executor(_executor, _encode)
