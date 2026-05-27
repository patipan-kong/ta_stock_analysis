"""add period return breakdown columns to portfolio_snapshots

Revision ID: t4u5v6w7x8y9
Revises: s3t4u5v6w7x8
Create Date: 2026-05-27

Adds three nullable Float columns that expose a per-period decomposition of
the return waterfall, making the investment_return_pct figure auditable:

  period_realized_pnl    — P&L from SELL transactions in this snapshot window.
                           Informational only: already embedded in total_value
                           delta (and therefore in investment_return_pct) via
                           cash-balance changes from execute_sell().

  period_dividend_income — Cash dividends received between the previous
                           snapshot and this one.  Also already in total_value
                           (dividends increase cash_balance), so this column
                           is purely for transparency.

  period_fees_paid       — Sum of brokerage fees on BUY + SELL transactions in
                           this window.  Fees reduce net_proceeds (sell) or
                           increase total_cost (buy) and thus reduce the NAV —
                           they are NOT stripped from investment_return_pct.
                           This column lets users see the fee drag explicitly.

Historical rows receive NULL; the snapshot engine and analytics engine both
default to 0.0 when reading NULL, so all existing calculations are unaffected.
"""
from alembic import op
import sqlalchemy as sa

revision = "t4u5v6w7x8y9"
down_revision = "s3t4u5v6w7x8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("portfolio_snapshots") as batch_op:
        batch_op.add_column(sa.Column("period_realized_pnl", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("period_dividend_income", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("period_fees_paid", sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("portfolio_snapshots") as batch_op:
        batch_op.drop_column("period_fees_paid")
        batch_op.drop_column("period_dividend_income")
        batch_op.drop_column("period_realized_pnl")
