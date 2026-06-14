from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.config.settings import settings

if TYPE_CHECKING:
    from app.db.models.message import Message


class MessageEmbedding(Base):
    __tablename__ = "message_embeddings"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)

    message_id: Mapped[int] = mapped_column(
        ForeignKey("messages.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Dimension configured via settings to match the chosen embedding model.
    embedding = mapped_column(Vector(settings.embedding_dimensions), nullable=False)

    model: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    message: Mapped[Message] = relationship("Message", back_populates="embedding")

    __table_args__ = (
        # HNSW index for approximate nearest-neighbour search with cosine distance.
        Index(
            "ix_message_embeddings_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )
