"""add_cash_balance_to_portfolios

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-05-20

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
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

    p = _existing_cols(inspector, "portfolios")
    if "cash_balance" not in p:
        op.add_column("portfolios", sa.Column("cash_balance", sa.Float(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("portfolios", "cash_balance")
