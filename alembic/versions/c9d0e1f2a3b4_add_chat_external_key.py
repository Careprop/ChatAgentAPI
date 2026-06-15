"""add chat external_key

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa

revision = 'c9d0e1f2a3b4'
down_revision = 'b8c9d0e1f2a3'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'chats',
        sa.Column('external_key', sa.String(255), nullable=True),
    )
    op.create_index(
        'ix_chats_external_key',
        'chats',
        ['external_key'],
        unique=True,
        postgresql_where=sa.text('external_key IS NOT NULL'),
    )


def downgrade() -> None:
    op.drop_index('ix_chats_external_key', table_name='chats')
    op.drop_column('chats', 'external_key')
