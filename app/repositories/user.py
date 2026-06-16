from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.db.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def create(
        self,
        client_id: str,
        display_name: str | None = None,
        token_budget: int | None = None,
    ) -> User:
        user = User(client_id=client_id, display_name=display_name, token_budget=token_budget)
        self._session.add(user)
        await self._session.flush()
        await self._session.refresh(user)
        return user

    async def get_by_external_id(self, external_id: UUID) -> User | None:
        result = await self._session.execute(
            select(User).where(User.external_id == external_id)
        )
        return result.scalar_one_or_none()

    async def get_by_client_id(self, client_id: str) -> User | None:
        result = await self._session.execute(
            select(User).where(User.client_id == client_id)
        )
        return result.scalar_one_or_none()

    async def update_display_name(self, user: User, display_name: str) -> None:
        user.display_name = display_name
        self._session.add(user)
        await self._session.flush()

    async def check_token_budget(self, user: User) -> tuple[bool, int]:
        """Check whether user has budget remaining, resetting the window if it has expired.
        Returns (allowed, retry_after_seconds). Only call when user.token_budget is not None."""
        now = datetime.now(timezone.utc)
        window = timedelta(hours=settings.token_window_hours)

        if user.token_window_start is None or (now - user.token_window_start) >= window:
            user.tokens_used = 0
            user.token_window_start = now
            self._session.add(user)
            await self._session.flush()
            return True, int(window.total_seconds())

        retry_after = max(1, int((user.token_window_start + window - now).total_seconds()))
        return user.tokens_used < user.token_budget, retry_after

    async def add_tokens(self, user: User, count: int) -> None:
        user.tokens_used += count
        self._session.add(user)
        await self._session.flush()
