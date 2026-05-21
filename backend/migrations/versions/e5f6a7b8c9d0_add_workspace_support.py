"""add_workspace_support

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-05-21

Phase 2 — Workspace Support:
  - Creates the 'workspaces' table (id, name, created_at, updated_at)
  - Inserts default workspace (id=1, name='Default')
  - Adds workspace_id FK to every user-owned table:
      portfolios, portfolio_items, watchlist,
      analysis_cache, analysis_history, optimizer_history, settings,
      transactions, portfolio_snapshots, signal_history
  - Backfills all existing rows with workspace_id = 1
  - Sets workspace_id NOT NULL on all tables
  - Replaces column-level unique constraints with workspace-scoped composite ones:
      watchlist.symbol           → (workspace_id, symbol)
      analysis_cache.symbol      → (workspace_id, symbol)
      settings.key               → (workspace_id, key)
"""
from typing import Sequence, Union
from datetime import datetime

import sqlalchemy as sa
from alembic import op

revision: str = 'e5f6a7b8c9d0'
down_revision: Union[str, Sequence[str], None] = 'd4e5f6a7b8c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Every user-owned table that gains workspace_id
_OWNED_TABLES = [
    "portfolios",
    "portfolio_items",
    "watchlist",
    "analysis_cache",
    "analysis_history",
    "optimizer_history",
    "settings",
    "transactions",
    "portfolio_snapshots",
    "signal_history",
]

# Old column-level unique constraints → new workspace-scoped composites
# (old_constraint_name, table, new_constraint_name, columns)
_UNIQUE_REWRITES = [
    ("watchlist_symbol_key",      "watchlist",      "uq_watchlist_ws_symbol",       ["workspace_id", "symbol"]),
    ("analysis_cache_symbol_key", "analysis_cache", "uq_analysis_cache_ws_symbol",  ["workspace_id", "symbol"]),
    ("settings_key_key",          "settings",       "uq_settings_ws_key",           ["workspace_id", "key"]),
]


def _col_names(inspector, table: str) -> set:
    try:
        return {c["name"] for c in inspector.get_columns(table)}
    except Exception:
        return set()


def _uq_names(inspector, table: str) -> set:
    try:
        return {c["name"] for c in inspector.get_unique_constraints(table)}
    except Exception:
        return set()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # ── 1. Create workspaces table ────────────────────────────────────────────
    if "workspaces" not in existing_tables:
        op.create_table(
            "workspaces",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(), nullable=False, server_default="Default"),
            sa.Column("created_at", sa.DateTime(), nullable=True),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )

    # ── 2. Insert default workspace ───────────────────────────────────────────
    op.execute(sa.text(
        "INSERT INTO workspaces (id, name, created_at, updated_at) "
        "SELECT 1, 'Default', NOW(), NOW() "
        "WHERE NOT EXISTS (SELECT 1 FROM workspaces WHERE id = 1)"
    ))

    # ── 3. Add workspace_id to each owned table ───────────────────────────────
    for table in _OWNED_TABLES:
        if table not in existing_tables:
            continue
        if "workspace_id" in _col_names(inspector, table):
            continue

        # Add as nullable first so existing rows don't violate NOT NULL
        op.add_column(table, sa.Column("workspace_id", sa.Integer(), nullable=True))
        op.execute(sa.text(f"UPDATE {table} SET workspace_id = 1"))
        op.alter_column(table, "workspace_id", nullable=False)

        op.create_foreign_key(
            f"fk_{table}_workspace_id",
            table, "workspaces",
            ["workspace_id"], ["id"],
            ondelete="CASCADE",
        )
        op.create_index(f"ix_{table}_workspace_id", table, ["workspace_id"])

    # ── 4. Rewrite unique constraints to be workspace-scoped ──────────────────
    for old_name, table, new_name, cols in _UNIQUE_REWRITES:
        if table not in existing_tables:
            continue
        uqs = _uq_names(inspector, table)
        if old_name in uqs:
            op.drop_constraint(old_name, table, type_="unique")
        if new_name not in uqs:
            op.create_unique_constraint(new_name, table, cols)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # ── Restore original single-column unique constraints ─────────────────────
    for old_name, table, new_name, cols in reversed(_UNIQUE_REWRITES):
        if table not in existing_tables:
            continue
        uqs = _uq_names(inspector, table)
        if new_name in uqs:
            op.drop_constraint(new_name, table, type_="unique")
        if old_name not in uqs:
            # Restore with just the second column (symbol or key)
            op.create_unique_constraint(old_name, table, [cols[1]])

    # ── Drop workspace_id from each table ────────────────────────────────────
    for table in reversed(_OWNED_TABLES):
        if table not in existing_tables:
            continue
        if "workspace_id" not in _col_names(inspector, table):
            continue
        try:
            op.drop_constraint(f"fk_{table}_workspace_id", table, type_="foreignkey")
        except Exception:
            pass
        try:
            op.drop_index(f"ix_{table}_workspace_id", table_name=table)
        except Exception:
            pass
        op.drop_column(table, "workspace_id")

    # ── Drop workspaces table ─────────────────────────────────────────────────
    if "workspaces" in existing_tables:
        op.drop_table("workspaces")
