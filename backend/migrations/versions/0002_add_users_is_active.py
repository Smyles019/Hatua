"""add users.is_active; store phone numbers as +254...

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-18 21:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing users stay active; the server default fills the column for them.
    op.add_column('users', sa.Column('is_active', sa.Boolean(), server_default=sa.true(),
                                     nullable=False))
    # The API now stores Kenyan numbers as +254XXXXXXXXX (app.schemas.users.kenyan_phone)
    # and looks them up that way at sign-in. Convert numbers saved earlier as 07.. or 01..
    op.execute("UPDATE users SET phone_number = '+254' || substr(phone_number, 2) "
               "WHERE phone_number ~ '^0[17][0-9]{8}$'")


def downgrade() -> None:
    # Phone numbers are left in +254 form; both forms are valid strings for the column.
    op.drop_column('users', 'is_active')
