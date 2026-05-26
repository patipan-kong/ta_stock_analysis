"""add imported_asset_value to portfolio_snapshots

Revision ID: r2s3t4u5v6w7
Revises: q1r2s3t4u5v6
Create Date: 2026-05-25

Adds a single nullable column to portfolio_snapshots that captures the
market value of all INITIAL_POSITION / position-import events that occurred
between the previous snapshot and this one.

This value is subtracted from the day-over-day NAV change when computing
investment_return_pct, ensuring that manually imported holdings are never
misclassified as trading gains.

Historical rows will have NULL — the snapshot engine defaults to 0.0 when
reading NULL, so all historical return calculations remain unchanged.

Companion change: portfolio_snapshots.py now also includes INITIAL_CASH
transactions in net_external_cash_flow (treated as onboarding deposits).
That is a pure code change — no schema migration is needed for it.
"""
from alembic import op
import sqlalchemy as sa

revision = "r2s3t4u5v6w7"
down_revision = "q1r2s3t4u5v6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("portfolio_snapshots") as batch_op:
        batch_op.add_column(
            sa.Column("imported_asset_value", sa.Float(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("portfolio_snapshots") as batch_op:
        batch_op.drop_column("imported_asset_value")
