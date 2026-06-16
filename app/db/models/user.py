from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid7

from sqlalchemy import BigInteger, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins.timestamps import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    external_id: Mapped[UUID] = mapped_column(
        unique=True, nullable=False, default=uuid7
    )

    client_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)

    display_name: Mapped[str | None] = mapped_column(String(256), nullable=True)

    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    token_window_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    token_budget: Mapped[int | None] = mapped_column(Integer, nullable=True)
