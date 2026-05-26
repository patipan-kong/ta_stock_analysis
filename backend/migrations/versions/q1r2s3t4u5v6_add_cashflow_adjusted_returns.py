"""add cashflow-adjusted return columns to portfolio_snapshots

Revision ID: q1r2s3t4u5v6
Revises: p0q1r2s3t4u5
Create Date: 2026-05-25

Adds three nullable columns to portfolio_snapshots that separate
external cash flows (deposits / withdrawals) from true investment
performance, eliminating the "deposit = return" accounting bug.

  net_external_cash_flow  — sum of deposits minus withdrawals since the
                            previous snapshot (positive = net inflow).
  investment_return_pct   — cash-flow-adjusted daily return percentage.
                            Formula: (today_nav - prev_nav - net_ecf) / prev_nav × 100
                            This is now identical to the corrected daily_return_pct.
  investment_return_amount — absolute monetary gain/loss from market
                            movement only (same numerator, in currency units).

Historical rows will have NULL in all three columns.  Code in
portfolio_snapshots.py defaults safely to 0.0 when reading them.
"""
from alembic import op
import sqlalchemy as sa

revision = "q1r2s3t4u5v6"
down_revision = "p0q1r2s3t4u5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("portfolio_snapshots") as batch_op:
        batch_op.add_column(sa.Column("net_external_cash_flow", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("investment_return_pct", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("investment_return_amount", sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("portfolio_snapshots") as batch_op:
        batch_op.drop_column("investment_return_amount")
        batch_op.drop_column("investment_return_pct")
        batch_op.drop_column("net_external_cash_flow")
