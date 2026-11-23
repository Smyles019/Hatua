"""push notifications: device tokens, and which age band a child was last reminded for

users.push_tokens      Firebase Cloud Messaging tokens of the person's phones, newest
                       last: [{"token", "updated_at"}]. JSONB on the user keeps the table
                       count down, like children.growth.
children.reminded_band the age band ("12-17") the "time for a check" reminder was last
                       sent for, so each band is reminded once

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-16 11:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('push_tokens', postgresql.JSONB(astext_type=sa.Text()),
                                     server_default=sa.text("'[]'::jsonb"), nullable=False))
    op.add_column('children', sa.Column('reminded_band', sa.String(length=10), nullable=True))


def downgrade() -> None:
    op.drop_column('children', 'reminded_band')
    op.drop_column('users', 'push_tokens')
