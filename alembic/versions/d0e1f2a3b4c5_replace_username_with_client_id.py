"""replace username with client_id and display_name

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa

revision = 'd0e1f2a3b4c5'
down_revision = 'c9d0e1f2a3b4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column('users', 'username')
    op.add_column('users', sa.Column('client_id', sa.String(128), nullable=False))
    op.create_unique_constraint('uq_users_client_id', 'users', ['client_id'])
    op.add_column('users', sa.Column('display_name', sa.String(256), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'display_name')
    op.drop_constraint('uq_users_client_id', 'users', type_='unique')
    op.drop_column('users', 'client_id')
    op.add_column('users', sa.Column('username', sa.Text(), nullable=False))
    op.create_unique_constraint(None, 'users', ['username'])
