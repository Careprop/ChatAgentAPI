from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.embedding.factory import get_embedding_backend
from app.agent.embedding.stores.pgvector import PgvectorStore


def get_embedding_store(session: AsyncSession) -> PgvectorStore:
    return PgvectorStore(session)


__all__ = ["get_embedding_backend", "get_embedding_store"]
