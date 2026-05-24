"""add_regime_snapshots_table

Revision ID: m7n8o9p0q1r2
Revises: l6m7n8o9p0q1
Create Date: 2026-05-24

Adds regime_snapshots table for daily market regime detection history.
Used by Phase 3B.3 Market Regime Detection & Adaptive Portfolio Intelligence.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "m7n8o9p0q1r2"
down_revision: Union[str, Sequence[str], None] = "l6m7n8o9p0q1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "regime_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("snapshot_date", sa.String(), nullable=False, index=True),
        sa.Column("regime", sa.String(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("trend_score", sa.Float(), nullable=True),
        sa.Column("volatility_score", sa.Float(), nullable=True),
        sa.Column("drawdown_score", sa.Float(), nullable=True),
        sa.Column("momentum_score", sa.Float(), nullable=True),
        sa.Column("vol_z_score", sa.Float(), nullable=True),
        sa.Column("ema_alignment", sa.Float(), nullable=True),
        sa.Column("regime_duration_days", sa.Integer(), nullable=True),
        sa.Column("previous_regime", sa.String(), nullable=True),
        sa.Column("transition_stability", sa.String(), nullable=True),
        sa.Column("signals_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("snapshot_date", name="uq_regime_snapshot_date"),
    )
    op.create_index("ix_regime_snapshots_regime", "regime_snapshots", ["regime"])


def downgrade() -> None:
    op.drop_index("ix_regime_snapshots_regime", "regime_snapshots")
    op.drop_table("regime_snapshots")
