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
import re
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from models.database import Portfolio, PortfolioItem, PortfolioSnapshot, Transaction
from services.data_fetcher import fetch_price_info

# Matches "Realized P&L: +1234.5678" embedded by execute_sell() in tx.notes
_REALIZED_RE = re.compile(r"Realized P&L:\s*([-+]?\d+\.?\d*)")

# Transaction types that are pure cash movements (no equity exchange)
_CASH_INFLOW_TYPES = {"DEPOSIT", "INITIAL_CASH"}
_CASH_OUTFLOW_TYPES = {"WITHDRAW"}

# Equity injections for new positions (portfolio reconstruction / onboarding)
_ASSET_IMPORT_TYPES = {"INITIAL_POSITION"}

# Equity adjustments to existing positions (share-count corrections)
_MANUAL_ADJUSTMENT_TYPES = {"QUANTITY_CORRECTION"}


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

    # ── Cumulative realized P/L from all SELL transactions ────────────────────
    sell_txs = db.query(Transaction).filter(
        Transaction.portfolio_id == portfolio_id,
        Transaction.transaction_type == "SELL",
    ).all()

    realized_pnl = 0.0
    for tx in sell_txs:
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

    # ── Cash-flow-adjusted daily return ──────────────────────────────────────
    # pure_market_gain = today_nav
    #                  - prev_nav
    #                  - net_external_cash_flow     (cash deposits / withdrawals)
    #                  - imported_asset_value       (new-position imports)
    #                  - manual_adjustment_value    (quantity corrections)
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
        "net_deposits": round(net_deposits_amount, 4),
        "net_withdrawals": round(net_withdrawals_amount, 4),
        "holdings_count": len(items),
        "sector_breakdown": sector_breakdown,
        "holdings": holdings,
        "updated": existing is not None,
    }
