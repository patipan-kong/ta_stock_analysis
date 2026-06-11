"""add goal profile columns to portfolios

Revision ID: x8y9z0a1b2c3
Revises: w7x8y9z0a1b2
Create Date: 2026-06-11

Phase 4C.3 (Goal Discovery Wizard): adds 4 nullable String columns capturing
what the user is investing for.  Pure discovery/personalization data — no
projections, no optimizer behavior changes.

    goal_type         WEDDING | HOUSE | EDUCATION | RETIREMENT |
                      FINANCIAL_FREEDOM | WEALTH_GROWTH | OTHER
    goal_priority     ESSENTIAL | IMPORTANT | ASPIRATIONAL
    goal_target_date  YYYY-MM-DD
    risk_personality  AGGRESSIVE | MODERATE | CONSERVATIVE

NULL on all fields means the wizard has not been completed — existing
portfolios keep working unchanged.  goal_target_value (amount) already exists
from Phase 4C.1 (u5v6w7x8y9z0).
"""
from alembic import op
import sqlalchemy as sa

revision = "x8y9z0a1b2c3"
down_revision = "w7x8y9z0a1b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("portfolios") as batch_op:
        batch_op.add_column(sa.Column("goal_type", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("goal_priority", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("goal_target_date", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("risk_personality", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("portfolios") as batch_op:
        batch_op.drop_column("risk_personality")
        batch_op.drop_column("goal_target_date")
        batch_op.drop_column("goal_priority")
        batch_op.drop_column("goal_type")
