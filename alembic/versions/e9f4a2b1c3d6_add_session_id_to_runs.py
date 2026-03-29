"""Add session_id to backtest_runs and research_runs

Revision ID: e9f4a2b1c3d6
Revises: c7e2f3a4b8d1
Create Date: 2026-03-28

"""
from alembic import op
import sqlalchemy as sa

revision = 'e9f4a2b1c3d6'
down_revision = 'c7e2f3a4b8d1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('backtest_runs', sa.Column('session_id', sa.String(), nullable=True))
    op.create_index(op.f('ix_backtest_runs_session_id'), 'backtest_runs', ['session_id'], unique=False)
    op.add_column('research_runs', sa.Column('session_id', sa.String(), nullable=True))
    op.create_index(op.f('ix_research_runs_session_id'), 'research_runs', ['session_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_research_runs_session_id'), table_name='research_runs')
    op.drop_column('research_runs', 'session_id')
    op.drop_index(op.f('ix_backtest_runs_session_id'), table_name='backtest_runs')
    op.drop_column('backtest_runs', 'session_id')
