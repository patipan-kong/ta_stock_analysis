"""add_registry_bootstrap_checkpoints

Revision ID: c6e8a0f2d4b6
Revises: f2a4c6e8b0d2
Create Date: 2026-07-09

Asset Registry epic — Milestone M5.3 (Registry Bootstrap).

Adds one new, standalone table: registry_bootstrap_checkpoints — a durable
append-only log of per-claim-shape mint attempts, used by
services/registry_bootstrap.py for resumability and audit (see
models/registry_bootstrap.py for the "history over state" rationale and why
this is a separate table from migration_execution_checkpoints rather than a
reuse of it).

Purely additive. No existing table (including the M1 asset tables, the M2
registry_findings table, and the M5.2 migration_execution_checkpoints
table) is altered; registry_bootstrap_checkpoints only holds a nullable
foreign key *into* assets.id, and no existing table gains a foreign key to
this one.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c6e8a0f2d4b6"
down_revision: Union[str, Sequence[str], None] = "f2a4c6e8b0d2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "registry_bootstrap_checkpoints",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("raw_symbol", sa.String(), nullable=False),
        sa.Column("canonical_symbol", sa.String(), nullable=True),
        sa.Column("currency", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("minted_asset_id", sa.Integer(), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=True),
        sa.Column("identifiers_attached", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_registry_bootstrap_checkpoints_run_id", "registry_bootstrap_checkpoints", ["run_id"],
    )
    op.create_index(
        "ix_registry_bootstrap_checkpoints_minted_asset_id", "registry_bootstrap_checkpoints", ["minted_asset_id"],
    )
    op.create_index(
        "ix_registry_bootstrap_checkpoints_resume_lookup",
        "registry_bootstrap_checkpoints",
        ["run_id", "raw_symbol", "canonical_symbol", "currency", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_registry_bootstrap_checkpoints_resume_lookup", table_name="registry_bootstrap_checkpoints")
    op.drop_index("ix_registry_bootstrap_checkpoints_minted_asset_id", table_name="registry_bootstrap_checkpoints")
    op.drop_index("ix_registry_bootstrap_checkpoints_run_id", table_name="registry_bootstrap_checkpoints")
    op.drop_table("registry_bootstrap_checkpoints")
