"""Canonical Transaction Layer.

Converts raw SQLAlchemy Transaction ORM rows into immutable CanonicalTransaction
value objects. All downstream engines (Portfolio Rebuilder, Ledger Validator,
Snapshot Return Recovery) consume CanonicalTransaction instead of ORM rows,
eliminating duplicated preprocessing.

Responsibilities
----------------
* Resolve symbol aliases via get_yfinance_symbol() — once, in one place
* Preserve raw_symbol for audit trails and holdings_json lookups
* Convert numeric fields (shares, price, total_amount, fees, taxes) to Decimal
* Parse QUANTITY_CORRECTION notes into a signed qty_correction_delta
* Parse SELL notes into realized_pnl
* Coerce transaction_date to date; preserve created_at as datetime
* Sort by (transaction_date, id) for deterministic replay ordering

Non-responsibilities
--------------------
* No replay, no portfolio state, no cash calculation
* No snapshot generation, no yfinance calls, no network I/O
* No database reads or writes
* No validation, no error reporting
* No caching, no singleton, no mutable state

Consumers
---------
* portfolio_rebuilder  — full consumer; use canonical_symbol for holdings keys
* ledger_validator     — full consumer; use canonical_symbol for alias detection
* snapshot_return_recovery — partial consumer; use raw_symbol for holdings_json
  lookups (those keys were stored using the raw symbol at write time)
* snapshot_repair      — not a consumer; operates on stored holdings_json, not
  on Transaction rows
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from services.symbol_normalization import get_yfinance_symbol

# These patterns are the single authoritative definitions.
# portfolio_rebuilder, ledger_validator, and snapshot_return_recovery each
# previously defined their own identical copies.  Those copies will be removed
# once each module is migrated to consume CanonicalTransaction.
_QCORR_RE    = re.compile(r"Quantity correction:\s*([+-]?\d[\d.]*)\s*shares", re.IGNORECASE)
_REALIZED_RE = re.compile(r"Realized P&L:\s*([-+]?\d+\.?\d*)")


def _to_decimal(v: Any) -> Decimal:
    """Convert any numeric-ish value to Decimal, returning Decimal('0') on failure."""
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")


def _to_date(v: Any) -> date | None:
    """Coerce a DateTime ORM column value to a plain date."""
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return None


def _to_datetime(v: Any) -> datetime | None:
    """Return a datetime as-is; return None for anything else."""
    if isinstance(v, datetime):
        return v
    return None


@dataclass(frozen=True)
class CanonicalTransaction:
    """Immutable, authoritative interpretation of one Transaction row.

    Downstream engines operate on this type instead of SQLAlchemy ORM objects.
    The ORM layer is an infrastructure concern; business engines should not
    depend on it.

    Fields
    ------
    id
        Source Transaction.id — required for audit trail (LedgerFinding.transaction_ids).
        Not a business field; carried for traceability only.

    transaction_type
        Preserved verbatim: BUY, SELL, DEPOSIT, WITHDRAW, INITIAL_POSITION,
        INITIAL_CASH, QUANTITY_CORRECTION, DIVIDEND.

    raw_symbol
        Original tx.symbol stripped and uppercased, or None for cash-only
        transactions (DEPOSIT, WITHDRAW, INITIAL_CASH, DIVIDEND).
        Use this when matching against holdings_json keys, which were stored
        using the raw symbol at write time.

    canonical_symbol
        get_yfinance_symbol(raw_symbol).  Use this for replay engine holdings
        dictionaries and for yfinance price lookups.
        None when raw_symbol is None.

    shares
        Decimal(tx.shares).  Zero if tx.shares is None or absent.

    price_per_share
        Decimal(tx.price_per_share).  Zero if None.

    total_amount
        Decimal(tx.total_amount).

    fees
        Decimal(tx.fees).  Zero if None.

    taxes
        Decimal(tx.taxes).  Zero if None.

    transaction_date
        Calendar date (date, not datetime) used for replay ordering.
        Derived from tx.transaction_date.

    created_at
        Physical insert timestamp (datetime) used by snapshot_return_recovery
        for created_at-windowed DB queries.  Preserved as-is.
        None if tx.created_at is absent.

    sector
        Preserved verbatim.  None if tx.sector is None or empty string.

    notes
        Preserved verbatim.  None if tx.notes is None or empty string.

    qty_correction_delta
        Pre-parsed signed Decimal for QUANTITY_CORRECTION transactions.
        Sign is extracted from the "Quantity correction: +5.0 shares" pattern
        in tx.notes.  Falls back to Decimal(tx.shares) when notes are absent
        or the pattern is not found — the live engine stores abs(delta) in
        tx.shares and the sign only in tx.notes, so the fallback is positive.
        None for all transaction types other than QUANTITY_CORRECTION.

    realized_pnl
        Pre-parsed float for SELL transactions.  Extracted from the
        "Realized P&L: 500.00" pattern in tx.notes.
        None when the pattern is not found in notes, or when the transaction
        type is not SELL.
        Consumers that need a numeric value when notes are absent should use:
            pnl = ctx.realized_pnl if ctx.realized_pnl is not None else 0.0

    asset_id
        M5 Track B Stage 4 (docs/implementation/M5_TRACK_B_NATIVE_INTEGRATION_TDD.md
        §2.2, §4.3). A plain, read-only reflection of tx.asset_id — never
        resolved here, never a Registry call (purity is preserved exactly as
        before; identity resolution happens once, upstream, at write time —
        services/portfolio_transactions.py, Stage 3).

        Populated only when canonicalize_transactions() is called with
        prefer_asset_id=True; None otherwise (the default). This is the one
        mechanical deviation from §2.2's literal "populated by simply reading
        that column" phrasing — necessary because the per-portfolio cutover
        gate (Portfolio.replay_asset_id_native, §9) has to live somewhere,
        and it cannot live in replay_key.py (test_replay_key.py asserts that
        function's signature stays exactly `(ctx)` — no flag parameter — so
        replay_key() keeps preferring asset_id *whenever present*,
        unconditionally, exactly as §2.1 specifies). Gating whether it is
        ever present is therefore this function's job: a portfolio still on
        legacy keying gets asset_id=None on every CanonicalTransaction it
        produces, so replay_key() naturally, correctly falls through to the
        canonical_symbol tier — with zero changes to replay_key.py itself.
    """

    id:                   int
    transaction_type:     str
    raw_symbol:           str | None
    canonical_symbol:     str | None
    shares:               Decimal
    price_per_share:      Decimal
    total_amount:         Decimal
    fees:                 Decimal
    taxes:                Decimal
    transaction_date:     date
    created_at:           datetime | None
    sector:               str | None
    notes:                str | None
    qty_correction_delta: Decimal | None
    realized_pnl:         float | None
    asset_id:             int | None = None


def _canonicalize_one(tx: Any, *, prefer_asset_id: bool = False) -> CanonicalTransaction:
    raw_sym   = tx.symbol.strip().upper() if tx.symbol and tx.symbol.strip() else None
    canon_sym = get_yfinance_symbol(raw_sym) if raw_sym else None

    qty_delta: Decimal | None = None
    if tx.transaction_type == "QUANTITY_CORRECTION":
        notes_str = tx.notes or ""
        m = _QCORR_RE.search(notes_str)
        qty_delta = Decimal(m.group(1)) if m else _to_decimal(tx.shares or "0")

    realized: float | None = None
    if tx.transaction_type == "SELL" and tx.notes:
        m = _REALIZED_RE.search(tx.notes)
        if m:
            realized = float(m.group(1))

    tx_date = _to_date(tx.transaction_date)
    if tx_date is None:
        tx_date = date.min   # defensive guard; transaction_date is non-nullable

    return CanonicalTransaction(
        id                   = tx.id,
        transaction_type     = tx.transaction_type or "",
        raw_symbol           = raw_sym,
        canonical_symbol     = canon_sym,
        shares               = _to_decimal(tx.shares),
        price_per_share      = _to_decimal(tx.price_per_share),
        total_amount         = _to_decimal(tx.total_amount),
        fees                 = _to_decimal(tx.fees),
        taxes                = _to_decimal(tx.taxes),
        transaction_date     = tx_date,
        created_at           = _to_datetime(tx.created_at),
        sector               = tx.sector if tx.sector else None,
        notes                = tx.notes if tx.notes else None,
        qty_correction_delta = qty_delta,
        realized_pnl         = realized,
        asset_id             = (getattr(tx, "asset_id", None) if prefer_asset_id else None),
    )


def canonicalize_transactions(
    txs: list[Any],
    *,
    prefer_asset_id: bool = False,
) -> tuple[CanonicalTransaction, ...]:
    """Convert a list of Transaction ORM rows into a sorted immutable tuple.

    Sort order: (transaction_date, id) — matches the ordering used by both
    portfolio_rebuilder and ledger_validator, and is deterministic when
    multiple transactions share the same date.

    Pure function: no database access, no network I/O, no side effects.
    Calling it twice with the same input always produces identical output.

    Args:
        txs: List of SQLAlchemy Transaction objects (or any object with the
             same attribute names — SimpleNamespace is accepted in tests).
        prefer_asset_id: M5 Track B Stage 4. When True, each
            CanonicalTransaction's asset_id is read from tx.asset_id (a
            plain ORM attribute access — no Registry call, purity intact).
            When False (the default), asset_id is always None, which is
            what every pre-Stage-4 caller still gets automatically since
            this parameter is additive. Callers that key replay state by
            replay_key() (portfolio_rebuilder.py, ledger_validator.py) pass
            this per-portfolio, from that portfolio's own
            Portfolio.replay_asset_id_native flag — never globally.

    Returns:
        Immutable tuple of CanonicalTransaction, sorted by (transaction_date, id).
    """
    canonical = [_canonicalize_one(tx, prefer_asset_id=prefer_asset_id) for tx in txs]
    canonical.sort(key=lambda c: (c.transaction_date, c.id))
    return tuple(canonical)
