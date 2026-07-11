"""add_ledger_asset_backfill_checkpoints

Revision ID: e6f8b0d2a4c6
Revises: b4d6f8a0c2e4
Create Date: 2026-07-11

M5 Track B — Stage 2 (docs/implementation/M5_TRACK_B_NATIVE_INTEGRATION_TDD.md
§5.1). Adds one new, standalone table: ledger_asset_backfill_checkpoints — a
durable append-only log of per-claim-shape backfill attempts, used by
services/ledger_asset_backfill.py for resumability, idempotency reporting,
and precise rollback (see models/ledger_asset_backfill.py for the "history
over state" rationale, and why this table also stores exact touched row ids
unlike its M5.2 sibling migration_execution_checkpoints).

Purely additive. No existing table (including the M1 asset tables and the
Stage 2 asset_id columns added in b4d6f8a0c2e4) is altered; this table only
holds a nullable foreign key *into* assets.id, and no existing table gains
a foreign key to this one.
"""
from alembic import op
import sqlalchemy as sa

revision = "e6f8b0d2a4c6"
down_revision = "b4d6f8a0c2e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ledger_asset_backfill_checkpoints",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("raw_symbol", sa.String(), nullable=False),
        sa.Column("canonical_symbol", sa.String(), nullable=True),
        sa.Column("currency", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("resolved_asset_id", sa.Integer(), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=True),
        sa.Column("transactions_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("portfolio_items_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("watchlist_rows_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("transaction_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("portfolio_item_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("watchlist_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_ledger_asset_backfill_checkpoints_run_id", "ledger_asset_backfill_checkpoints", ["run_id"],
    )
    op.create_index(
        "ix_ledger_asset_backfill_checkpoints_resolved_asset_id",
        "ledger_asset_backfill_checkpoints", ["resolved_asset_id"],
    )
    op.create_index(
        "ix_ledger_asset_backfill_checkpoints_resume_lookup",
        "ledger_asset_backfill_checkpoints",
        ["run_id", "raw_symbol", "canonical_symbol", "currency", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_ledger_asset_backfill_checkpoints_resume_lookup", table_name="ledger_asset_backfill_checkpoints")
    op.drop_index("ix_ledger_asset_backfill_checkpoints_resolved_asset_id", table_name="ledger_asset_backfill_checkpoints")
    op.drop_index("ix_ledger_asset_backfill_checkpoints_run_id", table_name="ledger_asset_backfill_checkpoints")
    op.drop_table("ledger_asset_backfill_checkpoints")
