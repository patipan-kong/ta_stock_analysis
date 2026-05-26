"""add manual_adjustment_value to portfolio_snapshots

Revision ID: s3t4u5v6w7x8
Revises: r2s3t4u5v6w7
Create Date: 2026-05-25

Adds manual_adjustment_value (nullable Float) to portfolio_snapshots.

This column stores the market value of QUANTITY_CORRECTION transactions that
occurred between the previous snapshot and this one.  Those corrections adjust
the share count of an existing position without a corresponding market trade —
they are balance-sheet events, not performance events, and must be subtracted
from the day-over-day NAV delta when computing investment_return_pct.

Historical rows have NULL; the snapshot engine defaults to 0.0 when reading
NULL, so all existing return calculations are unaffected.
"""
from alembic import op
import sqlalchemy as sa

revision = "s3t4u5v6w7x8"
down_revision = "r2s3t4u5v6w7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("portfolio_snapshots") as batch_op:
        batch_op.add_column(
            sa.Column("manual_adjustment_value", sa.Float(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("portfolio_snapshots") as batch_op:
        batch_op.drop_column("manual_adjustment_value")
