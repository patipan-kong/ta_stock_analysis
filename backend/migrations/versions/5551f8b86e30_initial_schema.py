"""initial_schema

Revision ID: 5551f8b86e30
Revises:
Create Date: 2026-05-19

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = '5551f8b86e30'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use CREATE TABLE IF NOT EXISTS semantics via inspect so this is safe
    # to run against both fresh and partially-migrated databases.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "portfolios" not in existing:
        op.create_table(
            "portfolios",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )

    if "portfolio_items" not in existing:
        op.create_table(
            "portfolio_items",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("portfolio_id", sa.Integer(), sa.ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("symbol", sa.String(), nullable=False),
            sa.Column("shares", sa.Float(), nullable=False),
            sa.Column("avg_cost", sa.Float(), nullable=False),
            sa.Column("allow_swap", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("portfolio_id", "symbol", name="uq_portfolio_symbol"),
        )

    if "watchlist" not in existing:
        op.create_table(
            "watchlist",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("symbol", sa.String(), unique=True, index=True, nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
        )

    if "agent_cache" not in existing:
        op.create_table(
            "agent_cache",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("symbol", sa.String(), index=True, nullable=False),
            sa.Column("agent", sa.String(), nullable=False),
            sa.Column("result_json", sa.Text(), nullable=False),
            sa.Column("cached_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("symbol", "agent", name="uq_agent_cache"),
        )

    if "analysis_cache" not in existing:
        op.create_table(
            "analysis_cache",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("symbol", sa.String(), unique=True, index=True, nullable=False),
            sa.Column("signal", sa.String(), nullable=False),
            sa.Column("confidence", sa.String(), nullable=False),
            sa.Column("reasoning", sa.Text(), nullable=False),
            sa.Column("risks", sa.Text(), nullable=False),
            sa.Column("analyzed_at", sa.DateTime(), nullable=False),
            sa.Column("ta_score", sa.Integer(), nullable=True),
            sa.Column("fa_score", sa.Integer(), nullable=True),
            sa.Column("ai_provider", sa.String(), nullable=True),
            sa.Column("ai_model", sa.String(), nullable=True),
            sa.Column("sources_used", sa.Text(), nullable=True),
        )

    if "analysis_history" not in existing:
        op.create_table(
            "analysis_history",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("symbol", sa.String(), index=True, nullable=False),
            sa.Column("signal", sa.String(), nullable=False),
            sa.Column("confidence", sa.String(), nullable=False),
            sa.Column("reasoning", sa.Text(), nullable=False),
            sa.Column("risks", sa.Text(), nullable=False),
            sa.Column("ta_score", sa.Integer(), nullable=True),
            sa.Column("fa_score", sa.Integer(), nullable=True),
            sa.Column("ai_provider", sa.String(), nullable=True),
            sa.Column("ai_model", sa.String(), nullable=True),
            sa.Column("sources_used", sa.Text(), nullable=True),
            sa.Column("scores", sa.Text(), nullable=True),
            sa.Column("analyzed_at", sa.DateTime(), nullable=False),
        )

    if "optimizer_history" not in existing:
        op.create_table(
            "optimizer_history",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("portfolio_id", sa.Integer(), sa.ForeignKey("portfolios.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("portfolio_name", sa.String(), nullable=False),
            sa.Column("analyzed_at", sa.DateTime(), nullable=False),
            sa.Column("swap_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("result_json", sa.Text(), nullable=False),
            sa.Column("ai_provider", sa.String(), nullable=True),
            sa.Column("ai_model", sa.String(), nullable=True),
        )

    if "settings" not in existing:
        op.create_table(
            "settings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("key", sa.String(), unique=True, nullable=False, index=True),
            sa.Column("value", sa.String(), nullable=False),
        )

    if "user_usage" not in existing:
        op.create_table(
            "user_usage",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("provider", sa.String(), nullable=False, index=True),
            sa.Column("model", sa.String(), nullable=False, index=True),
            sa.Column("operation", sa.String(), nullable=False, index=True),
            sa.Column("layer", sa.String(), nullable=True, index=True),
            sa.Column("input_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("output_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("total_tokens", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("input_cost_usd", sa.Float(), nullable=False, server_default=sa.text("0")),
            sa.Column("output_cost_usd", sa.Float(), nullable=False, server_default=sa.text("0")),
            sa.Column("total_cost_usd", sa.Float(), nullable=False, server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(), nullable=False, index=True),
        )


def downgrade() -> None:
    op.drop_table("user_usage")
    op.drop_table("settings")
    op.drop_table("optimizer_history")
    op.drop_table("analysis_history")
    op.drop_table("analysis_cache")
    op.drop_table("agent_cache")
    op.drop_table("watchlist")
    op.drop_table("portfolio_items")
    op.drop_table("portfolios")
