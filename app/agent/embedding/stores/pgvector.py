from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.embedding.stores.base import EmbeddingStore
from app.db.models.message import Message
from app.db.models.message_embedding import MessageEmbedding


class PgvectorStore(EmbeddingStore):
    """:class:`EmbeddingStore` backed by pgvector inside PostgreSQL."""

    def __init__(self, session: AsyncSession):
        self._session = session

    async def upsert(self, message_id: int, vector: list[float], model: str) -> None:
        stmt = (
            insert(MessageEmbedding)
            .values(message_id=message_id, embedding=vector, model=model)
            .on_conflict_do_update(
                index_elements=["message_id"],
                set_={"embedding": vector, "model": model},
            )
        )
        await self._session.execute(stmt)
        await self._session.commit()

    async def search_in_chat(
        self, chat_id: int, vector: list[float], *, k: int
    ) -> list[int]:
        result = await self._session.execute(
            select(MessageEmbedding.message_id)
            .join(Message, Message.id == MessageEmbedding.message_id)
            .where(Message.chat_id == chat_id)
            .order_by(MessageEmbedding.embedding.cosine_distance(vector))
            .limit(k)
        )
        return list(result.scalars().all())
