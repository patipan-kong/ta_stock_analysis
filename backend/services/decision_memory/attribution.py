"""attribution.py — Phase 3B.7 structural stub

Brinson-Hood-Beebower (BHB) performance attribution framework.

The three BHB effects decompose excess return (portfolio − benchmark) into:
  1. Allocation Effect  — did over/underweighting the right sectors add value?
  2. Selection Effect   — within each sector, did stock picking beat the sector?
  3. Interaction Effect — cross-term (simultaneous active weight × active return)

Total Alpha = Allocation + Selection + Interaction

Architecture notes
------------------
This module is a **structural stub**.  The mathematical scaffolding is present
so endpoints can return well-typed responses and the DB model is correctly
populated, but the core computations currently return None / placeholder values
until ShadowPortfolioSnapshot history accumulates enough data points and
benchmark sector returns are available.

To complete this stub:
  1. Populate BenchmarkPrice with sector-level benchmark returns (e.g. SET
     sector ETFs or MSCI sub-indices).
  2. Replace the _sector_benchmark_return() stubs with real lookups.
  3. Call compute_attribution() from the daily scheduler after enough history.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, date
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ─── BHB core (structural stub) ───────────────────────────────────────────────

def _sector_benchmark_return(sector: str, start: str, end: str, db: Session) -> float | None:
    """Return the benchmark return for a sector over [start, end].

    STUB: returns None until sector-level benchmark prices are available.
    Replace with BenchmarkPrice lookups keyed by sector ETF symbol.
    """
    return None


def _portfolio_sector_return(
    snapshots: list[dict],
    sector: str,
    start: str,
    end: str,
) -> float | None:
    """Compute the average return of holdings in `sector` from shadow snapshots.

    STUB: requires holdings_json with sector tagging per holding.
    """
    return None


def compute_attribution(
    db: Session,
    shadow_portfolio_id: int,
    start: str,
    end: str,
    benchmark_symbol: str = "^GSPC",
) -> dict[str, Any]:
    """Compute BHB attribution for a shadow portfolio over a date range.

    Returns a dict suitable for storing in AttributionMetric.attribution_breakdown_json.
    All numeric fields are None until enough data and sector benchmarks exist.
    """
    from models.database import ShadowPortfolio, ShadowPortfolioSnapshot, AttributionMetric

    shadow = db.query(ShadowPortfolio).filter_by(id=shadow_portfolio_id).first()
    if not shadow:
        return {"error": "shadow_not_found"}

    snaps = (
        db.query(ShadowPortfolioSnapshot)
        .filter(
            ShadowPortfolioSnapshot.shadow_portfolio_id == shadow_portfolio_id,
            ShadowPortfolioSnapshot.snapshot_date >= start,
            ShadowPortfolioSnapshot.snapshot_date <= end,
        )
        .order_by(ShadowPortfolioSnapshot.snapshot_date)
        .all()
    )

    if len(snaps) < 2:
        return {
            "status": "insufficient_data",
            "required": "≥2 daily snapshots in the evaluation window",
            "available": len(snaps),
        }

    first_snap, last_snap = snaps[0], snaps[-1]

    portfolio_return: float | None = None
    if first_snap.total_value and first_snap.total_value != 0:
        portfolio_return = round(
            (last_snap.total_value - first_snap.total_value) / first_snap.total_value * 100, 4
        )

    benchmark_return = last_snap.benchmark_return_pct  # cumulative benchmark return

    # BHB sector decomposition — stub returns None per sector until sector data available
    breakdown: dict[str, dict] = {}
    # Example structure (populated when sector data is ready):
    # {
    #   "Technology": {
    #     "portfolio_weight": 35.0,      # avg weight in shadow
    #     "benchmark_weight": 28.0,      # avg benchmark sector weight
    #     "portfolio_return": 12.5,      # shadow sector return
    #     "benchmark_return": 9.0,       # sector benchmark return
    #     "allocation_effect": 0.21,     # (pw - bw) * br_sector
    #     "selection_effect": 0.875,     # bw * (pr - br_sector)
    #     "interaction_effect": 0.245,   # (pw - bw) * (pr - br_sector)
    #   }
    # }

    selection_alpha = None
    allocation_alpha = None
    interaction_effect = None
    total_alpha = None

    if portfolio_return is not None and benchmark_return is not None:
        total_alpha = round(portfolio_return - benchmark_return, 4)

    result = {
        "status": "stub_computed",
        "evaluation_period_start": start,
        "evaluation_period_end": end,
        "portfolio_return": portfolio_return,
        "benchmark_return": benchmark_return,
        "selection_alpha": selection_alpha,
        "allocation_alpha": allocation_alpha,
        "interaction_effect": interaction_effect,
        "total_alpha": total_alpha,
        "breakdown_by_sector": breakdown,
        "note": "BHB sector decomposition requires per-sector benchmark data (stub).",
    }

    try:
        existing = (
            db.query(AttributionMetric)
            .filter_by(
                shadow_portfolio_id=shadow_portfolio_id,
                evaluation_period_start=start,
                evaluation_period_end=end,
            )
            .first()
        )
        if existing:
            existing.portfolio_return = portfolio_return
            existing.benchmark_return = benchmark_return
            existing.total_alpha = total_alpha
            existing.attribution_breakdown_json = json.dumps(result, default=str)
            existing.computed_at = datetime.utcnow()
        else:
            db.add(AttributionMetric(
                workspace_id=shadow.workspace_id,
                shadow_portfolio_id=shadow_portfolio_id,
                evaluation_period_start=start,
                evaluation_period_end=end,
                portfolio_return=portfolio_return,
                benchmark_return=benchmark_return,
                selection_alpha=selection_alpha,
                allocation_alpha=allocation_alpha,
                interaction_effect=interaction_effect,
                total_alpha=total_alpha,
                attribution_breakdown_json=json.dumps(result, default=str),
                computed_at=datetime.utcnow(),
            ))
        db.commit()
    except Exception as exc:
        logger.warning("[ATTRIBUTION] DB write failed: %s", exc)
        db.rollback()

    return result


def get_attribution_summary(db: Session, shadow_portfolio_id: int) -> list[dict]:
    """Return all AttributionMetric rows for a shadow portfolio as dicts."""
    from models.database import AttributionMetric

    rows = (
        db.query(AttributionMetric)
        .filter_by(shadow_portfolio_id=shadow_portfolio_id)
        .order_by(AttributionMetric.computed_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "evaluation_period_start": r.evaluation_period_start,
            "evaluation_period_end": r.evaluation_period_end,
            "portfolio_return": r.portfolio_return,
            "benchmark_return": r.benchmark_return,
            "selection_alpha": r.selection_alpha,
            "allocation_alpha": r.allocation_alpha,
            "interaction_effect": r.interaction_effect,
            "total_alpha": r.total_alpha,
            "computed_at": r.computed_at.isoformat() + "Z" if r.computed_at else None,
        }
        for r in rows
    ]
