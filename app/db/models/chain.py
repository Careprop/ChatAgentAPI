from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.db.models.message import Message


class ChainStatus:
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

    participant_id: Mapped[str | None] = mapped_column(Text, nullable=True)

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

    __table_args__ = (
        Index("ix_message_chains_chat_participant", "chat_id", "participant_id"),
        Index("ix_message_chains_chat_status", "chat_id", "status"),
    )
