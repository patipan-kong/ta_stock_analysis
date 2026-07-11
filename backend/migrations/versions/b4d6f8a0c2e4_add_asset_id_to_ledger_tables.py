"""add_asset_id_to_ledger_tables

Revision ID: b4d6f8a0c2e4
Revises: c6e8a0f2d4b6
Create Date: 2026-07-11

M5 Track B — Stage 2 (docs/implementation/M5_TRACK_B_NATIVE_INTEGRATION_TDD.md
§4.1, §7 Stage 2).

Adds one nullable, indexed `asset_id` FK column each to `transactions`,
`portfolio_items`, and `watchlist` — the three symbol-keyed ledger tables
named in §4.1. `portfolio_snapshots` is deliberately NOT touched here; per
§4.2, historical snapshot rows are frozen and gain `asset_id` only as an
additive optional key inside `holdings_json` going forward, never as a
schema column.

Purely additive and inert on its own:
  - nullable=True on all three, permanently (not just during migration) —
    per §4.1, `asset_id IS NULL` is a permanently legitimate state for any
    symbol the Registry has not yet adjudicated, mirroring what
    `Unresolved` already means everywhere else in this codebase.
  - no unique constraint, no existing constraint touched, no existing
    column altered or dropped.
  - ondelete left at default RESTRICT (an Asset must never be deletable
    while a ledger row references it) — belt-and-braces, not load-bearing,
    since ASSET_REGISTRY.md §6 assets are never deleted anyway.
  - nothing reads this column yet. Stage 2's backfill
    (services/ledger_asset_backfill.py) only writes it;
    transaction_canonicalizer.py, portfolio_rebuilder.py, and every other
    consumer are untouched in this stage.
"""
from alembic import op
import sqlalchemy as sa

revision = "b4d6f8a0c2e4"
down_revision = "c6e8a0f2d4b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.add_column(sa.Column("asset_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_transactions_asset_id", "assets", ["asset_id"], ["id"],
        )
        batch_op.create_index("ix_transactions_asset_id", ["asset_id"])

    with op.batch_alter_table("portfolio_items") as batch_op:
        batch_op.add_column(sa.Column("asset_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_portfolio_items_asset_id", "assets", ["asset_id"], ["id"],
        )
        batch_op.create_index("ix_portfolio_items_asset_id", ["asset_id"])

    with op.batch_alter_table("watchlist") as batch_op:
        batch_op.add_column(sa.Column("asset_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_watchlist_asset_id", "assets", ["asset_id"], ["id"],
        )
        batch_op.create_index("ix_watchlist_asset_id", ["asset_id"])


def downgrade() -> None:
    with op.batch_alter_table("watchlist") as batch_op:
        batch_op.drop_index("ix_watchlist_asset_id")
        batch_op.drop_constraint("fk_watchlist_asset_id", type_="foreignkey")
        batch_op.drop_column("asset_id")

    with op.batch_alter_table("portfolio_items") as batch_op:
        batch_op.drop_index("ix_portfolio_items_asset_id")
        batch_op.drop_constraint("fk_portfolio_items_asset_id", type_="foreignkey")
        batch_op.drop_column("asset_id")

    with op.batch_alter_table("transactions") as batch_op:
        batch_op.drop_index("ix_transactions_asset_id")
        batch_op.drop_constraint("fk_transactions_asset_id", type_="foreignkey")
        batch_op.drop_column("asset_id")
