"""add_registry_findings

Revision ID: e7a9c1d3f5b7
Revises: d6f8a0b2c4d6
Create Date: 2026-07-09

Asset Registry epic — Milestone M2 (Registry Service Boundary).

Adds one new, standalone table: registry_findings — durable evidence
records for duplicate-claim and identifier-conflict findings surfaced by
the M2 service boundary (docs/architecture/ASSET_REGISTRY.md Section 7).

Purely additive. No existing table (including the M1 asset tables) is
altered; registry_findings only holds nullable foreign keys *into*
assets.id, and no existing table gains a foreign key to this one.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "e7a9c1d3f5b7"
down_revision: Union[str, Sequence[str], None] = "d6f8a0b2c4d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "registry_findings",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("finding_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="OPEN"),
        sa.Column("subject_asset_id", sa.Integer(), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("related_asset_id", sa.Integer(), sa.ForeignKey("assets.id", ondelete="CASCADE"), nullable=True),
        sa.Column("identifier_type", sa.String(), nullable=True),
        sa.Column("identifier_value", sa.String(), nullable=True),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("resolution", sa.String(), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("resolved_by", sa.String(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_registry_findings_status", "registry_findings", ["status"])
    op.create_index("ix_registry_findings_subject_asset_id", "registry_findings", ["subject_asset_id"])
    op.create_index("ix_registry_findings_related_asset_id", "registry_findings", ["related_asset_id"])


def downgrade() -> None:
    op.drop_index("ix_registry_findings_related_asset_id", table_name="registry_findings")
    op.drop_index("ix_registry_findings_subject_asset_id", table_name="registry_findings")
    op.drop_index("ix_registry_findings_status", table_name="registry_findings")
    op.drop_table("registry_findings")
