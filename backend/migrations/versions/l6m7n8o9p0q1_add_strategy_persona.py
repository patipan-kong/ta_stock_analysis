"""add_strategy_persona_to_portfolios

Revision ID: l6m7n8o9p0q1
Revises: k5l6m7n8o9p0
Create Date: 2026-05-23

Adds strategy_persona column to the portfolios table.
Supported values: BALANCED | GROWTH | VALUE | DIVIDEND | MOMENTUM | PASSIVE
Default: BALANCED
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "l6m7n8o9p0q1"
down_revision: Union[str, Sequence[str], None] = "k5l6m7n8o9p0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "portfolios",
        sa.Column("strategy_persona", sa.String(), nullable=True, server_default="BALANCED"),
    )


def downgrade() -> None:
    op.drop_column("portfolios", "strategy_persona")
