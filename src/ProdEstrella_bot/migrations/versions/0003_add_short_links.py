"""add short_links table

Revision ID: 0003
Revises: 0002
Create Date: 2026-03-07 15:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0003'
down_revision: Union[str, None] = '0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'short_links',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('code', sa.String(16), nullable=False),
        sa.Column('destination', sa.Text(), nullable=False),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('now()'),
            nullable=False,
        ),
    )
    op.create_index('ix_short_links_code', 'short_links', ['code'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_short_links_code', table_name='short_links')
    op.drop_table('short_links')
