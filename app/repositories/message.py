import math
from uuid import UUID

from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.db.models.message import Message, MessageType


def _estimate_tokens(content: str) -> int:
    return max(1, math.ceil(len(content) / 4))


class MessageRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _next_sequence(self, chat_id: int) -> int:
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
        message_type: str = MessageType.MESSAGE,
        metadata: dict | None = None,
    ) -> Message:
        seq = await self._next_sequence(chat_id)
        message = Message(
            chat_id=chat_id,
            role=role,
            content=content,
            sequence=seq,
            user_id=user_id,
            message_type=message_type,
            token_count=_estimate_tokens(content),
            msg_metadata=metadata,
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

    async def list_for_context(self, chat_id: int, *, token_budget: int) -> list[Message]:
        """Recent MESSAGE-type messages fitting within token_budget (oldest-first).

        Uses a SQL window function to compute a running token sum newest-first,
        then keeps only rows where the cumulative total stays within the budget.
        Two queries: one for IDs, one to load full ORM objects with user joined.
        """
        running = func.sum(Message.token_count).over(
            order_by=Message.id.desc()
        ).label("running_total")

        subq = (
            select(Message.id, running)
            .where(
                Message.chat_id == chat_id,
                Message.message_type == MessageType.MESSAGE,
            )
            .subquery()
        )

        ids_result = await self.session.execute(
            select(subq.c.id).where(subq.c.running_total <= token_budget)
        )
        ids = list(ids_result.scalars().all())
        if not ids:
            return []

        result = await self.session.execute(
            select(Message)
            .where(Message.id.in_(ids))
            .options(joinedload(Message.user))
            .order_by(Message.id.asc())
        )
        return list(result.scalars().all())

    async def list_by_chat(
        self, chat_id: int, *, limit: int = 50, before_sequence: int | None = None
    ) -> list[Message]:
        q = select(Message).where(Message.chat_id == chat_id)
        if before_sequence is not None:
            q = q.where(Message.sequence < before_sequence)
        q = q.order_by(Message.sequence.desc()).limit(limit)
        result = await self.session.execute(q)
        return list(reversed(result.scalars().all()))

    async def delete_facts_by_external_ids(
        self, external_ids: list[str], user_id: int, chat_id: int
    ) -> int:
        parsed: list[UUID] = []
        for eid in external_ids:
            try:
                parsed.append(UUID(str(eid)))
            except (ValueError, AttributeError):
                continue
        if not parsed:
            return 0
        result = await self.session.execute(
            delete(Message)
            .where(
                Message.external_id.in_(parsed),
                Message.user_id == user_id,
                Message.chat_id == chat_id,
                Message.message_type == MessageType.FACT,
            )
            .execution_options(synchronize_session=False)
        )
        return result.rowcount

    async def list_recent_facts(
        self,
        user_id: int,
        chat_id: int,
        *,
        limit: int,
    ) -> list[Message]:
        """Most recent personal facts for a user scoped to this chat, oldest-first for context."""
        result = await self.session.execute(
            select(Message)
            .where(
                Message.user_id == user_id,
                Message.chat_id == chat_id,
                Message.message_type == MessageType.FACT,
            )
            .order_by(Message.id.desc())
            .limit(limit)
        )
        return list(reversed(result.scalars().all()))

    async def trim_old_facts(self, user_id: int, chat_id: int, max_count: int) -> int:
        keep_result = await self.session.execute(
            select(Message.id)
            .where(
                Message.user_id == user_id,
                Message.chat_id == chat_id,
                Message.message_type == MessageType.FACT,
            )
            .order_by(Message.id.desc())
            .limit(max_count)
        )
        keep_ids = list(keep_result.scalars().all())
        if not keep_ids:
            return 0
        result = await self.session.execute(
            delete(Message)
            .where(
                Message.user_id == user_id,
                Message.chat_id == chat_id,
                Message.message_type == MessageType.FACT,
                Message.id.not_in(keep_ids),
            )
            .execution_options(synchronize_session=False)
        )
        return result.rowcount

    async def list_chat_facts(self, chat_id: int, *, limit: int) -> list[Message]:
        """Most recent shared facts for a chat, ordered oldest-first for context."""
        result = await self.session.execute(
            select(Message)
            .where(
                Message.chat_id == chat_id,
                Message.message_type == MessageType.CHAT_FACT,
            )
            .order_by(Message.id.desc())
            .limit(limit)
        )
        return list(reversed(result.scalars().all()))

    async def trim_old_chat_facts(self, chat_id: int, max_count: int) -> int:
        keep_result = await self.session.execute(
            select(Message.id)
            .where(
                Message.chat_id == chat_id,
                Message.message_type == MessageType.CHAT_FACT,
            )
            .order_by(Message.id.desc())
            .limit(max_count)
        )
        keep_ids = list(keep_result.scalars().all())
        if not keep_ids:
            return 0
        result = await self.session.execute(
            delete(Message)
            .where(
                Message.chat_id == chat_id,
                Message.message_type == MessageType.CHAT_FACT,
                Message.id.not_in(keep_ids),
            )
            .execution_options(synchronize_session=False)
        )
        return result.rowcount

    async def delete_chat_facts_by_external_ids(
        self, external_ids: list[str], chat_id: int
    ) -> int:
        parsed: list[UUID] = []
        for eid in external_ids:
            try:
                parsed.append(UUID(str(eid)))
            except (ValueError, AttributeError):
                continue
        if not parsed:
            return 0
        result = await self.session.execute(
            delete(Message)
            .where(
                Message.external_id.in_(parsed),
                Message.chat_id == chat_id,
                Message.message_type == MessageType.CHAT_FACT,
            )
            .execution_options(synchronize_session=False)
        )
        return result.rowcount
