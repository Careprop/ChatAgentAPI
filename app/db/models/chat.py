from uuid import UUID, uuid7

from sqlalchemy import String, Index
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins.timestamps import TimestampMixin, SoftDeleteMixin


class Chat(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True
    )

    external_id: Mapped[UUID] = mapped_column(
        unique=True,
        nullable=False,
        default=uuid7,
        index=True
    )

    title: Mapped[str] = mapped_column(
        String(128),
        nullable=False
    )

    # Client-controlled unique key (e.g. "tg:123456789") for bot restart recovery.
    external_key: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
    )

    __table_args__ = (
        Index(
            "ix_chats_active_external_id",
            "external_id",
            postgresql_where="deleted_at IS NULL"
        ),
    )
