"""add_benchmark_prices

Revision ID: i3j4k5l6m7n8
Revises: h2i3j4k5l6m7
Create Date: 2026-05-22

Creates the benchmark_prices table for storing daily closing prices of
index/ETF benchmarks (e.g. ^SET, QQQ) used in the performance-comparison
analytics endpoint.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'i3j4k5l6m7n8'
down_revision: Union[str, Sequence[str], None] = 'h2i3j4k5l6m7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())

    if "benchmark_prices" not in existing:
        op.create_table(
            "benchmark_prices",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("symbol", sa.String(), nullable=False, index=True),
            sa.Column("price_date", sa.String(), nullable=False, index=True),
            sa.Column("close_price", sa.Float(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.UniqueConstraint("symbol", "price_date", name="uq_benchmark_symbol_date"),
        )


def downgrade() -> None:
    op.drop_table("benchmark_prices")
