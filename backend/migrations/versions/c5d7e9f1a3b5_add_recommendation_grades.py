"""add recommendation_grades table, is_system_generated, execution_decision_id

Revision ID: c5d7e9f1a3b5
Revises: b4c6d8e0f2a4
Create Date: 2026-07-06

AI Evaluation & Execution Intelligence — Milestone M0 (Groundwork).
See docs/AI_EVALUATION_IMPLEMENTATION_PLAN.md §3 (Planning Decisions P3-P5) and
docs/EXECUTION_INTELLIGENCE_UX.md for the design baseline this schema serves.

Three additive, backward-compatible changes:

1. `recommendation_grades` — new append-only table (P3). One row per
   (recommendation_snapshot_id, grade_kind); grade_kind in
   PLAN | H7 | H30 | H90 | H180. Rows are written once by the grading
   services (M1/M2) and never UPDATEd — corrections are future migrations,
   not writes, per OPTIMIZER_PHILOSOPHY.md Invariant 1.
2. `user_execution_decisions.is_system_generated` — bool, default false (P4).
   Distinguishes scheduler-authored EXPIRED rows from genuine human decisions.
3. `transactions.execution_decision_id` — nullable FK, metadata-only (P5).
   Populated only when a trade is entered via the app after an
   APPROVED/PARTIAL_EXECUTION decision. The canonicalizer, portfolio_rebuilder,
   ledger_validator, and repair executor must never read this column — it is
   evaluation-layer metadata riding on the ledger, not ledger data itself.

No AI calls, no optimizer changes. This DB is PostgreSQL 9.2 — no
`IF NOT EXISTS` on CREATE INDEX/ADD COLUMN (added in 9.5); every operation
below uses the plain, version-portable form the rest of this history already
relies on.
"""
from alembic import op
import sqlalchemy as sa

revision = "c5d7e9f1a3b5"
down_revision = "b4c6d8e0f2a4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recommendation_grades",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("workspace_id", sa.Integer(), nullable=False),
        sa.Column("recommendation_snapshot_id", sa.Integer(), nullable=False),
        sa.Column("portfolio_id", sa.Integer(), nullable=False),
        sa.Column("grade_kind", sa.String(), nullable=False),
        sa.Column("graded_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("window_start", sa.String(), nullable=True),
        sa.Column("window_end", sa.String(), nullable=True),
        sa.Column("return_pct", sa.Float(), nullable=True),
        sa.Column("benchmark_return_pct", sa.Float(), nullable=True),
        sa.Column("alpha", sa.Float(), nullable=True),
        sa.Column("max_drawdown_pct", sa.Float(), nullable=True),
        sa.Column("directional_correct", sa.Boolean(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("detail_json", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recommendation_snapshot_id"], ["recommendation_snapshots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["portfolio_id"], ["portfolios.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("recommendation_snapshot_id", "grade_kind", name="uq_recommendation_grade_kind"),
    )
    op.create_index("ix_recommendation_grades_workspace_id", "recommendation_grades", ["workspace_id"])
    op.create_index("ix_recommendation_grades_recommendation_snapshot_id", "recommendation_grades", ["recommendation_snapshot_id"])
    op.create_index("ix_recommendation_grades_portfolio_id", "recommendation_grades", ["portfolio_id"])
    op.create_index("ix_recommendation_grades_grade_kind", "recommendation_grades", ["grade_kind"])

    op.add_column(
        "user_execution_decisions",
        sa.Column("is_system_generated", sa.Boolean(), nullable=False, server_default=sa.false()),
    )

    op.add_column(
        "transactions",
        sa.Column("execution_decision_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_transactions_execution_decision",
        "transactions",
        "user_execution_decisions",
        ["execution_decision_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_transactions_execution_decision_id", "transactions", ["execution_decision_id"])


def downgrade() -> None:
    op.drop_index("ix_transactions_execution_decision_id", table_name="transactions")
    op.drop_constraint("fk_transactions_execution_decision", "transactions", type_="foreignkey")
    op.drop_column("transactions", "execution_decision_id")

    op.drop_column("user_execution_decisions", "is_system_generated")

    op.drop_index("ix_recommendation_grades_grade_kind", table_name="recommendation_grades")
    op.drop_index("ix_recommendation_grades_portfolio_id", table_name="recommendation_grades")
    op.drop_index("ix_recommendation_grades_recommendation_snapshot_id", table_name="recommendation_grades")
    op.drop_index("ix_recommendation_grades_workspace_id", table_name="recommendation_grades")
    op.drop_table("recommendation_grades")
