"""add_decision_memory_tables

Revision ID: n8o9p0q1r2s3
Revises: m7n8o9p0q1r2
Create Date: 2026-05-25

Phase 3B.7 — Decision Memory System.

Adds 6 tables that form the Decision Attribution & Benchmark Intelligence layer:
  - recommendation_snapshots  : full optimizer context at run time
  - user_execution_decisions  : APPROVED | REJECTED | MANUAL_OVERRIDE per recommendation
  - shadow_portfolios         : paper portfolio metadata (STATIC_FROZEN | ACTIVE_MODEL)
  - shadow_portfolio_snapshots: daily paper-trading valuations
  - attribution_metrics       : Brinson-Hood-Beebower alpha attribution stubs
  - confidence_calibration_records : AI confidence → realized-outcome calibration stubs
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "n8o9p0q1r2s3"
down_revision: Union[str, Sequence[str], None] = "m7n8o9p0q1r2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── recommendation_snapshots ──────────────────────────────────────────────
    op.create_table(
        "recommendation_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("optimizer_history_id", sa.Integer(), sa.ForeignKey("optimizer_history.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("portfolio_id", sa.Integer(), sa.ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("persona", sa.String(), nullable=True),
        sa.Column("total_portfolio_value", sa.Float(), nullable=True),
        sa.Column("regime_snapshot_json", sa.Text(), nullable=True),
        sa.Column("constraint_envelope_json", sa.Text(), nullable=True),
        sa.Column("active_policy_json", sa.Text(), nullable=True),
        sa.Column("layer1_output_json", sa.Text(), nullable=True),
        sa.Column("layer2_output_json", sa.Text(), nullable=True),
        sa.Column("layer3_output_json", sa.Text(), nullable=True),
        sa.Column("consensus_json", sa.Text(), nullable=True),
        sa.Column("portfolio_dna_json", sa.Text(), nullable=True),
        sa.Column("style_drift_json", sa.Text(), nullable=True),
        sa.Column("scores_map_json", sa.Text(), nullable=True),
        sa.Column("projected_allocations_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_rec_snap_ws", "recommendation_snapshots", ["workspace_id"])
    op.create_index("ix_rec_snap_portfolio", "recommendation_snapshots", ["portfolio_id"])
    op.create_index("ix_rec_snap_oh", "recommendation_snapshots", ["optimizer_history_id"])

    # ── user_execution_decisions ──────────────────────────────────────────────
    op.create_table(
        "user_execution_decisions",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("recommendation_snapshot_id", sa.Integer(), sa.ForeignKey("recommendation_snapshots.id", ondelete="CASCADE"), nullable=False),
        sa.Column("optimizer_history_id", sa.Integer(), sa.ForeignKey("optimizer_history.id", ondelete="SET NULL"), nullable=True),
        sa.Column("portfolio_id", sa.Integer(), sa.ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("decision", sa.String(), nullable=False),
        sa.Column("approved_allocations_json", sa.Text(), nullable=True),
        sa.Column("rejected_symbols_json", sa.Text(), nullable=True),
        sa.Column("override_notes", sa.Text(), nullable=True),
        sa.Column("executed_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ued_ws", "user_execution_decisions", ["workspace_id"])
    op.create_index("ix_ued_snapshot", "user_execution_decisions", ["recommendation_snapshot_id"])
    op.create_index("ix_ued_decision", "user_execution_decisions", ["decision"])
    op.create_index("ix_ued_portfolio", "user_execution_decisions", ["portfolio_id"])

    # ── shadow_portfolios ─────────────────────────────────────────────────────
    op.create_table(
        "shadow_portfolios",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("portfolio_id", sa.Integer(), sa.ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shadow_type", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("inception_date", sa.String(), nullable=False),
        sa.Column("inception_value", sa.Float(), nullable=True),
        sa.Column("recommendation_snapshot_id", sa.Integer(), sa.ForeignKey("recommendation_snapshots.id", ondelete="SET NULL"), nullable=True),
        sa.Column("execution_decision_id", sa.Integer(), sa.ForeignKey("user_execution_decisions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("inception_holdings_json", sa.Text(), nullable=True),
        sa.Column("paper_cash_balance", sa.Float(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("last_valued_at", sa.DateTime(), nullable=True),
        sa.Column("current_value", sa.Float(), nullable=True),
        sa.Column("inception_return_pct", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_sp_ws", "shadow_portfolios", ["workspace_id"])
    op.create_index("ix_sp_portfolio", "shadow_portfolios", ["portfolio_id"])
    op.create_index("ix_sp_type", "shadow_portfolios", ["shadow_type"])

    # ── shadow_portfolio_snapshots ────────────────────────────────────────────
    op.create_table(
        "shadow_portfolio_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("shadow_portfolio_id", sa.Integer(), sa.ForeignKey("shadow_portfolios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_date", sa.String(), nullable=False),
        sa.Column("total_value", sa.Float(), nullable=False),
        sa.Column("return_pct_since_inception", sa.Float(), nullable=True),
        sa.Column("daily_return_pct", sa.Float(), nullable=True),
        sa.Column("holdings_json", sa.Text(), nullable=True),
        sa.Column("benchmark_symbol", sa.String(), nullable=True),
        sa.Column("benchmark_return_pct", sa.Float(), nullable=True),
        sa.Column("alpha", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("shadow_portfolio_id", "snapshot_date", name="uq_shadow_snapshot_date"),
    )
    op.create_index("ix_sps_shadow", "shadow_portfolio_snapshots", ["shadow_portfolio_id"])
    op.create_index("ix_sps_date", "shadow_portfolio_snapshots", ["snapshot_date"])

    # ── attribution_metrics ───────────────────────────────────────────────────
    op.create_table(
        "attribution_metrics",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shadow_portfolio_id", sa.Integer(), sa.ForeignKey("shadow_portfolios.id", ondelete="CASCADE"), nullable=False),
        sa.Column("evaluation_period_start", sa.String(), nullable=False),
        sa.Column("evaluation_period_end", sa.String(), nullable=False),
        sa.Column("portfolio_return", sa.Float(), nullable=True),
        sa.Column("benchmark_return", sa.Float(), nullable=True),
        sa.Column("selection_alpha", sa.Float(), nullable=True),
        sa.Column("allocation_alpha", sa.Float(), nullable=True),
        sa.Column("interaction_effect", sa.Float(), nullable=True),
        sa.Column("total_alpha", sa.Float(), nullable=True),
        sa.Column("attribution_breakdown_json", sa.Text(), nullable=True),
        sa.Column("computed_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_am_ws", "attribution_metrics", ["workspace_id"])
    op.create_index("ix_am_shadow", "attribution_metrics", ["shadow_portfolio_id"])

    # ── confidence_calibration_records ────────────────────────────────────────
    op.create_table(
        "confidence_calibration_records",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("workspace_id", sa.Integer(), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("optimizer_history_id", sa.Integer(), sa.ForeignKey("optimizer_history.id", ondelete="SET NULL"), nullable=True),
        sa.Column("recommendation_snapshot_id", sa.Integer(), sa.ForeignKey("recommendation_snapshots.id", ondelete="SET NULL"), nullable=True),
        sa.Column("lookback_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("consensus_strength_calibration", sa.Float(), nullable=True),
        sa.Column("policy_alignment_calibration", sa.Float(), nullable=True),
        sa.Column("regime_confidence_calibration", sa.Float(), nullable=True),
        sa.Column("signal_accuracy_json", sa.Text(), nullable=True),
        sa.Column("calibration_score", sa.Float(), nullable=True),
        sa.Column("feedback_context_json", sa.Text(), nullable=True),
        sa.Column("computed_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_ccr_ws", "confidence_calibration_records", ["workspace_id"])
    op.create_index("ix_ccr_oh", "confidence_calibration_records", ["optimizer_history_id"])


def downgrade() -> None:
    op.drop_index("ix_ccr_oh", "confidence_calibration_records")
    op.drop_index("ix_ccr_ws", "confidence_calibration_records")
    op.drop_table("confidence_calibration_records")

    op.drop_index("ix_am_shadow", "attribution_metrics")
    op.drop_index("ix_am_ws", "attribution_metrics")
    op.drop_table("attribution_metrics")

    op.drop_index("ix_sps_date", "shadow_portfolio_snapshots")
    op.drop_index("ix_sps_shadow", "shadow_portfolio_snapshots")
    op.drop_table("shadow_portfolio_snapshots")

    op.drop_index("ix_sp_type", "shadow_portfolios")
    op.drop_index("ix_sp_portfolio", "shadow_portfolios")
    op.drop_index("ix_sp_ws", "shadow_portfolios")
    op.drop_table("shadow_portfolios")

    op.drop_index("ix_ued_portfolio", "user_execution_decisions")
    op.drop_index("ix_ued_decision", "user_execution_decisions")
    op.drop_index("ix_ued_snapshot", "user_execution_decisions")
    op.drop_index("ix_ued_ws", "user_execution_decisions")
    op.drop_table("user_execution_decisions")

    op.drop_index("ix_rec_snap_oh", "recommendation_snapshots")
    op.drop_index("ix_rec_snap_portfolio", "recommendation_snapshots")
    op.drop_index("ix_rec_snap_ws", "recommendation_snapshots")
    op.drop_table("recommendation_snapshots")
