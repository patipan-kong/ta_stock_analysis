"""add_migration_execution_checkpoints

Revision ID: f2a4c6e8b0d2
Revises: e7a9c1d3f5b7
Create Date: 2026-07-09

Asset Registry epic — Milestone M5.2 (Migration Execution Framework).

Adds one new, standalone table: migration_execution_checkpoints — a durable
append-only log of per-claim-shape execution attempts, used by
services/migration_executor.py for resumability and audit (see
models/migration_execution.py for the "history over state" rationale).

Purely additive. No existing table (including the M1 asset tables and the
M2 registry_findings table) is altered; migration_execution_checkpoints
only holds a foreign key *into* assets.id, and no existing table gains a
foreign key to this one.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "f2a4c6e8b0d2"
down_revision: Union[str, Sequence[str], None] = "e7a9c1d3f5b7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "migration_execution_checkpoints",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("raw_symbol", sa.String(), nullable=False),
        sa.Column("canonical_symbol", sa.String(), nullable=True),
        sa.Column("currency", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("resolved_asset_id", sa.Integer(), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identifiers_attached", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_migration_execution_checkpoints_run_id", "migration_execution_checkpoints", ["run_id"],
    )
    op.create_index(
        "ix_migration_execution_checkpoints_resolved_asset_id", "migration_execution_checkpoints", ["resolved_asset_id"],
    )
    op.create_index(
        "ix_migration_execution_checkpoints_resume_lookup",
        "migration_execution_checkpoints",
        ["run_id", "raw_symbol", "canonical_symbol", "currency", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_migration_execution_checkpoints_resume_lookup", table_name="migration_execution_checkpoints")
    op.drop_index("ix_migration_execution_checkpoints_resolved_asset_id", table_name="migration_execution_checkpoints")
    op.drop_index("ix_migration_execution_checkpoints_run_id", table_name="migration_execution_checkpoints")
    op.drop_table("migration_execution_checkpoints")
