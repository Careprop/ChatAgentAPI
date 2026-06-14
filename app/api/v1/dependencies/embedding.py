from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.embedding.base import EmbeddingBackend
from app.agent.embedding.factory import create_embedding_backend
from app.agent.embedding.stores.pgvector import PgvectorStore

_embedding_backend: EmbeddingBackend | None = None
_backend_init_attempted = False


def get_embedding_backend() -> EmbeddingBackend | None:
    """Return the configured embedding backend (cached), or None if unavailable."""
    global _embedding_backend, _backend_init_attempted
    if not _backend_init_attempted:
        _backend_init_attempted = True
        _embedding_backend = create_embedding_backend()
    return _embedding_backend


def get_embedding_store(session: AsyncSession) -> PgvectorStore:
    return PgvectorStore(session)
