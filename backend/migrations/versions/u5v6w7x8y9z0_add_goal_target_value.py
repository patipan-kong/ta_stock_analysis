"""add goal_target_value column to portfolios

Revision ID: u5v6w7x8y9z0
Revises: t4u5v6w7x8y9
Create Date: 2026-06-10

Phase 4C.1 (AI Operations Center UI): adds a nullable Float column holding the
user's portfolio value goal (in portfolio currency).  Used by the
/operations-center/status endpoint to compute goal_progress_pct
(= latest NAV / goal_target_value * 100).  NULL means no goal set — the
MUJI-mode Goal Progress card then shows a "set a goal" input instead.
"""
from alembic import op
import sqlalchemy as sa

revision = "u5v6w7x8y9z0"
down_revision = "t4u5v6w7x8y9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("portfolios") as batch_op:
        batch_op.add_column(sa.Column("goal_target_value", sa.Float(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("portfolios") as batch_op:
        batch_op.drop_column("goal_target_value")
