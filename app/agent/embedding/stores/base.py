from abc import ABC, abstractmethod


class EmbeddingStore(ABC):
    """Provider-agnostic interface for persisting and querying message embeddings."""

    @abstractmethod
    async def upsert(self, message_id: int, vector: list[float], model: str) -> None:
        """Persist or overwrite the embedding for a message."""
        raise NotImplementedError

    @abstractmethod
    async def search_in_chat(
        self, chat_id: int, vector: list[float], *, k: int
    ) -> list[int]:
        """Return up to `k` message IDs from `chat_id` closest to `vector`."""
        raise NotImplementedError
