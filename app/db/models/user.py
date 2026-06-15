from __future__ import annotations

from uuid import UUID, uuid7

from sqlalchemy import BigInteger, String
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
