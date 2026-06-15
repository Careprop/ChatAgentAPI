from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.message import Message
    from app.db.models.user import User


class ChainStatus(StrEnum):
    OPEN = "open"
    CLOSED = "closed"
    EMBEDDED = "embedded"


class MessageChain(Base):
    __tablename__ = "message_chains"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False,
    )

    user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(Text, nullable=False, default=ChainStatus.OPEN)

    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    messages: Mapped[list[Message]] = relationship(
        "Message",
        back_populates="chain",
        order_by="Message.sequence",
        lazy="raise",
    )

    user: Mapped[User | None] = relationship("User", lazy="raise")

    __table_args__ = (
        Index("ix_message_chains_chat_user", "chat_id", "user_id"),
        Index("ix_message_chains_chat_status", "chat_id", "status"),
    )
