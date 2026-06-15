"""drop updated_at from all tables

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-06-15 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('chats', 'updated_at')
    op.drop_column('messages', 'updated_at')
    op.drop_column('embedding_jobs', 'updated_at')
    op.drop_column('users', 'updated_at')


def downgrade() -> None:
    op.add_column('users', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.add_column('embedding_jobs', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.add_column('messages', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.add_column('chats', sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
