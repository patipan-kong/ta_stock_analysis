"""add_snapshot_detail_columns

Revision ID: g1h2i3j4k5l6
Revises: e5f6a7b8c9d0
Create Date: 2026-05-21

Adds three new columns to portfolio_snapshots:
  - realized_pnl      : cumulative realized P/L from all SELL transactions
  - daily_return_pct  : day-over-day return % versus the previous snapshot
  - holdings_json     : JSON array of per-holding breakdown for the snapshot date
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'g1h2i3j4k5l6'
down_revision: Union[str, Sequence[str], None] = 'f0a1b2c3d4e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _col_names(bind, table: str) -> set:
    try:
        return {c["name"] for c in sa.inspect(bind).get_columns(table)}
    except Exception:
        return set()


def upgrade() -> None:
    bind = op.get_bind()
    cols = _col_names(bind, "portfolio_snapshots")

    if "realized_pnl" not in cols:
        op.add_column("portfolio_snapshots", sa.Column("realized_pnl", sa.Float(), nullable=True))

    if "daily_return_pct" not in cols:
        op.add_column("portfolio_snapshots", sa.Column("daily_return_pct", sa.Float(), nullable=True))

    if "holdings_json" not in cols:
        op.add_column("portfolio_snapshots", sa.Column("holdings_json", sa.Text(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    cols = _col_names(bind, "portfolio_snapshots")

    if "holdings_json" in cols:
        op.drop_column("portfolio_snapshots", "holdings_json")
    if "daily_return_pct" in cols:
        op.drop_column("portfolio_snapshots", "daily_return_pct")
    if "realized_pnl" in cols:
        op.drop_column("portfolio_snapshots", "realized_pnl")
