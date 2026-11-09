"""add children.avatar_id (animal avatar) and children.growth (weight and height entries)

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-07 18:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None

AVATARS = ("lion", "elephant", "giraffe", "zebra", "hippo", "monkey", "cheetah", "rhino")


def upgrade() -> None:
    op.add_column('children', sa.Column('avatar_id', sa.String(length=20), nullable=True))
    op.add_column('children', sa.Column('growth', postgresql.JSONB(astext_type=sa.Text()),
                                        server_default=sa.text("'[]'::jsonb"),
                                        nullable=False))
    allowed = ', '.join(repr(a) for a in AVATARS)
    op.create_check_constraint('ck_children_avatar_valid', 'children',
                               f'avatar_id IS NULL OR avatar_id IN ({allowed})')


def downgrade() -> None:
    op.drop_constraint('ck_children_avatar_valid', 'children', type_='check')
    op.drop_column('children', 'growth')
    op.drop_column('children', 'avatar_id')
