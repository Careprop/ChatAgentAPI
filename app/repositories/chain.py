from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.chain import ChainStatus, MessageChain


class ChainRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(self, chat_id: int, participant_id: str | None) -> MessageChain:
        chain = MessageChain(
            chat_id=chat_id,
            participant_id=participant_id,
            status=ChainStatus.OPEN,
            opened_at=datetime.now(timezone.utc),
        )
        self._session.add(chain)
        await self._session.flush()
        await self._session.refresh(chain)
        return chain

    async def get_open_chain(
        self, chat_id: int, participant_id: str | None
    ) -> MessageChain | None:
        result = await self._session.execute(
            select(MessageChain).where(
                MessageChain.chat_id == chat_id,
                MessageChain.participant_id == participant_id,
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

    async def get_open_chains_with_messages(
        self, chat_id: int
    ) -> list[MessageChain]:
        result = await self._session.execute(
            select(MessageChain)
            .where(
                MessageChain.chat_id == chat_id,
                MessageChain.status == ChainStatus.OPEN,
            )
            .options(selectinload(MessageChain.messages))
            .order_by(MessageChain.opened_at)
        )
        return list(result.scalars().all())
