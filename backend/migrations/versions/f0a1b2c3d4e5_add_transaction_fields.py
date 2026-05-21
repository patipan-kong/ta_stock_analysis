"""add_transaction_fields

Revision ID: f0a1b2c3d4e5
Revises: e5f6a7b8c9d0
Create Date: 2026-05-21

Phase 2A — Transaction System:
  - transactions.taxes         : withholding tax / stamp duty
  - transactions.currency      : ISO currency code (e.g. THB, USD)
  - transactions.exchange_rate : FX rate at time of transaction
  - transactions.symbol        : make nullable for cash-only transaction types
    (DEPOSIT, WITHDRAW, INITIAL_CASH)

New transaction_type values (stored as strings, no schema constraint):
  DEPOSIT, WITHDRAW, INITIAL_POSITION, INITIAL_CASH
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'f0a1b2c3d4e5'
down_revision: Union[str, Sequence[str], None] = 'e5f6a7b8c9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _col_names(bind, table: str) -> set:
    inspector = sa.inspect(bind)
    try:
        return {c["name"] for c in inspector.get_columns(table)}
    except Exception:
        return set()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "transactions" not in existing_tables:
        return

    cols = _col_names(bind, "transactions")

    if "taxes" not in cols:
        op.add_column("transactions", sa.Column("taxes", sa.Float(), nullable=True, server_default="0"))

    if "currency" not in cols:
        op.add_column("transactions", sa.Column("currency", sa.String(), nullable=True, server_default="THB"))

    if "exchange_rate" not in cols:
        op.add_column("transactions", sa.Column("exchange_rate", sa.Float(), nullable=True, server_default="1.0"))

    # symbol is already nullable in SQLite (no NOT NULL was enforced at creation in d4e5f6a7b8c9).
    # For PostgreSQL, alter nullability so DEPOSIT/WITHDRAW/INITIAL_CASH rows can have symbol=NULL.
    dialect = bind.dialect.name
    if dialect == "postgresql":
        op.alter_column("transactions", "symbol", nullable=True)


def downgrade() -> None:
    bind = op.get_bind()
    cols = _col_names(bind, "transactions")

    if "exchange_rate" in cols:
        op.drop_column("transactions", "exchange_rate")
    if "currency" in cols:
        op.drop_column("transactions", "currency")
    if "taxes" in cols:
        op.drop_column("transactions", "taxes")
