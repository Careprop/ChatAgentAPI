from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid7

from sqlalchemy import BigInteger, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins.timestamps import TimestampMixin

if TYPE_CHECKING:
    from app.db.models.chain import MessageChain
    from app.db.models.message_embedding import MessageEmbedding


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

    participant_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    role: Mapped[str] = mapped_column(Text, nullable=False)

    content: Mapped[str] = mapped_column(Text, nullable=False)

    # Monotonically increasing position within the chat, assigned at insert time.
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    chain: Mapped[MessageChain | None] = relationship(
        "MessageChain",
        back_populates="messages",
        lazy="raise",
    )

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
