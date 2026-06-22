"""add recommendation_snapshot_id to shadow_portfolio_snapshots

Revision ID: z0a1b2c3d4e5
Revises: y9z0a1b2c3d4
Create Date: 2026-06-22

Phase 4C.6 (Timing Intelligence): adds recommendation_snapshot_id FK to
shadow_portfolio_snapshots so each daily SPS row records which optimizer
allocation was active that day.  Enables period-boundary detection via a
simple GROUP BY on an indexed integer column, and provides a direct JOIN to
RecommendationSnapshot for regime/persona attribution without JSON parsing.

NULL for rows written before this migration and for STATIC_FROZEN shadows
(which never rebalance).  Populated by value_shadow_portfolio() on every
write going forward.
"""
from alembic import op
import sqlalchemy as sa

revision = "z0a1b2c3d4e5"
down_revision = "y9z0a1b2c3d4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("shadow_portfolio_snapshots") as batch_op:
        batch_op.add_column(
            sa.Column("recommendation_snapshot_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_sps_recommendation_snapshot",
            "recommendation_snapshots",
            ["recommendation_snapshot_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_sps_recommendation_snapshot_id",
            ["recommendation_snapshot_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("shadow_portfolio_snapshots") as batch_op:
        batch_op.drop_index("ix_sps_recommendation_snapshot_id")
        batch_op.drop_constraint("fk_sps_recommendation_snapshot", type_="foreignkey")
        batch_op.drop_column("recommendation_snapshot_id")
