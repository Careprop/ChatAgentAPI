"""add users

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-15 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('external_id', sa.Uuid(), nullable=False),
        sa.Column('username', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_id'),
        sa.UniqueConstraint('username'),
    )

    # Replace participant_id (Text) with user_id (FK) on messages
    op.drop_column('messages', 'participant_id')
    op.add_column('messages', sa.Column('user_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        'fk_messages_user_id', 'messages', 'users', ['user_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_messages_user_id', 'messages', ['user_id'])

    # Replace participant_id (Text) with user_id (FK) on message_chains
    op.drop_index('ix_message_chains_chat_participant', table_name='message_chains')
    op.drop_column('message_chains', 'participant_id')
    op.add_column('message_chains', sa.Column('user_id', sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        'fk_message_chains_user_id', 'message_chains', 'users', ['user_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_message_chains_chat_user', 'message_chains', ['chat_id', 'user_id'])


def downgrade() -> None:
    op.drop_index('ix_message_chains_chat_user', table_name='message_chains')
    op.drop_constraint('fk_message_chains_user_id', 'message_chains', type_='foreignkey')
    op.drop_column('message_chains', 'user_id')
    op.add_column('message_chains', sa.Column('participant_id', sa.Text(), nullable=True))
    op.create_index('ix_message_chains_chat_participant', 'message_chains', ['chat_id', 'participant_id'])

    op.drop_index('ix_messages_user_id', table_name='messages')
    op.drop_constraint('fk_messages_user_id', 'messages', type_='foreignkey')
    op.drop_column('messages', 'user_id')
    op.add_column('messages', sa.Column('participant_id', sa.Text(), nullable=True))

    op.drop_table('users')
