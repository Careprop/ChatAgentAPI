"""add user token budget

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
Create Date: 2026-06-16

"""
from alembic import op
import sqlalchemy as sa

revision = 'e1f2a3b4c5d6'
down_revision = 'd0e1f2a3b4c5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('tokens_used', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('token_window_start', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'token_window_start')
    op.drop_column('users', 'tokens_used')
