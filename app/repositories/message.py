from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models.message import Message


class MessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _next_sequence(self, chat_id: int) -> int:
        # Advisory lock serializes sequence allocation per chat without conflicting
        # with FK-triggered ShareLocks that a SELECT…FOR UPDATE would deadlock against.
        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(:chat_id)"), {"chat_id": chat_id}
        )
        result = await self.session.execute(
            select(func.coalesce(func.max(Message.sequence), 0)).where(
                Message.chat_id == chat_id
            )
        )
        return result.scalar_one() + 1

    async def create(
        self,
        chat_id: int,
        role: str,
        content: str,
        *,
        user_id: int | None = None,
        chain_id: int | None = None,
    ) -> Message:
        seq = await self._next_sequence(chat_id)
        message = Message(
            chat_id=chat_id,
            role=role,
            content=content,
            sequence=seq,
            user_id=user_id,
            chain_id=chain_id,
        )
        self.session.add(message)
        await self.session.flush()
        await self.session.refresh(message)
        return message

    async def get_by_external_id(self, external_id: UUID) -> Message | None:
        result = await self.session.execute(
            select(Message).where(Message.external_id == external_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, message_id: int) -> Message | None:
        result = await self.session.execute(
            select(Message).where(Message.id == message_id)
        )
        return result.scalar_one_or_none()

    async def list_direct(self, chat_id: int, *, limit: int) -> list[Message]:
        """Recent messages not in any chain — direct agent-call exchanges."""
        result = await self.session.execute(
            select(Message)
            .where(
                Message.chat_id == chat_id,
                Message.chain_id.is_(None),
            )
            .order_by(Message.sequence.desc())
            .limit(limit)
        )
        return list(reversed(result.scalars().all()))

    async def list_by_chat(self, chat_id: int, *, limit: int) -> list[Message]:
        result = await self.session.execute(
            select(Message)
            .where(Message.chat_id == chat_id)
            .order_by(Message.sequence.desc())
            .limit(limit)
        )
        rows = result.scalars().all()
        return list(reversed(rows))

    async def list_by_chain(self, chain_id: int) -> list[Message]:
        result = await self.session.execute(
            select(Message)
            .where(Message.chain_id == chain_id)
            .options(joinedload(Message.user))
            .order_by(Message.sequence)
        )
        return list(result.scalars().all())

    async def get_last_by_user(
        self, chat_id: int, user_id: int
    ) -> Message | None:
        result = await self.session.execute(
            select(Message)
            .where(
                Message.chat_id == chat_id,
                Message.user_id == user_id,
            )
            .order_by(Message.sequence.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_ids(self, ids: list[int]) -> list[Message]:
        if not ids:
            return []
        result = await self.session.execute(
            select(Message)
            .where(Message.id.in_(ids))
            .options(joinedload(Message.user))
        )
        return list(result.scalars().all())
