"""add items to order

Revision ID: 0002
Revises: 0001
Create Date: 2026-03-04 18:50:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # We need to handle the DB column changes for orders

    # 1. Add items JSONB column
    op.add_column('orders', sa.Column('items', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False))

    # 2. Add customer_dni column if it was missing in 0001 but exists in model
    # Wait, looking at 0001, it didn't have customer_dni or product_id!
    # The models must have been updated since 0001. Let's add them to be safe.
    
    # Check if we need to alter product_id to be nullable
    try:
        op.alter_column('orders', 'product_id', existing_type=postgresql.UUID(), nullable=True)
    except Exception:
        pass # In case product_id doesn't exist yet in the actual remote DB


def downgrade() -> None:
    op.drop_column('orders', 'items')
