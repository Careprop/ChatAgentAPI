from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid7

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins.timestamps import TimestampMixin

if TYPE_CHECKING:
    from app.db.models.chain import MessageChain
    from app.db.models.message_embedding import MessageEmbedding
    from app.db.models.user import User


class MessageType(StrEnum):
    MESSAGE = "message"
    FACT = "fact"


class Message(Base, TimestampMixin):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    external_id: Mapped[UUID] = mapped_column(
        unique=True,
        nullable=False,
        default=uuid7,
    )

    chat_id: Mapped[int] = mapped_column(
        ForeignKey("chats.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    chain_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("message_chains.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    user_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    role: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(Text, nullable=False, default=MessageType.MESSAGE)

    content: Mapped[str] = mapped_column(Text, nullable=False)

    msg_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )

    # Monotonically increasing position within the chat, assigned at insert time.
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    chain: Mapped[MessageChain | None] = relationship(
        "MessageChain",
        back_populates="messages",
        lazy="raise",
    )

    user: Mapped[User | None] = relationship("User", lazy="raise")

    embedding: Mapped[MessageEmbedding | None] = relationship(
        "MessageEmbedding",
        back_populates="message",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="raise",
    )

    __table_args__ = (
        Index("ix_messages_chat_sequence", "chat_id", "sequence"),
    )
