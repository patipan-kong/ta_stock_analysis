"""add structured override fields to user_execution_decisions

Revision ID: a1b3c5d7e9f0
Revises: z0a1b2c3d4e5
Create Date: 2026-06-23

UX.2D: Adds override_type, original_symbol, replacement_symbol, reason_category
to user_execution_decisions.  All nullable — backward compatible with existing rows.
"""
from alembic import op
import sqlalchemy as sa

revision = "a1b3c5d7e9f0"
down_revision = "z0a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("user_execution_decisions") as batch_op:
        batch_op.add_column(sa.Column("override_type", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("original_symbol", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("replacement_symbol", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("reason_category", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("user_execution_decisions") as batch_op:
        batch_op.drop_column("reason_category")
        batch_op.drop_column("replacement_symbol")
        batch_op.drop_column("original_symbol")
        batch_op.drop_column("override_type")
