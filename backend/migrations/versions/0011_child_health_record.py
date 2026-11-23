"""the child health record from the purple book (MOH Mother and Child Health Handbook)

children.care_given        vaccines, vitamin A and deworming given: {"bcg": "2026-01-03"}
children.extra_vaccines    county-only vaccines switched on: ["malaria", "yellow_fever"]
children.birth             {"weight_kg", "gestation_weeks", "place"}
children.birth_certificate / bed_net   yes or no, unknown until answered
children.next_clinic_on    the next visit date the nurse wrote in the booklet
children.clinic_reminded_on  the visit date the "clinic tomorrow" reminder was sent for
children.sick_visits       [{"visit_id", "visit_on", "illness", "treatment"}]

Kept as columns and JSONB on children, like growth and care_factors, so the record adds
no tables to the five-table design.

Revision ID: 0011
Revises: 0010
Create Date: 2026-11-17 15:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0011'
down_revision = '0010'
branch_labels = None
depends_on = None

JSON_OBJ = sa.text("'{}'::jsonb")
JSON_LIST = sa.text("'[]'::jsonb")


def upgrade() -> None:
    op.add_column('children', sa.Column('care_given', postgresql.JSONB(astext_type=sa.Text()),
                                        server_default=JSON_OBJ, nullable=False))
    op.add_column('children', sa.Column('extra_vaccines', postgresql.JSONB(astext_type=sa.Text()),
                                        server_default=JSON_LIST, nullable=False))
    op.add_column('children', sa.Column('birth', postgresql.JSONB(astext_type=sa.Text()),
                                        server_default=JSON_OBJ, nullable=False))
    op.add_column('children', sa.Column('birth_certificate', sa.Boolean(), nullable=True))
    op.add_column('children', sa.Column('bed_net', sa.Boolean(), nullable=True))
    op.add_column('children', sa.Column('next_clinic_on', sa.Date(), nullable=True))
    op.add_column('children', sa.Column('clinic_reminded_on', sa.Date(), nullable=True))
    op.add_column('children', sa.Column('sick_visits', postgresql.JSONB(astext_type=sa.Text()),
                                        server_default=JSON_LIST, nullable=False))


def downgrade() -> None:
    for col in ('sick_visits', 'clinic_reminded_on', 'next_clinic_on', 'bed_net',
                'birth_certificate', 'birth', 'extra_vaccines', 'care_given'):
        op.drop_column('children', col)
