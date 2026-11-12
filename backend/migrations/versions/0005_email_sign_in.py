"""add users.email_verified for email sign-in

People now sign in with their email. Accounts that already have an email got it from
Google, which verifies addresses, so they start verified.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-10 21:10:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('email_verified', sa.Boolean(),
                                     server_default=sa.false(), nullable=False))
    op.execute("UPDATE users SET email_verified = true WHERE email IS NOT NULL")


def downgrade() -> None:
    op.drop_column('users', 'email_verified')
