"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------ #
    # chats                                                                #
    # ------------------------------------------------------------------ #
    op.create_table(
        'chats',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('external_id', sa.Uuid(), nullable=False),
        sa.Column('title', sa.String(128), nullable=False),
        sa.Column('external_key', sa.String(255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_id', name='uq_chats_external_id'),
        sa.UniqueConstraint('external_key', name='uq_chats_external_key'),
    )
    op.create_index('ix_chats_external_id', 'chats', ['external_id'], unique=True)
    op.execute(
        "CREATE UNIQUE INDEX ix_chats_active_external_id "
        "ON chats (external_id) WHERE deleted_at IS NULL"
    )

    # ------------------------------------------------------------------ #
    # users                                                                #
    # ------------------------------------------------------------------ #
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('external_id', sa.Uuid(), nullable=False),
        sa.Column('client_id', sa.String(128), nullable=False),
        sa.Column('display_name', sa.String(256), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('token_window_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('token_budget', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_id', name='uq_users_external_id'),
        sa.UniqueConstraint('client_id', name='uq_users_client_id'),
    )

    # ------------------------------------------------------------------ #
    # messages                                                             #
    # ------------------------------------------------------------------ #
    op.create_table(
        'messages',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('external_id', sa.Uuid(), nullable=False),
        sa.Column('chat_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=True),
        sa.Column('role', sa.Text(), nullable=False),
        sa.Column('message_type', sa.Text(), nullable=False, server_default='message'),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('token_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('metadata', sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL',
                                name='fk_messages_user_id'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('external_id', name='uq_messages_external_id'),
        sa.CheckConstraint(
            "role IN ('user', 'assistant', 'system')",
            name='messages_role_check',
        ),
        sa.CheckConstraint(
            "message_type IN ('message', 'fact', 'chat_fact')",
            name='messages_message_type_check',
        ),
    )
    op.create_index('ix_messages_chat_id', 'messages', ['chat_id'])
    op.create_index('ix_messages_user_id', 'messages', ['user_id'])
    op.create_index('ix_messages_chat_sequence', 'messages', ['chat_id', 'sequence'])
    op.execute(
        "CREATE INDEX ix_messages_user_facts "
        "ON messages (user_id, chat_id) WHERE message_type = 'fact'"
    )
    op.execute(
        "CREATE INDEX ix_messages_chat_facts "
        "ON messages (chat_id) WHERE message_type = 'chat_fact'"
    )


def downgrade() -> None:
    op.drop_table('messages')
    op.drop_table('users')
    op.drop_table('chats')
