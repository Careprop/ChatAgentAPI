import httpx

from app.agent.embedding.base import EmbeddingBackend


class RemoteEmbeddingBackend(EmbeddingBackend):
    """Delegates embedding generation to the worker HTTP service."""

    def __init__(self, base_url: str, model_name: str, api_key: str = ""):
        self._base_url = base_url.rstrip("/")
        self._model_name = model_name
        self._api_key = api_key

    @property
    def model_name(self) -> str:
        return self._model_name

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        headers = {"X-Worker-Key": self._api_key} if self._api_key else {}
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self._base_url}/embed",
                json={"texts": texts},
                headers=headers,
            )
            response.raise_for_status()
            return response.json()["vectors"]
