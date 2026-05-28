"""Portfolio snapshot generation service.

Computes a point-in-time summary of portfolio value, P/L, sector allocation,
and per-holding breakdown using the latest market prices from yfinance.

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
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models.database import Portfolio, PortfolioItem, PortfolioSnapshot, Transaction
from services.data_fetcher import fetch_price_info

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


async def generate_daily_snapshot(
    db: Session,
    portfolio_id: int,
    workspace_id: int,
    snapshot_date: str | None = None,
) -> dict:
    """Generate (or overwrite) a daily snapshot for the given portfolio.

    Args:
        db: SQLAlchemy session.
        portfolio_id: Target portfolio.
        workspace_id: Owning workspace.
        snapshot_date: Override date string "YYYY-MM-DD". Defaults to today (UTC).

    Returns:
        Dict with all computed snapshot fields.

    Raises:
        ValueError: Portfolio not found.
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

    # ── Fetch latest prices in parallel ───────────────────────────────────────
    if items:
        prices_list = await asyncio.gather(*[
            asyncio.to_thread(fetch_price_info, item.symbol)
            for item in items
        ])
        price_map: dict[str, float] = {
            item.symbol: (p.get("current_price") or item.avg_cost)
            for item, p in zip(items, prices_list)
        }
    else:
        price_map = {}

    # ── Compute holdings breakdown + aggregates ───────────────────────────────
    holdings: list[dict] = []
    equity_value = 0.0
    total_cost = 0.0
    sector_agg: dict[str, float] = {}

    for item in items:
        price = price_map.get(item.symbol, item.avg_cost)
        mv = item.shares * price
        cost = item.shares * item.avg_cost
        upnl = mv - cost
        sector = item.sector or "Other"

        equity_value += mv
        total_cost += cost
        sector_agg[sector] = sector_agg.get(sector, 0.0) + mv

        holdings.append({
            "symbol": item.symbol,
            "shares": round(item.shares, 6),
            "avg_cost": round(item.avg_cost, 4),
            "current_price": round(price, 4),
            "market_value": round(mv, 4),
            "unrealized_pnl": round(upnl, 4),
            "unrealized_pnl_pct": round(upnl / cost * 100, 2) if cost > 0 else 0.0,
            "sector": sector,
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

    if prev:
        prev_day_end = datetime.strptime(prev.snapshot_date, "%Y-%m-%d") + timedelta(days=1)
        today_end = datetime.strptime(today, "%Y-%m-%d") + timedelta(days=1)

        # ── Cash inflows / outflows ────────────────────────────────────────────
        cf_txs = db.query(Transaction).filter(
            Transaction.portfolio_id == portfolio_id,
            Transaction.transaction_type.in_(
                list(_CASH_INFLOW_TYPES | _CASH_OUTFLOW_TYPES)
            ),
            Transaction.created_at >= prev_day_end,
            Transaction.created_at < today_end,
        ).all()

        net_deposits_amount = sum(
            t.total_amount
            for t in cf_txs
            if t.transaction_type in _CASH_INFLOW_TYPES
        )
        net_withdrawals_amount = sum(
            t.total_amount
            for t in cf_txs
            if t.transaction_type in _CASH_OUTFLOW_TYPES
        )
        net_external_cash_flow = net_deposits_amount - net_withdrawals_amount

        # ── Asset imports (INITIAL_POSITION) ──────────────────────────────────
        # New-position imports: strip current market value so the import has
        # exactly zero effect on investment_return_pct.
        import_txs = db.query(Transaction).filter(
            Transaction.portfolio_id == portfolio_id,
            Transaction.transaction_type.in_(list(_ASSET_IMPORT_TYPES)),
            Transaction.created_at >= prev_day_end,
            Transaction.created_at < today_end,
        ).all()

        for tx in import_txs:
            if tx.symbol and tx.shares:
                live_price = price_map.get(tx.symbol, tx.price_per_share or 0.0)
                imported_asset_value += tx.shares * live_price

        # ── Manual quantity corrections (QUANTITY_CORRECTION) ─────────────────
        # Share-count corrections to existing positions are balance-sheet events,
        # not trades.  Strip the same way as asset imports.
        adj_txs = db.query(Transaction).filter(
            Transaction.portfolio_id == portfolio_id,
            Transaction.transaction_type.in_(list(_MANUAL_ADJUSTMENT_TYPES)),
            Transaction.created_at >= prev_day_end,
            Transaction.created_at < today_end,
        ).all()

        for tx in adj_txs:
            if tx.symbol and tx.shares:
                live_price = price_map.get(tx.symbol, tx.price_per_share or 0.0)
                manual_adjustment_value += tx.shares * live_price

        # ── Period realized P/L from SELLs ────────────────────────────────────
        # Realized P&L = (sell_price − avg_cost) × shares − fees.
        # This value is already embedded in investment_return_pct through the
        # cash balance increase from execute_sell(). We compute it here purely
        # for transparency so the UI can show users the trade-level contribution.
        #
        # Important distinction:
        #   period_realized_pnl = TOTAL gain from original cost to sell price
        #   Contribution to today's return = sell_price_delta × shares − fees
        #     where sell_price_delta = sell_price − prev_snapshot_price_of_stock
        # The latter is always smaller when the stock appreciated over multiple days.
        sell_txs_period = db.query(Transaction).filter(
            Transaction.portfolio_id == portfolio_id,
            Transaction.transaction_type == "SELL",
            Transaction.created_at >= prev_day_end,
            Transaction.created_at < today_end,
        ).all()

        for tx in sell_txs_period:
            if tx.notes:
                m = _REALIZED_RE.search(tx.notes)
                if m:
                    period_realized_pnl += float(m.group(1))
            # fees = pre-VAT component; taxes = VAT component (both non-zero for
            # transactions recorded after the broker-fee decomposition upgrade).
            # Historical rows have taxes=0 so fees alone equalled the total — the
            # sum is correct for both old and new records.
            period_fees_paid += (tx.fees or 0.0) + (tx.taxes or 0.0)

        # ── Period dividend income ─────────────────────────────────────────────
        div_txs = db.query(Transaction).filter(
            Transaction.portfolio_id == portfolio_id,
            Transaction.transaction_type == "DIVIDEND",
            Transaction.created_at >= prev_day_end,
            Transaction.created_at < today_end,
        ).all()
        period_dividend_income = sum(tx.total_amount for tx in div_txs)

        # ── Period fees from BUY transactions ─────────────────────────────────
        buy_txs_period = db.query(Transaction).filter(
            Transaction.portfolio_id == portfolio_id,
            Transaction.transaction_type == "BUY",
            Transaction.created_at >= prev_day_end,
            Transaction.created_at < today_end,
        ).all()
        for tx in buy_txs_period:
            period_fees_paid += (tx.fees or 0.0) + (tx.taxes or 0.0)

    # ── Cash-flow-adjusted daily return ──────────────────────────────────────
    # pure_market_gain = today_nav
    #                  - prev_nav
    #                  - net_external_cash_flow     (cash deposits / withdrawals)
    #                  - imported_asset_value       (new-position imports)
    #                  - manual_adjustment_value    (quantity corrections)
    #
    # Realized gains and dividends are NOT stripped — they are market returns.
    # Fees are NOT stripped — they are real costs that drag on performance.
    daily_return_pct: float | None = None
    investment_return_pct: float | None = None
    investment_return_amount: float | None = None

    if prev and prev.total_value and prev.total_value > 0:
        pure_market_gain = (
            total_value
            - prev.total_value
            - net_external_cash_flow
            - imported_asset_value
            - manual_adjustment_value
        )
        investment_return_pct = round(pure_market_gain / prev.total_value * 100, 4)
        investment_return_amount = round(pure_market_gain, 4)
        daily_return_pct = investment_return_pct  # always performance-adjusted

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
