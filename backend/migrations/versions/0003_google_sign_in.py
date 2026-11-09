"""add users.email and users.google_id for Google sign-in; password becomes optional

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-05 12:10:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('email', sa.String(length=254), nullable=True))
    op.add_column('users', sa.Column('google_id', sa.String(length=64), nullable=True))
    op.create_unique_constraint('uq_users_email', 'users', ['email'])
    op.create_unique_constraint('uq_users_google_id', 'users', ['google_id'])
    # Google accounts have no Hatua password. Every account still needs one way in.
    op.alter_column('users', 'password_hash', existing_type=sa.String(length=255),
                    nullable=True)
    op.create_check_constraint('ck_users_has_sign_in', 'users',
                               'password_hash IS NOT NULL OR google_id IS NOT NULL')


def downgrade() -> None:
    op.drop_constraint('ck_users_has_sign_in', 'users', type_='check')
    # Google-only accounts cannot be kept without a password column value.
    op.execute("DELETE FROM users WHERE password_hash IS NULL")
    op.alter_column('users', 'password_hash', existing_type=sa.String(length=255),
                    nullable=False)
    op.drop_constraint('uq_users_google_id', 'users', type_='unique')
    op.drop_constraint('uq_users_email', 'users', type_='unique')
    op.drop_column('users', 'google_id')
    op.drop_column('users', 'email')
