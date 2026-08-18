"""add_is_discoverable_and_indexes_to_mentor_profiles

Revision ID: b5d9e3f4a81c
Revises: a3c8d1f5e72b
Create Date: 2026-08-17 00:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b5d9e3f4a81c'
down_revision: Union[str, Sequence[str], None] = 'a3c8d1f5e72b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add is_discoverable column and GIN indexes for efficient discovery queries."""
    # Discoverability toggle — defaults to true so existing mentors are visible
    op.add_column('mentor_profiles',
        sa.Column('is_discoverable', sa.Boolean(), nullable=False, server_default='true')
    )

    # GIN indexes on ARRAY columns for efficient overlap/contains queries
    op.execute(
        'CREATE INDEX ix_mentor_profiles_industries ON mentor_profiles USING GIN (industries)'
    )
    op.execute(
        'CREATE INDEX ix_mentor_profiles_expertise ON mentor_profiles USING GIN (areas_of_expertise)'
    )
    op.execute(
        'CREATE INDEX ix_mentor_profiles_stages ON mentor_profiles USING GIN (startup_stages)'
    )

    # B-tree indexes for scalar filter/sort columns
    op.create_index('ix_mentor_profiles_availability', 'mentor_profiles', ['availability'])
    op.create_index('ix_mentor_profiles_discoverable', 'mentor_profiles', ['is_discoverable'])


def downgrade() -> None:
    """Remove is_discoverable column and discovery indexes."""
    op.drop_index('ix_mentor_profiles_discoverable', table_name='mentor_profiles')
    op.drop_index('ix_mentor_profiles_availability', table_name='mentor_profiles')
    op.execute('DROP INDEX IF EXISTS ix_mentor_profiles_stages')
    op.execute('DROP INDEX IF EXISTS ix_mentor_profiles_expertise')
    op.execute('DROP INDEX IF EXISTS ix_mentor_profiles_industries')
    op.drop_column('mentor_profiles', 'is_discoverable')
