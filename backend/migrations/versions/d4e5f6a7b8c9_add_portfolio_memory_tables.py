"""add_portfolio_memory_tables

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-05-21

Phase 2 — Portfolio Memory:
  - transactions         : BUY / SELL / DIVIDEND records per portfolio holding
  - portfolio_snapshots  : daily total-value snapshot for historical charting
  - signal_history       : append-only signal log with sector + prev_signal for Thai SET grouping
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables(bind) -> set:
    inspector = sa.inspect(bind)
    return set(inspector.get_table_names())


def upgrade() -> None:
    bind = op.get_bind()
    tables = _existing_tables(bind)

    if "transactions" not in tables:
        op.create_table(
            "transactions",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("portfolio_id", sa.Integer(), sa.ForeignKey("portfolios.id", ondelete="CASCADE"),
                      nullable=False, index=True),
            sa.Column("symbol", sa.String(), nullable=False, index=True),
            sa.Column("transaction_type", sa.String(), nullable=False, index=True),
            sa.Column("shares", sa.Float(), nullable=True),
            sa.Column("price_per_share", sa.Float(), nullable=True),
            sa.Column("total_amount", sa.Float(), nullable=False),
            sa.Column("fees", sa.Float(), nullable=False, server_default="0"),
            sa.Column("transaction_date", sa.DateTime(), nullable=False, index=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("sector", sa.String(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )

    if "portfolio_snapshots" not in tables:
        op.create_table(
            "portfolio_snapshots",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("portfolio_id", sa.Integer(), sa.ForeignKey("portfolios.id", ondelete="CASCADE"),
                      nullable=False, index=True),
            sa.Column("snapshot_date", sa.String(), nullable=False, index=True),
            sa.Column("total_value", sa.Float(), nullable=False),
            sa.Column("cash_balance", sa.Float(), nullable=False, server_default="0"),
            sa.Column("total_invested", sa.Float(), nullable=False, server_default="0"),
            sa.Column("unrealized_pnl", sa.Float(), nullable=True),
            sa.Column("unrealized_pnl_pct", sa.Float(), nullable=True),
            sa.Column("sector_breakdown_json", sa.Text(), nullable=True),
            sa.Column("holdings_count", sa.Integer(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("portfolio_id", "snapshot_date", name="uq_portfolio_snapshot_date"),
        )

    if "signal_history" not in tables:
        op.create_table(
            "signal_history",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("symbol", sa.String(), nullable=False, index=True),
            sa.Column("sector", sa.String(), nullable=True, index=True),
            sa.Column("signal", sa.String(), nullable=False),
            sa.Column("prev_signal", sa.String(), nullable=True),
            sa.Column("confidence", sa.String(), nullable=True),
            sa.Column("ta_score", sa.Integer(), nullable=True),
            sa.Column("fa_score", sa.Integer(), nullable=True),
            sa.Column("ai_provider", sa.String(), nullable=True),
            sa.Column("ai_model", sa.String(), nullable=True),
            sa.Column("price_at_signal", sa.Float(), nullable=True),
            sa.Column("recorded_at", sa.DateTime(), nullable=False, index=True),
        )


def downgrade() -> None:
    op.drop_table("signal_history")
    op.drop_table("portfolio_snapshots")
    op.drop_table("transactions")
