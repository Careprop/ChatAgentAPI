"""add message_type and check constraints

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-06-15 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'f6a7b8c9d0e1'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 2a: message_type column — distinguishes conversational turns from saved facts
    op.add_column(
        'messages',
        sa.Column('message_type', sa.Text(), nullable=False, server_default='message'),
    )
    op.create_check_constraint(
        'messages_message_type_check',
        'messages',
        "message_type IN ('message', 'fact')",
    )

    # 2b: role is now validated at DB level
    op.create_check_constraint(
        'messages_role_check',
        'messages',
        "role IN ('user', 'assistant', 'system')",
    )

    # 2c: exactly one of chain_id / message_id must be set on an embedding job
    op.create_check_constraint(
        'embedding_jobs_target_check',
        'embedding_jobs',
        '(chain_id IS NULL) <> (message_id IS NULL)',
    )


def downgrade() -> None:
    op.drop_constraint('embedding_jobs_target_check', 'embedding_jobs')
    op.drop_constraint('messages_role_check', 'messages')
    op.drop_constraint('messages_message_type_check', 'messages')
    op.drop_column('messages', 'message_type')
