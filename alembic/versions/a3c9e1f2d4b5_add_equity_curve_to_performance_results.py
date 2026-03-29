"""Add equity_curve and fills to performance_results

Revision ID: a3c9e1f2d4b5
Revises: f17d31bb0c54
Create Date: 2026-03-25 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a3c9e1f2d4b5'
down_revision: Union[str, Sequence[str], None] = 'f17d31bb0c54'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('performance_results', sa.Column('equity_curve', sa.JSON(), nullable=True))
    op.add_column('performance_results', sa.Column('fills', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('performance_results', 'fills')
    op.drop_column('performance_results', 'equity_curve')
