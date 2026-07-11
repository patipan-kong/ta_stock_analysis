"""add_replay_asset_id_native_to_portfolios

Revision ID: f8a0c2e4b6d8
Revises: e6f8b0d2a4c6
Create Date: 2026-07-11

M5 Track B — Stage 4 (docs/implementation/M5_TRACK_B_NATIVE_INTEGRATION_TDD.md
§9 Rollout Plan, §7 Stage 4).

Adds one nullable boolean column, `portfolios.replay_asset_id_native`, default
False. This is the per-portfolio replay cutover gate: OFF (NULL or False) keys
replay by canonical_symbol/raw_symbol exactly as every portfolio already does
today; ON prefers that portfolio's own asset_id via ReplayKey. Never a global
switch (Migration Principle 3, "no flag days") — flipped one portfolio at a
time by services/replay_cutover.py, only after that portfolio's native replay
is proven bit-identical to its own Golden Baseline.

Purely additive and inert on its own: every existing portfolio row defaults
to OFF, and nothing about replay behavior changes until this column is
explicitly flipped for a specific portfolio.
"""
from alembic import op
import sqlalchemy as sa

revision = "f8a0c2e4b6d8"
down_revision = "e6f8b0d2a4c6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("portfolios") as batch_op:
        batch_op.add_column(
            sa.Column("replay_asset_id_native", sa.Boolean(), nullable=True, server_default=sa.false()),
        )


def downgrade() -> None:
    with op.batch_alter_table("portfolios") as batch_op:
        batch_op.drop_column("replay_asset_id_native")
