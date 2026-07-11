"""Asset Registry — Ledger Asset Backfill Checkpoints (M5 Track B, Stage 2).

LedgerAssetBackfillCheckpoint mirrors models/migration_execution.py's
"history over state" doctrine exactly, applied to a different set of
tables: an append-only log of backfill *attempts*, one row per (run_id,
ClaimShape) processed, never updated or deleted by
services/ledger_asset_backfill.py. Resumability ("has this shape completed
in this run?") is answered by querying for an existing COMPLETED row for
that (run_id, raw_symbol, canonical_symbol, currency) key — computed on
read, every time — never by a cached status column. See
models/migration_execution.py's own module docstring for the full
rationale; it applies here unchanged (ADR-004 — one implementation per
rule, reused rather than restated as a second doctrine).

Why this table also records exact row ids (unlike MigrationExecutionCheckpoint,
which only counts identifiers attached)
------------------------------------------------------------------------------
MigrationExecutionCheckpoint's writes (Registry identifier attachment) are
themselves append-only and self-describing — nothing needs to be "undone,"
only superseded. This module's writes are ordinary column UPDATEs
(`asset_id` on a ledger row), which are not self-describing after the fact:
querying `transactions.asset_id = 41` cannot tell you whether *this run*
set that value or a different run did. Precise rollback (§7 Stage 2's
"Rollback verification" requirement) therefore needs the exact primary
keys this run actually changed, not just a count — so each COMPLETED
checkpoint row carries three JSON arrays of ids. Purely additive: no
existing table is altered, and no existing table gains a foreign key to
this one.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from models.database import Base


class LedgerAssetBackfillCheckpoint(Base):
    """One durable fact: an attempt to backfill one ClaimShape's `asset_id`
    onto Transaction/PortfolioItem/Watchlist rows, within one backfill run,
    produced one outcome.

    raw_symbol/canonical_symbol/currency together are the same claim-shape
    key services.migration_planner.ClaimShape already uses — deliberately
    reused rather than inventing a second key for the same identity
    question (ADR-004), exactly as MigrationExecutionCheckpoint already
    does for the same reason.
    """

    __tablename__ = "ledger_asset_backfill_checkpoints"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String, nullable=False, index=True)

    raw_symbol = Column(String, nullable=False)
    canonical_symbol = Column(String, nullable=True)
    currency = Column(String, nullable=True)

    status = Column(String, nullable=False)
    # "COMPLETED" | "SKIPPED_NOT_RESOLVED" | "SKIPPED_NO_PORTFOLIOS_IN_SCOPE"
    resolved_asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=True, index=True)

    transactions_updated = Column(Integer, nullable=False, default=0)
    portfolio_items_updated = Column(Integer, nullable=False, default=0)
    watchlist_rows_updated = Column(Integer, nullable=False, default=0)

    # JSON arrays of primary keys this run actually changed (old value !=
    # resolved_asset_id before the write) — the precise undo set for
    # rollback_backfill(). Empty-list JSON ("[]") for shapes that changed
    # nothing (already backfilled, or not resolved).
    transaction_ids_json = Column(Text, nullable=False, default="[]")
    portfolio_item_ids_json = Column(Text, nullable=False, default="[]")
    watchlist_ids_json = Column(Text, nullable=False, default="[]")

    detail = Column(Text, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    resolved_asset = relationship("Asset", foreign_keys=[resolved_asset_id])

    __table_args__ = (
        Index(
            "ix_ledger_asset_backfill_checkpoints_resume_lookup",
            "run_id", "raw_symbol", "canonical_symbol", "currency", "status",
        ),
    )
