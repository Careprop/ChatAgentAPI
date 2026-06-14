"""add chains and embedding jobs

Revision ID: a1b2c3d4e5f6
Revises: de357e437ed1
Create Date: 2026-06-14 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'de357e437ed1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'message_chains',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('chat_id', sa.Integer(), nullable=False),
        sa.Column('participant_id', sa.Text(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False, server_default='open'),
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['chat_id'], ['chats.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_message_chains_chat_participant',
        'message_chains', ['chat_id', 'participant_id'],
    )
    op.create_index(
        'ix_message_chains_chat_status',
        'message_chains', ['chat_id', 'status'],
    )

    op.add_column(
        'messages',
        sa.Column('chain_id', sa.BigInteger(), nullable=True),
    )
    op.add_column(
        'messages',
        sa.Column('participant_id', sa.Text(), nullable=True),
    )
    op.create_foreign_key(
        'fk_messages_chain_id',
        'messages', 'message_chains',
        ['chain_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_messages_chain_id', 'messages', ['chain_id'])

    op.create_table(
        'embedding_jobs',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('chain_id', sa.BigInteger(), nullable=True),
        sa.Column('message_id', sa.BigInteger(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False, server_default='pending'),
        sa.Column('attempts', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['chain_id'], ['message_chains.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['message_id'], ['messages.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'ix_embedding_jobs_pending',
        'embedding_jobs', ['status'],
        postgresql_where=sa.text("status = 'pending'"),
    )


def downgrade() -> None:
    op.drop_index('ix_embedding_jobs_pending', table_name='embedding_jobs')
    op.drop_table('embedding_jobs')

    op.drop_index('ix_messages_chain_id', table_name='messages')
    op.drop_constraint('fk_messages_chain_id', 'messages', type_='foreignkey')
    op.drop_column('messages', 'participant_id')
    op.drop_column('messages', 'chain_id')

    op.drop_index('ix_message_chains_chat_status', table_name='message_chains')
    op.drop_index('ix_message_chains_chat_participant', table_name='message_chains')
    op.drop_table('message_chains')
