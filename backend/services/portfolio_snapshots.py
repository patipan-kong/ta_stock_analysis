"""Portfolio snapshot generation service.

Computes a point-in-time summary of portfolio value, P/L, sector allocation,
and per-holding breakdown using the latest market prices from yfinance.

Duplicate prevention: the (portfolio_id, snapshot_date) unique constraint means
calling generate_daily_snapshot twice on the same day updates the existing row
rather than inserting a duplicate.
"""
import asyncio
import json
import re
from datetime import datetime

from sqlalchemy.orm import Session

from models.database import Portfolio, PortfolioItem, PortfolioSnapshot, Transaction
from services.data_fetcher import fetch_price_info

# Matches "Realized P&L: +1234.5678" embedded by execute_sell() in tx.notes
_REALIZED_RE = re.compile(r"Realized P&L:\s*([-+]?\d+\.?\d*)")


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

    # ── Daily return vs. previous snapshot ────────────────────────────────────
    prev = (
        db.query(PortfolioSnapshot)
        .filter(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.snapshot_date < today,
        )
        .order_by(PortfolioSnapshot.snapshot_date.desc())
        .first()
    )

    daily_return_pct: float | None = None
    if prev and prev.total_value and prev.total_value > 0:
        daily_return_pct = round(
            (total_value - prev.total_value) / prev.total_value * 100, 4
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
        "holdings_count": len(items),
        "sector_breakdown": sector_breakdown,
        "holdings": holdings,
        "updated": existing is not None,
    }
