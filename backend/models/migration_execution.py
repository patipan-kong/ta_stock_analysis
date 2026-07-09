"""Asset Registry — Migration Execution Checkpoints (Milestone M5.2).

MigrationExecutionCheckpoint is a durable log of execution *attempts*, not a
mutable per-shape status table. This is a deliberate choice, not an
oversight — see the "History over state" note below before adding a column
or a second table for "current status."

History over state
-------------------
The executor's resumability requirement ("what remains") looks at first
like a state question, but the milestone also requires the log to explain
"what happened, why, and what remains" — and only a log of attempts can
answer "why did shape X fail on attempt 1 but succeed on attempt 2." A
single mutable status row can only ever answer the latest question, never
the history behind it.

This module resolves that by treating history as the source of truth and
state as a derived projection, never stored separately: "has shape X
completed in run Y?" is answered by querying for an existing COMPLETED row
for that (run_id, raw_symbol, canonical_symbol, currency) key, computed on
read, every time — never by reading or writing a cached status column. This
mirrors the same idiom ADR-001 already established for the Transaction
ledger (append-only source of truth; every "current state" view is a
disposable derivation) and that RegistryFinding (models/registry_finding.py)
already follows for identity findings.

A mutable "current status" row would be a second representation of a fact
this table already records durably — and two representations of one fact
is exactly the drift risk ADR-004 ("one implementation per rule") exists to
prevent, applied to storage rather than business logic. Do not add one.

Rows are never updated or deleted by services/migration_executor.py. A
shape that was BLOCKED and is later retried (same or a later run) gets a
new row on its next attempt, not a rewritten one.

Purely additive: no existing table is altered, and no existing table gains
a foreign key to this one.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from models.database import Base


class MigrationExecutionCheckpoint(Base):
    """One durable fact: an attempt to execute one ClaimShape within one
    execution run produced one outcome (COMPLETED or BLOCKED).

    raw_symbol/canonical_symbol/currency together are the same claim-shape
    key services.migration_planner.ClaimShape already uses — deliberately
    reused rather than inventing a second key (a hash, a synthetic id) for
    the same identity question.
    """

    __tablename__ = "migration_execution_checkpoints"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String, nullable=False, index=True)

    raw_symbol = Column(String, nullable=False)
    canonical_symbol = Column(String, nullable=True)
    currency = Column(String, nullable=True)

    status = Column(String, nullable=False)  # "COMPLETED" | "BLOCKED"
    resolved_asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, index=True)
    identifiers_attached = Column(Integer, nullable=False, default=0)
    detail = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    resolved_asset = relationship("Asset", foreign_keys=[resolved_asset_id])

    __table_args__ = (
        Index(
            "ix_migration_execution_checkpoints_resume_lookup",
            "run_id", "raw_symbol", "canonical_symbol", "currency", "status",
        ),
    )
