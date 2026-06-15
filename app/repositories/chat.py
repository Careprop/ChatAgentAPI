from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chat import Chat


class ChatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, title: str, external_key: str | None = None) -> Chat:
        chat = Chat(title=title, external_key=external_key)
        self.session.add(chat)
        await self.session.flush()
        await self.session.refresh(chat)
        return chat

    async def get_by_id(self, chat_id: int) -> Chat | None:
        return await self.session.get(Chat, chat_id)

    async def get_by_external_id(self, external_id: UUID) -> Chat | None:
        result = await self.session.execute(
            select(Chat).where(
                Chat.external_id == external_id,
                Chat.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_external_key(self, external_key: str) -> Chat | None:
        result = await self.session.execute(
            select(Chat).where(
                Chat.external_key == external_key,
                Chat.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def list_active(
        self,
        *,
        limit: int = 100,
        before_id: UUID | None = None,
        external_key: str | None = None,
    ) -> list[Chat]:
        q = select(Chat).where(Chat.deleted_at.is_(None))
        if external_key is not None:
            q = q.where(Chat.external_key == external_key)
        if before_id is not None:
            sub = select(Chat.id).where(Chat.external_id == before_id).scalar_subquery()
            q = q.where(Chat.id < sub)
        q = q.order_by(Chat.id.desc()).limit(limit)
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def delete(self, chat: Chat) -> None:
        from datetime import datetime, UTC
        chat.deleted_at = datetime.now(UTC)
        self.session.add(chat)
        await self.session.flush()

    async def update_title(self, chat: Chat, title: str) -> Chat:
        chat.title = title
        self.session.add(chat)
        await self.session.flush()
        await self.session.refresh(chat)
        return chat
