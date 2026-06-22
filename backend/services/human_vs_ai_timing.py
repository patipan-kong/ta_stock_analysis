"""Phase 4C.6E — Human vs AI Timing Attribution.

For each UserExecutionDecision, computes how much value the human's choice
added or destroyed versus what the AI's STATIC_FROZEN shadow portfolio would
have returned over the same allocation period.

No AI calls.  No new tables.  No migrations.  Attribution analytics only.

Override definition:
  REJECTED / MANUAL_OVERRIDE / PARTIAL_EXECUTION  → override = True
  APPROVED                                         → override = False

Public API
----------
build_human_vs_ai_timing(portfolio_id, workspace_id, db)
    -> tuple[list[OverrideAttribution], HumanVsAISummary]

evaluate_override(decision_type, symbol, ai_action, rs_id,
                  portfolio_snaps, shadow_snaps)
    -> OverrideAttribution          (pure, testable without DB)

build_override_summary(attributions)
    -> HumanVsAISummary             (pure)
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session


# ── Response models ───────────────────────────────────────────────────────────

class OverrideAttribution(BaseModel):
    recommendation_snapshot_id: int
    symbol: str
    ai_action: str
    human_action: str
    override: bool
    human_return_pct: Optional[float]
    ai_return_pct: Optional[float]
    delta_return_pct: Optional[float]
    human_drawdown_pct: Optional[float]
    ai_drawdown_pct: Optional[float]
    saved_drawdown_pct: Optional[float]
    outcome: str


class HumanVsAISummary(BaseModel):
    overrides: int
    good_overrides: int
    bad_overrides: int
    neutral_overrides: int
    override_win_rate: float
    total_added_return_pct: float
    total_saved_drawdown_pct: float


_OVERRIDE_DECISIONS = {"REJECTED", "MANUAL_OVERRIDE", "PARTIAL_EXECUTION"}


# ── Top-level builder (loads DB data then delegates to pure evaluators) ───────

def build_human_vs_ai_timing(
    portfolio_id: int,
    workspace_id: int,
    db: Session,
) -> tuple[list[OverrideAttribution], HumanVsAISummary]:
    """Load all decisions + performance data, then evaluate overrides."""
    from models.database import (
        PortfolioSnapshot, RecommendationSnapshot,
        ShadowPortfolio, ShadowPortfolioSnapshot, UserExecutionDecision,
    )
    from services.timing_periods import build_allocation_periods
    import json as _json

    # Allocation periods for period boundary lookup
    periods = build_allocation_periods(portfolio_id, workspace_id, db)
    period_by_rs_id = {p.recommendation_snapshot_id: p for p in periods}

    # All decisions for this portfolio, sorted by execution time
    decisions = (
        db.query(UserExecutionDecision)
        .filter(
            UserExecutionDecision.portfolio_id == portfolio_id,
            UserExecutionDecision.workspace_id == workspace_id,
        )
        .order_by(UserExecutionDecision.executed_at.asc())
        .all()
    )
    if not decisions:
        return [], build_override_summary([])

    today_str = date.today().isoformat()
    first_date = min(
        _date_str(p.start_date) for p in periods
    ) if periods else today_str

    # Bulk-load all portfolio snapshots (avoids N+1)
    all_port_snaps = (
        db.query(PortfolioSnapshot)
        .filter(
            PortfolioSnapshot.portfolio_id == portfolio_id,
            PortfolioSnapshot.workspace_id == workspace_id,
            PortfolioSnapshot.snapshot_date >= first_date,
            PortfolioSnapshot.snapshot_date <= today_str,
        )
        .order_by(PortfolioSnapshot.snapshot_date.asc())
        .all()
    )

    # Load shadow snapshots per decision's STATIC_FROZEN shadow
    shadow_snaps_by_decision: dict[int, list] = {}
    for d in decisions:
        shadow = (
            db.query(ShadowPortfolio)
            .filter(
                ShadowPortfolio.execution_decision_id == d.id,
                ShadowPortfolio.shadow_type == "STATIC_FROZEN",
            )
            .first()
        )
        if shadow:
            snaps = (
                db.query(ShadowPortfolioSnapshot)
                .filter(
                    ShadowPortfolioSnapshot.shadow_portfolio_id == shadow.id,
                    ShadowPortfolioSnapshot.snapshot_date >= first_date,
                    ShadowPortfolioSnapshot.snapshot_date <= today_str,
                )
                .order_by(ShadowPortfolioSnapshot.snapshot_date.asc())
                .all()
            )
            shadow_snaps_by_decision[d.id] = snaps

    # Build one attribution record per decision
    results: list[OverrideAttribution] = []
    for d in decisions:
        period = period_by_rs_id.get(d.recommendation_snapshot_id)
        if period is None:
            continue  # decision has no matching allocation period

        start_str = _date_str(period.start_date)
        end_str = _date_str(period.end_date) if period.end_date is not None else today_str

        port_window = [
            s for s in all_port_snaps
            if start_str <= _snap_date(s) <= end_str
        ]
        shadow_window = [
            s for s in shadow_snaps_by_decision.get(d.id, [])
            if start_str <= _snap_date(s) <= end_str
        ]

        # Derive symbol label and AI action from the linked RecommendationSnapshot
        rs = db.query(RecommendationSnapshot).filter_by(
            id=d.recommendation_snapshot_id
        ).first()
        symbol = _extract_symbol(d, rs, _json)
        ai_action = _extract_ai_action(rs, _json)

        results.append(evaluate_override(
            decision_type=d.decision,
            symbol=symbol,
            ai_action=ai_action,
            rs_id=d.recommendation_snapshot_id,
            portfolio_snaps=port_window,
            shadow_snaps=shadow_window,
        ))

    return results, build_override_summary(results)


# ── Pure evaluator (testable without DB) ─────────────────────────────────────

def evaluate_override(
    decision_type: str,
    symbol: str,
    ai_action: str,
    rs_id: int,
    portfolio_snaps: list,
    shadow_snaps: list,
) -> OverrideAttribution:
    """Compute attribution for a single decision.

    Args:
        portfolio_snaps: PortfolioSnapshot ORM rows or plain dicts in period window
        shadow_snaps:    ShadowPortfolioSnapshot rows or plain dicts (may be empty)
    """
    is_override = decision_type.upper() in _OVERRIDE_DECISIONS

    human_return = _twr(portfolio_snaps, return_field="investment_return_pct",
                        fallback_field="daily_return_pct")
    ai_return = _twr(shadow_snaps, return_field="daily_return_pct",
                     fallback_field="daily_return_pct")

    delta = _subtract(human_return, ai_return)

    human_dd = _max_drawdown(portfolio_snaps)
    ai_dd = _max_drawdown(shadow_snaps)
    saved_dd = _subtract(ai_dd, human_dd)  # positive = human avoided more drawdown

    outcome = _classify_outcome(delta, is_override)

    return OverrideAttribution(
        recommendation_snapshot_id=rs_id,
        symbol=symbol,
        ai_action=ai_action,
        human_action=decision_type,
        override=is_override,
        human_return_pct=human_return,
        ai_return_pct=ai_return,
        delta_return_pct=delta,
        human_drawdown_pct=human_dd,
        ai_drawdown_pct=ai_dd,
        saved_drawdown_pct=saved_dd,
        outcome=outcome,
    )


def build_override_summary(attributions: list[OverrideAttribution]) -> HumanVsAISummary:
    """Aggregate override statistics across all attribution records."""
    override_rows = [a for a in attributions if a.override]

    good = sum(1 for a in override_rows if a.outcome == "GOOD_OVERRIDE")
    bad = sum(1 for a in override_rows if a.outcome == "BAD_OVERRIDE")
    neutral = sum(1 for a in override_rows if a.outcome == "NEUTRAL_OVERRIDE")
    total = len(override_rows)

    win_rate = round(good / total * 100, 1) if total > 0 else 0.0

    added_return = sum(
        a.delta_return_pct for a in override_rows if a.delta_return_pct is not None
    )
    saved_drawdown = sum(
        a.saved_drawdown_pct for a in override_rows if a.saved_drawdown_pct is not None
    )

    return HumanVsAISummary(
        overrides=total,
        good_overrides=good,
        bad_overrides=bad,
        neutral_overrides=neutral,
        override_win_rate=win_rate,
        total_added_return_pct=round(added_return, 4),
        total_saved_drawdown_pct=round(saved_drawdown, 4),
    )


# ── Metric helpers ────────────────────────────────────────────────────────────

def _twr(snaps: list, return_field: str, fallback_field: str) -> float | None:
    returns: list[float] = []
    for s in snaps:
        r = _attr(s, return_field) or _attr(s, fallback_field)
        if r is not None:
            returns.append(float(r))
    if not returns:
        return None
    product = 1.0
    for r in returns:
        product *= (1.0 + r / 100.0)
    return round((product - 1.0) * 100.0, 4)


def _max_drawdown(snaps: list) -> float | None:
    values = [
        float(v) for s in snaps
        if (v := _attr(s, "total_value")) is not None and float(v) > 0
    ]
    if len(values) < 2:
        return None
    peak = values[0]
    max_dd = 0.0
    for v in values[1:]:
        if v > peak:
            peak = v
        else:
            dd = (peak - v) / peak * 100.0
            if dd > max_dd:
                max_dd = dd
    return round(max_dd, 4) if max_dd > 0 else None


def _classify_outcome(delta: float | None, is_override: bool) -> str:
    if not is_override:
        return "NOT_OVERRIDE"
    if delta is None:
        return "UNKNOWN"
    if abs(delta) < 0.25:
        return "NEUTRAL_OVERRIDE"
    return "GOOD_OVERRIDE" if delta > 0 else "BAD_OVERRIDE"


def _subtract(a: float | None, b: float | None) -> float | None:
    if a is None or b is None:
        return None
    return round(a - b, 4)


# ── Data extraction helpers ───────────────────────────────────────────────────

def _extract_ai_action(rs, json_mod) -> str:
    if rs is None or not rs.consensus_json:
        return "UNKNOWN"
    try:
        c = json_mod.loads(rs.consensus_json)
        return c.get("consensus_decision") or c.get("consensus_type") or "REBALANCE"
    except Exception:
        return "UNKNOWN"


def _extract_symbol(decision, rs, json_mod) -> str:
    """Best-effort symbol label for this decision.

    Uses rejected_symbols first (most specific), then falls back to 'PORTFOLIO'.
    """
    if decision.rejected_symbols_json:
        try:
            syms = json_mod.loads(decision.rejected_symbols_json)
            if syms:
                return syms[0] if len(syms) == 1 else f"{syms[0]}+{len(syms)-1}more"
        except Exception:
            pass
    return "PORTFOLIO"


# ── Date helpers ──────────────────────────────────────────────────────────────

def _date_str(dt: datetime) -> str:
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt.strftime("%Y-%m-%d")


def _snap_date(snap) -> str:
    v = snap.snapshot_date if hasattr(snap, "snapshot_date") else snap["snapshot_date"]
    return str(v)[:10]


def _attr(obj, name: str):
    if hasattr(obj, name):
        return getattr(obj, name)
    return obj.get(name) if isinstance(obj, dict) else None
