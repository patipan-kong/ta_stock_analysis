"""ideal_series.py — AI Evaluation M6: friction-free Ideal Portfolio series.

Computes the "Ideal" line of the Three Portfolios comparison
(OPTIMIZER_PHILOSOPHY.md §4/§5; EXECUTION_INTELLIGENCE_UX.md §1.1): what
capital would have returned if every RecommendationSnapshot's target weights
had been followed instantly and exactly — zero fees, zero timing delay, zero
funding constraints.

This is deliberately NOT the ACTIVE_MODEL shadow. That object already exists
(services/decision_memory/shadow_tracker.py) and answers a related but
different question: what has a persisted, stateful, 100%-compliant paper
portfolio accumulated since ITS OWN inception (which may predate, or not
align with, whatever period window a caller asks for). Ideal is instead
recomputed fresh, per request, for the exact requested period — directly
from RecommendationSnapshot.projected_allocations_json and PortfolioSnapshot's
own daily holdings prices (DB-only, never yfinance) — so it is always
reproducible for any window and never depends on ACTIVE_MODEL's own
valuation cadence or historical gaps (Risk R6: the friction-free-return
methodology is defined exactly once, here).

Read-only: never writes to RecommendationSnapshot, ShadowPortfolio, or any
other upstream table (implementation plan §4.1) — produces a plain dict,
persists nothing.

Methodology (documented once — do not re-derive elsewhere, Risk R6):
    1. Find every RecommendationSnapshot for the portfolio with a parseable
       projected_allocations_json, ordered by created_at. The "seed"
       allocation is the latest snapshot at or before the period start (if
       any); every later snapshot inside the window is a rebalance point.
    2. Walk daily prices from PortfolioSnapshot.holdings_json — the same
       DB-only price source shadow_tracker.py's backfill path uses (reused
       via _snapshot_price_history / _price_near_date, never re-derived).
    3. At the seed date, convert target weights to share counts at that
       day's prices (reused _resolve_shares_from_weights, base NAV = 100
       since only relative weights matter). On every later rebalance date,
       value the OLD holdings at the new day's prices, add back the carried-
       forward cash, then instantly re-derive shares + cash for the NEW
       weights at that same NAV — a zero-cost, zero-delay rebalance (the
       same "running_nav" mechanic create_active_model_shadow uses, reused
       conceptually, computed independently here so the result is
       reproducible for any window).
    4. Index the resulting NAV series to 100 at the first date used.

Paper cash accounting (correctness fix, 2026-07-07)
----------------------------------------------------
Target weights intentionally sum to less than 100% (the optimizer's own
cash floor — OPTIMIZER_PHILOSOPHY.md §2 Priority 7, policy_engine.py's
min_cash_pct enforcement). _resolve_shares_from_weights now returns the
unallocated residual as explicit cash, which this replay carries forward
across every rebalance and adds back into the NAV basis of the next one
(cash itself earns zero return between rebalances). Previously the
residual was computed nowhere and stored nowhere — silently deleted from
NAV at every rebalance, compounding multiplicatively across a period's
rebalance history. See docs/DECISION_LOG.md, "Paper Portfolio Cash-Leak
Fix," for the full root-cause analysis and worked example. This fix does
not change Gap A's formula (compute_three_portfolios /
_revalue_ai_portfolio_with_canonical_prices, below, are untouched) — Gap
A's *computed value* changes only insofar as its correctly-fixed inputs
now conserve NAV instead of leaking it.

Status is "insufficient_data" (no snapshot exists at or before the window's
end) or "no_price_history" (no PortfolioSnapshot holdings_json rows at all)
— never a fabricated flat line.

Gap A price-source unification (correctness fix, 2026-07-06)
--------------------------------------------------------------
Gap A (Ideal − AI) must isolate execution friction, not an artifact of two
hypothetical constructs being valued from two different price feeds. Ideal
values holdings from this module's own canonical `_snapshot_price_history`
walk (PortfolioSnapshot.holdings_json daily-close prices). The ACTIVE_MODEL
shadow's persisted ShadowPortfolioSnapshot rows, by contrast, are valued via
shadow_tracker.value_shadow_portfolio's live AgentCache-cache price reads —
a different, independently-sourced observation for the same calendar date,
whose day-over-day noise compounds through TWR chaining. `compute_three_
portfolios` therefore never reads compute_portfolio_attribution's
`ai_model_shadow.return_pct` for Gap A — it revalues the shadow's own
persisted holdings-per-date (`_revalue_ai_portfolio_with_canonical_prices`,
below) through this module's identical canonical price archive first. The
shadow's rebalance *events* (which weights, on which dates) are read as-is
and never altered — only the price used to value them changes. See that
function's docstring for the full analysis.

Rebalance-event-sequence alignment (verified, not a bug)
----------------------------------------------------------
Ideal's rebalance points and the ACTIVE_MODEL shadow's rebalance points are
driven by the identical trigger: main.py's optimizer-run endpoint writes one
RecommendationSnapshot and then calls create_active_model_shadow with that
same snapshot id in the same request (see main.py's analyze_optimizer
handler). The daily scheduler only calls value_all_active_shadows
(valuation, not rebalancing) — it never rebalances ACTIVE_MODEL outside an
optimizer run. So both objects replay the same RecommendationSnapshot
sequence by construction. The one legitimate divergence is that
ACTIVE_MODEL only replays from its own immutable inception_date forward
(Phase 4C.6) while Ideal replays from period_start — expected and already
surfaced via `ai_portfolio.status` / per-row None values in `chart`, not a
correctness defect.

Public API
----------
compute_ideal_series(db, portfolio_id, period_days=90) -> dict
compute_three_portfolios(db, portfolio_id, period_days=90) -> dict
    Aligns Ideal / AI (ACTIVE_MODEL shadow) / Actual / Benchmark onto one
    date axis (indexed to 100) and computes Gap A (Ideal − AI) / Gap B
    (AI − Actual, identical sign convention to
    attribution_engine.compute_portfolio_attribution's regret_score — reused,
    not recomputed, for Gap B specifically).
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def _snapshots_for_window(
    db: Session, portfolio_id: int, period_start: str, period_end: str,
) -> tuple[tuple[str, list[dict]] | None, list[tuple[str, list[dict]]]]:
    """Return (seed, rebalances): seed is the latest snapshot at/before
    period_start (or None); rebalances are later snapshots inside the window,
    each (date, target_allocations), ordered ascending.
    """
    from models.database import RecommendationSnapshot

    rows = (
        db.query(RecommendationSnapshot)
        .filter(
            RecommendationSnapshot.portfolio_id == portfolio_id,
            RecommendationSnapshot.projected_allocations_json.isnot(None),
        )
        .order_by(RecommendationSnapshot.created_at.asc())
        .all()
    )

    parsed: list[tuple[str, list[dict]]] = []
    for r in rows:
        if not r.created_at:
            continue
        try:
            allocs = json.loads(r.projected_allocations_json)
        except Exception:
            continue
        if not allocs:
            continue
        parsed.append((r.created_at.date().isoformat(), allocs))

    seed: tuple[str, list[dict]] | None = None
    rebalances: list[tuple[str, list[dict]]] = []
    for d, allocs in parsed:
        if d <= period_start:
            seed = (d, allocs)  # keep the latest one at/before period_start
        elif d <= period_end:
            rebalances.append((d, allocs))
    return seed, rebalances


def _empty_result(status: str, reason: str, period_start: str, period_end: str) -> dict[str, Any]:
    return {
        "status": status,
        "reason": reason,
        "period_start": period_start,
        "period_end": period_end,
        "series": [],
        "series_start": None,
        "return_pct": None,
        "max_drawdown_pct": None,
        "annualized_volatility": None,
        "rebalance_dates": [],
        "snapshots_used": 0,
    }


def compute_ideal_series(db: Session, portfolio_id: int, period_days: int = 90) -> dict[str, Any]:
    """The friction-free Ideal Portfolio trajectory over the last `period_days`."""
    from services.decision_memory.shadow_tracker import (
        _snapshot_price_history,
        _price_near_date,
        _resolve_shares_from_weights,
        _compute_paper_value,
        assert_nav_conserved,
    )
    from services.analytics.attribution_engine import compute_max_drawdown, _compute_daily_volatility

    period_end = date.today().isoformat()
    period_start = (date.today() - timedelta(days=period_days)).isoformat()

    seed, rebalances = _snapshots_for_window(db, portfolio_id, period_start, period_end)
    if seed is None and not rebalances:
        return _empty_result(
            "insufficient_data", "no_recommendation_snapshot_at_or_before_period",
            period_start, period_end,
        )

    history = _snapshot_price_history(db)
    if not history:
        return _empty_result("no_price_history", "no_portfolio_snapshot_prices_available", period_start, period_end)

    if seed is not None:
        start_date, start_allocs = seed
    else:
        start_date, start_allocs = rebalances[0]
        rebalances = rebalances[1:]

    dates = sorted(d for d in history if start_date <= d <= period_end)
    if not dates:
        return _empty_result(
            "no_price_history", "no_price_dates_on_or_after_first_recommendation",
            period_start, period_end,
        )

    rebalance_map = {d: allocs for d, allocs in rebalances}

    seed_symbols = [a.get("symbol") for a in start_allocs if a.get("symbol")]
    seed_prices = {
        sym: p for sym in seed_symbols
        if (p := _price_near_date(history, start_date, sym))
    }

    # Bootstrap NAV = 100 — only relative weights matter, indexing is trivial.
    # Target weights summing to <100% are the optimizer's intentional cash
    # floor (OPTIMIZER_PHILOSOPHY.md §2 Priority 7) — the residual is carried
    # forward as explicit paper cash, never dropped (docs/DECISION_LOG.md,
    # "Paper Portfolio Cash-Leak Fix").
    holdings, cash = _resolve_shares_from_weights(start_allocs, 100.0, seed_prices)
    deployed_value, _ = _compute_paper_value(holdings, seed_prices)
    assert_nav_conserved(
        label=f"compute_ideal_series seed portfolio_id={portfolio_id} date={start_date}",
        expected_nav=100.0, equity=deployed_value, cash=cash,
    )

    series: list[dict[str, Any]] = []
    values: list[float] = []
    daily_returns: list[float] = []
    last_prices: dict[str, float] = dict(seed_prices)

    for d in dates:
        last_prices.update(history.get(d, {}))

        if d in rebalance_map and d != start_date:
            equity_before, _ = _compute_paper_value(holdings, last_prices)
            nav = equity_before + cash  # carry forward cash, never reset to 0
            if nav <= 0:
                nav = values[-1] if values else 100.0
            new_symbols = [a.get("symbol") for a in rebalance_map[d] if a.get("symbol")]
            for s in new_symbols:
                if s not in last_prices:
                    p = _price_near_date(history, d, s)
                    if p:
                        last_prices[s] = p
            holdings, cash = _resolve_shares_from_weights(rebalance_map[d], nav, last_prices)
            deployed_value, _ = _compute_paper_value(holdings, last_prices)
            assert_nav_conserved(
                label=f"compute_ideal_series rebalance portfolio_id={portfolio_id} date={d}",
                expected_nav=nav, equity=deployed_value, cash=cash,
            )

        total, _ = _compute_paper_value(holdings, last_prices)
        total += cash  # cash earns zero return; carried forward flat between rebalances
        if total <= 0:
            total = values[-1] if values else 100.0

        if values and values[-1] > 0:
            daily_returns.append((total - values[-1]) / values[-1] * 100)
        values.append(total)
        series.append({"date": d, "value": total})

    base = values[0]
    indexed_series = [
        {"date": row["date"], "index": round(row["value"] / base * 100, 4) if base else None}
        for row in series
    ]

    return_pct = round((values[-1] - base) / base * 100, 4) if base else None
    max_dd = compute_max_drawdown(values)
    vol = _compute_daily_volatility(daily_returns)

    return {
        "status": "ok",
        "reason": None,
        "period_start": period_start,
        "period_end": period_end,
        "series": indexed_series,
        "series_start": start_date,
        "return_pct": return_pct,
        "max_drawdown_pct": max_dd,
        "annualized_volatility": vol,
        "rebalance_dates": sorted(rebalance_map.keys()),
        "snapshots_used": 1 + len(rebalance_map),
    }


def _reindex_to_100(
    dated_values: dict[str, float], axis: list[str], rebase: bool = True,
) -> tuple[list[float | None], str | None]:
    """Forward-fill *dated_values* onto *axis*.

    rebase=True (default, ideal/ai/benchmark): re-index to 100 at the first
    axis date with an observation — correct for series that are already
    self-normalized to exactly 100 at their own start (compute_ideal_series,
    _revalue_ai_portfolio_with_canonical_prices), where this is a no-op.

    rebase=False (actual): forward-fill only, values passed through as-is.
    compute_actual_indexed_series's TWR chain is already absolute-scaled
    (its own first value need not be exactly 100 — e.g. it may already
    carry a return earned before the shared axis's first date coincides
    with it); rebasing a second time here would renormalize that value
    back to 100 and silently erase the return it represents (Accounting
    Correctness C5, Issue B).

    Returns (values, base_date); base_date is None when dated_values has no
    observation anywhere on/before the axis, and is unused when rebase=False.
    """
    if not dated_values or not axis:
        return [None] * len(axis), None

    sorted_items = sorted(dated_values.items())
    out: list[float | None] = []
    base_value: float | None = None
    base_date: str | None = None
    last: float | None = None
    idx = 0
    n = len(sorted_items)

    for d in axis:
        while idx < n and sorted_items[idx][0] <= d:
            last = sorted_items[idx][1]
            idx += 1
        if last is None:
            out.append(None)
            continue
        if not rebase:
            out.append(round(last, 4))
            continue
        if base_value is None:
            base_value = last
            base_date = d
        out.append(round(last / base_value * 100, 4) if base_value else None)
    return out, base_date


def _revalue_ai_portfolio_with_canonical_prices(
    db: Session,
    portfolio_id: int,
    history: dict[str, dict[str, float]],
    period_start: str,
    period_end: str,
) -> dict[str, Any]:
    """Re-derive the ACTIVE_MODEL shadow's NAV series from the identical
    canonical price archive (_snapshot_price_history — PortfolioSnapshot.
    holdings_json, the same source compute_ideal_series uses) instead of its
    persisted total_value/daily_return_pct.

    Root cause this exists to fix: ShadowPortfolioSnapshot rows are normally
    written by shadow_tracker.value_shadow_portfolio, which prices holdings
    via _fetch_cached_prices (AgentCache "technical" live cache, 15-min TTL,
    read at whatever moment the daily valuation job ran) — a different,
    independently-sourced price observation than the once-daily-close prices
    Ideal reads from PortfolioSnapshot.holdings_json. Both nominally trace
    back to yfinance, but at different times of day through different
    caches, so day-over-day deltas (TWR-chained into the persisted
    return_pct_since_inception) can diverge from what Ideal sees for the
    same calendar date — and that divergence compounds daily. This function
    does NOT change what the shadow held or when it rebalanced (its
    persisted holdings_json per date is read as-is, untouched) — only which
    price values those same holdings, so Gap A compares Ideal and AI
    Portfolio at one shared set of price observations.

    This is deliberately scoped to the Three Portfolios / Gap A view only.
    It does not change compute_portfolio_attribution's own ai_model_shadow
    figure, which remains the correct "what has our persisted paper account
    actually returned using its live valuation policy" answer used elsewhere
    (Scorecard, S4, S5, the attribution waterfall) — a legitimately
    different question from "controlling for identical market data, how
    much of the Ideal-vs-AI gap is friction."
    """
    from models.database import ShadowPortfolio, ShadowPortfolioSnapshot
    from services.decision_memory.shadow_tracker import _price_near_date, _compute_paper_value
    from services.analytics.attribution_engine import compute_max_drawdown, _compute_daily_volatility

    shadow = (
        db.query(ShadowPortfolio)
        .filter_by(portfolio_id=portfolio_id, shadow_type="ACTIVE_MODEL", is_active=True)
        .order_by(ShadowPortfolio.created_at.desc())
        .first()
    )
    if not shadow:
        return {"status": "unavailable", "return_pct": None, "max_drawdown_pct": None,
                "annualized_volatility": None, "series": []}

    snaps = (
        db.query(ShadowPortfolioSnapshot)
        .filter(
            ShadowPortfolioSnapshot.shadow_portfolio_id == shadow.id,
            ShadowPortfolioSnapshot.snapshot_date >= period_start,
            ShadowPortfolioSnapshot.snapshot_date <= period_end,
        )
        .order_by(ShadowPortfolioSnapshot.snapshot_date.asc())
        .all()
    )
    if not snaps:
        return {"status": "no_snapshots_in_window", "return_pct": None, "max_drawdown_pct": None,
                "annualized_volatility": None, "series": []}

    cash = shadow.paper_cash_balance or 0.0
    series: list[dict[str, Any]] = []
    values: list[float] = []
    daily_returns: list[float] = []

    for snap in snaps:
        try:
            holdings = json.loads(snap.holdings_json) if snap.holdings_json else []
        except Exception:
            continue
        symbols = [h.get("symbol") for h in holdings if h.get("symbol")]
        canonical_prices = {
            sym: p for sym in symbols
            if (p := _price_near_date(history, snap.snapshot_date, sym))
        }
        total, _ = _compute_paper_value(holdings, canonical_prices)
        total += cash
        if total <= 0:
            continue
        if values and values[-1] > 0:
            daily_returns.append((total - values[-1]) / values[-1] * 100)
        values.append(total)
        series.append({"date": snap.snapshot_date, "value": total})

    if not values:
        return {"status": "no_price_history", "return_pct": None, "max_drawdown_pct": None,
                "annualized_volatility": None, "series": []}

    base = values[0]
    indexed_series = [
        {"date": row["date"], "index": round(row["value"] / base * 100, 4) if base else None}
        for row in series
    ]
    return_pct = round((values[-1] - base) / base * 100, 4) if base else None

    return {
        "status": "ok",
        "return_pct": return_pct,
        "max_drawdown_pct": compute_max_drawdown(values),
        "annualized_volatility": _compute_daily_volatility(daily_returns),
        "series": indexed_series,
    }


def _index_at_or_before(series: list[dict], target_date: str) -> float | None:
    """Nearest indexed value on/before target_date in a [{date, index}]
    series sorted ascending by date; falls back to the first value after
    target_date if nothing precedes it (mirrors _price_near_date)."""
    best: float | None = None
    for row in series:
        d, idx = row.get("date"), row.get("index")
        if d is None or idx is None:
            continue
        if d <= target_date:
            best = idx
        elif best is None:
            return idx
        else:
            break
    return best


def _return_over_window(series: list[dict], start_date: str) -> tuple[float | None, float | None, float | None]:
    """(return_pct, max_drawdown_pct, annualized_volatility) for a
    [{date, index}] series restricted to [start_date, end] — used to align
    Ideal and AI Portfolio to a common comparison window (see
    compute_three_portfolios docstring, "event-sequence alignment")."""
    from services.analytics.attribution_engine import compute_max_drawdown, _compute_daily_volatility

    base = _index_at_or_before(series, start_date)
    tail = [row["index"] for row in series if row.get("date") and row["date"] >= start_date and row.get("index") is not None]
    if base is None or not base or not tail:
        return None, None, None

    values = [base] + tail
    daily_returns = []
    prev = values[0]
    for v in values[1:]:
        if prev:
            daily_returns.append((v - prev) / prev * 100)
        prev = v

    return_pct = round((values[-1] - base) / base * 100, 4)
    return return_pct, compute_max_drawdown(values), _compute_daily_volatility(daily_returns)


def compute_three_portfolios(db: Session, portfolio_id: int, period_days: int = 90) -> dict[str, Any]:
    """Ideal / AI (ACTIVE_MODEL) / Actual / Benchmark, aligned + Gap A/B (UX S7).

    Gap B (AI − Actual) is read from attribution_engine's existing
    `regret_score` (Single Source of Truth, never recomputed a second way
    here) — Actual is a real brokerage account, so comparing it against the
    AI shadow's own official (live-priced) valuation is the correct,
    apples-to-real-world comparison for that gap.

    Gap A (Ideal − AI) is different: both sides are hypothetical, friction-
    free constructs, so a fair comparison requires valuing them from the
    SAME price observations. ai_return here is therefore sourced from
    _revalue_ai_portfolio_with_canonical_prices (see its docstring for the
    price-source root cause), not from compute_portfolio_attribution's
    ai_model_shadow. The aligned chart's "ai" line uses this same canonical
    series for consistency with the Gap A number shown alongside it.

    Event-sequence alignment: Ideal replays every RecommendationSnapshot
    from period_start forward. The ACTIVE_MODEL shadow replays the same
    snapshots (both are driven by the same optimizer-run trigger — see
    module docstring), but only from its own immutable inception_date
    forward, which can postdate period_start by a wide margin (e.g. after
    an admin reset-inception, Phase 4C.6). Comparing a full period_days
    Ideal return against a much-shorter AI Portfolio return would silently
    conflate "different time horizons" with "friction cost." Both sides are
    therefore truncated to their overlap — max(ideal_first_date,
    ai_first_date) through period_end — before return_pct/max_drawdown_pct/
    annualized_volatility are computed for either the ideal/ai_portfolio
    blocks or gap_a below.
    """
    from models.database import BenchmarkPrice
    from services.analytics.attribution_engine import compute_portfolio_attribution, compute_actual_indexed_series
    from services.decision_memory.shadow_tracker import _snapshot_price_history

    cutoff = (date.today() - timedelta(days=period_days)).isoformat()
    today = date.today().isoformat()

    ideal = compute_ideal_series(db, portfolio_id, period_days)
    attribution = compute_portfolio_attribution(db, portfolio_id, period_days)

    actual = attribution.get("actual") or {}

    history = _snapshot_price_history(db)
    ai_canonical = _revalue_ai_portfolio_with_canonical_prices(
        db, portfolio_id, history, ideal["period_start"], ideal["period_end"],
    )

    actual_return = actual.get("return_pct")

    # ── Align Ideal and AI Portfolio to their overlapping window ──────────
    # (see "Event-sequence alignment" in the docstring above)
    ideal_series_list = ideal.get("series") or []
    ai_series_list = ai_canonical.get("series") or []

    if ideal_series_list and ai_series_list:
        comparison_start = max(ideal_series_list[0]["date"], ai_series_list[0]["date"])
    else:
        comparison_start = None

    if comparison_start:
        i_ret, i_dd, i_vol = _return_over_window(ideal_series_list, comparison_start)
        a_ret, a_dd, a_vol = _return_over_window(ai_series_list, comparison_start)
    else:
        i_ret = i_dd = i_vol = a_ret = a_dd = a_vol = None

    ideal_return = i_ret if i_ret is not None else ideal.get("return_pct")
    ideal_max_dd = i_dd if i_dd is not None else ideal.get("max_drawdown_pct")
    ideal_vol = i_vol if i_vol is not None else ideal.get("annualized_volatility")

    ai_return = a_ret if a_ret is not None else ai_canonical.get("return_pct")
    ai_max_dd = a_dd if a_dd is not None else ai_canonical.get("max_drawdown_pct")
    ai_vol = a_vol if a_vol is not None else ai_canonical.get("annualized_volatility")

    gap_a = round(ideal_return - ai_return, 4) if ideal_return is not None and ai_return is not None else None
    gap_b = attribution.get("regret_score")  # AI − Actual, already computed there

    # ── Aligned chart series (display only) ───────────────────────────────
    # Issue B (Accounting Correctness C5): "actual" must be the same
    # cash-flow-adjusted TWR series the summary card's actual.return_pct
    # already uses (attribution.actual, via _actual_portfolio_metrics) —
    # never a raw total_value ratio, which double-counts deposits/
    # withdrawals as investment return. See compute_actual_indexed_series.
    actual_dated = compute_actual_indexed_series(db, portfolio_id, cutoff)

    ai_dated = {
        row["date"]: row["index"] for row in ai_canonical.get("series", []) if row.get("index") is not None
    }

    bench_rows = (
        db.query(BenchmarkPrice.price_date, BenchmarkPrice.close_price)
        .filter(BenchmarkPrice.symbol == "^SET.BK", BenchmarkPrice.price_date >= cutoff)
        .all()
    )
    bench_dated = {d: v for d, v in bench_rows}

    ideal_dated = {row["date"]: row["index"] for row in ideal.get("series", []) if row.get("index") is not None}

    axis = sorted(set(ideal_dated) | set(ai_dated) | set(actual_dated) | set(bench_dated))

    ideal_chart, _ = _reindex_to_100(ideal_dated, axis) if axis else ([], None)
    ai_chart, _ = _reindex_to_100(ai_dated, axis) if axis else ([], None)
    actual_chart, _ = _reindex_to_100(actual_dated, axis, rebase=False) if axis else ([], None)
    bench_chart, _ = _reindex_to_100(bench_dated, axis) if axis else ([], None)

    chart = [
        {
            "date": axis[i],
            "ideal": ideal_chart[i] if i < len(ideal_chart) else None,
            "ai": ai_chart[i] if i < len(ai_chart) else None,
            "actual": actual_chart[i] if i < len(actual_chart) else None,
            "benchmark": bench_chart[i] if i < len(bench_chart) else None,
        }
        for i in range(len(axis))
    ]

    # BenchmarkPrice is a global (not portfolio-scoped) table synced
    # independently of any portfolio's own activity — its presence alone must
    # never flip status to "ok" for a portfolio with no data of its own
    # (would otherwise silently show a cold-start portfolio as "ok").
    has_portfolio_data = bool(ideal_dated) or bool(ai_dated) or bool(actual_dated)
    status = "ok" if has_portfolio_data else "insufficient_data"

    from datetime import datetime as _datetime

    return {
        "portfolio_id": portfolio_id,
        "period_days": period_days,
        "status": status,
        "as_of": _datetime.utcnow().isoformat() + "Z",
        "chart": chart,
        "ideal": {
            "status": ideal.get("status"),
            "return_pct": ideal_return,
            "max_drawdown_pct": ideal_max_dd,
            "annualized_volatility": ideal_vol,
        },
        "ai_portfolio": {
            "status": ai_canonical.get("status"),
            "return_pct": ai_return,
            "max_drawdown_pct": ai_max_dd,
            "annualized_volatility": ai_vol,
        },
        "actual": {
            "status": attribution.get("status"),
            "return_pct": actual_return,
            "max_drawdown_pct": actual.get("max_drawdown_pct"),
            "annualized_volatility": actual.get("annualized_volatility"),
        },
        "gap_a": {"value": gap_a, "label": "Ideal − AI"},
        "gap_b": {"value": gap_b, "label": "AI − You"},
    }
