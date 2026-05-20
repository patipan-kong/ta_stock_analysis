"""add_latency_columns

Revision ID: a1b2c3d4e5f6
Revises: 5551f8b86e30
Create Date: 2026-05-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '5551f8b86e30'
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

    # user_usage — add latency_ms
    uu = _existing_cols(inspector, "user_usage")
    if "latency_ms" not in uu:
        op.add_column("user_usage", sa.Column("latency_ms", sa.Integer(), nullable=True))

    # analysis_history — add latency_ms, total_latency_ms
    ah = _existing_cols(inspector, "analysis_history")
    if "latency_ms" not in ah:
        op.add_column("analysis_history", sa.Column("latency_ms", sa.Integer(), nullable=True))
    if "total_latency_ms" not in ah:
        op.add_column("analysis_history", sa.Column("total_latency_ms", sa.Integer(), nullable=True))

    # optimizer_history — add four latency columns
    oh = _existing_cols(inspector, "optimizer_history")
    for col in ("layer1_latency_ms", "layer2_latency_ms", "layer3_latency_ms", "total_latency_ms"):
        if col not in oh:
            op.add_column("optimizer_history", sa.Column(col, sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("optimizer_history", "total_latency_ms")
    op.drop_column("optimizer_history", "layer3_latency_ms")
    op.drop_column("optimizer_history", "layer2_latency_ms")
    op.drop_column("optimizer_history", "layer1_latency_ms")
    op.drop_column("analysis_history", "total_latency_ms")
    op.drop_column("analysis_history", "latency_ms")
    op.drop_column("user_usage", "latency_ms")
