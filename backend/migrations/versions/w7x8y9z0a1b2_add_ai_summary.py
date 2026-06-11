"""add ai_summary column to analysis_cache and analysis_history

Revision ID: w7x8y9z0a1b2
Revises: v6w7x8y9z0a1
Create Date: 2026-06-11

AI Summary Investment Interpreter Layer: a plain-Thai narrative (80-120
words, 2-4 short paragraphs) translating the quantitative signals into
human-readable investment context.  Displayed in the AI Summary box on the
stock detail page; executive_summary is now scoped to "what the company is"
while ai_summary covers "what the AI thinks right now".  NULL for analyses
run before this feature existed.
"""
from alembic import op
import sqlalchemy as sa

revision = "w7x8y9z0a1b2"
down_revision = "v6w7x8y9z0a1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("analysis_cache") as batch_op:
        batch_op.add_column(sa.Column("ai_summary", sa.Text(), nullable=True))
    with op.batch_alter_table("analysis_history") as batch_op:
        batch_op.add_column(sa.Column("ai_summary", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("analysis_history") as batch_op:
        batch_op.drop_column("ai_summary")
    with op.batch_alter_table("analysis_cache") as batch_op:
        batch_op.drop_column("ai_summary")
