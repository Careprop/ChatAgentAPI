from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.message import Message


class MessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _next_sequence(self, chat_id: int) -> int:
        result = await self.session.execute(
            select(func.coalesce(func.max(Message.sequence), 0)).where(
                Message.chat_id == chat_id
            )
        )
        return result.scalar_one() + 1

    async def create(self, chat_id: int, role: str, content: str) -> Message:
        seq = await self._next_sequence(chat_id)
        message = Message(chat_id=chat_id, role=role, content=content, sequence=seq)
        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)
        return message

    async def get_by_external_id(self, external_id: UUID) -> Message | None:
        result = await self.session.execute(
            select(Message).where(Message.external_id == external_id)
        )
        return result.scalar_one_or_none()

    async def list_by_chat(self, chat_id: int, *, limit: int) -> list[Message]:
        """Return the `limit` most recent messages ordered oldest-first."""
        result = await self.session.execute(
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.sequence.desc())
            .limit(limit)
        )
        rows = result.scalars().all()
        return list(reversed(rows))

    async def get_by_ids(self, ids: list[int]) -> list[Message]:
        if not ids:
            return []
        result = await self.session.execute(
            select(Message).where(Message.id.in_(ids))
        )
        return list(result.scalars().all())
