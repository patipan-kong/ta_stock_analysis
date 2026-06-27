"""Ledger Validator — read-only inspection of a portfolio's transaction ledger.

Design invariants
-----------------
* NEVER writes to the database.
* NEVER modifies replay behavior in portfolio_rebuilder.
* NEVER raises exceptions to the caller — errors produce findings, not stack traces.
* Internal replay is private; does NOT import from portfolio_rebuilder.
* Price-dependent checks require fetch_prices=True and contact yfinance.

Severity levels
---------------
  WARNING  — suspicious pattern; may or may not be a real problem
  ERROR    — likely corruption that will cause incorrect replay results
  CRITICAL — definite corruption; action required before trusting replay output

Usage
-----
  from services.ledger_validator import validate_portfolio_ledger

  report = await validate_portfolio_ledger(
      db=db, portfolio_id=4, workspace_id=1, fetch_prices=True
  )
  for f in report.findings:
      print(f.severity, f.title)
"""
from __future__ import annotations

import asyncio
import bisect
import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from models.database import Portfolio, PortfolioItem, PortfolioSnapshot, Transaction
from services.symbol_normalization import get_yfinance_symbol
from services.data_fetcher import fetch_history

_log = logging.getLogger(__name__)

# ── Module-level thresholds (callers can override per-call) ────────────────────
_DATE_SKEW_WARNING_DAYS  = 90
_DATE_SKEW_ERROR_DAYS    = 365
_CASH_TOLERANCE          = 1.0    # THB absolute
_SHARES_TOLERANCE        = 0.001  # shares absolute

# ── Transaction type groups ────────────────────────────────────────────────────
_EQUITY_TYPES  = frozenset({"BUY", "SELL", "INITIAL_POSITION", "QUANTITY_CORRECTION"})
_BUY_TYPES     = frozenset({"BUY", "INITIAL_POSITION"})
_CASH_IN_TYPES = frozenset({"DEPOSIT", "INITIAL_CASH"})

# Matches "Quantity correction: +5.0 shares" in tx.notes
_QCORR_RE = re.compile(r"Quantity correction:\s*([+-]?\d[\d.]*)\s*shares", re.IGNORECASE)


def _d(v: Any) -> Decimal:
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")


def _parse_qty_delta(tx: Any) -> Decimal:
    """Extract signed delta from a QUANTITY_CORRECTION transaction.

    Mirrors the logic in portfolio_rebuilder without importing from it.
    tx.shares stores abs(delta); the sign comes from tx.notes.
    """
    if tx.notes:
        m = _QCORR_RE.search(tx.notes)
        if m:
            return Decimal(m.group(1))
    return Decimal(str(tx.shares or "0"))


# ══════════════════════════════════════════════════════════════════════════════
# Public data structures
# ══════════════════════════════════════════════════════════════════════════════

class FindingSeverity(str, Enum):
    WARNING  = "WARNING"
    ERROR    = "ERROR"
    CRITICAL = "CRITICAL"


_SEV_ORDER = {FindingSeverity.CRITICAL: 0, FindingSeverity.ERROR: 1, FindingSeverity.WARNING: 2}


@dataclass
class LedgerFinding:
    """One anomaly found in the transaction ledger."""
    check_id:          str
    severity:          FindingSeverity
    portfolio_id:      int
    transaction_ids:   list[int]
    symbol:            str | None
    normalized_symbol: str | None
    title:             str
    explanation:       str
    recommendation:    str
    details:           dict[str, Any] = field(default_factory=dict)


@dataclass
class LedgerValidationReport:
    portfolio_id:           int
    portfolio_name:         str
    transactions_inspected: int
    findings:               list[LedgerFinding] = field(default_factory=list)
    elapsed_seconds:        float = 0.0
    price_check_performed:  bool  = False

    @property
    def criticals(self) -> list[LedgerFinding]:
        return [f for f in self.findings if f.severity == FindingSeverity.CRITICAL]

    @property
    def errors(self) -> list[LedgerFinding]:
        return [f for f in self.findings if f.severity == FindingSeverity.ERROR]

    @property
    def warnings(self) -> list[LedgerFinding]:
        return [f for f in self.findings if f.severity == FindingSeverity.WARNING]

    @property
    def overall_severity(self) -> str:
        if self.criticals:
            return "CRITICAL"
        if self.errors:
            return "ERROR"
        if self.warnings:
            return "WARNING"
        return "PASS"


# ══════════════════════════════════════════════════════════════════════════════
# Structural checks (pure read of transaction list, no replay, no DB beyond txs)
# ══════════════════════════════════════════════════════════════════════════════

def _check_duplicate_initial_positions(
    portfolio_id: int,
    txs: list[Any],
) -> list[LedgerFinding]:
    """CHECK 1 — Multiple INITIAL_POSITION records for the same symbol on the same date.

    Replay accumulates all of them, silently overstating the position.
    """
    groups: dict[tuple[str, str], list[Any]] = defaultdict(list)
    for tx in txs:
        if tx.transaction_type != "INITIAL_POSITION":
            continue
        if not tx.symbol:
            continue
        canon    = get_yfinance_symbol(tx.symbol)
        date_str = tx.transaction_date.strftime("%Y-%m-%d") if tx.transaction_date else "unknown"
        groups[(canon, date_str)].append(tx)

    findings: list[LedgerFinding] = []
    for (canon, date_str), group in sorted(groups.items()):
        if len(group) <= 1:
            continue
        tx_ids      = [t.id for t in group]
        raw_symbols = sorted({t.symbol for t in group})
        total_sh    = sum(float(t.shares or 0) for t in group)
        entry_lines = "\n".join(
            f"  tx{t.id}  {t.symbol}  {t.shares or 0:.4f} @ {t.price_per_share or 0:.4f}"
            for t in group
        )
        findings.append(LedgerFinding(
            check_id          = "DUP_INITIAL_POSITION",
            severity          = FindingSeverity.CRITICAL,
            portfolio_id      = portfolio_id,
            transaction_ids   = tx_ids,
            symbol            = group[0].symbol,
            normalized_symbol = canon,
            title             = f"Duplicate INITIAL_POSITION: {canon} on {date_str} ({len(group)}×)",
            explanation       = (
                f"Portfolio {portfolio_id} has {len(group)} INITIAL_POSITION records "
                f"for '{canon}' on {date_str}. "
                f"Raw symbols: {raw_symbols}. "
                f"Replay will accumulate all of them (total={total_sh:.4f} shares).\n"
                f"{entry_lines}"
            ),
            recommendation    = (
                "Review manually. Identify the authoritative import record. "
                "Do NOT auto-delete. After verifying, delete the duplicate(s), "
                "then run rebuild_portfolio."
            ),
            details={
                "canonical_symbol": canon,
                "date":             date_str,
                "count":            len(group),
                "transaction_ids":  tx_ids,
                "raw_symbols":      raw_symbols,
                "total_shares":     round(total_sh, 6),
            },
        ))
    return findings


def _check_symbol_aliases(
    portfolio_id: int,
    txs: list[Any],
) -> list[LedgerFinding]:
    """CHECK 2 — Multiple raw symbols resolve to the same canonical yfinance ticker.

    e.g. KBANK and KBANK.BK both map to KBANK.BK;
         NVDA01 and NVDA01.BK both map to NVDA.
    Replay treats them as separate holdings, creating phantom positions.
    """
    canon_to_raw:    dict[str, set[str]]  = defaultdict(set)
    canon_to_tx_ids: dict[str, list[int]] = defaultdict(list)

    for tx in txs:
        if not tx.symbol:
            continue
        raw   = tx.symbol.strip().upper()
        canon = get_yfinance_symbol(raw)
        canon_to_raw[canon].add(raw)
        canon_to_tx_ids[canon].append(tx.id)

    findings: list[LedgerFinding] = []
    for canon, raw_set in sorted(canon_to_raw.items()):
        if len(raw_set) <= 1:
            continue
        raw_list = sorted(raw_set)
        findings.append(LedgerFinding(
            check_id          = "SYMBOL_ALIAS",
            severity          = FindingSeverity.WARNING,
            portfolio_id      = portfolio_id,
            transaction_ids   = canon_to_tx_ids[canon],
            symbol            = raw_list[0],
            normalized_symbol = canon,
            title             = f"Symbol alias: multiple raw forms resolve to '{canon}'",
            explanation       = (
                f"Raw symbols {raw_list} in portfolio {portfolio_id} all resolve "
                f"to the canonical ticker '{canon}'. "
                "Replay treats each raw symbol as a distinct holding, which may "
                "produce duplicate positions or incorrect share balances. "
                "This typically results from legacy symbol storage without .BK "
                "suffix or from a symbol rename."
            ),
            recommendation    = (
                "Verify all raw symbols refer to the same instrument. "
                "Normalise older transactions to the canonical form, then run "
                "rebuild_portfolio."
            ),
            details={
                "canonical_symbol":  canon,
                "raw_symbols":       raw_list,
                "transaction_count": len(canon_to_tx_ids[canon]),
            },
        ))
    return findings


def _check_null_symbols(
    portfolio_id: int,
    txs: list[Any],
) -> list[LedgerFinding]:
    """CHECK 3 — Equity transactions with a null or empty symbol."""
    findings: list[LedgerFinding] = []
    for tx in txs:
        if tx.transaction_type not in _EQUITY_TYPES:
            continue
        if not tx.symbol or not tx.symbol.strip():
            findings.append(LedgerFinding(
                check_id          = "NULL_SYMBOL",
                severity          = FindingSeverity.ERROR,
                portfolio_id      = portfolio_id,
                transaction_ids   = [tx.id],
                symbol            = None,
                normalized_symbol = None,
                title             = f"tx{tx.id}: {tx.transaction_type} with null/empty symbol",
                explanation       = (
                    f"tx{tx.id} (type={tx.transaction_type}, "
                    f"date={tx.transaction_date}) has no symbol. "
                    "Replay silently skips it."
                ),
                recommendation    = (
                    "Determine the correct symbol and update it, or delete "
                    "this transaction if it was recorded in error."
                ),
                details={"transaction_id": tx.id, "type": tx.transaction_type,
                         "date": str(tx.transaction_date)},
            ))
    return findings


def _check_zero_shares(
    portfolio_id: int,
    txs: list[Any],
) -> list[LedgerFinding]:
    """CHECK 4 — Equity transactions with zero or null shares."""
    findings: list[LedgerFinding] = []
    for tx in txs:
        if tx.transaction_type not in _EQUITY_TYPES:
            continue
        if not tx.shares or float(tx.shares) == 0.0:
            findings.append(LedgerFinding(
                check_id          = "ZERO_SHARES",
                severity          = FindingSeverity.ERROR,
                portfolio_id      = portfolio_id,
                transaction_ids   = [tx.id],
                symbol            = tx.symbol,
                normalized_symbol = get_yfinance_symbol(tx.symbol) if tx.symbol else None,
                title             = (
                    f"tx{tx.id}: {tx.transaction_type} {tx.symbol or '?'} "
                    f"has zero/null shares"
                ),
                explanation       = (
                    f"tx{tx.id} ({tx.transaction_type} {tx.symbol} on "
                    f"{tx.transaction_date}) has shares={tx.shares}. "
                    "Replay skips this transaction."
                ),
                recommendation    = (
                    "Correct the shares field or remove this transaction."
                ),
                details={"transaction_id": tx.id, "shares": tx.shares,
                         "type": tx.transaction_type, "symbol": tx.symbol},
            ))
    return findings


def _check_zero_prices(
    portfolio_id: int,
    txs: list[Any],
) -> list[LedgerFinding]:
    """CHECK 5 — BUY/INITIAL_POSITION with zero or null price_per_share.

    Zero price causes avg_cost=0, corrupting cost-basis for all future SELLs.
    """
    findings: list[LedgerFinding] = []
    for tx in txs:
        if tx.transaction_type not in {"BUY", "INITIAL_POSITION"}:
            continue
        if tx.price_per_share is None or float(tx.price_per_share) == 0.0:
            findings.append(LedgerFinding(
                check_id          = "ZERO_PRICE",
                severity          = FindingSeverity.WARNING,
                portfolio_id      = portfolio_id,
                transaction_ids   = [tx.id],
                symbol            = tx.symbol,
                normalized_symbol = get_yfinance_symbol(tx.symbol) if tx.symbol else None,
                title             = (
                    f"tx{tx.id}: {tx.transaction_type} {tx.symbol or '?'} "
                    f"has zero/null price_per_share"
                ),
                explanation       = (
                    f"tx{tx.id} ({tx.transaction_type} {tx.symbol} on "
                    f"{tx.transaction_date}) has price_per_share={tx.price_per_share}. "
                    "This sets avg_cost=0, causing incorrect cost-basis and "
                    "unrealized P/L calculations."
                ),
                recommendation    = "Correct price_per_share for this transaction.",
                details={"transaction_id": tx.id, "price_per_share": tx.price_per_share,
                         "symbol": tx.symbol},
            ))
    return findings


def _check_pre_portfolio_transactions(
    portfolio_id:        int,
    portfolio_created_at: datetime | None,
    txs: list[Any],
) -> list[LedgerFinding]:
    """CHECK 6 — Transactions whose date is before the portfolio was created."""
    if not portfolio_created_at:
        return []

    cutoff = (
        portfolio_created_at.date()
        if hasattr(portfolio_created_at, "date")
        else portfolio_created_at
    )
    findings: list[LedgerFinding] = []
    for tx in txs:
        if not tx.transaction_date:
            continue
        tx_date = (
            tx.transaction_date.date()
            if hasattr(tx.transaction_date, "date")
            else tx.transaction_date
        )
        if tx_date >= cutoff:
            continue
        findings.append(LedgerFinding(
            check_id          = "PRE_PORTFOLIO_TX",
            severity          = FindingSeverity.ERROR,
            portfolio_id      = portfolio_id,
            transaction_ids   = [tx.id],
            symbol            = tx.symbol,
            normalized_symbol = get_yfinance_symbol(tx.symbol) if tx.symbol else None,
            title             = (
                f"tx{tx.id}: {tx.transaction_type} dated {tx_date} "
                f"before portfolio creation ({cutoff})"
            ),
            explanation       = (
                f"tx{tx.id} has transaction_date={tx_date}, "
                f"which precedes the portfolio creation date {cutoff}. "
                "This suggests a backdated import or a transaction belonging "
                "to a different portfolio."
            ),
            recommendation    = (
                "Verify the transaction date. If backdated intentionally "
                "(historical position import), this may be acceptable. "
                "Otherwise, correct the date or move to the correct portfolio."
            ),
            details={
                "transaction_id":       tx.id,
                "transaction_date":     str(tx_date),
                "portfolio_created_at": str(cutoff),
                "type":                 tx.transaction_type,
                "symbol":               tx.symbol,
            },
        ))
    return findings


def _check_date_skew(
    portfolio_id: int,
    txs: list[Any],
    warning_days: int = _DATE_SKEW_WARNING_DAYS,
    error_days:   int = _DATE_SKEW_ERROR_DAYS,
) -> list[LedgerFinding]:
    """CHECK 7 — Large gap between created_at (physical insert) and transaction_date.

    The live snapshot engine uses created_at; the rebuild engine uses
    transaction_date.  A large skew means these two engines place the
    transaction in different periods — a source of irreconcilable divergence.
    """
    findings: list[LedgerFinding] = []
    for tx in txs:
        if not tx.created_at or not tx.transaction_date:
            continue
        ca  = tx.created_at.date()       if hasattr(tx.created_at, "date")       else tx.created_at
        td  = tx.transaction_date.date() if hasattr(tx.transaction_date, "date") else tx.transaction_date
        skew = abs((ca - td).days)
        if skew < warning_days:
            continue
        severity = FindingSeverity.ERROR if skew >= error_days else FindingSeverity.WARNING
        findings.append(LedgerFinding(
            check_id          = "LARGE_DATE_SKEW",
            severity          = severity,
            portfolio_id      = portfolio_id,
            transaction_ids   = [tx.id],
            symbol            = tx.symbol,
            normalized_symbol = get_yfinance_symbol(tx.symbol) if tx.symbol else None,
            title             = (
                f"tx{tx.id}: {tx.transaction_type} "
                f"created_at vs transaction_date skew = {skew} days"
            ),
            explanation       = (
                f"tx{tx.id} ({tx.transaction_type} {tx.symbol or ''}) "
                f"was inserted (created_at={tx.created_at}) "
                f"but bears a transaction_date {skew} days away "
                f"({tx.transaction_date}). "
                "The live snapshot engine attributes this transaction to the "
                "created_at period; the rebuild engine attributes it to "
                "transaction_date.  A large skew causes these engines to "
                "disagree on which snapshot period the transaction belongs to."
            ),
            recommendation    = (
                "Verify both dates are intentional. If not, correct "
                "transaction_date to reflect the actual trade date."
            ),
            details={
                "transaction_id":   tx.id,
                "created_at":       str(tx.created_at),
                "transaction_date": str(tx.transaction_date),
                "skew_days":        skew,
                "type":             tx.transaction_type,
                "symbol":           tx.symbol,
            },
        ))
    return findings


def _check_duplicate_fingerprints(
    portfolio_id: int,
    txs: list[Any],
) -> list[LedgerFinding]:
    """CHECK 8 — Transactions with identical (type, symbol, shares, price, date).

    Replay applies each record independently, potentially multiplying the position.
    """
    seen: dict[tuple, list[int]] = defaultdict(list)
    for tx in txs:
        date_str = tx.transaction_date.strftime("%Y-%m-%d") if tx.transaction_date else ""
        key = (
            tx.transaction_type or "",
            (tx.symbol or "").strip().upper(),
            round(float(tx.shares or 0), 6),
            round(float(tx.price_per_share or 0), 4),
            date_str,
        )
        seen[key].append(tx.id)

    findings: list[LedgerFinding] = []
    for key, ids in sorted(seen.items(), key=lambda kv: kv[1][0]):
        if len(ids) <= 1:
            continue
        tx_type, sym, shares, price, date_str = key
        findings.append(LedgerFinding(
            check_id          = "DUP_TX_FINGERPRINT",
            severity          = FindingSeverity.ERROR,
            portfolio_id      = portfolio_id,
            transaction_ids   = ids,
            symbol            = sym or None,
            normalized_symbol = get_yfinance_symbol(sym) if sym else None,
            title             = (
                f"Duplicate fingerprint: {tx_type} {sym} "
                f"{shares} @ {price} on {date_str} ({len(ids)}×)"
            ),
            explanation       = (
                f"Transactions {ids} share identical "
                f"(type={tx_type}, symbol={sym}, shares={shares}, "
                f"price={price}, date={date_str}). "
                "Replay applies each independently, likely doubling the position."
            ),
            recommendation    = (
                "Keep the authoritative record and delete the duplicate(s), "
                "then run rebuild_portfolio."
            ),
            details={
                "transaction_ids": ids,
                "type":            tx_type,
                "symbol":          sym,
                "shares":          shares,
                "price":           price,
                "date":            date_str,
                "count":           len(ids),
            },
        ))
    return findings


# ══════════════════════════════════════════════════════════════════════════════
# Internal private replay state
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class _ReplayState:
    holdings: dict[str, Decimal]
    cash:     Decimal

    def copy(self) -> "_ReplayState":
        return _ReplayState(holdings=dict(self.holdings), cash=self.cash)


# ══════════════════════════════════════════════════════════════════════════════
# Replay-based checks (single-pass, private replay — no import from rebuilder)
# ══════════════════════════════════════════════════════════════════════════════

def _replay_and_check(
    portfolio_id:   int,
    txs:            list[Any],
    snapshot_dates: list[str] | None = None,
) -> tuple[_ReplayState, list[LedgerFinding], dict[str, _ReplayState]]:
    """Single-pass replay that detects balance anomalies and captures snapshot states.

    snapshot_dates must be sorted ascending.  State is captured end-of-day:
    transactions on or before each date are included.

    Returns:
        (final_state, findings, state_by_date)
    """
    state    = _ReplayState(holdings={}, cash=Decimal("0"))
    findings: list[LedgerFinding] = []

    snap_sorted = sorted(snapshot_dates or [])
    snap_idx    = 0
    state_by_date: dict[str, _ReplayState] = {}

    for tx in txs:
        tx_type = tx.transaction_type
        amount  = _d(tx.total_amount or "0")
        sym     = (tx.symbol or "").strip().upper() if tx.symbol else None
        tx_date = tx.transaction_date.strftime("%Y-%m-%d") if tx.transaction_date else ""

        # Capture snapshot states for all dates that are now "past" (< current tx_date)
        while snap_idx < len(snap_sorted) and snap_sorted[snap_idx] < tx_date:
            state_by_date[snap_sorted[snap_idx]] = state.copy()
            snap_idx += 1

        if tx_type in _CASH_IN_TYPES or tx_type == "DIVIDEND":
            state.cash += amount

        elif tx_type == "WITHDRAW":
            state.cash -= amount

        elif tx_type == "BUY":
            if not sym or not tx.shares or float(tx.shares) <= 0:
                continue
            shares = _d(tx.shares)
            state.cash -= amount
            if state.cash < Decimal("-0.01"):
                findings.append(LedgerFinding(
                    check_id          = "NEG_CASH_BALANCE",
                    severity          = FindingSeverity.WARNING,
                    portfolio_id      = portfolio_id,
                    transaction_ids   = [tx.id],
                    symbol            = sym,
                    normalized_symbol = get_yfinance_symbol(sym),
                    title             = f"tx{tx.id}: BUY {sym} drives cash negative ({float(state.cash):,.2f})",
                    explanation       = (
                        f"After tx{tx.id} (BUY {sym} {tx.shares} @ "
                        f"{tx.price_per_share} on {tx.transaction_date}), "
                        f"replayed cash drops to {float(state.cash):,.2f}. "
                        "Possible missing DEPOSIT, incorrect total_amount, or "
                        "out-of-order transaction dates."
                    ),
                    recommendation    = (
                        "Verify all deposits are recorded and that total_amount "
                        "and transaction ordering are correct."
                    ),
                    details={
                        "transaction_id": tx.id,
                        "cash_after":     round(float(state.cash), 2),
                        "buy_amount":     round(float(amount), 2),
                        "date":           tx_date,
                    },
                ))
            state.holdings[sym] = state.holdings.get(sym, Decimal("0")) + shares

        elif tx_type == "SELL":
            if not sym or not tx.shares or float(tx.shares) <= 0:
                continue
            shares = _d(tx.shares)

            if sym not in state.holdings:
                findings.append(LedgerFinding(
                    check_id          = "SELL_WITHOUT_HOLDING",
                    severity          = FindingSeverity.CRITICAL,
                    portfolio_id      = portfolio_id,
                    transaction_ids   = [tx.id],
                    symbol            = sym,
                    normalized_symbol = get_yfinance_symbol(sym),
                    title             = f"tx{tx.id}: SELL {sym} — no prior holding",
                    explanation       = (
                        f"tx{tx.id} (SELL {sym} {tx.shares} on {tx.transaction_date}) "
                        f"was reached during replay but {sym} was not in the portfolio. "
                        "Possible causes: missing BUY/INITIAL_POSITION, symbol alias "
                        "mismatch, or orphan SELL transaction."
                    ),
                    recommendation    = (
                        "Locate the original BUY or INITIAL_POSITION. If the symbol "
                        "was stored under a different alias, normalise it. "
                        "If the SELL is spurious, delete it."
                    ),
                    details={
                        "transaction_id": tx.id, "symbol": sym,
                        "shares": float(shares), "date": tx_date,
                    },
                ))
                state.cash += amount
                continue

            state.cash += amount
            new_shares = state.holdings[sym] - shares

            if new_shares < Decimal("-0.001"):
                findings.append(LedgerFinding(
                    check_id          = "NEG_SHARE_BALANCE",
                    severity          = FindingSeverity.CRITICAL,
                    portfolio_id      = portfolio_id,
                    transaction_ids   = [tx.id],
                    symbol            = sym,
                    normalized_symbol = get_yfinance_symbol(sym),
                    title             = f"tx{tx.id}: SELL {sym} creates negative share balance ({float(new_shares):.4f})",
                    explanation       = (
                        f"tx{tx.id} (SELL {sym} {tx.shares} on {tx.transaction_date}) "
                        f"reduces {sym} shares from {float(state.holdings[sym]):.4f} "
                        f"to {float(new_shares):.4f}. "
                        "Indicates incorrect SELL quantity, missing prior BUY, "
                        "or symbol alias mismatch."
                    ),
                    recommendation    = (
                        "Verify the SELL quantity against broker statements. "
                        "Check whether prior BUYs used a different symbol alias."
                    ),
                    details={
                        "transaction_id": tx.id,
                        "symbol":         sym,
                        "shares_sold":    round(float(shares), 6),
                        "shares_before":  round(float(state.holdings[sym]), 6),
                        "shares_after":   round(float(new_shares), 6),
                        "date":           tx_date,
                    },
                ))

            if new_shares <= Decimal("0.001"):
                del state.holdings[sym]
            else:
                state.holdings[sym] = new_shares

        elif tx_type == "INITIAL_POSITION":
            if not sym or not tx.shares or float(tx.shares) <= 0:
                continue
            state.holdings[sym] = state.holdings.get(sym, Decimal("0")) + _d(tx.shares)

        elif tx_type == "QUANTITY_CORRECTION":
            if not sym:
                continue
            delta = _parse_qty_delta(tx)

            if sym not in state.holdings:
                # A correction on a symbol not yet held is suspicious
                findings.append(LedgerFinding(
                    check_id          = "QCORR_WITHOUT_HOLDING",
                    severity          = FindingSeverity.ERROR,
                    portfolio_id      = portfolio_id,
                    transaction_ids   = [tx.id],
                    symbol            = sym,
                    normalized_symbol = get_yfinance_symbol(sym),
                    title             = f"tx{tx.id}: QUANTITY_CORRECTION for {sym} — not in holdings",
                    explanation       = (
                        f"tx{tx.id} is a QUANTITY_CORRECTION for {sym} "
                        f"(delta={float(delta):+.4f} on {tx.transaction_date}), "
                        f"but {sym} was not in the replayed portfolio at that point. "
                        "Replay silently skips corrections on absent symbols."
                    ),
                    recommendation    = (
                        "Check whether this correction targets a different symbol "
                        "or whether a prior BUY/INITIAL_POSITION is missing."
                    ),
                    details={
                        "transaction_id": tx.id, "symbol": sym,
                        "delta": round(float(delta), 4), "date": tx_date,
                    },
                ))
                continue

            new_shares = state.holdings[sym] + delta
            if new_shares < Decimal("-0.001"):
                findings.append(LedgerFinding(
                    check_id          = "NEG_SHARE_BALANCE",
                    severity          = FindingSeverity.CRITICAL,
                    portfolio_id      = portfolio_id,
                    transaction_ids   = [tx.id],
                    symbol            = sym,
                    normalized_symbol = get_yfinance_symbol(sym),
                    title             = f"tx{tx.id}: QUANTITY_CORRECTION {sym} creates negative balance ({float(new_shares):.4f})",
                    explanation       = (
                        f"tx{tx.id} (QUANTITY_CORRECTION {sym} delta={float(delta):+.4f} "
                        f"on {tx.transaction_date}) would leave {float(new_shares):.4f} shares."
                    ),
                    recommendation    = "Review and correct the quantity correction delta.",
                    details={
                        "transaction_id": tx.id,
                        "symbol":         sym,
                        "delta":          round(float(delta), 4),
                        "shares_before":  round(float(state.holdings[sym]), 6),
                        "shares_after":   round(float(new_shares), 6),
                    },
                ))

            if new_shares <= Decimal("0.001"):
                del state.holdings[sym]
            else:
                state.holdings[sym] = new_shares

    # Capture remaining snapshot dates (on or after last transaction)
    while snap_idx < len(snap_sorted):
        state_by_date[snap_sorted[snap_idx]] = state.copy()
        snap_idx += 1

    return state, findings, state_by_date


# ══════════════════════════════════════════════════════════════════════════════
# DB consistency checks (compare replayed state against stored DB rows)
# ══════════════════════════════════════════════════════════════════════════════

def _check_cash_consistency(
    portfolio_id:  int,
    portfolio_cash: float,
    replayed_cash:  Decimal,
    tolerance:      float = _CASH_TOLERANCE,
) -> list[LedgerFinding]:
    """CHECK 8 (consistency) — Replayed final cash vs Portfolio.cash_balance."""
    diff = float(replayed_cash) - portfolio_cash
    if abs(diff) <= tolerance:
        return []
    return [LedgerFinding(
        check_id          = "CASH_MISMATCH",
        severity          = FindingSeverity.ERROR,
        portfolio_id      = portfolio_id,
        transaction_ids   = [],
        symbol            = None,
        normalized_symbol = None,
        title             = (
            f"Cash mismatch: replayed={float(replayed_cash):,.2f}  "
            f"stored={portfolio_cash:,.2f}  (Δ{diff:+,.2f})"
        ),
        explanation       = (
            f"Replaying all transactions for portfolio {portfolio_id} produces "
            f"a final cash balance of {float(replayed_cash):,.2f}, "
            f"but Portfolio.cash_balance is {portfolio_cash:,.2f} "
            f"(difference: {diff:+,.2f}). "
            "The live portfolio state has drifted from the transaction ledger."
        ),
        recommendation    = (
            "Run rebuild_portfolio to resynchronise the portfolio state from "
            "the ledger.  If the ledger is itself corrupted, identify the root "
            "cause first."
        ),
        details={
            "replayed_cash": round(float(replayed_cash), 2),
            "stored_cash":   round(portfolio_cash, 2),
            "difference":    round(diff, 2),
        },
    )]


def _check_holdings_consistency(
    portfolio_id:    int,
    portfolio_items: list[Any],
    replay_state:    _ReplayState,
    shares_tol:      float = _SHARES_TOLERANCE,
) -> list[LedgerFinding]:
    """CHECK 9 — Replayed final holdings vs current PortfolioItem rows."""
    findings: list[LedgerFinding] = []
    current = {item.symbol.strip().upper(): item for item in portfolio_items}
    replay  = replay_state.holdings

    for sym in sorted(set(current) | set(replay)):
        curr = current.get(sym)
        repl = replay.get(sym)

        if curr and repl is None:
            findings.append(LedgerFinding(
                check_id          = "HOLDINGS_MISMATCH",
                severity          = FindingSeverity.ERROR,
                portfolio_id      = portfolio_id,
                transaction_ids   = [],
                symbol            = sym,
                normalized_symbol = get_yfinance_symbol(sym),
                title             = f"Holdings mismatch: {sym} in DB but not in replay",
                explanation       = (
                    f"PortfolioItem({sym}, shares={curr.shares}) exists in the DB "
                    "but the ledger replay produces no position for this symbol. "
                    "The portfolio state has diverged from the transaction ledger."
                ),
                recommendation    = "Run rebuild_portfolio to resync holdings.",
                details={"symbol": sym, "db_shares": curr.shares, "replay_shares": None},
            ))
        elif repl is not None and curr is None:
            findings.append(LedgerFinding(
                check_id          = "HOLDINGS_MISMATCH",
                severity          = FindingSeverity.ERROR,
                portfolio_id      = portfolio_id,
                transaction_ids   = [],
                symbol            = sym,
                normalized_symbol = get_yfinance_symbol(sym),
                title             = f"Holdings mismatch: {sym} in replay but not in DB",
                explanation       = (
                    f"Ledger replay produces {float(repl):.4f} shares of {sym}, "
                    "but no PortfolioItem row exists for this symbol in the DB."
                ),
                recommendation    = "Run rebuild_portfolio to add missing holdings.",
                details={"symbol": sym, "db_shares": None, "replay_shares": round(float(repl), 6)},
            ))
        elif curr and repl is not None:
            diff = float(repl) - float(curr.shares)
            if abs(diff) > shares_tol:
                findings.append(LedgerFinding(
                    check_id          = "HOLDINGS_MISMATCH",
                    severity          = FindingSeverity.ERROR,
                    portfolio_id      = portfolio_id,
                    transaction_ids   = [],
                    symbol            = sym,
                    normalized_symbol = get_yfinance_symbol(sym),
                    title             = (
                        f"Holdings mismatch: {sym} shares differ "
                        f"(DB={curr.shares:.4f} replay={float(repl):.4f})"
                    ),
                    explanation       = (
                        f"{sym}: DB has {curr.shares:.6f} shares, "
                        f"replay produces {float(repl):.6f} (Δ{diff:+.6f})."
                    ),
                    recommendation    = "Run rebuild_portfolio to resync holdings.",
                    details={
                        "symbol":        sym,
                        "db_shares":     round(float(curr.shares), 6),
                        "replay_shares": round(float(repl), 6),
                        "difference":    round(diff, 6),
                    },
                ))

    return findings


def _check_snapshot_cash_consistency(
    portfolio_id:  int,
    snapshots:     list[Any],
    state_by_date: dict[str, _ReplayState],
    cash_tol:      float = _CASH_TOLERANCE,
) -> list[LedgerFinding]:
    """CHECK 10 — Replayed cash at each snapshot date vs stored snapshot.cash_balance.

    This check is free (no yfinance) and catches the most common snapshot drift.
    """
    findings: list[LedgerFinding] = []
    for snap in snapshots:
        date = snap.snapshot_date
        if date not in state_by_date:
            continue
        replay_cash = float(state_by_date[date].cash)
        stored_cash = float(snap.cash_balance or 0.0)
        diff        = replay_cash - stored_cash
        if abs(diff) <= cash_tol:
            continue
        findings.append(LedgerFinding(
            check_id          = "SNAPSHOT_CASH_MISMATCH",
            severity          = FindingSeverity.WARNING,
            portfolio_id      = portfolio_id,
            transaction_ids   = [],
            symbol            = None,
            normalized_symbol = None,
            title             = (
                f"Snapshot {date}: cash mismatch "
                f"(replayed={replay_cash:,.2f} stored={stored_cash:,.2f} Δ{diff:+,.2f})"
            ),
            explanation       = (
                f"On {date}, replaying the ledger yields cash={replay_cash:,.2f}, "
                f"but the stored snapshot has cash_balance={stored_cash:,.2f} "
                f"(Δ{diff:+,.2f}). "
                "Indicates a transaction was recorded/modified after the snapshot "
                "was taken, or the snapshot was computed with stale cash data."
            ),
            recommendation    = "Run rebuild_portfolio to recalculate this snapshot.",
            details={
                "snapshot_date": date,
                "snapshot_id":   snap.id,
                "replay_cash":   round(replay_cash, 2),
                "stored_cash":   round(stored_cash, 2),
                "difference":    round(diff, 2),
            },
        ))
    return findings


# ══════════════════════════════════════════════════════════════════════════════
# Price-gated check (optional, async, requires yfinance)
# ══════════════════════════════════════════════════════════════════════════════

async def _check_impossible_prices(
    portfolio_id:        int,
    txs:                 list[Any],
    price_deviation_pct: float = 100.0,
) -> list[LedgerFinding]:
    """CHECK 11 — Import/buy prices deviating wildly from historical market prices.

    Requires yfinance.  Gracefully skips symbols where data is unavailable.
    """
    findings: list[LedgerFinding] = []

    equity_txs = [
        tx for tx in txs
        if tx.transaction_type in _BUY_TYPES
        and tx.symbol
        and tx.price_per_share
        and float(tx.price_per_share) > 0
        and tx.transaction_date
    ]
    if not equity_txs:
        return findings

    # Symbols to fetch, date range to cover
    yf_symbols  = list({get_yfinance_symbol(tx.symbol) for tx in equity_txs})
    min_date_dt = min(tx.transaction_date for tx in equity_txs)
    delta_days  = (datetime.utcnow() - min_date_dt).days
    period      = "max" if delta_days > 5 * 365 else "10y" if delta_days > 3 * 365 else "5y"

    # Build {yf_symbol: {date_str: close_price}}
    price_matrix: dict[str, dict[str, float | None]] = {}

    for yf_sym in yf_symbols:
        try:
            df: pd.DataFrame | None = await asyncio.to_thread(
                fetch_history, yf_sym, period, "1d"
            )
        except Exception as exc:
            _log.warning("price_check: fetch failed sym=%s: %s", yf_sym, exc)
            continue

        if df is None or df.empty:
            continue

        df_sorted = df.sort_index()
        df_dates  = df_sorted.index.strftime("%Y-%m-%d").tolist()
        df_closes = [
            float(v) if pd.notna(v) and float(v) > 0 else None
            for v in df_sorted["Close"]
        ]

        date_price: dict[str, float | None] = {}
        for tx in equity_txs:
            if get_yfinance_symbol(tx.symbol) != yf_sym:
                continue
            ds = tx.transaction_date.strftime("%Y-%m-%d")
            if ds not in date_price:
                idx = bisect.bisect_right(df_dates, ds) - 1
                date_price[ds] = df_closes[idx] if idx >= 0 else None

        price_matrix[yf_sym] = date_price

    # Compare recorded vs market price
    for tx in equity_txs:
        yf_sym   = get_yfinance_symbol(tx.symbol)
        date_str = tx.transaction_date.strftime("%Y-%m-%d")
        market   = price_matrix.get(yf_sym, {}).get(date_str)
        if market is None:
            continue
        recorded  = float(tx.price_per_share)
        deviation = abs(recorded - market) / market * 100
        if deviation <= price_deviation_pct:
            continue
        findings.append(LedgerFinding(
            check_id          = "IMPOSSIBLE_PRICE",
            severity          = FindingSeverity.ERROR,
            portfolio_id      = portfolio_id,
            transaction_ids   = [tx.id],
            symbol            = tx.symbol,
            normalized_symbol = yf_sym,
            title             = (
                f"tx{tx.id}: {tx.transaction_type} {tx.symbol} "
                f"price {recorded:.2f} deviates {deviation:.0f}% "
                f"from market {market:.2f}"
            ),
            explanation       = (
                f"tx{tx.id} ({tx.transaction_type} {tx.symbol} on {date_str}) "
                f"records price={recorded:.4f}, but yfinance shows ≈{market:.4f} "
                f"on that date (deviation={deviation:.1f}%). "
                "Possible causes: price entry error, split-adjustment mismatch, "
                "currency conversion not applied, or wrong symbol."
            ),
            recommendation    = (
                "Verify against broker contract note. "
                "Check for stock splits or currency issues. "
                "Correct price_per_share if needed."
            ),
            details={
                "transaction_id":  tx.id,
                "symbol":          tx.symbol,
                "yfinance_symbol": yf_sym,
                "date":            date_str,
                "recorded_price":  round(recorded, 4),
                "market_price":    round(market, 4),
                "deviation_pct":   round(deviation, 1),
                "type":            tx.transaction_type,
            },
        ))
    return findings


# ══════════════════════════════════════════════════════════════════════════════
# Public API
# ══════════════════════════════════════════════════════════════════════════════

async def validate_portfolio_ledger(
    db:                  Session,
    portfolio_id:        int,
    workspace_id:        int,
    fetch_prices:        bool  = False,
    price_deviation_pct: float = 100.0,
    date_skew_warning:   int   = _DATE_SKEW_WARNING_DAYS,
    date_skew_error:     int   = _DATE_SKEW_ERROR_DAYS,
    cash_tolerance:      float = _CASH_TOLERANCE,
    shares_tolerance:    float = _SHARES_TOLERANCE,
) -> LedgerValidationReport:
    """Validate the transaction ledger for a single portfolio.

    Read-only.  Never modifies the database.  Never raises.

    Args:
        db:                  SQLAlchemy session (caller manages lifecycle).
        portfolio_id:        Portfolio to validate.
        workspace_id:        Owning workspace.
        fetch_prices:        Enable IMPOSSIBLE_PRICE check (contacts yfinance).
        price_deviation_pct: Flag price deviations beyond this % from market.
        date_skew_warning:   Days of created_at/transaction_date skew → WARNING.
        date_skew_error:     Days of skew → ERROR.
        cash_tolerance:      Absolute THB tolerance for cash comparison.
        shares_tolerance:    Absolute shares tolerance for holdings comparison.
    """
    t_start = time.monotonic()

    # ── Load portfolio ────────────────────────────────────────────────────────
    portfolio = (
        db.query(Portfolio)
        .filter_by(id=portfolio_id, workspace_id=workspace_id)
        .first()
    )
    if portfolio is None:
        return LedgerValidationReport(
            portfolio_id           = portfolio_id,
            portfolio_name         = "?",
            transactions_inspected = 0,
            findings               = [LedgerFinding(
                check_id="PORTFOLIO_NOT_FOUND",
                severity=FindingSeverity.CRITICAL,
                portfolio_id=portfolio_id,
                transaction_ids=[],
                symbol=None, normalized_symbol=None,
                title=f"Portfolio {portfolio_id} not found in workspace {workspace_id}",
                explanation=f"No portfolio with id={portfolio_id}.",
                recommendation="Verify the portfolio ID.",
            )],
            elapsed_seconds = time.monotonic() - t_start,
        )

    # ── Load data ─────────────────────────────────────────────────────────────
    txs: list[Transaction] = (
        db.query(Transaction)
        .filter_by(portfolio_id=portfolio_id)
        .order_by(Transaction.transaction_date, Transaction.id)
        .all()
    )
    portfolio_items: list[PortfolioItem] = (
        db.query(PortfolioItem)
        .filter_by(portfolio_id=portfolio_id)
        .all()
    )
    snapshots: list[PortfolioSnapshot] = (
        db.query(PortfolioSnapshot)
        .filter_by(portfolio_id=portfolio_id)
        .order_by(PortfolioSnapshot.snapshot_date)
        .all()
    )
    snap_dates = [s.snapshot_date for s in snapshots]

    report = LedgerValidationReport(
        portfolio_id           = portfolio_id,
        portfolio_name         = portfolio.name,
        transactions_inspected = len(txs),
    )
    if not txs:
        return report

    findings: list[LedgerFinding] = []

    # ── Structural checks ─────────────────────────────────────────────────────
    findings.extend(_check_duplicate_initial_positions(portfolio_id, txs))
    findings.extend(_check_symbol_aliases(portfolio_id, txs))
    findings.extend(_check_null_symbols(portfolio_id, txs))
    findings.extend(_check_zero_shares(portfolio_id, txs))
    findings.extend(_check_zero_prices(portfolio_id, txs))
    findings.extend(_check_pre_portfolio_transactions(portfolio_id, portfolio.created_at, txs))
    findings.extend(_check_date_skew(portfolio_id, txs, date_skew_warning, date_skew_error))
    findings.extend(_check_duplicate_fingerprints(portfolio_id, txs))

    # ── Replay-based checks ───────────────────────────────────────────────────
    final_state, replay_findings, state_by_date = _replay_and_check(
        portfolio_id   = portfolio_id,
        txs            = txs,
        snapshot_dates = snap_dates,
    )
    findings.extend(replay_findings)

    # ── DB consistency checks ─────────────────────────────────────────────────
    findings.extend(_check_cash_consistency(
        portfolio_id   = portfolio_id,
        portfolio_cash = float(portfolio.cash_balance),
        replayed_cash  = final_state.cash,
        tolerance      = cash_tolerance,
    ))
    findings.extend(_check_holdings_consistency(
        portfolio_id    = portfolio_id,
        portfolio_items = portfolio_items,
        replay_state    = final_state,
        shares_tol      = shares_tolerance,
    ))
    findings.extend(_check_snapshot_cash_consistency(
        portfolio_id  = portfolio_id,
        snapshots     = snapshots,
        state_by_date = state_by_date,
    ))

    # ── Price check (optional, async) ─────────────────────────────────────────
    if fetch_prices:
        try:
            price_findings = await _check_impossible_prices(
                portfolio_id        = portfolio_id,
                txs                 = txs,
                price_deviation_pct = price_deviation_pct,
            )
            findings.extend(price_findings)
            report.price_check_performed = True
        except Exception as exc:
            _log.warning("price check failed portfolio=%d: %s", portfolio_id, exc)
            findings.append(LedgerFinding(
                check_id          = "PRICE_CHECK_FAILED",
                severity          = FindingSeverity.WARNING,
                portfolio_id      = portfolio_id,
                transaction_ids   = [],
                symbol            = None,
                normalized_symbol = None,
                title             = "IMPOSSIBLE_PRICE check could not complete",
                explanation       = f"yfinance error: {exc}",
                recommendation    = "Check network connectivity and retry with --price-check.",
                details={"error": str(exc)},
            ))

    # ── Sort findings: CRITICAL first, then ERROR, then WARNING; within each
    #    severity sort by check_id for deterministic output ────────────────────
    report.findings = sorted(findings, key=lambda f: (_SEV_ORDER[f.severity], f.check_id))
    report.elapsed_seconds = time.monotonic() - t_start
    return report


async def validate_all_ledgers(
    db:                  Session,
    workspace_id:        int,
    fetch_prices:        bool  = False,
    price_deviation_pct: float = 100.0,
    date_skew_warning:   int   = _DATE_SKEW_WARNING_DAYS,
    date_skew_error:     int   = _DATE_SKEW_ERROR_DAYS,
    cash_tolerance:      float = _CASH_TOLERANCE,
    shares_tolerance:    float = _SHARES_TOLERANCE,
) -> list[LedgerValidationReport]:
    """Validate every portfolio in a workspace."""
    portfolios = (
        db.query(Portfolio)
        .filter_by(workspace_id=workspace_id)
        .order_by(Portfolio.id)
        .all()
    )
    results: list[LedgerValidationReport] = []
    for p in portfolios:
        r = await validate_portfolio_ledger(
            db                  = db,
            portfolio_id        = p.id,
            workspace_id        = workspace_id,
            fetch_prices        = fetch_prices,
            price_deviation_pct = price_deviation_pct,
            date_skew_warning   = date_skew_warning,
            date_skew_error     = date_skew_error,
            cash_tolerance      = cash_tolerance,
            shares_tolerance    = shares_tolerance,
        )
        results.append(r)
    return results
