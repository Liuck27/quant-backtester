"""add research_runs table

Revision ID: c7e2f3a4b8d1
Revises: a3c9e1f2d4b5
Create Date: 2026-03-26

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = 'c7e2f3a4b8d1'
down_revision = 'a3c9e1f2d4b5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'research_runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('job_id', sa.String(), nullable=True),
        sa.Column('symbol', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('short_windows', sa.JSON(), nullable=True),
        sa.Column('long_windows', sa.JSON(), nullable=True),
        sa.Column('initial_capital', sa.Float(), nullable=True),
        sa.Column('commission_rate', sa.Float(), nullable=True),
        sa.Column('slippage_rate', sa.Float(), nullable=True),
        sa.Column('risk_per_trade', sa.Float(), nullable=True),
        sa.Column('all_results', sa.JSON(), nullable=True),
        sa.Column('best_sharpe_ratio', sa.Float(), nullable=True),
        sa.Column('best_equity_curve', sa.JSON(), nullable=True),
        sa.Column('best_fills', sa.JSON(), nullable=True),
        sa.Column('error', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_research_runs_job_id'), 'research_runs', ['job_id'], unique=True)
    op.create_index(op.f('ix_research_runs_symbol'), 'research_runs', ['symbol'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_research_runs_symbol'), table_name='research_runs')
    op.drop_index(op.f('ix_research_runs_job_id'), table_name='research_runs')
    op.drop_table('research_runs')
