"""ReplayKey — deterministic replay-state key derivation.

Stage 0 of the M5 Track B / M6 Native Integration technical design
(docs/implementation/M5_TRACK_B_NATIVE_INTEGRATION_TDD.md §2.1, §7 Stage 0).
Satisfies ADR-005 (docs/decisions/ADR-005_REPLAY_CORRECTNESS_BASELINE.md): replay
must key holdings state by resolved identity, not the raw symbol string, before
any golden baseline is captured.

Three-tier fallback, always deterministic:
    asset_id            if the transaction carries a Registry-resolved identity
    else canonical_symbol  if present  (ADR-005's own literal fix — the
                                         yfinance-routing alias that collapses
                                         KBANK / KBANK.BK into one form)
    else raw_symbol

At Stage 0, no transaction carries an ``asset_id`` yet — that field is added to
CanonicalTransaction only in M5 Track B (TDD §2.2, §4.3), once
``Transaction.asset_id`` exists as a materialized column.  ``replay_key()``
reads it via ``getattr`` with a ``None`` default specifically so this function
does not need to change again when that field is introduced — an unresolved
transaction today and an unresolved transaction after Track A's backlog
clears both simply fall through to the canonical_symbol tier, unchanged.

Pure function. No database access, no I/O, no Registry calls — same purity
class as transaction_canonicalizer.py itself (by design: this module must be
safely importable from ledger_validator.py, portfolio_rebuilder.py, and any
future replay-adjacent module without pulling in a DB session).
"""
from __future__ import annotations

from typing import Union

from services.transaction_canonicalizer import CanonicalTransaction

# int today would be an asset_id (not introduced until M5 Track B); str is the
# canonical_symbol / raw_symbol fallback tiers used at Stage 0.
ReplayKeyT = Union[int, str]


def replay_key(ctx: CanonicalTransaction) -> ReplayKeyT | None:
    """Return the deterministic replay-state key for one canonical transaction.

    Returns None only for cash-only transactions (ctx.raw_symbol is None) —
    DEPOSIT, WITHDRAW, INITIAL_CASH, and symbol-less DIVIDEND rows never
    touch the holdings keyspace.
    """
    asset_id = getattr(ctx, "asset_id", None)
    if asset_id is not None:
        return asset_id
    if ctx.canonical_symbol is not None:
        return ctx.canonical_symbol
    return ctx.raw_symbol
