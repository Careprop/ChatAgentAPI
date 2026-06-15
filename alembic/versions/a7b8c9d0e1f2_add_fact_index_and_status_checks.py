"""add fact index and status check constraints

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-06-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = 'a7b8c9d0e1f2'
down_revision: Union[str, Sequence[str], None] = 'f6a7b8c9d0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Partial index for fact queries filtered by (chat_id, user_id)
    op.execute(
        "CREATE INDEX ix_messages_facts "
        "ON messages (chat_id, user_id) "
        "WHERE message_type = 'fact'"
    )

    # Validate status values at DB level
    op.create_check_constraint(
        'message_chains_status_check',
        'message_chains',
        "status IN ('open', 'closed', 'embedded')",
    )
    op.create_check_constraint(
        'embedding_jobs_status_check',
        'embedding_jobs',
        "status IN ('pending', 'processing', 'done', 'failed')",
    )


def downgrade() -> None:
    op.drop_constraint('embedding_jobs_status_check', 'embedding_jobs')
    op.drop_constraint('message_chains_status_check', 'message_chains')
    op.drop_index('ix_messages_facts', table_name='messages')
