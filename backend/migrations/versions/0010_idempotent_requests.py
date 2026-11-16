"""offline mode: requests the app may send more than once

idempotent_requests  one row per change the phone queued while offline (a check, a
                     message, a growth entry, a CHW outcome). The phone gives each one a
                     random key; when it sends the same key again (the answer was lost on
                     a bad connection), the saved answer is returned and nothing is
                     saved twice. Rows older than 30 days are removed by the daily task.

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-16 17:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '0010'
down_revision = '0009'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'idempotent_requests',
        sa.Column('key', sa.String(length=64), nullable=False),
        sa.Column('path', sa.String(length=200), nullable=False),
        sa.Column('status_code', sa.Integer(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.PrimaryKeyConstraint('key', name='pk_idempotent_requests'),
    )
    op.create_index('ix_idempotent_requests_created_at', 'idempotent_requests',
                    ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_idempotent_requests_created_at', table_name='idempotent_requests')
    op.drop_table('idempotent_requests')
