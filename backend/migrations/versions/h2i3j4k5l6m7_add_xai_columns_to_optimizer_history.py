"""add_xai_columns_to_optimizer_history

Revision ID: h2i3j4k5l6m7
Revises: g1h2i3j4k5l6
Create Date: 2026-05-22

Adds five XAI metadata columns to optimizer_history:
  - optimizer_status             : REBALANCE | NO_ACTION
  - rebalance_opportunity_score  : 0-100 integer
  - no_action_reason             : enum string (WELL_BALANCED | LOW_CONFIDENCE | ...)
  - no_action_summary            : human-readable explanation when NO_ACTION
  - blocked_opportunities_json   : JSON array of watchlist candidates blocked by constraints
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'h2i3j4k5l6m7'
down_revision: Union[str, Sequence[str], None] = 'g1h2i3j4k5l6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_cols(inspector, table: str) -> set:
    try:
        return {c["name"] for c in inspector.get_columns(table)}
    except Exception:
        return set()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    oh = _existing_cols(inspector, "optimizer_history")

    if "optimizer_status" not in oh:
        op.add_column("optimizer_history", sa.Column("optimizer_status", sa.String(), nullable=True))
    if "rebalance_opportunity_score" not in oh:
        op.add_column("optimizer_history", sa.Column("rebalance_opportunity_score", sa.Integer(), nullable=True))
    if "no_action_reason" not in oh:
        op.add_column("optimizer_history", sa.Column("no_action_reason", sa.String(), nullable=True))
    if "no_action_summary" not in oh:
        op.add_column("optimizer_history", sa.Column("no_action_summary", sa.Text(), nullable=True))
    if "blocked_opportunities_json" not in oh:
        op.add_column("optimizer_history", sa.Column("blocked_opportunities_json", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("optimizer_history", "blocked_opportunities_json")
    op.drop_column("optimizer_history", "no_action_summary")
    op.drop_column("optimizer_history", "no_action_reason")
    op.drop_column("optimizer_history", "rebalance_opportunity_score")
    op.drop_column("optimizer_history", "optimizer_status")
