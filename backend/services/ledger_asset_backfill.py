"""Asset Registry — Ledger Asset ID Backfill (M5 Track B, Stage 2).

docs/implementation/M5_TRACK_B_NATIVE_INTEGRATION_TDD.md §5.1, §7 Stage 2.

Consumes an already-computed MigrationPlan (M5.1, unmodified) and writes
its already-decided RESOLVED verdicts onto the ledger's own `asset_id`
columns (Transaction, PortfolioItem, Watchlist) — the schema Stage 2's
migration (b4d6f8a0c2e4, e6f8b0d2a4c6) adds. Mirrors
services/migration_executor.py's discipline exactly (same checkpoint-
append-only pattern, same dry-run-rolls-back-every-stage default, same
`requested_by` provenance field) because it performs the same *kind* of
operation — committing an already-decided verdict — just against a
different set of tables.

Never resolves anything itself (ADR-004: zero new identity logic in this
module). It never imports identity_resolver, never calls resolve() or
mint_asset() or attach_identifier(); its only branch on ResolutionVerdict
is the same mechanical one migration_executor.py already uses (RESOLVED or
not). It also never re-derives symbol matching: which rows belong to a
ClaimShape is read directly off the plan's own
`ClaimShapeResolution.transaction_ids`/`.portfolio_ids` (M5.1, unmodified)
rather than re-querying by symbol string — reusing the planner's exact
canonicalization instead of risking drift from a second implementation.

Watchlist is the one exception: it is never a party to any Transaction, so
it carries no transaction_ids/portfolio_ids linkage in the plan at all. Per
§5.1's literal wording ("every ... Watchlist row whose symbol matches that
shape's raw_symbol"), Watchlist rows are matched by symbol string alone,
workspace-wide, with no portfolio scoping (Watchlist has no portfolio_id
column to scope by).

Read-only guarantee for dry_run=True: identical to migration_executor.py —
every stage is executed against the session and then explicitly rolled
back, never committed (ADR-004 — reuse the one proven pattern).

Rollback
--------
Because every value this module writes is inert until Stage 5 (nothing
reads `asset_id` yet), rolling back a live run is low-risk by construction.
`rollback_backfill()` reverses one run_id precisely: for each COMPLETED
checkpoint in that run, it resets exactly the row ids recorded on that
checkpoint (not a symbol re-match, which could now catch rows a *later*
run legitimately touched) back to NULL — and only if the row's current
`asset_id` still equals what this run set it to, so a rollback can never
clobber a value some other run wrote afterward.
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from models.database import PortfolioItem, Transaction, Watchlist
from models.ledger_asset_backfill import LedgerAssetBackfillCheckpoint
from services.migration_planner import ClaimShape, ClaimShapeResolution, MigrationPlan
from services.resolver_domain import ResolutionVerdict

__all__ = [
    "BackfillOutcome",
    "BackfillStepResult",
    "BackfillReport",
    "RollbackReport",
    "backfill_ledger_asset_ids",
    "rollback_backfill",
    "unresolved_steps",
]

_log = logging.getLogger(__name__)


class BackfillOutcome(str, Enum):
    """Per-shape outcome of one backfill_ledger_asset_ids() invocation."""

    COMPLETED = "COMPLETED"
    SKIPPED_NOT_RESOLVED = "SKIPPED_NOT_RESOLVED"
    SKIPPED_NO_PORTFOLIOS_IN_SCOPE = "SKIPPED_NO_PORTFOLIOS_IN_SCOPE"
    SKIPPED_ALREADY_DONE = "SKIPPED_ALREADY_DONE"


@dataclass(frozen=True)
class BackfillStepResult:
    """One claim shape's outcome for this invocation. Not itself persisted
    — the persisted record is LedgerAssetBackfillCheckpoint; this is the
    in-memory read model BackfillReport hands back to the caller."""

    shape: ClaimShape
    outcome: BackfillOutcome
    resolved_asset_id: Optional[int]
    transaction_count: int             # size of this shape, regardless of outcome — what "unresolved" reporting needs
    transactions_updated: int
    portfolio_items_updated: int
    watchlist_rows_updated: int
    detail: str


@dataclass(frozen=True)
class BackfillReport:
    """TDD §5.1's literal 7-field shape, plus two additive fields.

    `steps` and `generated_at` are not in the TDD's literal dataclass —
    disclosed deviation, same posture as registry_replay_parity.ParityReport's
    additive `validator_diffs` field (Stage 1 precedent): the task's own
    "detailed progress reporting" and "every unresolved record must be
    reported" requirements have nowhere else to live without them, and both
    are purely additive (any caller reading only the original 7 fields is
    unaffected).
    """

    run_id: str
    portfolios_scanned: Tuple[int, ...]
    transactions_updated: int
    portfolio_items_updated: int
    watchlist_rows_updated: int
    still_unresolved_transaction_count: int
    dry_run: bool
    steps: Tuple[BackfillStepResult, ...] = ()
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class RollbackReport:
    run_id: str
    dry_run: bool
    shapes_rolled_back: int
    transactions_reset: int
    portfolio_items_reset: int
    watchlist_rows_reset: int
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def _shape_sort_key(shape: ClaimShape) -> Tuple[str, str, str]:
    return (shape.raw_symbol, shape.canonical_symbol or "", shape.currency or "")


def _already_completed(db: Session, run_id: str, shape: ClaimShape) -> bool:
    return (
        db.query(LedgerAssetBackfillCheckpoint.id)
        .filter_by(
            run_id=run_id,
            raw_symbol=shape.raw_symbol,
            canonical_symbol=shape.canonical_symbol,
            currency=shape.currency,
            status=BackfillOutcome.COMPLETED.value,
        )
        .first()
        is not None
    )


def _scoped_portfolio_ids(
    resolution: ClaimShapeResolution, portfolio_ids: Optional[Sequence[int]],
) -> Tuple[int, ...]:
    if portfolio_ids is None:
        return resolution.portfolio_ids
    requested = set(portfolio_ids)
    return tuple(pid for pid in resolution.portfolio_ids if pid in requested)


def _backfill_one_shape(
    db: Session, resolution: ClaimShapeResolution, portfolio_ids: Optional[Sequence[int]],
) -> Tuple[BackfillOutcome, int, int, int, List[int], List[int], List[int], str]:
    """Returns (outcome, tx_updated, item_updated, wl_updated, tx_ids, item_ids, wl_ids, detail)."""
    shape = resolution.shape
    resolved_asset_id = resolution.result.resolved_asset_id
    scope = _scoped_portfolio_ids(resolution, portfolio_ids)

    if portfolio_ids is not None and not scope:
        return (
            BackfillOutcome.SKIPPED_NO_PORTFOLIOS_IN_SCOPE, 0, 0, 0, [], [], [],
            "none of this shape's portfolios are in the requested scope",
        )

    tx_query = db.query(Transaction).filter(Transaction.id.in_(resolution.transaction_ids))
    if portfolio_ids is not None:
        tx_query = tx_query.filter(Transaction.portfolio_id.in_(scope))
    tx_ids_touched: List[int] = []
    for tx in tx_query.all():
        if tx.asset_id != resolved_asset_id:
            tx.asset_id = resolved_asset_id
            tx_ids_touched.append(tx.id)

    item_query = (
        db.query(PortfolioItem)
        .filter(PortfolioItem.symbol == shape.raw_symbol)
        .filter(PortfolioItem.portfolio_id.in_(scope))
    ) if scope else None
    item_ids_touched: List[int] = []
    if item_query is not None:
        for item in item_query.all():
            if item.asset_id != resolved_asset_id:
                item.asset_id = resolved_asset_id
                item_ids_touched.append(item.id)

    # Watchlist has no portfolio_id column — matched by symbol alone,
    # workspace-wide, per §5.1's literal wording (see module docstring).
    wl_ids_touched: List[int] = []
    for wl in db.query(Watchlist).filter(Watchlist.symbol == shape.raw_symbol).all():
        if wl.asset_id != resolved_asset_id:
            wl.asset_id = resolved_asset_id
            wl_ids_touched.append(wl.id)

    detail = (
        f"asset_id={resolved_asset_id}: "
        f"{len(tx_ids_touched)} transaction(s), {len(item_ids_touched)} portfolio_item(s), "
        f"{len(wl_ids_touched)} watchlist row(s) updated"
    )
    return (
        BackfillOutcome.COMPLETED,
        len(tx_ids_touched), len(item_ids_touched), len(wl_ids_touched),
        tx_ids_touched, item_ids_touched, wl_ids_touched, detail,
    )


def backfill_ledger_asset_ids(
    db: Session,
    plan: MigrationPlan,
    *,
    portfolio_ids: Optional[Sequence[int]] = None,
    run_id: Optional[str] = None,
    dry_run: bool = True,
    requested_by: str = "ledger_asset_backfill",
) -> BackfillReport:
    """Writes every RESOLVED claim shape's `resolved_asset_id` in `plan`
    onto matching Transaction/PortfolioItem/Watchlist rows.

    `run_id` identifies one backfill attempt across possibly-many
    invocations, exactly as migration_executor.execute_migration()'s
    `run_id` does — omit it to start a new run; pass a prior run's id to
    resume it (the checkpoint lookup skips already-COMPLETED shapes).
    Callers resuming a run should recompute `plan` fresh
    (services.migration_planner.plan_migration()) rather than reuse a
    stale plan object, for the same reason execute_migration()'s docstring
    gives.

    Idempotent independent of run_id: each row write is itself a no-op
    once `asset_id` already equals the shape's `resolved_asset_id` — a
    second invocation (even under a fresh run_id) always reports zero
    additional writes, because there is nothing left to change.

    dry_run=True (the default) rolls back every stage — no ledger write
    and no checkpoint row survives the call. Every unresolved shape
    (CANDIDATE/AMBIGUOUS/CONFLICT/UNKNOWN verdict) is always reported as a
    step with outcome SKIPPED_NOT_RESOLVED — never silently dropped.
    """
    resolved_run_id = run_id or str(uuid.uuid4())
    steps: List[BackfillStepResult] = []

    for resolution in sorted(plan.resolutions, key=lambda r: _shape_sort_key(r.shape)):
        shape = resolution.shape
        result = resolution.result

        if result.verdict != ResolutionVerdict.RESOLVED or result.resolved_asset_id is None:
            steps.append(
                BackfillStepResult(
                    shape=shape,
                    outcome=BackfillOutcome.SKIPPED_NOT_RESOLVED,
                    resolved_asset_id=None,
                    transaction_count=len(resolution.transaction_ids),
                    transactions_updated=0,
                    portfolio_items_updated=0,
                    watchlist_rows_updated=0,
                    detail=f"verdict={result.verdict.value}; not executable without adjudication",
                )
            )
            continue

        if _already_completed(db, resolved_run_id, shape):
            steps.append(
                BackfillStepResult(
                    shape=shape,
                    outcome=BackfillOutcome.SKIPPED_ALREADY_DONE,
                    resolved_asset_id=result.resolved_asset_id,
                    transaction_count=len(resolution.transaction_ids),
                    transactions_updated=0,
                    portfolio_items_updated=0,
                    watchlist_rows_updated=0,
                    detail=f"already completed in run_id={resolved_run_id}",
                )
            )
            continue

        try:
            (outcome, tx_n, item_n, wl_n, tx_ids, item_ids, wl_ids, detail) = _backfill_one_shape(
                db, resolution, portfolio_ids,
            )
        except Exception as exc:  # noqa: BLE001 — unexpected infra failure, mirrors migration_executor.py
            _log.exception(
                "Unexpected failure backfilling claim shape %s/%s in run_id=%s",
                shape.raw_symbol, shape.canonical_symbol, resolved_run_id,
            )
            db.rollback()
            steps.append(
                BackfillStepResult(
                    shape=shape,
                    outcome=BackfillOutcome.SKIPPED_NOT_RESOLVED,
                    resolved_asset_id=result.resolved_asset_id,
                    transaction_count=len(resolution.transaction_ids),
                    transactions_updated=0,
                    portfolio_items_updated=0,
                    watchlist_rows_updated=0,
                    detail=f"unexpected failure: {exc}",
                )
            )
            continue

        if outcome == BackfillOutcome.COMPLETED:
            checkpoint = LedgerAssetBackfillCheckpoint(
                run_id=resolved_run_id,
                raw_symbol=shape.raw_symbol,
                canonical_symbol=shape.canonical_symbol,
                currency=shape.currency,
                status=BackfillOutcome.COMPLETED.value,
                resolved_asset_id=result.resolved_asset_id,
                transactions_updated=tx_n,
                portfolio_items_updated=item_n,
                watchlist_rows_updated=wl_n,
                transaction_ids_json=json.dumps(tx_ids),
                portfolio_item_ids_json=json.dumps(item_ids),
                watchlist_ids_json=json.dumps(wl_ids),
                detail=f"[{requested_by}] {detail}",
            )
            db.add(checkpoint)

        if dry_run:
            db.rollback()
        else:
            db.commit()

        steps.append(
            BackfillStepResult(
                shape=shape,
                outcome=outcome,
                resolved_asset_id=result.resolved_asset_id,
                transaction_count=len(resolution.transaction_ids),
                transactions_updated=tx_n,
                portfolio_items_updated=item_n,
                watchlist_rows_updated=wl_n,
                detail=detail,
            )
        )

    still_unresolved = sum(
        s.transaction_count for s in steps if s.outcome == BackfillOutcome.SKIPPED_NOT_RESOLVED
    )

    return BackfillReport(
        run_id=resolved_run_id,
        portfolios_scanned=plan.portfolios_scanned,
        transactions_updated=sum(s.transactions_updated for s in steps),
        portfolio_items_updated=sum(s.portfolio_items_updated for s in steps),
        watchlist_rows_updated=sum(s.watchlist_rows_updated for s in steps),
        still_unresolved_transaction_count=still_unresolved,
        dry_run=dry_run,
        steps=tuple(steps),
    )


def unresolved_steps(report: BackfillReport) -> Tuple[BackfillStepResult, ...]:
    """The unresolved-assets report: every shape this run could not act on,
    with its full transaction/portfolio scope — never silently dropped."""
    return tuple(s for s in report.steps if s.outcome == BackfillOutcome.SKIPPED_NOT_RESOLVED)


def rollback_backfill(db: Session, run_id: str, *, dry_run: bool = True) -> RollbackReport:
    """Reverses one backfill run precisely: for every COMPLETED checkpoint
    in `run_id`, resets exactly the row ids that checkpoint recorded back
    to NULL — and only where the row's current `asset_id` still equals
    what this run set it to, so a later run's legitimate write is never
    clobbered.

    dry_run=True (the default) rolls back every stage, identical in
    discipline to backfill_ledger_asset_ids() itself.
    """
    checkpoints = (
        db.query(LedgerAssetBackfillCheckpoint)
        .filter_by(run_id=run_id, status=BackfillOutcome.COMPLETED.value)
        .all()
    )

    tx_reset = item_reset = wl_reset = 0
    for cp in checkpoints:
        tx_ids = json.loads(cp.transaction_ids_json)
        item_ids = json.loads(cp.portfolio_item_ids_json)
        wl_ids = json.loads(cp.watchlist_ids_json)

        if tx_ids:
            rows = db.query(Transaction).filter(
                Transaction.id.in_(tx_ids), Transaction.asset_id == cp.resolved_asset_id,
            ).all()
            for row in rows:
                row.asset_id = None
                tx_reset += 1
        if item_ids:
            rows = db.query(PortfolioItem).filter(
                PortfolioItem.id.in_(item_ids), PortfolioItem.asset_id == cp.resolved_asset_id,
            ).all()
            for row in rows:
                row.asset_id = None
                item_reset += 1
        if wl_ids:
            rows = db.query(Watchlist).filter(
                Watchlist.id.in_(wl_ids), Watchlist.asset_id == cp.resolved_asset_id,
            ).all()
            for row in rows:
                row.asset_id = None
                wl_reset += 1

    if dry_run:
        db.rollback()
    else:
        db.commit()

    return RollbackReport(
        run_id=run_id,
        dry_run=dry_run,
        shapes_rolled_back=len(checkpoints),
        transactions_reset=tx_reset,
        portfolio_items_reset=item_reset,
        watchlist_rows_reset=wl_reset,
    )
