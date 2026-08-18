"""create_mentor_profiles_table

Revision ID: a3c8d1f5e72b
Revises: 793350f693a1
Create Date: 2026-08-16 19:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a3c8d1f5e72b'
down_revision: Union[str, Sequence[str], None] = '793350f693a1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('mentor_profiles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('headline', sa.String(length=200), nullable=True),
    sa.Column('bio', sa.Text(), nullable=True),
    sa.Column('current_role', sa.String(length=150), nullable=True),
    sa.Column('company', sa.String(length=200), nullable=True),
    sa.Column('location', sa.String(length=200), nullable=True),
    sa.Column('years_of_experience', sa.Integer(), nullable=True),
    sa.Column('startup_experience', sa.Integer(), nullable=True),
    sa.Column('mentoring_experience', sa.Integer(), nullable=True),
    sa.Column('industries', postgresql.ARRAY(sa.String()), nullable=True),
    sa.Column('areas_of_expertise', postgresql.ARRAY(sa.String()), nullable=True),
    sa.Column('startup_stages', postgresql.ARRAY(sa.String()), nullable=True),
    sa.Column('mentorship_areas', postgresql.ARRAY(sa.String()), nullable=True),
    sa.Column('availability', sa.String(length=50), nullable=True),
    sa.Column('profile_completion', sa.Integer(), nullable=False, server_default='0'),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', name='uq_mentor_profiles_user_id')
    )
    op.create_index(op.f('ix_mentor_profiles_id'), 'mentor_profiles', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_mentor_profiles_id'), table_name='mentor_profiles')
    op.drop_table('mentor_profiles')
