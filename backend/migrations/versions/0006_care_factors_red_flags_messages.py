"""special care factors, hearing and vision red flags, Ask a CHW messages, language

children.care_factors        ticked "reasons for special care" (MOH Mother and Child
                             Health Handbook), shown to the CHW
prediction_results.red_flags hearing and vision screening answers that need a look;
                             these route a result to the CHW outside the model
messages                     Ask a CHW: one thread per caregiver (sixth table)
users.language               the person's app language (en or sw)

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-11 09:40:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    empty_list = sa.text("'[]'::jsonb")
    op.add_column('children', sa.Column('care_factors', postgresql.JSONB(astext_type=sa.Text()),
                                        server_default=empty_list, nullable=False))
    op.add_column('prediction_results',
                  sa.Column('red_flags', postgresql.JSONB(astext_type=sa.Text()),
                            server_default=empty_list, nullable=False))
    op.add_column('users', sa.Column('language', sa.String(length=2), server_default='en',
                                     nullable=False))
    op.create_check_constraint('ck_users_language_valid', 'users', "language IN ('en', 'sw')")

    op.create_table(
        'messages',
        sa.Column('message_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('caregiver_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sender_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('prediction_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('body', sa.String(length=1000), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(),
                  nullable=False),
        sa.ForeignKeyConstraint(['caregiver_id'], ['users.user_id'], ondelete='CASCADE',
                                name='fk_messages_caregiver_id_users'),
        sa.ForeignKeyConstraint(['sender_id'], ['users.user_id'], ondelete='CASCADE',
                                name='fk_messages_sender_id_users'),
        sa.ForeignKeyConstraint(['prediction_id'], ['prediction_results.prediction_id'],
                                ondelete='SET NULL',
                                name='fk_messages_prediction_id_prediction_results'),
        sa.PrimaryKeyConstraint('message_id', name='pk_messages'),
    )
    op.create_index('ix_messages_caregiver_id', 'messages', ['caregiver_id'])


def downgrade() -> None:
    op.drop_index('ix_messages_caregiver_id', table_name='messages')
    op.drop_table('messages')
    op.drop_constraint('ck_users_language_valid', 'users', type_='check')
    op.drop_column('users', 'language')
    op.drop_column('prediction_results', 'red_flags')
    op.drop_column('children', 'care_factors')
