"""add ledger_repairs table

Revision ID: b4c6d8e0f2a4
Revises: a1b3c5d7e9f0
Create Date: 2026-06-28

Phase 6.7A: LedgerRepair Foundation.

Introduces the ledger_repairs table — a durable, append-only metadata layer
that sits above the immutable Transaction ledger.  Repairs describe intended
overlay transformations (EXCLUDE, SUPPRESS_FINDING) without touching Transaction
rows.  The effective canonical list is derived at rebuild time by applying
active repairs to the raw canonical list.

Design notes
------------
* is_active soft-delete: deactivated rows are retained for audit.
* repair_plan_id (UUID string) groups all repairs from one plan invocation.
  Version history = sequence of plans ordered by created_at.
* Partial unique index enforces at most one active repair of the same type per
  transaction (PostgreSQL only).  Application-layer validation covers SQLite.
* transaction_id is nullable for future portfolio-level repair types that do
  not target a single transaction.

Graph-repair note (AI Evaluation M0, 2026-07-06): this revision originally
shipped as id "a1b2c3d4e5f6", colliding with the pre-existing
add_latency_columns migration, and its down_revision pointed at z0a1b2c3d4e5
in parallel with a1b3c5d7e9f0 (an unmerged branch) — `alembic current`
detected a graph cycle and could not run at all. The ledger_repairs table
was already live in the dev DB (created out-of-band, missing two of its
indexes) with alembic_version stamped at a1b3c5d7e9f0. Fixed here: renamed to
a unique id, rebased onto the true head (a1b3c5d7e9f0), and the two missing
indexes were added to the live DB directly before stamping this revision as
applied (no upgrade() re-run against the already-existing table). See
DECISION_LOG.md.
"""
from alembic import op
import sqlalchemy as sa

revision = "b4c6d8e0f2a4"
down_revision = "a1b3c5d7e9f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ledger_repairs",
        sa.Column("id",             sa.Integer(),  nullable=False, autoincrement=True),
        sa.Column("portfolio_id",   sa.Integer(),  nullable=False),
        sa.Column("transaction_id", sa.Integer(),  nullable=True),
        sa.Column("repair_plan_id", sa.String(),   nullable=False),
        sa.Column("repair_type",    sa.String(),   nullable=False),
        sa.Column("reason",         sa.Text(),     nullable=False),
        sa.Column("reason_code",    sa.String(),   nullable=True),
        sa.Column("payload_json",   sa.Text(),     nullable=True),
        sa.Column("created_by",     sa.String(),   nullable=False, server_default="system"),
        sa.Column("created_at",     sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("is_active",      sa.Boolean(),  nullable=False, server_default=sa.true()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["portfolio_id"],   ["portfolios.id"],   ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_ledger_repairs_portfolio_id",        "ledger_repairs", ["portfolio_id"])
    op.create_index("ix_ledger_repairs_transaction_id",      "ledger_repairs", ["transaction_id"])
    op.create_index("ix_ledger_repairs_repair_plan_id",      "ledger_repairs", ["repair_plan_id"])
    op.create_index("ix_ledger_repairs_repair_type",         "ledger_repairs", ["repair_type"])
    op.create_index("ix_ledger_repairs_portfolio_is_active", "ledger_repairs", ["portfolio_id", "is_active"])
    # Partial unique: at most one active repair of the same type per transaction.
    # postgresql_where is ignored on SQLite; application-layer validation covers that path.
    op.create_index(
        "uq_ledger_repairs_active_per_tx_type",
        "ledger_repairs",
        ["portfolio_id", "transaction_id", "repair_type"],
        unique=True,
        postgresql_where=sa.text("is_active = TRUE"),
    )


def downgrade() -> None:
    op.drop_index("uq_ledger_repairs_active_per_tx_type", table_name="ledger_repairs")
    op.drop_index("ix_ledger_repairs_portfolio_is_active", table_name="ledger_repairs")
    op.drop_index("ix_ledger_repairs_repair_type",         table_name="ledger_repairs")
    op.drop_index("ix_ledger_repairs_repair_plan_id",      table_name="ledger_repairs")
    op.drop_index("ix_ledger_repairs_transaction_id",      table_name="ledger_repairs")
    op.drop_index("ix_ledger_repairs_portfolio_id",        table_name="ledger_repairs")
    op.drop_table("ledger_repairs")
