from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.chain import ChainStatus, MessageChain
from app.db.models.message import Message


class ChainRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, chat_id: int, user_id: int | None) -> MessageChain:
        chain = MessageChain(
            chat_id=chat_id,
            user_id=user_id,
            status=ChainStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )
        self._session.add(chain)
        await self._session.flush()
        await self._session.refresh(chain)
        return chain

    async def get_open_chain(
        self, chat_id: int, user_id: int | None
    ) -> MessageChain | None:
        result = await self._session.execute(
            select(MessageChain).where(
                MessageChain.chat_id == chat_id,
                MessageChain.user_id == user_id,
                MessageChain.status == ChainStatus.OPEN,
            )
        )
        return result.scalar_one_or_none()

    async def close(self, chain_id: int) -> None:
        await self._session.execute(
            update(MessageChain)
            .where(
                MessageChain.id == chain_id,
                MessageChain.status == ChainStatus.OPEN,
            )
            .values(status=ChainStatus.CLOSED, closed_at=datetime.now(timezone.utc))
        )

    async def mark_embedded(self, chain_id: int) -> None:
        await self._session.execute(
            update(MessageChain)
            .where(MessageChain.id == chain_id)
            .values(status=ChainStatus.EMBEDDED)
        )

    async def get_abandoned_chains(self, gap_seconds: int) -> list[MessageChain]:
        """Return open chains whose last message is older than gap_seconds."""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=gap_seconds)

        last_msg = (
            select(Message.chain_id, func.max(Message.created_at).label("last_at"))
            .where(Message.chain_id.isnot(None))
            .group_by(Message.chain_id)
            .subquery()
        )

        result = await self._session.execute(
            select(MessageChain)
            .outerjoin(last_msg, last_msg.c.chain_id == MessageChain.id)
            .where(
                MessageChain.status == ChainStatus.OPEN,
                func.coalesce(last_msg.c.last_at, MessageChain.opened_at) < cutoff,
            )
        )
        return list(result.scalars().all())

    async def get_open_chains_with_messages(
        self, chat_id: int, max_age_seconds: int = 300
    ) -> list[MessageChain]:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=max_age_seconds)

        last_msg = (
            select(Message.chain_id, func.max(Message.created_at).label("last_at"))
            .where(Message.chain_id.isnot(None))
            .group_by(Message.chain_id)
            .subquery()
        )

        result = await self._session.execute(
            select(MessageChain)
            .outerjoin(last_msg, last_msg.c.chain_id == MessageChain.id)
            .where(
                MessageChain.chat_id == chat_id,
                MessageChain.status == ChainStatus.OPEN,
                func.coalesce(last_msg.c.last_at, MessageChain.opened_at) >= cutoff,
            )
            .options(
                selectinload(MessageChain.messages).selectinload(Message.user),
                selectinload(MessageChain.user),
            )
            .order_by(MessageChain.opened_at)
        )
        return list(result.scalars().all())
