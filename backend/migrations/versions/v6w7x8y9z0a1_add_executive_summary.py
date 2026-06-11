"""add executive_summary column to analysis_cache and analysis_history

Revision ID: v6w7x8y9z0a1
Revises: u5v6w7x8y9z0
Create Date: 2026-06-11

Executive Summary Layer: a plain-Thai qualitative interpretation (80-120
words, 2-4 short paragraphs) produced by the summary agent alongside the
6-level signal.  Displayed at the top of the stock detail page above the
quantitative data.  NULL for analyses run before this feature existed.
"""
from alembic import op
import sqlalchemy as sa

revision = "v6w7x8y9z0a1"
down_revision = "u5v6w7x8y9z0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("analysis_cache") as batch_op:
        batch_op.add_column(sa.Column("executive_summary", sa.Text(), nullable=True))
    with op.batch_alter_table("analysis_history") as batch_op:
        batch_op.add_column(sa.Column("executive_summary", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("analysis_history") as batch_op:
        batch_op.drop_column("executive_summary")
    with op.batch_alter_table("analysis_cache") as batch_op:
        batch_op.drop_column("executive_summary")
