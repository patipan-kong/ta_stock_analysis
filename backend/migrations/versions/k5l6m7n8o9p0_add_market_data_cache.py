"""add_market_data_cache

Revision ID: k5l6m7n8o9p0
Revises: j4k5l6m7n8o9
Create Date: 2026-05-23

Creates the market_data_cache table: a DB-backed cache for raw yfinance
responses (quotes, fundamentals, OHLCV history).  Shared across workspaces —
market data is not user-specific.

TTL policy is enforced by the application layer (services/data_fetcher.py),
not by the DB; the expires_at column lets the app quickly identify stale rows.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "k5l6m7n8o9p0"
down_revision: Union[str, Sequence[str], None] = "j4k5l6m7n8o9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "market_data_cache" in inspector.get_table_names():
        return  # idempotent – already applied

    op.create_table(
        "market_data_cache",
        sa.Column("id",           sa.Integer(),  primary_key=True),
        sa.Column("symbol",       sa.String(),   nullable=False),
        sa.Column("cache_type",   sa.String(),   nullable=False),
        sa.Column("payload_json", sa.Text(),     nullable=False),
        sa.Column("fetched_at",   sa.DateTime(), nullable=False),
        sa.Column("expires_at",   sa.DateTime(), nullable=False),
        sa.Column("hit_count",    sa.Integer(),  nullable=False, server_default="0"),
        sa.UniqueConstraint("symbol", "cache_type", name="uq_market_data_cache"),
    )
    op.create_index("ix_mdc_symbol",  "market_data_cache", ["symbol"])
    op.create_index("ix_mdc_expires", "market_data_cache", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_mdc_expires", table_name="market_data_cache")
    op.drop_index("ix_mdc_symbol",  table_name="market_data_cache")
    op.drop_table("market_data_cache")
