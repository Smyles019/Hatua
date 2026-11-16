"""CHW invites: an administrator adds a CHW by name and email, and the CHW sets up the
account from an emailed link (or with Google)

users.invited_at    when the invite was last sent; set for accounts made by invite
users.phone_number  may be empty while an invite is waiting: the CHW adds it when they
                    set up the account
ck_users_has_sign_in  an account waiting on its invite has no way in yet, so it counts

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-16 09:30:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('invited_at', sa.DateTime(timezone=True), nullable=True))
    op.alter_column('users', 'phone_number', existing_type=sa.String(length=15),
                    nullable=True)
    op.drop_constraint('ck_users_has_sign_in', 'users', type_='check')
    op.create_check_constraint(
        'ck_users_has_sign_in', 'users',
        'password_hash IS NOT NULL OR google_id IS NOT NULL OR invited_at IS NOT NULL')
    # Only an invite still waiting may have no phone number.
    op.create_check_constraint(
        'ck_users_phone_or_invited', 'users',
        'phone_number IS NOT NULL OR (invited_at IS NOT NULL AND password_hash IS NULL '
        'AND google_id IS NULL)')


def downgrade() -> None:
    # Invites nobody took up cannot be kept: they have no phone number and no way in.
    op.execute("DELETE FROM users WHERE password_hash IS NULL AND google_id IS NULL")
    op.drop_constraint('ck_users_phone_or_invited', 'users', type_='check')
    op.drop_constraint('ck_users_has_sign_in', 'users', type_='check')
    op.create_check_constraint('ck_users_has_sign_in', 'users',
                               'password_hash IS NOT NULL OR google_id IS NOT NULL')
    op.alter_column('users', 'phone_number', existing_type=sa.String(length=15),
                    nullable=False)
    op.drop_column('users', 'invited_at')
