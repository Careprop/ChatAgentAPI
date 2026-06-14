from abc import ABC, abstractmethod

from app.agent.schemas import Role

MIN_EMBED_LENGTH = 20


class EmbeddingBackend(ABC):
    """Provider-agnostic interface for generating text embeddings."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Identifier of the model used (stored alongside vectors for provenance)."""
        raise NotImplementedError

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""
        raise NotImplementedError


def should_embed(role: str, content: str) -> bool:
    """Return True when a message is worth embedding.

    System messages and very short messages (greetings, one-word replies)
    are skipped — they add noise without meaningful semantic signal.
    """
    if role == Role.SYSTEM:
        return False
    return len(content.strip()) >= MIN_EMBED_LENGTH
