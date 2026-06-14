from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.embedding.backends.openai import OpenAIEmbeddingBackend
from app.agent.embedding.stores.pgvector import PgvectorStore

_embedding_backend: OpenAIEmbeddingBackend | None = None


def get_embedding_backend() -> OpenAIEmbeddingBackend:
    global _embedding_backend
    if _embedding_backend is None:
        _embedding_backend = OpenAIEmbeddingBackend()
    return _embedding_backend


def get_embedding_store(session: AsyncSession) -> PgvectorStore:
    return PgvectorStore(session)
