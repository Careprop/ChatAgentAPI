from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.embedding.stores.base import EmbeddingStore
from app.db.models.chat import Chat
from app.db.models.message import Message, MessageType
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

    async def search_in_chat(
        self, chat_id: int, vector: list[float], *, k: int
    ) -> list[int]:
        """Top-k conversational messages (excludes facts) by cosine similarity."""
        result = await self._session.execute(
            select(MessageEmbedding.message_id)
            .join(Message, Message.id == MessageEmbedding.message_id)
            .where(
                Message.chat_id == chat_id,
                Message.message_type == MessageType.MESSAGE,
            )
            .order_by(MessageEmbedding.embedding.cosine_distance(vector))
            .limit(k)
        )
        return list(result.scalars().all())

    async def search_facts(
        self, chat_id: int, user_id: int, vector: list[float], *, k: int
    ) -> list[tuple[int, list[float]]]:
        """Top-k facts for a user, returning (message_id, embedding_vector) for dedup."""
        result = await self._session.execute(
            select(MessageEmbedding.message_id, MessageEmbedding.embedding)
            .join(Message, Message.id == MessageEmbedding.message_id)
            .where(
                Message.chat_id == chat_id,
                Message.user_id == user_id,
                Message.message_type == MessageType.FACT,
            )
            .order_by(MessageEmbedding.embedding.cosine_distance(vector))
            .limit(k)
        )
        return [(row.message_id, [float(x) for x in row.embedding]) for row in result]

    async def search_other_chats(
        self, exclude_chat_id: int, vector: list[float], *, k: int
    ) -> list[int]:
        """Top-k conversational messages (excludes facts) from other non-deleted chats."""
        result = await self._session.execute(
            select(MessageEmbedding.message_id)
            .join(Message, Message.id == MessageEmbedding.message_id)
            .join(Chat, Chat.id == Message.chat_id)
            .where(
                Message.chat_id != exclude_chat_id,
                Message.message_type == MessageType.MESSAGE,
                Chat.deleted_at.is_(None),
            )
            .order_by(MessageEmbedding.embedding.cosine_distance(vector))
            .limit(k)
        )
        return list(result.scalars().all())
