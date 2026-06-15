"""change embedding dimensions

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-06-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    dims = 384  # paraphrase-multilingual-MiniLM-L12-v2 output size

    # Drop HNSW index — it is bound to the column type and must be recreated.
    op.drop_index("ix_message_embeddings_hnsw", table_name="message_embeddings")

    # Clear stale vectors: existing embeddings were produced by a different model
    # and cannot be compared to new ones after the dimension change.
    op.execute("TRUNCATE TABLE message_embeddings")

    op.execute(
        f"ALTER TABLE message_embeddings "
        f"ALTER COLUMN embedding TYPE vector({dims})"
    )

    op.execute(
        "CREATE INDEX ix_message_embeddings_hnsw ON message_embeddings "
        "USING hnsw (embedding vector_cosine_ops) "
        "WITH (m=16, ef_construction=64)"
    )


def downgrade() -> None:
    op.drop_index("ix_message_embeddings_hnsw", table_name="message_embeddings")
    op.execute("TRUNCATE TABLE message_embeddings")
    op.execute(
        "ALTER TABLE message_embeddings "
        "ALTER COLUMN embedding TYPE vector(1536)"
    )
    op.execute(
        "CREATE INDEX ix_message_embeddings_hnsw ON message_embeddings "
        "USING hnsw (embedding vector_cosine_ops) "
        "WITH (m=16, ef_construction=64)"
    )
