from uuid import UUID
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.chat import Chat


class ChatRepository:
    def __init__(self, session: AsyncSession):
        self.session = session


    async def create(self, title: str) -> Chat:
        chat = Chat(title=title)

        self.session.add(chat)
        await self.session.commit()
        await self.session.refresh(chat)

        return chat

    async def get_by_id(self, chat_id: int) -> Chat | None:
        return await self.session.get(Chat, chat_id)

    async def get_by_external_id(self, external_id: UUID) -> Chat | None:
        result = await self.session.execute(
            select(Chat).where(
                Chat.external_id == external_id,
                Chat.deleted_at.is_(None)
            )
        )

        return result.scalar_one_or_none()

    async def list_active(self) -> Sequence[Chat]:
        result = await self.session.execute(
            select(Chat).where(Chat.deleted_at.is_(None))
        )

        return result.scalars().all()

    async def delete(self, chat: Chat) -> None:
        from datetime import datetime, UTC

        chat.deleted_at = datetime.now(UTC)

        self.session.add(chat)
        await self.session.commit()

    async def update_title(self, chat: Chat, title: str) -> Chat:
        chat.title = title

        self.session.add(chat)
        await self.session.commit()
        await self.session.refresh(chat)

        return chat