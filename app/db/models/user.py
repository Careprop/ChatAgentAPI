from __future__ import annotations

from uuid import UUID, uuid7

from sqlalchemy import BigInteger, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins.timestamps import TimestampMixin


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    external_id: Mapped[UUID] = mapped_column(
        unique=True, nullable=False, default=uuid7
    )

    username: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
