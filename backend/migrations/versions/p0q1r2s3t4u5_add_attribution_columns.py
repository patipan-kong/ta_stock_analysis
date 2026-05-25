"""add attribution columns for Phase 3B.7B

Adds human-vs-AI comparison columns to attribution_metrics:
  portfolio_id, recommendation_snapshot_id, evaluation_window_days,
  actual_return_pct, static_shadow_return_pct, ai_model_return_pct,
  avoided_drawdown_pct, regret_score, ai_outperformed

Revision ID: p0q1r2s3t4u5
Revises: n8o9p0q1r2s3
Create Date: 2026-05-25
"""
from alembic import op
import sqlalchemy as sa

revision = "p0q1r2s3t4u5"
down_revision = "n8o9p0q1r2s3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("attribution_metrics") as batch_op:
        batch_op.add_column(sa.Column("portfolio_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("recommendation_snapshot_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("evaluation_window_days", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("actual_return_pct", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("static_shadow_return_pct", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("ai_model_return_pct", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("avoided_drawdown_pct", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("regret_score", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("ai_outperformed", sa.Boolean(), nullable=True))
        batch_op.create_index("ix_am_portfolio", ["portfolio_id"])
        batch_op.create_index("ix_am_rec_snap", ["recommendation_snapshot_id"])


def downgrade() -> None:
    with op.batch_alter_table("attribution_metrics") as batch_op:
        batch_op.drop_index("ix_am_rec_snap")
        batch_op.drop_index("ix_am_portfolio")
        batch_op.drop_column("ai_outperformed")
        batch_op.drop_column("regret_score")
        batch_op.drop_column("avoided_drawdown_pct")
        batch_op.drop_column("ai_model_return_pct")
        batch_op.drop_column("static_shadow_return_pct")
        batch_op.drop_column("actual_return_pct")
        batch_op.drop_column("evaluation_window_days")
        batch_op.drop_column("recommendation_snapshot_id")
        batch_op.drop_column("portfolio_id")
