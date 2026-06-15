from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins.timestamps import TimestampMixin


class JobStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class EmbeddingJob(Base, TimestampMixin):
    __tablename__ = "embedding_jobs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    # Exactly one of chain_id / message_id is set.
    chain_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("message_chains.id", ondelete="CASCADE"),
        nullable=True,
    )
    message_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("messages.id", ondelete="CASCADE"),
        nullable=True,
    )

    status: Mapped[str] = mapped_column(
        Text, nullable=False, default=JobStatus.PENDING
    )
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    processing_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index(
            "ix_embedding_jobs_pending",
            "status",
            postgresql_where="status = 'pending'",
        ),
    )
