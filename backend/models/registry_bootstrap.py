"""Asset Registry — Registry Bootstrap Checkpoints (Milestone M5.3).

RegistryBootstrapCheckpoint is a durable log of mint *attempts*, not a
mutable per-shape status table — the same "history over state" discipline
models/migration_execution.py established for M5.2 (see that module for the
full rationale). This is a separate table, not a reuse of
MigrationExecutionCheckpoint, and that split is deliberate rather than a
duplication of the rule ADR-004 protects:

MigrationExecutionCheckpoint.resolved_asset_id is NOT NULL by design,
because every shape M5.2's executor acts on already has a resolved_asset_id
— a BLOCKED attach still knows which asset it was attaching to. Bootstrap's
MINT operation is different in kind: a BLOCKED mint has no asset_id,
because minting is what failed. Weakening M5.2's NOT NULL to accommodate
that would force two structurally different operations through one schema
that fits neither cleanly — the actual violation of "one implementation per
rule" would be that forcing, not this second table. The *pattern* (append-
only attempt log; resumability answered by querying for an existing
successful row, computed on read, never a mutable status column) is reused
identically; only the columns differ, because the fact being recorded
differs.

Rows are never updated or deleted by services/registry_bootstrap.py. A
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


class RegistryBootstrapCheckpoint(Base):
    """One durable fact: an attempt to mint one UNKNOWN ClaimShape within
    one bootstrap run produced one outcome (MINTED or BLOCKED).

    raw_symbol/canonical_symbol/currency together are the same claim-shape
    key services.migration_planner.ClaimShape already uses — deliberately
    reused rather than inventing a second key for the same identity
    question (mirrors MigrationExecutionCheckpoint's own choice).
    """

    __tablename__ = "registry_bootstrap_checkpoints"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String, nullable=False, index=True)

    raw_symbol = Column(String, nullable=False)
    canonical_symbol = Column(String, nullable=True)
    currency = Column(String, nullable=True)

    status = Column(String, nullable=False)  # "MINTED" | "BLOCKED"
    minted_asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=True, index=True)
    identifiers_attached = Column(Integer, nullable=False, default=0)
    detail = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    minted_asset = relationship("Asset", foreign_keys=[minted_asset_id])

    __table_args__ = (
        Index(
            "ix_registry_bootstrap_checkpoints_resume_lookup",
            "run_id", "raw_symbol", "canonical_symbol", "currency", "status",
        ),
    )
