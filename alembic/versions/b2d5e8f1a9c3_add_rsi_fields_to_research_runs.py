"""add rsi fields to research_runs

Revision ID: b2d5e8f1a9c3
Revises: e9f4a2b1c3d6
Create Date: 2026-03-28

"""
from alembic import op
import sqlalchemy as sa

revision = 'b2d5e8f1a9c3'
down_revision = 'e9f4a2b1c3d6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('research_runs', sa.Column('strategy', sa.String(), nullable=True, server_default='ma_crossover'))
    op.add_column('research_runs', sa.Column('rsi_periods', sa.JSON(), nullable=True))
    op.add_column('research_runs', sa.Column('oversold_levels', sa.JSON(), nullable=True))
    op.add_column('research_runs', sa.Column('overbought_levels', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('research_runs', 'overbought_levels')
    op.drop_column('research_runs', 'oversold_levels')
    op.drop_column('research_runs', 'rsi_periods')
    op.drop_column('research_runs', 'strategy')
