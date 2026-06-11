"""add market data sync columns to benchmark_prices

Revision ID: y9z0a1b2c3d4
Revises: x8y9z0a1b2c3
Create Date: 2026-06-11

Phase S.3 (Market Data Infrastructure): adds three nullable columns to
benchmark_prices so the GitHub Actions sync job can record provenance and
freshness for each price row.

    updated_at   DATETIME — timestamp of last sync write for this row
    data_source  VARCHAR  — 'yfinance_github_actions' | 'yfinance_local' | 'manual'
    sync_status  VARCHAR  — 'ok' | 'error' | 'stale'

NULL on all three columns is valid for rows written before this migration.
"""
from alembic import op
import sqlalchemy as sa

revision = "y9z0a1b2c3d4"
down_revision = "x8y9z0a1b2c3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("benchmark_prices") as batch_op:
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))
        batch_op.add_column(sa.Column("data_source", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("sync_status", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("benchmark_prices") as batch_op:
        batch_op.drop_column("sync_status")
        batch_op.drop_column("data_source")
        batch_op.drop_column("updated_at")
