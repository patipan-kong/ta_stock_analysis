"""Snapshot repair service.

Identifies historically corrupted portfolio snapshots and regenerates
them from the stored historical snapshot contents.

Corruption pattern targeted
---------------------------
Before Phase 1 was shipped, a missing yfinance price silently fell back to
avg_cost (``p.get("current_price") or item.avg_cost``).  This caused:

  • current_price == avg_cost  for the affected holding
  • unrealized_pnl == 0        for the affected holding
  • total_value inflated or deflated vs the true market value

Repair approach — snapshot-only, no PortfolioItem dependency
-------------------------------------------------------------
Each PortfolioSnapshot stores the complete portfolio state at its date
inside ``holdings_json``.  Repair reads ONLY this stored historical data:

  1. Parse holdings_json  → historical symbol / shares / avg_cost / sector
  2. Fetch historical closing prices using the exact platform symbol (no DR normalisation)
  3. Recalculate: market_value, unrealized_pnl, sector_breakdown, total_value
  4. Persist updated fields; leave return-series columns unchanged

Fields updated by repair:
  total_value, total_invested, unrealized_pnl, unrealized_pnl_pct,
  sector_breakdown_json, holdings_json

Fields NOT touched by this repair:
  realized_pnl, cash_balance.

Return-series fields (investment_return_pct, daily_return_pct,
net_external_cash_flow, imported_asset_value, manual_adjustment_value,
period_realized_pnl, period_dividend_income, period_fees_paid) are now
recalculated atomically via snapshot_return_recovery._compute_return_fields()
after the NAV fields are corrected, so both sets of fields are committed in
the same transaction.

Design constraints
------------------
• Never read PortfolioItem or portfolio.cash_balance — use holdings_json
  and snapshot.cash_balance instead.
• Never overwrite a snapshot if historical price coverage < 90%.
• Keep the original row on failure; log the reason.
• Return a full RepairResult for every snapshot touched (pass or fail).
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session

from models.database import PortfolioSnapshot, Workspace
from services import capability_lookup_service
from services.capability_lookup_service import UnresolvedCapability
from services.capability_safety import permits_quantity_valuation
from services.data_fetcher import fetch_history
from services.runtime_consultation import (
    RuntimeConsultationLog,
    RuntimeFindingCategory,
    RuntimeValidationFinding,
)
from services.snapshot_return_recovery import _compute_return_fields

_log = logging.getLogger(__name__)

# Fraction of holdings whose current_price equals avg_cost (within tolerance)
# above which a snapshot is flagged as HIGH-confidence corrupted.
_PRICE_EQ_COST_THRESHOLD = 0.50

# Relative tolerance for price == avg_cost comparison (0.1 %).
_PRICE_EQ_COST_TOL = 0.001

# NAV deviation vs adjacent-snapshot interpolation above which a snapshot is
# flagged for discontinuity.
_NAV_JUMP_THRESHOLD = 0.15  # 15 %

# Minimum fraction of holdings with a retrievable historical price.
_COVERAGE_THRESHOLD = 0.90


# ── Result types ────────────────────────────────────────────────────────────────

class RepairStatus(str, Enum):
    REPAIRED = "REPAIRED"           # successfully regenerated and saved
    SKIPPED = "SKIPPED"             # coverage too low or no holdings — original preserved
    DRY_RUN = "DRY_RUN"             # would repair; database untouched
    FAILED = "FAILED"               # unexpected error
    NOT_CORRUPT = "NOT_CORRUPT"     # corruption check passed — no action needed


class CorruptionReason(str, Enum):
    PRICE_EQUALS_COST = "price_equals_avg_cost"
    ZERO_UNREALIZED_PNL = "zero_unrealized_pnl"
    NAV_DISCONTINUITY = "nav_discontinuity"
    MISSING_HOLDINGS = "missing_holdings"


class CorruptionConfidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass
class CorruptionReport:
    portfolio_id: int
    snapshot_id: int
    snapshot_date: str
    reasons: list[CorruptionReason]
    confidence: CorruptionConfidence
    details: dict = field(default_factory=dict)


@dataclass
class RepairResult:
    snapshot_id: int
    portfolio_id: int
    snapshot_date: str
    status: RepairStatus
    old_total_value: float | None
    new_total_value: float | None
    reason: str
    coverage: dict | None = None        # {total, successful, missing}
    before_after: dict | None = None    # equity/price comparison for the repaired snapshot
    repaired_at: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )
    error: str | None = None


# ── Corruption detection ─────────────────────────────────────────────────────────

def detect_corrupted_snapshots(
    db: Session,
    portfolio_id: int,
    workspace_id: int,
) -> list[CorruptionReport]:
    """Scan all snapshots for a portfolio and return corruption reports.

    Corruption indicators checked (each independently contributes to confidence):
      1. current_price ≈ avg_cost for ≥ 50% of holdings (PRICE_EQUALS_COST)
      2. unrealized_pnl == 0 for all non-zero-cost holdings (ZERO_UNREALIZED_PNL)
      3. NAV deviates >15% from linear interpolation of neighbors (NAV_DISCONTINUITY)
      4. holdings_json empty / absent while holdings_count > 0 (MISSING_HOLDINGS)

    Returns only snapshots that show at least one indicator.
    """
    snaps = (
        db.query(PortfolioSnapshot)
        .filter_by(portfolio_id=portfolio_id, workspace_id=workspace_id)
        .order_by(PortfolioSnapshot.snapshot_date)
        .all()
    )
    if not snaps:
        return []

    # Build a date → total_value lookup for discontinuity detection
    nav_by_date: dict[str, float] = {
        s.snapshot_date: s.total_value
        for s in snaps
        if s.total_value is not None
    }
    dates_sorted = sorted(nav_by_date)

    reports: list[CorruptionReport] = []

    for snap in snaps:
        reasons: list[CorruptionReason] = []
        details: dict = {}

        holdings: list[dict] = []
        try:
            holdings = json.loads(snap.holdings_json or "[]")
        except (ValueError, TypeError):
            pass

        # ── Indicator 1: missing holdings data ─────────────────────────────
        if (snap.holdings_count or 0) > 0 and not holdings:
            reasons.append(CorruptionReason.MISSING_HOLDINGS)
            details["missing_holdings"] = {
                "holdings_count_column": snap.holdings_count,
                "holdings_json_length": 0,
            }

        if holdings:
            total_h = len(holdings)
            price_eq_cost_count = 0
            zero_upnl_count = 0

            for h in holdings:
                avg_c = h.get("avg_cost") or 0.0
                curr  = h.get("current_price") or 0.0
                upnl  = h.get("unrealized_pnl")

                # price ≈ avg_cost check (only meaningful when avg_cost > 0)
                if avg_c > 0 and abs(curr - avg_c) / avg_c <= _PRICE_EQ_COST_TOL:
                    price_eq_cost_count += 1

                # zero unrealized P&L (only meaningful when cost > 0)
                if avg_c > 0 and (upnl is None or abs(upnl) < 0.01):
                    zero_upnl_count += 1

            # ── Indicator 2: price == cost ──────────────────────────────────
            price_eq_frac = price_eq_cost_count / total_h if total_h else 0.0
            if price_eq_frac >= _PRICE_EQ_COST_THRESHOLD:
                reasons.append(CorruptionReason.PRICE_EQUALS_COST)
                details["price_eq_cost"] = {
                    "count": price_eq_cost_count,
                    "total": total_h,
                    "fraction": round(price_eq_frac, 3),
                }

            # ── Indicator 3: zero unrealized P&L ───────────────────────────
            zero_upnl_frac = zero_upnl_count / total_h if total_h else 0.0
            if zero_upnl_frac >= _PRICE_EQ_COST_THRESHOLD:
                reasons.append(CorruptionReason.ZERO_UNREALIZED_PNL)
                details["zero_unrealized_pnl"] = {
                    "count": zero_upnl_count,
                    "total": total_h,
                    "fraction": round(zero_upnl_frac, 3),
                }

        # ── Indicator 4: NAV discontinuity ─────────────────────────────────
        if snap.total_value is not None and snap.snapshot_date in dates_sorted:
            idx = dates_sorted.index(snap.snapshot_date)
            prev_nav: float | None = None
            next_nav: float | None = None
            if idx > 0:
                prev_nav = nav_by_date[dates_sorted[idx - 1]]
            if idx < len(dates_sorted) - 1:
                next_nav = nav_by_date[dates_sorted[idx + 1]]

            if prev_nav is not None and next_nav is not None:
                interpolated = (prev_nav + next_nav) / 2.0
                if interpolated > 0:
                    deviation = abs(snap.total_value - interpolated) / interpolated
                    if deviation > _NAV_JUMP_THRESHOLD:
                        reasons.append(CorruptionReason.NAV_DISCONTINUITY)
                        details["nav_discontinuity"] = {
                            "snapshot_value": snap.total_value,
                            "interpolated": round(interpolated, 2),
                            "deviation_pct": round(deviation * 100, 2),
                        }

        if not reasons:
            continue

        # ── Confidence scoring ──────────────────────────────────────────────
        has_price_eq_cost   = CorruptionReason.PRICE_EQUALS_COST in reasons
        has_zero_upnl       = CorruptionReason.ZERO_UNREALIZED_PNL in reasons
        has_nav_disc        = CorruptionReason.NAV_DISCONTINUITY in reasons
        has_missing         = CorruptionReason.MISSING_HOLDINGS in reasons

        if (has_price_eq_cost and has_zero_upnl) or has_missing:
            confidence = CorruptionConfidence.HIGH
        elif has_price_eq_cost or (has_zero_upnl and has_nav_disc):
            confidence = CorruptionConfidence.HIGH
        elif has_zero_upnl or has_nav_disc:
            confidence = CorruptionConfidence.MEDIUM
        else:
            confidence = CorruptionConfidence.LOW

        reports.append(CorruptionReport(
            portfolio_id=portfolio_id,
            snapshot_id=snap.id,
            snapshot_date=snap.snapshot_date,
            reasons=reasons,
            confidence=confidence,
            details=details,
        ))

    return reports


# ── Historical price fetching ─────────────────────────────────────────────────

def _period_for_date(date_str: str) -> str:
    """Return the shortest yfinance period string that covers date_str."""
    days_ago = (datetime.utcnow().date() -
                datetime.strptime(date_str, "%Y-%m-%d").date()).days
    if days_ago <= 90:
        return "3mo"
    if days_ago <= 180:
        return "6mo"
    if days_ago <= 365:
        return "1y"
    if days_ago <= 730:
        return "2y"
    return "5y"


def _closing_price_on_or_before(df: pd.DataFrame, date_str: str) -> float | None:
    """Extract the most-recent closing price on or before date_str from an OHLCV DataFrame."""
    if df is None or df.empty:
        return None
    idx = pd.to_datetime(df.index).normalize()
    # Strip timezone so comparison works for both tz-aware (cached, UTC) and
    # tz-naive (direct yfinance) indexes.  We only compare calendar dates so
    # dropping the tz offset after normalising to midnight is always safe.
    if idx.tz is not None:
        idx = idx.tz_localize(None)
    df = df.copy()
    df.index = idx
    target = pd.Timestamp(date_str)
    rows = df[df.index <= target]
    if rows.empty:
        return None
    price = float(rows["Close"].iloc[-1])
    return price if price > 0 else None


async def fetch_historical_prices(
    symbols: list[str],
    date_str: str,
) -> dict[str, float | None]:
    """Fetch closing prices for *symbols* on (or closest before) *date_str*.

    Accepts any yfinance-compatible ticker, including Thai SET DR symbols
    (AAPL01.BK, NVDA01.BK), regular SET equities (AOT.BK), and US tickers (NVDA).
    Returns None for any symbol whose history cannot be fetched or does not
    cover the requested date.
    """
    period = _period_for_date(date_str)

    async def _one(symbol: str) -> tuple[str, float | None]:
        df = await asyncio.to_thread(fetch_history, symbol, period)
        return symbol, _closing_price_on_or_before(df, date_str)

    pairs = await asyncio.gather(*[_one(sym) for sym in symbols])
    return dict(pairs)


# ── Audit logging ─────────────────────────────────────────────────────────────

def _audit_log(result: RepairResult) -> None:
    old_fmt = f"{result.old_total_value:,.2f}" if result.old_total_value is not None else "N/A"
    new_fmt = f"{result.new_total_value:,.2f}" if result.new_total_value is not None else "N/A"

    cov = ""
    if result.coverage:
        cov = (
            f"\n  Coverage:   {result.coverage['successful']}/{result.coverage['total']} "
            f"({result.coverage.get('missing', [])})"
        )

    ba = ""
    if result.before_after:
        d = result.before_after
        eq_b = f"{d['equity_before']:,.2f}" if d.get("equity_before") is not None else "N/A"
        eq_a = f"{d['equity_after']:,.2f}" if d.get("equity_after") is not None else "N/A"
        cash_fmt = f"{d['cash']:,.2f}" if d.get("cash") is not None else "N/A"
        ba = f"\n  Equity Δ:   {eq_b} → {eq_a}\n  Cash:       {cash_fmt}"

    _log.info(
        "[REPAIR AUDIT] Snapshot %s\n"
        "  Status:     %s\n"
        "  Portfolio:  %s\n"
        "  Date:       %s\n"
        "  Old Value:  %s\n"
        "  New Value:  %s\n"
        "  Reason:     %s%s%s\n"
        "  Timestamp:  %s",
        result.snapshot_id,
        result.status.value,
        result.portfolio_id,
        result.snapshot_date,
        old_fmt,
        new_fmt,
        result.reason,
        cov,
        ba,
        result.repaired_at,
    )


# ── Stage R1 runtime consultation (M30.3 brief; fourth portfolio-domain
# shadow consumer) ───────────────────────────────────────────────────────────
#
# One legacy assumption in this module has no capability gate today (M29
# audit, SR-1 finding): `market_value = shares × price` is recomputed for
# every historical holding with a retrievable price — see the
# repaired-holdings loop in _repair_one(). Read-only, never raises, never
# gates — mirrors portfolio_snapshots._consult_runtime_for_snapshot()
# (M30.2) exactly.
#
# No DIVIDEND-flow check here: this module never touches DIVIDEND
# transactions directly — return-series fields (including
# period_dividend_income) are recalculated separately via
# snapshot_return_recovery._compute_return_fields() ->
# portfolio_metrics.compute_period_metrics(), which is pure by construction
# (ADR-004: "no ORM, no database session, no network access") and therefore
# out of scope for this DB-backed shadow-consultation pattern — see
# DECISION_LOG.md's M30.3 entry.
def _consult_runtime_for_repair(
    db: Session,
    unique_symbols: list[str],
    price_map: dict[str, float | None],
) -> RuntimeConsultationLog:
    """Never raises — resolve_capability_views() already turns an unminted
    symbol, an undefined asset_type, or a registry boot failure into an
    UnresolvedCapability per symbol rather than an exception; this function
    just turns that into a MISSING_BINDING finding, same as the other
    Stage R1 consumers.
    """
    priced_symbols = [s for s in unique_symbols if price_map.get(s) is not None]
    lookup_symbols = sorted({s.strip().upper() for s in priced_symbols})
    if not lookup_symbols:
        return RuntimeConsultationLog(consulted=0, agreements=0, findings=())

    views = capability_lookup_service.resolve_capability_views(db, lookup_symbols)

    findings: list[RuntimeValidationFinding] = []
    consulted  = 0
    agreements = 0

    for symbol in priced_symbols:
        consulted += 1
        legacy_result = True  # repair recomputes market_value = shares × price unconditionally
        view = views[symbol.strip().upper()]
        if isinstance(view, UnresolvedCapability):
            findings.append(RuntimeValidationFinding(
                category=RuntimeFindingCategory.MISSING_BINDING.value,
                check_id="RUNTIME_REPAIR_QUANTITY_VALUATION", transaction_ids=(),
                binding=symbol, question="permits_quantity_valuation()",
                legacy_result=legacy_result, runtime_result=None, detail=view.reason,
            ))
            continue
        runtime_result = permits_quantity_valuation(view)
        if runtime_result == legacy_result:
            agreements += 1
        else:
            findings.append(RuntimeValidationFinding(
                category=RuntimeFindingCategory.RUNTIME_MISMATCH.value,
                check_id="RUNTIME_REPAIR_QUANTITY_VALUATION", transaction_ids=(),
                binding=symbol, question="permits_quantity_valuation()",
                legacy_result=legacy_result, runtime_result=runtime_result,
                detail=(
                    f"snapshot repair recomputes market_value = shares × price "
                    f"for {symbol!r} unconditionally, but the runtime "
                    "capability view does not permit quantity-based valuation "
                    "for this asset."
                ),
            ))

    return RuntimeConsultationLog(consulted=consulted, agreements=agreements, findings=tuple(findings))


# ── Core repair logic ─────────────────────────────────────────────────────────

async def _repair_one(
    db: Session,
    snap: PortfolioSnapshot,
    workspace_id: int,
    dry_run: bool,
) -> RepairResult:
    """Repair a single PortfolioSnapshot using only its stored holdings_json.

    Does NOT read PortfolioItem or portfolio.cash_balance.  All position data
    (symbol, shares, avg_cost, sector) comes from holdings_json; cash comes
    from snapshot.cash_balance.  This ensures repairs reflect the historical
    portfolio state, not the current one.
    """
    portfolio_id    = snap.portfolio_id
    snapshot_date   = snap.snapshot_date
    old_total_value = snap.total_value

    # ── Parse historical holdings from the snapshot ───────────────────────────
    raw_holdings: list[dict] = []
    try:
        raw_holdings = json.loads(snap.holdings_json or "[]")
    except (ValueError, TypeError):
        pass

    if not raw_holdings:
        reason = (
            "holdings_json is empty or absent — cannot repair without "
            "historical position data"
        )
        _log.warning(
            "[REPAIR SKIPPED] portfolio=%d date=%s %s",
            portfolio_id, snapshot_date, reason,
        )
        result = RepairResult(
            snapshot_id=snap.id,
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            status=RepairStatus.SKIPPED,
            old_total_value=old_total_value,
            new_total_value=None,
            reason=reason,
        )
        _audit_log(result)
        return result

    platform_symbols: list[str] = [h["symbol"] for h in raw_holdings if h.get("symbol")]
    unique_symbols = list(dict.fromkeys(platform_symbols))

    # Fetch prices using the platform symbol as-is — do NOT normalise DR tickers.
    # AAPL01.BK / NVDA01.BK are SET-listed instruments; yfinance returns their
    # THB prices when queried with the .BK ticker.  Resolving them to the
    # underlying US ticker (AAPL / NVDA) would return a USD price stored as THB,
    # inflating the NAV by 10–50×.
    price_map: dict[str, float | None] = await fetch_historical_prices(unique_symbols, snapshot_date)

    # ── Coverage check ────────────────────────────────────────────────────────
    total      = len(unique_symbols)
    successful = sum(1 for v in price_map.values() if v is not None)
    missing    = [s for s, v in price_map.items() if v is None]
    coverage   = {"total": total, "successful": successful, "missing": missing}
    coverage_frac = successful / total if total > 0 else 1.0

    if total > 0 and coverage_frac < _COVERAGE_THRESHOLD:
        reason = (
            f"Historical price coverage {successful}/{total} "
            f"({coverage_frac * 100:.0f}%) is below 90% threshold. "
            f"Missing: {missing}"
        )
        _log.warning(
            "[REPAIR SKIPPED] portfolio=%d date=%s %s",
            portfolio_id, snapshot_date, reason,
        )
        result = RepairResult(
            snapshot_id=snap.id,
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            status=RepairStatus.SKIPPED,
            old_total_value=old_total_value,
            new_total_value=None,
            reason=reason,
            coverage=coverage,
        )
        _audit_log(result)
        return result

    if dry_run:
        result = RepairResult(
            snapshot_id=snap.id,
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            status=RepairStatus.DRY_RUN,
            old_total_value=old_total_value,
            new_total_value=None,
            reason="Dry run — would repair from holdings_json + yfinance history",
            coverage=coverage,
        )
        _audit_log(result)
        return result

    # ── Recalculate all NAV fields from holdings_json + historical prices ─────
    cash = float(snap.cash_balance or 0.0)

    repaired_holdings: list[dict] = []
    equity_value = 0.0
    total_cost   = 0.0
    sector_agg: dict[str, float] = {}
    per_holding_comparison: list[dict] = []

    for h in raw_holdings:
        symbol   = h.get("symbol", "")
        shares   = float(h.get("shares") or 0.0)
        avg_cost = float(h.get("avg_cost") or 0.0)
        sector   = h.get("sector") or "Other"
        old_price = h.get("current_price")

        price = price_map.get(symbol)
        mv    = shares * price if price is not None else None
        cost  = shares * avg_cost
        upnl  = (mv - cost) if mv is not None else None

        if mv is not None:
            equity_value += mv
            sector_agg[sector] = sector_agg.get(sector, 0.0) + mv
        total_cost += cost

        repaired_holdings.append({
            "symbol":           symbol,
            "shares":           round(shares, 6),
            "avg_cost":         round(avg_cost, 4),
            "current_price":    round(price, 4) if price is not None else None,
            "market_value":     round(mv, 4) if mv is not None else None,
            "unrealized_pnl":   round(upnl, 4) if upnl is not None else None,
            "unrealized_pnl_pct": (
                round(upnl / cost * 100, 2)
                if (upnl is not None and cost > 0)
                else None
            ),
            "sector":           sector,
            "price_missing":    price is None,
        })

        per_holding_comparison.append({
            "symbol":           symbol,
            "old_price":        old_price,
            "new_price":        round(price, 4) if price is not None else None,
            "old_market_value": h.get("market_value"),
            "new_market_value": round(mv, 4) if mv is not None else None,
        })

    total_value      = equity_value + cash
    unrealized_pnl   = equity_value - total_cost
    unrealized_pnl_pct = (unrealized_pnl / total_cost * 100) if total_cost > 0 else 0.0

    sector_breakdown: dict[str, float] = {
        s: round(val / total_value * 100, 2) if total_value > 0 else 0.0
        for s, val in sector_agg.items()
    }

    # Derive the old equity from the stored per-holding market values so the
    # before/after comparison reflects what was actually in holdings_json, not
    # a derived (total_value − cash) approximation.
    old_equity = sum(float(h.get("market_value") or 0.0) for h in raw_holdings)

    before_after = {
        "equity_before":  round(old_equity, 4),
        "equity_after":   round(equity_value, 4),
        "cash":           round(cash, 4),
        "total_before":   old_total_value,
        "total_after":    round(total_value, 4),
        "holdings":       per_holding_comparison,
    }

    # ── Persist: NAV fields ───────────────────────────────────────────────────
    snap.total_value           = round(total_value, 4)
    snap.total_invested        = round(total_cost, 4)
    snap.unrealized_pnl        = round(unrealized_pnl, 4)
    snap.unrealized_pnl_pct    = round(unrealized_pnl_pct, 4)
    snap.sector_breakdown_json = json.dumps(sector_breakdown)
    snap.holdings_json         = json.dumps(repaired_holdings)
    # holdings_count is the count of positions in holdings_json — unchanged.

    # ── Atomically recalculate return fields against the corrected NAV ────────
    # snap.total_value is the new NAV at this point; _compute_return_fields
    # uses it as curr_nav so the return is coherent with the repaired snapshot.
    try:
        prev_snap = (
            db.query(PortfolioSnapshot)
            .filter(
                PortfolioSnapshot.portfolio_id == portfolio_id,
                PortfolioSnapshot.workspace_id == workspace_id,
                PortfolioSnapshot.snapshot_date < snapshot_date,
            )
            .order_by(PortfolioSnapshot.snapshot_date.desc())
            .first()
        )
        return_vals = _compute_return_fields(db, portfolio_id, prev_snap, snap)
        for f, v in return_vals.items():
            setattr(snap, f, v)
        _log.debug(
            "[REPAIR+RETURNS] portfolio=%d date=%s investment_return_pct=%s",
            portfolio_id, snapshot_date, return_vals.get("investment_return_pct"),
        )
    except Exception:
        _log.exception(
            "[REPAIR WARN] portfolio=%d date=%s return field recalculation failed "
            "— NAV fields updated but return fields unchanged",
            portfolio_id, snapshot_date,
        )

    db.commit()

    # ── Stage R1 runtime consultation (M30.3; read-only shadow, never
    # raises, never affects any value computed above or the RepairResult
    # returned below — runs after commit) ─────────────────────────────────
    try:
        runtime_log = _consult_runtime_for_repair(db, unique_symbols, price_map)
    except Exception as exc:
        _log.warning(
            "runtime consultation failed for repair portfolio=%d date=%s: %s",
            portfolio_id, snapshot_date, exc,
        )
    else:
        for finding in runtime_log.findings:
            _log.warning(
                "runtime consultation finding on repair: check_id=%s category=%s "
                "binding=%s detail=%s",
                finding.check_id, finding.category, finding.binding, finding.detail,
            )

    _log.info(
        "[REPAIR OK] portfolio=%d date=%s "
        "old_nav=%.2f new_nav=%.2f equity_delta=%.2f cash=%.2f coverage=%d/%d",
        portfolio_id, snapshot_date,
        old_total_value or 0.0, total_value,
        equity_value - old_equity, cash,
        successful, total,
    )

    result = RepairResult(
        snapshot_id=snap.id,
        portfolio_id=portfolio_id,
        snapshot_date=snapshot_date,
        status=RepairStatus.REPAIRED,
        old_total_value=old_total_value,
        new_total_value=round(total_value, 4),
        reason=(
            "Repaired from holdings_json + yfinance history; "
            "PortfolioItem not consulted"
        ),
        coverage=coverage,
        before_after=before_after,
    )
    _audit_log(result)
    return result


# ── Public API ────────────────────────────────────────────────────────────────

async def repair_snapshot(
    db: Session,
    snapshot_id: int,
    workspace_id: int,
    dry_run: bool = False,
) -> RepairResult:
    """Repair a single snapshot identified by its primary key.

    Args:
        db: SQLAlchemy session.
        snapshot_id: PortfolioSnapshot.id to repair.
        workspace_id: Owning workspace (for security scoping).
        dry_run: When True, fetch prices and validate but do not write to DB.

    Returns:
        RepairResult describing what happened.
    """
    snap = (
        db.query(PortfolioSnapshot)
        .filter_by(id=snapshot_id, workspace_id=workspace_id)
        .first()
    )
    if snap is None:
        return RepairResult(
            snapshot_id=snapshot_id,
            portfolio_id=0,
            snapshot_date="",
            status=RepairStatus.FAILED,
            old_total_value=None,
            new_total_value=None,
            reason=f"Snapshot {snapshot_id} not found in workspace {workspace_id}",
        )
    return await _repair_one(db, snap, workspace_id, dry_run)


async def repair_snapshot_by_date(
    db: Session,
    portfolio_id: int,
    workspace_id: int,
    snapshot_date: str,
    dry_run: bool = False,
) -> RepairResult:
    """Repair the snapshot for a specific portfolio + date.

    Args:
        db: SQLAlchemy session.
        portfolio_id: Target portfolio.
        workspace_id: Owning workspace.
        snapshot_date: Date string "YYYY-MM-DD".
        dry_run: When True, validate but do not write.

    Returns:
        RepairResult describing what happened.
    """
    snap = (
        db.query(PortfolioSnapshot)
        .filter_by(
            portfolio_id=portfolio_id,
            workspace_id=workspace_id,
            snapshot_date=snapshot_date,
        )
        .first()
    )
    if snap is None:
        return RepairResult(
            snapshot_id=0,
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            status=RepairStatus.FAILED,
            old_total_value=None,
            new_total_value=None,
            reason=f"No snapshot found for portfolio={portfolio_id} date={snapshot_date}",
        )
    return await _repair_one(db, snap, workspace_id, dry_run)


async def repair_snapshots(
    db: Session,
    portfolio_id: int,
    workspace_id: int,
    from_date: str,
    to_date: str,
    dry_run: bool = False,
) -> list[RepairResult]:
    """Repair all snapshots for a portfolio within a date range.

    Snapshots are processed oldest-first.  Each snapshot is repaired
    independently — failure on one does not abort the rest.

    Args:
        db: SQLAlchemy session.
        portfolio_id: Target portfolio.
        workspace_id: Owning workspace.
        from_date: Inclusive start date "YYYY-MM-DD".
        to_date:   Inclusive end date "YYYY-MM-DD".
        dry_run:   When True, validate but do not write.

    Returns:
        List of RepairResult, one per snapshot in the date range.
    """
    snaps = (
        db.query(PortfolioSnapshot)
        .filter(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.workspace_id == workspace_id,
            PortfolioSnapshot.snapshot_date >= from_date,
            PortfolioSnapshot.snapshot_date <= to_date,
        )
        .order_by(PortfolioSnapshot.snapshot_date)
        .all()
    )

    results: list[RepairResult] = []
    for snap in snaps:
        result = await _repair_one(db, snap, workspace_id, dry_run)
        results.append(result)

    # Summary log
    counts = {s: 0 for s in RepairStatus}
    for r in results:
        counts[r.status] += 1
    _log.info(
        "[REPAIR SUMMARY] portfolio=%d from=%s to=%s dry_run=%s "
        "repaired=%d skipped=%d failed=%d dry_run_count=%d not_corrupt=%d",
        portfolio_id, from_date, to_date, dry_run,
        counts[RepairStatus.REPAIRED],
        counts[RepairStatus.SKIPPED],
        counts[RepairStatus.FAILED],
        counts[RepairStatus.DRY_RUN],
        counts[RepairStatus.NOT_CORRUPT],
    )
    return results
