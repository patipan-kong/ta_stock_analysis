"""Portfolio snapshot generation service.

Computes a point-in-time summary of portfolio value, P/L, sector allocation,
and per-holding breakdown using the latest market prices from yfinance.

The actual return-metric formulas (net_external_cash_flow, imported_asset_value,
manual_adjustment_value, investment_return_pct/amount, daily_return_pct,
period_realized_pnl, period_dividend_income, period_fees_paid) live in
services.portfolio_metrics.compute_period_metrics() — the single shared
implementation used by every snapshot-producing engine (ADR-004). This module
remains responsible for window detection (created_at-based — see below),
price fetching, and NAV/holdings construction.

Cash-flow-adjusted return accounting
-------------------------------------
External non-performance events must be stripped from the day-over-day NAV
change before computing daily return.  Without stripping, a 22,000 THB deposit
looks like a +23.95% gain, and importing 1,000 SCB.BK shares looks like a
massive overnight windfall.

Three categories of non-performance inflows are excluded:

  1. net_external_cash_flow — pure cash movements:
       DEPOSIT, WITHDRAW, INITIAL_CASH (onboarding cash)
       Formula: total_deposits - total_withdrawals
       (INITIAL_CASH is treated as an onboarding DEPOSIT)

  2. imported_asset_value — equity capital injections for NEW positions:
       INITIAL_POSITION transactions (portfolio reconstruction / onboarding)
       Value at snapshot time: shares × current_market_price

  3. manual_adjustment_value — equity adjustments to EXISTING positions:
       QUANTITY_CORRECTION transactions (correcting share counts)
       Value at snapshot time: shares × current_market_price

Using current price (not avg_cost) for both (2) and (3) ensures that
unrealised appreciation that pre-dated the import is also excluded.

Corrected return formula (Modified Dietz, simplified for daily periods):
    investment_return_pct =
        (today_nav - prev_nav - net_external_cash_flow
         - imported_asset_value - manual_adjustment_value)
        / prev_nav × 100

Why realized gains are NOT stripped
-------------------------------------
When a SELL executes: equity (shares) leaves the portfolio, cash enters by
exactly the net proceeds (sell_price × shares − fees).  The net effect on
total_value is:

    delta_total_value = net_proceeds − prev_snapshot_equity_value_of_position
                      = (sell_price − prev_close_price) × shares − fees

This is exactly the daily price-appreciation gain from the position — so it
is already the correct performance contribution.  Stripping it would be wrong.

Key corollary: the cumulative `realized_pnl` column (P&L from avg_cost to sell
price, summed across ALL sells ever) is NOT the daily gain.  Most of that gain
was captured in previous snapshots as unrealized appreciation.  The three new
`period_*` columns expose the within-period contribution explicitly.

Period decomposition columns (transparent, informational)
---------------------------------------------------------
  period_realized_pnl    — P&L recorded in SELL transaction notes this period.
                           Already embedded in investment_return_pct; shown
                           separately so users can see the trade contribution.

  period_dividend_income — Cash dividends in this window (DIVIDEND transactions).
                           Also already in investment_return_pct (dividends add
                           to cash_balance and therefore to total_value).

  period_fees_paid       — Total brokerage fees on BUY + SELL trades in this
                           window.  Fees reduce total_value and therefore
                           appear as a drag on investment_return_pct — they are
                           NOT stripped (users pay real fees on real trades).

IMPORTANT — window detection uses Transaction.created_at, NOT transaction_date:
    Users can supply a historical transaction_date when recording an import
    (e.g. backdating to the original purchase date).  If we filtered by
    transaction_date, any backdated import would fall outside the
    prev_snapshot → today window and be silently ignored, causing the full
    NAV delta to appear as investment gain.  created_at is the timestamp when
    the record was physically inserted, which always equals the day the equity
    actually entered the tracked portfolio.

Performance events (excluded from non-performance stripping):
    BUY  — cash leaves portfolio, equity enters: net cash-flow effect = 0
    SELL — equity leaves portfolio, cash enters: net cash-flow effect = 0
    DIVIDEND — income from holdings (increases cash, treated as market-related)

Duplicate prevention: the (portfolio_id, snapshot_date) unique constraint means
calling generate_daily_snapshot twice on the same day updates the existing row
rather than inserting a duplicate.
"""
import asyncio
import json
import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models.database import Portfolio, PortfolioItem, PortfolioSnapshot, Transaction
from services import capability_lookup_service
from services.capability_lookup_service import UnresolvedCapability
from services.capability_safety import grants_dividend_flow, permits_quantity_valuation
from services.data_fetcher import fetch_price_info
from services.portfolio_metrics import compute_period_metrics
from services.runtime_consultation import (
    RuntimeConsultationLog,
    RuntimeFindingCategory,
    RuntimeValidationFinding,
)
from services.transaction_canonicalizer import CanonicalTransaction, canonicalize_transactions

_log = logging.getLogger(__name__)

# Matches "Realized P&L: +1234.5678" embedded by execute_sell() in tx.notes
_REALIZED_RE = re.compile(r"Realized P&L:\s*([-+]?\d+\.?\d*)")

# Transaction types that are pure cash movements (no equity exchange)
_CASH_INFLOW_TYPES = {"DEPOSIT", "INITIAL_CASH"}
_CASH_OUTFLOW_TYPES = {"WITHDRAW"}

# Equity injections for new positions (portfolio reconstruction / onboarding)
_ASSET_IMPORT_TYPES = {"INITIAL_POSITION"}

# Equity adjustments to existing positions (share-count corrections)
_MANUAL_ADJUSTMENT_TYPES = {"QUANTITY_CORRECTION"}

# Warn when single-period |return| exceeds this threshold (likely a data error)
_NAV_JUMP_WARN_PCT = 25.0

# Minimum fraction of holdings that must have live prices for a snapshot to be saved.
# Below this threshold the snapshot is aborted to prevent NAV corruption.
_COVERAGE_THRESHOLD = 0.90


class SnapshotCoverageError(Exception):
    """Raised when market price coverage is too low to produce a valid snapshot.

    Attributes:
        portfolio_id: The portfolio that was being snapshotted.
        date: The snapshot date string ("YYYY-MM-DD").
        total: Total number of holdings.
        successful: Number of holdings with a live price.
        missing: Symbols for which no live price was found.
    """

    def __init__(
        self,
        portfolio_id: int,
        date: str,
        total: int,
        successful: int,
        missing: list[str],
    ) -> None:
        self.portfolio_id = portfolio_id
        self.date = date
        self.total = total
        self.successful = successful
        self.missing = missing
        super().__init__(
            f"Snapshot skipped — portfolio={portfolio_id} date={date} "
            f"coverage={successful}/{total} "
            f"missing={missing}"
        )


# ── Stage R1 runtime consultation (M30.2 brief, third Asset Definition Runtime
# consumer) ─────────────────────────────────────────────────────────────────
#
# Two legacy assumptions in this module have no capability gate today (M29
# audit, SR-1 finding):
#   1. `market_value = shares × price` is computed for every holding with a
#      live price, unconditionally — see the holdings loop below.
#   2. DIVIDEND transactions in the return window are folded into
#      period_dividend_income unconditionally — see compute_period_metrics().
# This function asks the runtime the same two questions Legacy logic already
# answers implicitly, and records any disagreement as a shadow finding —
# mirrors ledger_validator._consult_runtime_capabilities() (M11) and
# asset_registry._consult_runtime_for_mint() (M12) exactly: read-only,
# never raises, never gates, never changes any computed value.
#
# `binding` on each finding is the holding's symbol, not an Asset Definition
# binding spelling — CapabilityView is deliberately anonymous (D5) and does
# not expose the AssetType it was resolved from, so the symbol is the only
# per-holding identifier available to this consumer.
def _consult_runtime_for_snapshot(
    db: Session,
    items: list[PortfolioItem],
    price_map: dict[str, float],
    window_txs: list[CanonicalTransaction],
) -> RuntimeConsultationLog:
    """Never raises — resolve_capability_views() already turns an unminted
    symbol, an undefined asset_type, or a registry boot failure into an
    UnresolvedCapability per symbol rather than an exception; this function
    just turns that into a MISSING_BINDING finding, same as the other two
    Stage R1 consumers.
    """
    dividend_tx_ids_by_symbol: dict[str, list[int]] = defaultdict(list)
    for ctx in window_txs:
        if ctx.transaction_type == "DIVIDEND" and ctx.raw_symbol:
            dividend_tx_ids_by_symbol[ctx.raw_symbol.strip().upper()].append(ctx.id)

    lookup_symbols = sorted({item.symbol.strip().upper() for item in items} | set(dividend_tx_ids_by_symbol))
    if not lookup_symbols:
        return RuntimeConsultationLog(consulted=0, agreements=0, findings=())

    views = capability_lookup_service.resolve_capability_views(db, lookup_symbols)

    findings: list[RuntimeValidationFinding] = []
    consulted  = 0
    agreements = 0

    # ── 1. market_value = shares × price ⇔ runtime permits quantity valuation ──
    for item in items:
        if price_map.get(item.symbol) is None:
            continue  # legacy never computed a shares×price value for this holding
        consulted += 1
        legacy_result = True  # legacy computes market_value = shares × price unconditionally
        view = views[item.symbol.strip().upper()]
        if isinstance(view, UnresolvedCapability):
            findings.append(RuntimeValidationFinding(
                category=RuntimeFindingCategory.MISSING_BINDING.value,
                check_id="RUNTIME_SNAPSHOT_QUANTITY_VALUATION", transaction_ids=(),
                binding=item.symbol, question="permits_quantity_valuation()",
                legacy_result=legacy_result, runtime_result=None, detail=view.reason,
            ))
            continue
        runtime_result = permits_quantity_valuation(view)
        if runtime_result == legacy_result:
            agreements += 1
        else:
            findings.append(RuntimeValidationFinding(
                category=RuntimeFindingCategory.RUNTIME_MISMATCH.value,
                check_id="RUNTIME_SNAPSHOT_QUANTITY_VALUATION", transaction_ids=(),
                binding=item.symbol, question="permits_quantity_valuation()",
                legacy_result=legacy_result, runtime_result=runtime_result,
                detail=(
                    f"snapshot valuation computes market_value = shares × price for "
                    f"{item.symbol!r} unconditionally, but the runtime capability view "
                    "does not permit quantity-based valuation for this asset."
                ),
            ))

    # ── 2. DIVIDEND transaction accepted ⇔ runtime grants FlowType.DIVIDEND ────
    for symbol, tx_ids in dividend_tx_ids_by_symbol.items():
        consulted += 1
        tx_ids_tuple = tuple(tx_ids)
        legacy_result = True  # legacy folds DIVIDEND into period_dividend_income unconditionally
        view = views[symbol]
        if isinstance(view, UnresolvedCapability):
            findings.append(RuntimeValidationFinding(
                category=RuntimeFindingCategory.MISSING_BINDING.value,
                check_id="RUNTIME_SNAPSHOT_DIVIDEND_FLOW", transaction_ids=tx_ids_tuple,
                binding=symbol, question="grants_dividend_flow()",
                legacy_result=legacy_result, runtime_result=None, detail=view.reason,
            ))
            continue
        runtime_result = grants_dividend_flow(view)
        if runtime_result == legacy_result:
            agreements += 1
        else:
            findings.append(RuntimeValidationFinding(
                category=RuntimeFindingCategory.RUNTIME_MISMATCH.value,
                check_id="RUNTIME_SNAPSHOT_DIVIDEND_FLOW", transaction_ids=tx_ids_tuple,
                binding=symbol, question="grants_dividend_flow()",
                legacy_result=legacy_result, runtime_result=runtime_result,
                detail=(
                    f"{len(tx_ids_tuple)} DIVIDEND transaction(s) for {symbol!r} are folded "
                    "into period_dividend_income by legacy replay unconditionally, but the "
                    "runtime capability view does not grant FlowType.DIVIDEND for this asset."
                ),
            ))

    return RuntimeConsultationLog(consulted=consulted, agreements=agreements, findings=tuple(findings))


async def generate_daily_snapshot(
    db: Session,
    portfolio_id: int,
    workspace_id: int,
    snapshot_date: str | None = None,
    price_override: dict[str, float] | None = None,
) -> dict:
    """Generate (or overwrite) a daily snapshot for the given portfolio.

    Args:
        db: SQLAlchemy session.
        portfolio_id: Target portfolio.
        workspace_id: Owning workspace.
        snapshot_date: Override date string "YYYY-MM-DD". Defaults to today (UTC).
        price_override: When provided, use these prices instead of calling
            fetch_price_info. Intended for historical repair where live prices
            are not meaningful (key = symbol, value = closing price for that date).
            Symbols absent from the map are treated as missing (no price available).

    Returns:
        Dict with all computed snapshot fields.

    Raises:
        ValueError: Portfolio not found.
        SnapshotCoverageError: Coverage below 90% threshold.
    """
    today = snapshot_date or datetime.utcnow().strftime("%Y-%m-%d")

    portfolio = db.query(Portfolio).filter_by(
        id=portfolio_id, workspace_id=workspace_id
    ).first()
    if not portfolio:
        raise ValueError(f"Portfolio {portfolio_id} not found")

    items: list[PortfolioItem] = db.query(PortfolioItem).filter_by(
        portfolio_id=portfolio_id
    ).all()
    cash = portfolio.cash_balance or 0.0

    # ── Fetch (or inject) market prices ───────────────────────────────────────
    if items:
        if price_override is not None:
            # Repair / backfill mode: caller already fetched historical prices.
            price_map: dict[str, float] = {}
            failed_symbols: list[str] = []
            for item in items:
                raw_price = price_override.get(item.symbol)
                if raw_price:
                    price_map[item.symbol] = float(raw_price)
                else:
                    failed_symbols.append(item.symbol)
        else:
            prices_list = await asyncio.gather(*[
                asyncio.to_thread(fetch_price_info, item.symbol)
                for item in items
            ])
            price_map = {}
            failed_symbols = []
            for item, p in zip(items, prices_list):
                raw_price = p.get("current_price") if p else None
                if raw_price:
                    price_map[item.symbol] = float(raw_price)
                else:
                    failed_symbols.append(item.symbol)
    else:
        price_map = {}
        failed_symbols = []

    # ── Coverage validation ────────────────────────────────────────────────────
    total_holdings = len(items)
    successful_lookups = total_holdings - len(failed_symbols)
    coverage = successful_lookups / total_holdings if total_holdings > 0 else 1.0

    if total_holdings > 0 and coverage < _COVERAGE_THRESHOLD:
        _log.warning(
            "[SNAPSHOT SKIPPED]\nPortfolio: %d\nCoverage: %d / %d\nMissing:\n%s\nReason:\nMarket cache incomplete",
            portfolio_id,
            successful_lookups,
            total_holdings,
            "\n".join(failed_symbols),
        )
        raise SnapshotCoverageError(
            portfolio_id=portfolio_id,
            date=today,
            total=total_holdings,
            successful=successful_lookups,
            missing=failed_symbols,
        )

    if failed_symbols:
        _log.warning(
            "[SNAPSHOT PARTIAL COVERAGE] portfolio=%d date=%s coverage=%d/%d "
            "missing=%s — proceeding; missing positions excluded from equity",
            portfolio_id,
            today,
            successful_lookups,
            total_holdings,
            ", ".join(failed_symbols),
        )

    # ── Compute holdings breakdown + aggregates ───────────────────────────────
    holdings: list[dict] = []
    equity_value = 0.0
    total_cost = 0.0
    sector_agg: dict[str, float] = {}

    for item in items:
        price: float | None = price_map.get(item.symbol)
        mv: float | None = item.shares * price if price is not None else None
        cost = item.shares * item.avg_cost
        upnl: float | None = (mv - cost) if mv is not None else None
        sector = item.sector or "Other"

        if mv is not None:
            equity_value += mv
            sector_agg[sector] = sector_agg.get(sector, 0.0) + mv
        total_cost += cost

        holdings.append({
            "symbol": item.symbol,
            # M5_TRACK_B_NATIVE_INTEGRATION_TDD.md §4.2: additive-only key.
            # `None` = not yet backfilled (Stage 2); absent entirely on any
            # snapshot row written before this shipped — the two are
            # distinguishable states readers must not conflate.
            "asset_id": item.asset_id,
            "shares": round(item.shares, 6),
            "avg_cost": round(item.avg_cost, 4),
            "current_price": round(price, 4) if price is not None else None,
            "market_value": round(mv, 4) if mv is not None else None,
            "unrealized_pnl": round(upnl, 4) if upnl is not None else None,
            "unrealized_pnl_pct": round(upnl / cost * 100, 2) if (upnl is not None and cost > 0) else None,
            "sector": sector,
            "price_missing": price is None,
        })

    total_value = equity_value + cash
    unrealized_pnl = equity_value - total_cost
    unrealized_pnl_pct = (unrealized_pnl / total_cost * 100) if total_cost > 0 else 0.0

    # ── Sector weights (% of total portfolio value incl. cash) ────────────────
    sector_breakdown: dict[str, float] = {
        sector: round(val / total_value * 100, 2) if total_value > 0 else 0.0
        for sector, val in sector_agg.items()
    }

    # ── Cumulative realized P/L from all SELL transactions (all time) ─────────
    sell_txs_all = db.query(Transaction).filter(
        Transaction.portfolio_id == portfolio_id,
        Transaction.transaction_type == "SELL",
    ).all()

    realized_pnl = 0.0
    for tx in sell_txs_all:
        if tx.notes:
            m = _REALIZED_RE.search(tx.notes)
            if m:
                realized_pnl += float(m.group(1))

    # ── Previous snapshot (for day-over-day comparison) ───────────────────────
    prev = (
        db.query(PortfolioSnapshot)
        .filter(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.snapshot_date < today,
        )
        .order_by(PortfolioSnapshot.snapshot_date.desc())
        .first()
    )

    # ── Non-performance inflows since previous snapshot ────────────────────────
    # Window detection uses Transaction.created_at (physical insert time), NOT
    # transaction_date.  Users can supply a historical transaction_date when
    # recording an import; filtering by transaction_date would silently exclude
    # any backdated entry whose stated date falls before prev_snapshot_date.
    # created_at is always the moment the equity actually entered the system.
    #
    # Formulas live in services.portfolio_metrics.compute_period_metrics()
    # (ADR-004 — exactly one implementation of portfolio return calculations,
    # shared across every snapshot-producing engine).
    net_external_cash_flow = 0.0
    net_deposits_amount = 0.0
    net_withdrawals_amount = 0.0
    imported_asset_value = 0.0
    manual_adjustment_value = 0.0

    # ── Period return decomposition ────────────────────────────────────────────
    # These fields break down what drove the period's return for transparency.
    # All three are ALREADY embedded in investment_return_pct through total_value
    # changes — they are NOT stripped from returns.
    period_realized_pnl = 0.0      # P&L from sells (sell_price − avg_cost) × shares − fees
    period_dividend_income = 0.0   # dividends received (pure market income)
    period_fees_paid = 0.0         # brokerage drag from trades

    daily_return_pct: float | None = None
    investment_return_pct: float | None = None
    investment_return_amount: float | None = None

    # Populated inside the `if prev:` block below; stays empty otherwise.
    # Kept in scope afterward only for the Stage R1 shadow consultation —
    # no legacy computation reads it outside that block.
    window_txs: list[CanonicalTransaction] = []

    if prev:
        prev_day_end = datetime.strptime(prev.snapshot_date, "%Y-%m-%d") + timedelta(days=1)
        today_end = datetime.strptime(today, "%Y-%m-%d") + timedelta(days=1)

        window_txs = canonicalize_transactions(
            db.query(Transaction).filter(
                Transaction.portfolio_id == portfolio_id,
                Transaction.transaction_type.in_(list(
                    _CASH_INFLOW_TYPES | _CASH_OUTFLOW_TYPES | _ASSET_IMPORT_TYPES
                    | _MANUAL_ADJUSTMENT_TYPES | {"SELL", "BUY", "DIVIDEND"}
                )),
                Transaction.created_at >= prev_day_end,
                Transaction.created_at < today_end,
            ).all()
        )

        # CanonicalTransaction.raw_symbol is always .strip().upper()'d, but
        # price_map is keyed by item.symbol as stored — normalize the lookup
        # so symbol casing/whitespace differences can't silently break the
        # price match (price_map itself is left untouched; it's also used by
        # the holdings valuation loop above, keyed by the raw item.symbol).
        normalized_price_lookup = {
            sym.strip().upper(): price for sym, price in price_map.items()
        }

        metrics = compute_period_metrics(
            curr_nav=total_value,
            prev_nav=prev.total_value,
            period_transactions=window_txs,
            price_lookup=normalized_price_lookup,
        )

        # net_deposits_amount / net_withdrawals_amount are returned to API
        # callers as a breakdown of net_external_cash_flow — not part of
        # compute_period_metrics()'s output (which only returns the net),
        # so derive them directly from the same already-fetched window_txs.
        net_deposits_amount = sum(
            float(ctx.total_amount) for ctx in window_txs
            if ctx.transaction_type in _CASH_INFLOW_TYPES
        )
        net_withdrawals_amount = sum(
            float(ctx.total_amount) for ctx in window_txs
            if ctx.transaction_type in _CASH_OUTFLOW_TYPES
        )

        net_external_cash_flow  = metrics.net_external_cash_flow or 0.0
        imported_asset_value    = metrics.imported_asset_value or 0.0
        manual_adjustment_value = metrics.manual_adjustment_value or 0.0
        period_realized_pnl     = metrics.period_realized_pnl or 0.0
        period_dividend_income  = metrics.period_dividend_income or 0.0
        period_fees_paid        = metrics.period_fees_paid or 0.0
        investment_return_pct    = metrics.investment_return_pct
        investment_return_amount = metrics.investment_return_amount
        daily_return_pct         = metrics.daily_return_pct

    # ── Diagnostic logging ────────────────────────────────────────────────────
    prev_nav = prev.total_value if prev else None
    _log.info(
        "[SNAPSHOT] portfolio=%d date=%s "
        "prev_nav=%s curr_nav=%.4f "
        "external_flows=%.4f imports=%.4f adj=%.4f "
        "period_realized=%.4f period_dividends=%.4f period_fees=%.4f "
        "investment_return=%s%%",
        portfolio_id, today,
        f"{prev_nav:.4f}" if prev_nav is not None else "none",
        total_value,
        net_external_cash_flow, imported_asset_value, manual_adjustment_value,
        period_realized_pnl, period_dividend_income, period_fees_paid,
        f"{investment_return_pct:.4f}" if investment_return_pct is not None else "n/a",
    )

    # ── NAV validation ────────────────────────────────────────────────────────
    if prev and prev.total_value and prev.total_value > 0 and investment_return_pct is not None:
        abs_return = abs(investment_return_pct)
        if abs_return > _NAV_JUMP_WARN_PCT:
            _log.warning(
                "[SNAPSHOT VALIDATION] portfolio=%d date=%s "
                "suspicious investment_return=%.2f%% (>%.0f%% threshold) "
                "prev_nav=%.2f curr_nav=%.2f "
                "external_flows=%.2f imports=%.2f adj=%.2f — "
                "check for missing external-flow strips",
                portfolio_id, today,
                investment_return_pct, _NAV_JUMP_WARN_PCT,
                prev.total_value, total_value,
                net_external_cash_flow, imported_asset_value, manual_adjustment_value,
            )

        # Inform when realized P/L greatly exceeds daily return (expected, but
        # helps users understand the "why is my return only X% when I realized Y?" question)
        if (
            period_realized_pnl > 0
            and investment_return_amount is not None
            and period_realized_pnl > abs(investment_return_amount) * 2
        ):
            _log.info(
                "[SNAPSHOT ACCOUNTING] portfolio=%d date=%s "
                "period_realized_pnl=%.2f >> investment_return_amount=%.2f — "
                "most of the realized gain was captured in prior snapshots as "
                "unrealized appreciation; today's return reflects only the "
                "price movement since the previous snapshot",
                portfolio_id, today,
                period_realized_pnl, investment_return_amount,
            )

    # ── NAV reconciliation ───────────────────────────────────────────────────
    # Invariant: cash + equity_value must equal total_value (always true by
    # construction, but logged so the audit trail is explicit in server logs).
    _computed_nav = equity_value + cash
    _nav_delta = abs(_computed_nav - total_value)
    if _nav_delta > 0.01:
        _log.error(
            "[NAV RECONCILIATION FAILED] portfolio=%d date=%s "
            "cash=%.4f equity=%.4f computed_nav=%.4f stored_nav=%.4f delta=%.6f — "
            "total_value formula is broken; investigate immediately",
            portfolio_id, today,
            cash, equity_value, _computed_nav, total_value, _nav_delta,
        )
    elif total_value < 0:
        _log.warning(
            "[NAV NEGATIVE] portfolio=%d date=%s total_value=%.4f — "
            "portfolio is net-negative (leveraged or fee-distorted)",
            portfolio_id, today, total_value,
        )
    else:
        _log.debug(
            "[NAV RECONCILIATION OK] portfolio=%d date=%s "
            "cash=%.4f + equity=%.4f = nav=%.4f",
            portfolio_id, today, cash, equity_value, total_value,
        )

    # ── Stage R1 runtime consultation (M30.2; read-only shadow, never raises,
    # never affects any value computed above or the dict returned below) ──────
    try:
        runtime_log = _consult_runtime_for_snapshot(db, items, price_map, window_txs)
    except Exception as exc:
        _log.warning(
            "runtime consultation failed for snapshot portfolio=%d date=%s: %s",
            portfolio_id, today, exc,
        )
    else:
        for finding in runtime_log.findings:
            _log.warning(
                "runtime consultation finding on snapshot: check_id=%s category=%s "
                "binding=%s detail=%s",
                finding.check_id, finding.category, finding.binding, finding.detail,
            )

    # ── Upsert snapshot row ───────────────────────────────────────────────────
    existing = db.query(PortfolioSnapshot).filter_by(
        portfolio_id=portfolio_id, snapshot_date=today
    ).first()

    snap_data = dict(
        total_value=round(total_value, 4),
        cash_balance=round(cash, 4),
        total_invested=round(total_cost, 4),
        unrealized_pnl=round(unrealized_pnl, 4),
        unrealized_pnl_pct=round(unrealized_pnl_pct, 4),
        realized_pnl=round(realized_pnl, 4),
        daily_return_pct=daily_return_pct,
        net_external_cash_flow=round(net_external_cash_flow, 4) if net_external_cash_flow else None,
        investment_return_pct=investment_return_pct,
        investment_return_amount=investment_return_amount,
        imported_asset_value=round(imported_asset_value, 4) if imported_asset_value else None,
        manual_adjustment_value=round(manual_adjustment_value, 4) if manual_adjustment_value else None,
        period_realized_pnl=round(period_realized_pnl, 4) if period_realized_pnl else None,
        period_dividend_income=round(period_dividend_income, 4) if period_dividend_income else None,
        period_fees_paid=round(period_fees_paid, 4) if period_fees_paid else None,
        sector_breakdown_json=json.dumps(sector_breakdown),
        holdings_json=json.dumps(holdings),
        holdings_count=len(items),
    )

    if existing:
        for k, v in snap_data.items():
            setattr(existing, k, v)
    else:
        db.add(PortfolioSnapshot(
            workspace_id=workspace_id,
            portfolio_id=portfolio_id,
            snapshot_date=today,
            **snap_data,
        ))

    db.commit()

    return {
        "snapshot_date": today,
        "portfolio_id": portfolio_id,
        "total_value": snap_data["total_value"],
        "cash_balance": snap_data["cash_balance"],
        "equity_value": round(equity_value, 4),
        "total_invested": snap_data["total_invested"],
        "unrealized_pnl": snap_data["unrealized_pnl"],
        "unrealized_pnl_pct": snap_data["unrealized_pnl_pct"],
        "realized_pnl": snap_data["realized_pnl"],
        "daily_return_pct": daily_return_pct,
        "net_external_cash_flow": snap_data["net_external_cash_flow"],
        "investment_return_pct": investment_return_pct,
        "investment_return_amount": investment_return_amount,
        "imported_asset_value": snap_data["imported_asset_value"],
        "manual_adjustment_value": snap_data["manual_adjustment_value"],
        "period_realized_pnl": snap_data["period_realized_pnl"],
        "period_dividend_income": snap_data["period_dividend_income"],
        "period_fees_paid": snap_data["period_fees_paid"],
        "net_deposits": round(net_deposits_amount, 4),
        "net_withdrawals": round(net_withdrawals_amount, 4),
        "holdings_count": len(items),
        "sector_breakdown": sector_breakdown,
        "holdings": holdings,
        "updated": existing is not None,
    }
