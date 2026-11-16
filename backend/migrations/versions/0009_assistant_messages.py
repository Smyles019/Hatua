"""the Hatua assistant: a caregiver's saved conversation with the AI assistant

assistant_messages  one row per message, from the caregiver ("user") or the assistant.
                    Kept apart from messages (the CHW chat) so the two can never mix
                    in the CHW's views. child_id says which child a question was about
                    (only the child's age is sent to the AI). flagged marks a message
                    answered with the fixed "go to a health facility now" reply.

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-16 15:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0009'
down_revision = '0008'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'assistant_messages',
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('caregiver_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('child_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('role', sa.String(length=10), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('flagged', sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.CheckConstraint("role IN ('user', 'assistant')",
                           name='ck_assistant_messages_role_valid'),
        sa.ForeignKeyConstraint(['caregiver_id'], ['users.user_id'], ondelete='CASCADE',
                                name='fk_assistant_messages_caregiver_id_users'),
        sa.ForeignKeyConstraint(['child_id'], ['children.child_id'], ondelete='SET NULL',
                                name='fk_assistant_messages_child_id_children'),
        sa.PrimaryKeyConstraint('message_id', name='pk_assistant_messages'),
    )
    op.create_index('ix_assistant_messages_caregiver_id', 'assistant_messages',
                    ['caregiver_id'])


def downgrade() -> None:
    op.drop_index('ix_assistant_messages_caregiver_id', table_name='assistant_messages')
    op.drop_table('assistant_messages')
