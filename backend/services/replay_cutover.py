"""M5 Track B Stage 4 — Controlled Replay Cutover.

docs/implementation/M5_TRACK_B_NATIVE_INTEGRATION_TDD.md §7 Stage 4, §9
Rollout Plan. Flips Portfolio.replay_asset_id_native for exactly one
portfolio at a time, gated on proving native (asset_id-preferring) replay
is bit-identical to that portfolio's Golden Baseline.

No new diff/replay logic (ADR-004): every heavy-lifting piece here already
exists — rebuild_portfolio() (Stage 0/1) and compare_against_baseline()
(Stage 1), both reused exactly as built. This module's only job is
orchestration: run native replay in the same DB session with the flag
provisionally set, compare, and either commit the flag flip (accept) or
roll it back (reject) — never both, never partial, never more than one
portfolio per call ("no flag days", §9 — there is deliberately no
"all portfolios" parameter anywhere in this module).
"""
from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from models.database import Portfolio, Transaction
from services.portfolio_rebuilder import rebuild_portfolio
from services.registry_replay_parity import GoldenBaseline, ParityReport, compare_against_baseline

__all__ = ["CutoverResult", "attempt_cutover", "rollback_cutover", "unresolved_transaction_count"]


@dataclass(frozen=True)
class CutoverResult:
    """Outcome of one per-portfolio cutover attempt.

    accepted=True means native replay proved bit-identical to the supplied
    baseline. It does NOT by itself mean the flag was persisted — that only
    happens when the caller also passed commit=True to attempt_cutover()
    (see that function's own docstring: dry-run-by-default, exactly like
    every other write path in this codebase)."""
    portfolio_id:                       int
    portfolio_name:                     str
    accepted:                           bool
    committed:                          bool
    parity:                             ParityReport | None
    still_unresolved_transaction_count: int
    error:                              str | None = None


def unresolved_transaction_count(db: Session, portfolio_id: int) -> int:
    """Symbol-bearing transactions still missing asset_id for this portfolio.

    Informational only (TDD §7 Stage 4 point 1: "reviewed and accepted", not
    an automated hard gate) — a portfolio with a residual count > 0 is still
    eligible for cutover; those specific transactions simply keep replaying
    at the canonical_symbol tier (§2.1), exactly as designed. Surfaced on
    every CutoverResult so the count is named, never hidden (§11 Risk 1).
    """
    return (
        db.query(Transaction)
        .filter(
            Transaction.portfolio_id == portfolio_id,
            Transaction.symbol.isnot(None),
            Transaction.asset_id.is_(None),
        )
        .count()
    )


async def attempt_cutover(
    db: Session,
    portfolio_id: int,
    workspace_id: int,
    baseline: GoldenBaseline,
    *,
    commit: bool = False,
    skip_snapshots: bool = False,
) -> CutoverResult:
    """Attempt to cut one portfolio over to native (asset_id-preferring) replay.

    Always runs a dry-run native replay (portfolio_rebuilder.py's own
    dry_run=True never writes ledger/holdings/snapshot data regardless of
    this function's own commit flag) and compares it against `baseline` via
    compare_against_baseline(). `skip_snapshots` must match whatever value
    `baseline` was captured with (capture_golden_baseline's own parameter)
    — comparing a skip_snapshots=True baseline against a skip_snapshots=False
    native run would compare unlike things. The provisional flip this
    function makes to the in-session Portfolio row is:
      - rolled back immediately if the comparison finds any diff (rejected
        — the portfolio stays in legacy mode, per Stage 4's own "Abort
        cutover. Leave the portfolio in legacy mode." requirement),
      - rolled back if accepted but commit=False (the default — proves the
        cutover would succeed without persisting it, mirroring every other
        dry_run-by-default operation already established in this codebase,
        e.g. ledger_asset_backfill.backfill_ledger_asset_ids()),
      - committed only when accepted AND commit=True.

    Never flips more than one portfolio_id per call — there is no "all
    portfolios" mode by design (TDD §9: "not a global flag day").
    """
    portfolio = db.query(Portfolio).filter_by(id=portfolio_id, workspace_id=workspace_id).first()
    if portfolio is None:
        return CutoverResult(
            portfolio_id=portfolio_id, portfolio_name="?", accepted=False, committed=False,
            parity=None, still_unresolved_transaction_count=0,
            error=f"Portfolio {portfolio_id} not found in workspace {workspace_id}",
        )
    if baseline.portfolio_id != portfolio_id:
        return CutoverResult(
            portfolio_id=portfolio_id, portfolio_name=portfolio.name, accepted=False, committed=False,
            parity=None, still_unresolved_transaction_count=0,
            error=f"Baseline is for portfolio {baseline.portfolio_id}, not {portfolio_id}",
        )

    unresolved = unresolved_transaction_count(db, portfolio_id)
    portfolio.replay_asset_id_native = True   # provisional — in-session only until commit/rollback below

    try:
        native_run = await rebuild_portfolio(
            db=db, portfolio_id=portfolio_id, workspace_id=workspace_id,
            dry_run=True, backup=False, skip_snapshots=skip_snapshots,
        )
    except Exception as exc:
        db.rollback()
        return CutoverResult(
            portfolio_id=portfolio_id, portfolio_name=portfolio.name, accepted=False, committed=False,
            parity=None, still_unresolved_transaction_count=unresolved, error=str(exc),
        )

    if not native_run.success:
        db.rollback()
        return CutoverResult(
            portfolio_id=portfolio_id, portfolio_name=portfolio.name, accepted=False, committed=False,
            parity=None, still_unresolved_transaction_count=unresolved,
            error=native_run.error or "native replay did not succeed",
        )

    parity = compare_against_baseline(baseline, native_run)

    if not parity.is_bit_identical:
        db.rollback()   # discard the provisional flip — portfolio stays in legacy mode
        return CutoverResult(
            portfolio_id=portfolio_id, portfolio_name=portfolio.name, accepted=False, committed=False,
            parity=parity, still_unresolved_transaction_count=unresolved,
        )

    if commit:
        db.commit()
        return CutoverResult(
            portfolio_id=portfolio_id, portfolio_name=portfolio.name, accepted=True, committed=True,
            parity=parity, still_unresolved_transaction_count=unresolved,
        )

    db.rollback()   # accepted, but caller only asked to prove it — not persist it
    return CutoverResult(
        portfolio_id=portfolio_id, portfolio_name=portfolio.name, accepted=True, committed=False,
        parity=parity, still_unresolved_transaction_count=unresolved,
    )


def rollback_cutover(db: Session, portfolio_id: int, workspace_id: int) -> bool:
    """Flip a portfolio's replay_asset_id_native back to False.

    Per TDD §9: reversible in either direction, and never requires a data
    rollback of the ledger itself — only the flag, since ReplayKey's
    fallback tiers are themselves stable and deterministic. Returns False
    if the portfolio doesn't exist; True otherwise (idempotent — flipping
    an already-legacy portfolio back to legacy is a harmless no-op write).
    """
    portfolio = db.query(Portfolio).filter_by(id=portfolio_id, workspace_id=workspace_id).first()
    if portfolio is None:
        return False
    portfolio.replay_asset_id_native = False
    db.commit()
    return True
