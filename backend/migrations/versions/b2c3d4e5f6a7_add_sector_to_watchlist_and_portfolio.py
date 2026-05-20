"""add_sector_to_watchlist_and_portfolio

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-05-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
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

    wl = _existing_cols(inspector, "watchlist")
    if "sector" not in wl:
        op.add_column("watchlist", sa.Column("sector", sa.String(), nullable=True))

    pi = _existing_cols(inspector, "portfolio_items")
    if "sector" not in pi:
        op.add_column("portfolio_items", sa.Column("sector", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("portfolio_items", "sector")
    op.drop_column("watchlist", "sector")
