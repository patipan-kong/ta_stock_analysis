"""add_signal_history_action_fields

Revision ID: j4k5l6m7n8o9
Revises: i3j4k5l6m7n8
Create Date: 2026-05-22

Adds session_id, action, score_at_signal, signal_type, and reasoning_snippet
to signal_history to support the optimizer-driven Signal History pipeline.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'j4k5l6m7n8o9'
down_revision: Union[str, Sequence[str], None] = 'i3j4k5l6m7n8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    existing_cols = {c["name"] for c in inspector.get_columns("signal_history")}

    with op.batch_alter_table("signal_history") as batch_op:
        if "session_id" not in existing_cols:
            batch_op.add_column(sa.Column("session_id", sa.String(), nullable=True))
        if "action" not in existing_cols:
            batch_op.add_column(sa.Column("action", sa.String(), nullable=True))
        if "score_at_signal" not in existing_cols:
            batch_op.add_column(sa.Column("score_at_signal", sa.Float(), nullable=True))
        if "signal_type" not in existing_cols:
            batch_op.add_column(sa.Column("signal_type", sa.String(), nullable=True))
        if "reasoning_snippet" not in existing_cols:
            batch_op.add_column(sa.Column("reasoning_snippet", sa.Text(), nullable=True))

    # Index session_id for efficient job-scoped queries
    existing_indexes = {i["name"] for i in inspector.get_indexes("signal_history")}
    if "ix_signal_history_session_id" not in existing_indexes:
        op.create_index("ix_signal_history_session_id", "signal_history", ["session_id"])


def downgrade() -> None:
    with op.batch_alter_table("signal_history") as batch_op:
        for col in ("reasoning_snippet", "signal_type", "score_at_signal", "action", "session_id"):
            batch_op.drop_column(col)
