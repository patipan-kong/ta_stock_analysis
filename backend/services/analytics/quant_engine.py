"""
Quantitative analytics engine — pure pandas/numpy, no AI.

Five analytics groups:
  A. Portfolio Return Analytics  — cumulative/annualised return, drawdown, Sharpe, volatility
  B. Benchmark Comparison        — alpha, beta, tracking error, information ratio
  C. Signal Analytics            — buy win-rate, sell accuracy, holding return, signal decay
  D. Allocation Analytics        — sector contribution, top/worst contributors, cash idle, HHI
  E. Chart data helpers          — equity curve, rolling returns, sector evolution

All public ``build_*`` functions accept SQLAlchemy ORM row lists and return typed
dicts ready for JSON serialisation.  Low-level per-metric functions are also
exported so callers can compose custom responses.

Analytics Cache
---------------
An in-process TTL cache (15 minutes) keyed by (portfolio_id, group).
Call ``invalidate_cache(portfolio_id)`` after any mutation that changes portfolio
history (new transaction, new snapshot, new signal).
"""
from __future__ import annotations

import json
import logging
import math
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

# ── In-process analytics cache (15-minute TTL) ────────────────────────────────
_CACHE: dict[str, tuple[dict, float]] = {}
_CACHE_TTL: int = 900  # seconds


def _cache_key(portfolio_id: int, group: str) -> str:
    return f"{portfolio_id}:{group}"


def get_cached(portfolio_id: int, group: str) -> dict | None:
    """Return cached result if still fresh, else None."""
    entry = _CACHE.get(_cache_key(portfolio_id, group))
    if entry and entry[1] > time.monotonic():
        return entry[0]
    return None


def set_cached(portfolio_id: int, group: str, result: dict) -> None:
    _CACHE[_cache_key(portfolio_id, group)] = (result, time.monotonic() + _CACHE_TTL)


def invalidate_cache(portfolio_id: int) -> None:
    """Remove all cached analytics results for a portfolio."""
    for group in ("portfolio", "benchmark", "signal", "allocation", "full"):
        _CACHE.pop(_cache_key(portfolio_id, group), None)


def invalidate_all() -> None:
    """Flush the entire analytics cache (e.g. after bulk data import)."""
    _CACHE.clear()


# ── Internal helpers ──────────────────────────────────────────────────────────

def _snap_to_df(snapshots: list) -> pd.DataFrame:
    """Convert PortfolioSnapshot ORM rows → sorted date-indexed DataFrame."""
    if not snapshots:
        return pd.DataFrame()
    rows = []
    for s in snapshots:
        date_str = s.snapshot_date if isinstance(s.snapshot_date, str) else str(s.snapshot_date)
        rows.append({
            "date": date_str,
            "total_value": float(s.total_value or 0.0),
            "cash_balance": float(s.cash_balance or 0.0),
            "total_invested": float(s.total_invested or 0.0),
            "daily_return_pct": float(s.daily_return_pct) if s.daily_return_pct is not None else None,
            "sector_breakdown": json.loads(s.sector_breakdown_json) if s.sector_breakdown_json else {},
            "holdings": json.loads(s.holdings_json) if s.holdings_json else [],
        })
    return pd.DataFrame(rows).sort_values("date").reset_index(drop=True)


def _daily_returns(df: pd.DataFrame) -> pd.Series:
    """Decimal daily-return Series.  Prefers stored daily_return_pct; falls back to pct_change."""
    if "daily_return_pct" in df.columns:
        stored = df["daily_return_pct"].dropna()
        if len(stored) >= 2:
            return (stored / 100.0).replace([np.inf, -np.inf], np.nan).dropna()
    return df["total_value"].pct_change().dropna().replace([np.inf, -np.inf], np.nan).dropna()


def _r(val: float | None, n: int = 4) -> float | None:
    """Safe round — returns None for NaN/inf."""
    if val is None:
        return None
    fval = float(val)
    if math.isnan(fval) or math.isinf(fval):
        return None
    return round(fval, n)


# ═══════════════════════════════════════════════════════════════════════════════
# A. PORTFOLIO RETURN ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_cumulative_return(snapshots: list) -> float | None:
    """Total % return from the first to the last snapshot."""
    df = _snap_to_df(snapshots)
    if len(df) < 2:
        return None
    first, last = df.iloc[0]["total_value"], df.iloc[-1]["total_value"]
    return None if first <= 0 else _r((last - first) / first * 100, 2)


def calculate_annualized_return(snapshots: list) -> float | None:
    """CAGR (%) — compound annual growth rate across the snapshot range."""
    df = _snap_to_df(snapshots)
    if len(df) < 2:
        return None
    first, last = df.iloc[0]["total_value"], df.iloc[-1]["total_value"]
    if first <= 0:
        return None
    days = (
        datetime.fromisoformat(df.iloc[-1]["date"])
        - datetime.fromisoformat(df.iloc[0]["date"])
    ).days
    if days < 1:
        return None
    return _r(((last / first) ** (365.25 / days) - 1.0) * 100, 2)


def calculate_max_drawdown(snapshots: list) -> dict:
    """Maximum peak-to-trough drawdown with peak/trough/recovery dates and duration."""
    _empty: dict = {
        "max_drawdown_pct": None,
        "peak_date": None,
        "trough_date": None,
        "recovery_date": None,
        "duration_days": None,
    }
    df = _snap_to_df(snapshots)
    if len(df) < 2:
        return _empty

    values = df["total_value"].values
    dates = df["date"].values

    peak_idx = 0
    max_dd = 0.0
    best_peak = 0
    best_trough = 0

    for i in range(1, len(values)):
        if values[i] >= values[peak_idx]:
            peak_idx = i
        dd = (values[peak_idx] - values[i]) / values[peak_idx] if values[peak_idx] > 0 else 0.0
        if dd > max_dd:
            max_dd = dd
            best_peak, best_trough = peak_idx, i

    if max_dd == 0.0:
        return _empty

    peak_date = str(dates[best_peak])
    trough_date = str(dates[best_trough])
    peak_value = values[best_peak]

    recovery_date: str | None = None
    for i in range(best_trough + 1, len(values)):
        if values[i] >= peak_value:
            recovery_date = str(dates[i])
            break

    end_for_duration = recovery_date or trough_date
    duration_days = (
        datetime.fromisoformat(end_for_duration) - datetime.fromisoformat(peak_date)
    ).days

    return {
        "max_drawdown_pct": _r(-max_dd * 100, 2),
        "peak_date": peak_date,
        "trough_date": trough_date,
        "recovery_date": recovery_date,
        "duration_days": duration_days,
    }


def calculate_volatility(snapshots: list) -> float | None:
    """Annualized daily-return volatility (%), assuming 252 trading days/year."""
    df = _snap_to_df(snapshots)
    if len(df) < 3:
        return None
    dr = _daily_returns(df)
    if len(dr) < 3:
        return None
    return _r(float(dr.std()) * math.sqrt(252) * 100, 2)


def calculate_sharpe_ratio(
    snapshots: list,
    risk_free_rate: float = 0.025,
) -> float | None:
    """Annualized Sharpe ratio.  risk_free_rate is annual (default 2.5%)."""
    df = _snap_to_df(snapshots)
    if len(df) < 3:
        return None
    dr = _daily_returns(df)
    if len(dr) < 3:
        return None
    ann_ret = float(dr.mean()) * 252
    ann_vol = float(dr.std()) * math.sqrt(252)
    if ann_vol <= 0:
        return None
    return _r((ann_ret - risk_free_rate) / ann_vol, 3)


def calculate_monthly_win_rate(snapshots: list) -> dict:
    """Fraction of calendar months with a positive total return."""
    _empty_mwr: dict = {
        "win_rate": None,
        "wins": 0,
        "losses": 0,
        "total_months": 0,
        "monthly_returns": [],
    }
    df = _snap_to_df(snapshots)
    if len(df) < 2:
        return _empty_mwr

    df = df.copy()
    df["month"] = df["date"].str[:7]

    # First and last portfolio value per month
    monthly_first = df.groupby("month")["total_value"].first()
    monthly_last = df.groupby("month")["total_value"].last()
    monthly = pd.DataFrame({"first": monthly_first, "last": monthly_last}).reset_index()
    monthly = monthly[monthly["first"] > 0].copy()
    monthly["return_pct"] = (monthly["last"] - monthly["first"]) / monthly["first"] * 100

    wins = int((monthly["return_pct"] > 0).sum())
    losses = int((monthly["return_pct"] <= 0).sum())
    total = wins + losses

    return {
        "win_rate": _r(wins / total * 100, 1) if total > 0 else None,
        "wins": wins,
        "losses": losses,
        "total_months": total,
        "monthly_returns": [
            {"month": str(row["month"]), "return_pct": _r(row["return_pct"], 2)}
            for _, row in monthly.iterrows()
        ],
    }


def build_portfolio_metrics(snapshots: list) -> dict:
    """All portfolio return metrics combined."""
    if not snapshots:
        return {
            "cumulative_return_pct": None,
            "annualized_return_pct": None,
            "volatility_pct": None,
            "sharpe_ratio": None,
            "max_drawdown": {
                "max_drawdown_pct": None,
                "peak_date": None,
                "trough_date": None,
                "recovery_date": None,
                "duration_days": None,
            },
            "monthly_win_rate": {
                "win_rate": None,
                "wins": 0,
                "losses": 0,
                "total_months": 0,
                "monthly_returns": [],
            },
            "snapshot_count": 0,
            "date_range": {"from": None, "to": None},
        }

    sorted_snaps = sorted(snapshots, key=lambda s: s.snapshot_date)
    return {
        "cumulative_return_pct": calculate_cumulative_return(sorted_snaps),
        "annualized_return_pct": calculate_annualized_return(sorted_snaps),
        "volatility_pct": calculate_volatility(sorted_snaps),
        "sharpe_ratio": calculate_sharpe_ratio(sorted_snaps),
        "max_drawdown": calculate_max_drawdown(sorted_snaps),
        "monthly_win_rate": calculate_monthly_win_rate(sorted_snaps),
        "snapshot_count": len(sorted_snaps),
        "date_range": {
            "from": sorted_snaps[0].snapshot_date,
            "to": sorted_snaps[-1].snapshot_date,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# B. BENCHMARK COMPARISON ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════

def _align_series(
    portfolio_df: pd.DataFrame,
    bench_price_map: dict[str, float],
) -> tuple[pd.Series, pd.Series]:
    """Align portfolio and benchmark daily-return Series on matching dates."""
    bench_rows = sorted(bench_price_map.items())
    bench_df = pd.DataFrame(bench_rows, columns=["date", "price"])
    bench_df["bench_ret"] = bench_df["price"].pct_change()

    port_ret = _daily_returns(portfolio_df)
    # daily_returns drops the first row, so dates align from index 1 onward
    port_dates = portfolio_df.iloc[1 : len(port_ret) + 1]["date"].values
    port_df = pd.DataFrame({"date": port_dates, "port_ret": port_ret.values})

    merged = (
        pd.merge(port_df, bench_df[["date", "bench_ret"]], on="date", how="inner")
        .replace([np.inf, -np.inf], np.nan)
        .dropna()
    )
    return merged["port_ret"], merged["bench_ret"]


def _assess_data_quality(
    aligned_days: int,
    alpha: float | None,
    beta: float | None,
    r_squared: float | None,
    tracking_error_pct: float | None,
) -> dict:
    """Return data_quality, statistical_confidence, sample_size, and warnings for one benchmark.

    Quality tiers:
        aligned_days < 20   → INSUFFICIENT / UNRELIABLE
        20 <= days < 60     → LOW / LOW          + LOW_SAMPLE_SIZE warning
        60 <= days < 252    → MODERATE / MODERATE
        days >= 252         → GOOD / HIGH

    Additional reliability flags:
        UNRELIABLE_REGRESSION — |alpha| > 100% and r² < 0.1 (regression is noise-driven)
        SUSPECT_ALPHA         — |alpha| > 50% and r² < 0.05
        NEAR_ZERO_TE          — tracking error < 0.1%, makes IR unreliable
    """
    warnings: list[str] = []

    if aligned_days < 20:
        data_quality = "INSUFFICIENT"
        confidence = "UNRELIABLE"
        warnings.append("LOW_SAMPLE_SIZE")
    elif aligned_days < 60:
        data_quality = "LOW"
        confidence = "LOW"
        warnings.append("LOW_SAMPLE_SIZE")
    elif aligned_days < 252:
        data_quality = "MODERATE"
        confidence = "MODERATE"
    else:
        data_quality = "GOOD"
        confidence = "HIGH"

    alpha_abs = abs(alpha) if alpha is not None else 0.0
    r_sq = r_squared if r_squared is not None else 1.0

    if alpha_abs > 100.0 and r_sq < 0.1:
        warnings.append("UNRELIABLE_REGRESSION")
        confidence = "UNRELIABLE"
    elif alpha_abs > 50.0 and r_sq < 0.05:
        warnings.append("SUSPECT_ALPHA")
        if confidence == "MODERATE":
            confidence = "LOW"

    if tracking_error_pct is not None and 0.0 < tracking_error_pct < 0.1:
        warnings.append("NEAR_ZERO_TE")

    return {
        "data_quality": data_quality,
        "statistical_confidence": confidence,
        "sample_size": aligned_days,
        "warnings": warnings,
    }


def calculate_alpha_beta(
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series,
) -> dict:
    """OLS beta and annualised alpha (%) from aligned daily-return Series (decimal inputs).

    Both series must be decimal returns (e.g. 0.0129 for a 1.29% day).

    Alpha annualisation uses the correct compound formula:
        daily_alpha  = mean(rp) - beta * mean(rb)          # Jensen's daily intercept
        annual_alpha = ((1 + daily_alpha) ** 252 - 1) * 100

    Simple linear scaling (*252*100) is mathematically equivalent only for near-zero
    daily alphas; it produces extreme anomalies (+1000%+) for any non-trivial daily
    excess return, so it must not be used here.

    Tracking error and information ratio use the standard annualisation:
        TE  = std(active, ddof=1) * sqrt(252) * 100   [%]
        IR  = mean(active) * 252 / (std(active) * sqrt(252))
    These are linear in the mean/std and are correct as-is.
    """
    _empty_ab: dict = {"alpha": None, "beta": None, "r_squared": None, "correlation": None}
    if len(portfolio_returns) < 10:
        return _empty_ab

    rp = portfolio_returns.values.astype(float)
    rb = benchmark_returns.values.astype(float)

    var_rb = float(np.var(rb, ddof=1))
    if var_rb <= 0:
        return _empty_ab

    cov_matrix = np.cov(rp, rb, ddof=1)
    beta = float(cov_matrix[0, 1] / var_rb)

    # OLS intercept — Jensen's daily alpha (decimal)
    daily_alpha = float(np.mean(rp) - beta * np.mean(rb))

    # Compound annualisation: ((1 + r_daily)^252 - 1) * 100
    # Guard against pathological daily_alpha ≤ -1 (total loss per day).
    if daily_alpha > -1.0:
        alpha = ((1.0 + daily_alpha) ** 252 - 1.0) * 100.0
    else:
        alpha = -100.0  # total-loss edge case

    y_pred = beta * rb + (float(np.mean(rp)) - beta * float(np.mean(rb)))
    ss_res = float(np.sum((rp - y_pred) ** 2))
    ss_tot = float(np.sum((rp - float(np.mean(rp))) ** 2))
    r_squared: float | None = (1.0 - ss_res / ss_tot) if ss_tot > 0 else None

    return {
        "alpha": _r(alpha, 3),
        "beta": _r(beta, 3),
        "r_squared": _r(r_squared, 3),
        "correlation": _r(float(np.corrcoef(rp, rb)[0, 1]), 3),
    }


def calculate_tracking_error(
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series,
) -> float | None:
    """Annualized tracking error (%)."""
    if len(portfolio_returns) < 5:
        return None
    active = portfolio_returns.values - benchmark_returns.values
    return _r(float(np.std(active, ddof=1)) * math.sqrt(252) * 100, 3)


def calculate_information_ratio(
    portfolio_returns: pd.Series,
    benchmark_returns: pd.Series,
) -> float | None:
    """Annualized active return / tracking error."""
    if len(portfolio_returns) < 5:
        return None
    active = portfolio_returns.values - benchmark_returns.values
    ann_active = float(np.mean(active)) * 252
    ann_te = float(np.std(active, ddof=1)) * math.sqrt(252)
    if ann_te <= 0:
        return None
    return _r(ann_active / ann_te, 3)


def build_benchmark_metrics(
    snapshots: list,
    benchmark_prices: dict[str, dict[str, float]],
) -> dict:
    """Benchmark comparison for all provided symbols.

    Args:
        snapshots: Ordered PortfolioSnapshot ORM rows.
        benchmark_prices: {symbol: {date_str: close_price}} mapping.
    """
    portfolio_df = _snap_to_df(snapshots)
    if portfolio_df.empty or len(portfolio_df) < 3:
        return {"benchmarks": [], "error": "insufficient_snapshots"}

    results: list[dict] = []
    for symbol, price_map in benchmark_prices.items():
        if len(price_map) < 3:
            results.append({"symbol": symbol, "error": "insufficient_benchmark_data"})
            continue
        try:
            port_ret, bench_ret = _align_series(portfolio_df, price_map)
            n_aligned = len(port_ret)
            if n_aligned < 5:
                results.append({
                    "symbol": symbol,
                    "error": "insufficient_aligned_data",
                    "aligned_days": n_aligned,
                    "data_quality": "INSUFFICIENT",
                    "statistical_confidence": "UNRELIABLE",
                    "sample_size": n_aligned,
                    "warnings": ["LOW_SAMPLE_SIZE"],
                })
                continue

            ab = calculate_alpha_beta(port_ret, bench_ret)
            te = calculate_tracking_error(port_ret, bench_ret)
            ir = calculate_information_ratio(port_ret, bench_ret)
            quality = _assess_data_quality(
                aligned_days=n_aligned,
                alpha=ab["alpha"],
                beta=ab["beta"],
                r_squared=ab["r_squared"],
                tracking_error_pct=te,
            )
            results.append({
                "symbol": symbol,
                "alpha": ab["alpha"],
                "beta": ab["beta"],
                "r_squared": ab["r_squared"],
                "correlation": ab["correlation"],
                "tracking_error_pct": te,
                "information_ratio": ir,
                "aligned_days": n_aligned,
                **quality,
            })
        except Exception as exc:
            log.warning("quant_engine: benchmark %s failed — %s", symbol, exc)
            results.append({"symbol": symbol, "error": str(exc)})

    return {"benchmarks": results}


# ═══════════════════════════════════════════════════════════════════════════════
# C. SIGNAL ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════

def _snap_value_map(snapshots: list) -> tuple[dict[str, float], list[str]]:
    """Build a {date_str: total_value} dict and a sorted date list from snapshots."""
    m = {
        s.snapshot_date: float(s.total_value or 0.0)
        for s in snapshots
        if (s.total_value or 0) > 0
    }
    return m, sorted(m.keys())


def _value_at_or_after(
    signal_date: str,
    n_days: int,
    value_map: dict[str, float],
    sorted_dates: list[str],
) -> float | None:
    """Portfolio value at the first snapshot on or after signal_date + n_days."""
    target = (
        datetime.fromisoformat(signal_date) + timedelta(days=n_days)
    ).strftime("%Y-%m-%d")
    for d in sorted_dates:
        if d >= target:
            return value_map.get(d)
    return None


def calculate_buy_win_rate(
    signals: list,
    snapshots: list,
    n_days: int = 30,
) -> dict:
    """Win rate for BUY/ACCUMULATE signals.  Win = portfolio higher n_days later."""
    _empty: dict = {
        "win_rate": None, "wins": 0, "losses": 0,
        "total": 0, "n_days": n_days, "details": [],
    }
    buy = [s for s in signals if s.action in ("BUY", "ACCUMULATE")]
    if not buy or not snapshots:
        return _empty

    value_map, sorted_dates = _snap_value_map(snapshots)
    wins = losses = 0
    details: list[dict] = []

    for sig in buy:
        sig_date = sig.recorded_at.strftime("%Y-%m-%d") if sig.recorded_at else None
        if not sig_date:
            continue
        v0 = value_map.get(sig_date) or _value_at_or_after(sig_date, 0, value_map, sorted_dates)
        v_n = _value_at_or_after(sig_date, n_days, value_map, sorted_dates)
        if v0 and v_n and v0 > 0:
            ret = (v_n - v0) / v0 * 100
            if ret > 0:
                wins += 1
            else:
                losses += 1
            details.append({
                "symbol": sig.symbol,
                "signal_date": sig_date,
                "action": sig.action,
                "return_pct": _r(ret, 2),
                "win": ret > 0,
            })

    total = wins + losses
    return {
        "win_rate": _r(wins / total * 100, 1) if total > 0 else None,
        "wins": wins,
        "losses": losses,
        "total": total,
        "n_days": n_days,
        "details": details[:20],
    }


def calculate_sell_accuracy(
    signals: list,
    snapshots: list,
    n_days: int = 30,
) -> dict:
    """Accuracy for SELL/REDUCE signals.  Accurate = portfolio lower n_days later."""
    _empty: dict = {
        "accuracy": None, "accurate": 0, "inaccurate": 0,
        "total": 0, "n_days": n_days, "details": [],
    }
    sell = [s for s in signals if s.action in ("SELL", "REDUCE")]
    if not sell or not snapshots:
        return _empty

    value_map, sorted_dates = _snap_value_map(snapshots)
    accurate = inaccurate = 0
    details: list[dict] = []

    for sig in sell:
        sig_date = sig.recorded_at.strftime("%Y-%m-%d") if sig.recorded_at else None
        if not sig_date:
            continue
        v0 = value_map.get(sig_date) or _value_at_or_after(sig_date, 0, value_map, sorted_dates)
        v_n = _value_at_or_after(sig_date, n_days, value_map, sorted_dates)
        if v0 and v_n and v0 > 0:
            ret = (v_n - v0) / v0 * 100
            is_ok = ret < 0  # portfolio declined → sell call was correct
            if is_ok:
                accurate += 1
            else:
                inaccurate += 1
            details.append({
                "symbol": sig.symbol,
                "signal_date": sig_date,
                "action": sig.action,
                "portfolio_return_pct": _r(ret, 2),
                "accurate": is_ok,
            })

    total = accurate + inaccurate
    return {
        "accuracy": _r(accurate / total * 100, 1) if total > 0 else None,
        "accurate": accurate,
        "inaccurate": inaccurate,
        "total": total,
        "n_days": n_days,
        "details": details[:20],
    }


def calculate_average_holding_return(signals: list, snapshots: list) -> dict:
    """Average portfolio return 30 days after any actionable signal."""
    _empty: dict = {
        "avg_return_pct": None, "median_return_pct": None,
        "std_return_pct": None, "sample_size": 0,
    }
    if not signals or not snapshots:
        return _empty

    value_map, sorted_dates = _snap_value_map(snapshots)
    returns: list[float] = []

    for sig in signals:
        sig_date = sig.recorded_at.strftime("%Y-%m-%d") if sig.recorded_at else None
        if not sig_date:
            continue
        v0 = value_map.get(sig_date) or _value_at_or_after(sig_date, 0, value_map, sorted_dates)
        v_n = _value_at_or_after(sig_date, 30, value_map, sorted_dates)
        if v0 and v_n and v0 > 0:
            returns.append((v_n - v0) / v0 * 100)

    if not returns:
        return _empty

    arr = np.array(returns, dtype=float)
    return {
        "avg_return_pct": _r(float(arr.mean()), 2),
        "median_return_pct": _r(float(np.median(arr)), 2),
        "std_return_pct": _r(float(arr.std(ddof=1)) if len(arr) > 1 else 0.0, 2),
        "sample_size": len(returns),
    }


def calculate_signal_decay(
    signals: list,
    snapshots: list,
    buckets: list[int] | None = None,
) -> dict:
    """Average portfolio return at 7d / 30d / 90d buckets after each signal.

    The decay chart shows how predictive power of signals fades over time.
    """
    if buckets is None:
        buckets = [7, 30, 90]
    if not signals or not snapshots:
        return {"buckets": [], "by_action": {}}

    value_map, sorted_dates = _snap_value_map(snapshots)
    by_action: dict[str, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))

    for sig in signals:
        sig_date = sig.recorded_at.strftime("%Y-%m-%d") if sig.recorded_at else None
        if not sig_date:
            continue
        v0 = value_map.get(sig_date) or _value_at_or_after(sig_date, 0, value_map, sorted_dates)
        if not v0 or v0 <= 0:
            continue
        action = sig.action or "UNKNOWN"
        for b in buckets:
            vb = _value_at_or_after(sig_date, b, value_map, sorted_dates)
            if vb:
                by_action[action][b].append((vb - v0) / v0 * 100)

    bucket_summary = []
    for b in buckets:
        all_rets: list[float] = []
        for bd in by_action.values():
            all_rets.extend(bd.get(b, []))
        bucket_summary.append({
            "days": b,
            "avg_return_pct": _r(float(np.mean(all_rets)), 2) if all_rets else None,
            "sample_size": len(all_rets),
        })

    action_breakdown = {
        action: {
            str(b): {
                "avg_return_pct": _r(float(np.mean(rets)), 2) if rets else None,
                "sample_size": len(rets),
            }
            for b, rets in bd.items()
        }
        for action, bd in by_action.items()
    }

    return {"buckets": bucket_summary, "by_action": action_breakdown}


def build_signal_metrics(signals: list, snapshots: list) -> dict:
    """All signal analytics combined."""
    return {
        "buy_win_rate": calculate_buy_win_rate(signals, snapshots, n_days=30),
        "sell_accuracy": calculate_sell_accuracy(signals, snapshots, n_days=30),
        "average_holding_return": calculate_average_holding_return(signals, snapshots),
        "signal_decay": calculate_signal_decay(signals, snapshots, buckets=[7, 30, 90]),
        "total_signals": len(signals),
        "signals_by_action": {
            action: sum(1 for s in signals if s.action == action)
            for action in ("BUY", "SELL", "ACCUMULATE", "REDUCE")
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
# D. ALLOCATION ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_sector_contribution(snapshots: list) -> list[dict]:
    """Each sector's weighted contribution to overall portfolio return.

    Uses a Brinson-style approximation:
    contribution ≈ average_sector_weight × overall_portfolio_return.
    """
    if len(snapshots) < 2:
        return []
    df = _snap_to_df(snapshots)
    if df.empty:
        return []

    first_val = df.iloc[0]["total_value"]
    last_val = df.iloc[-1]["total_value"]
    overall_return = (last_val - first_val) / first_val * 100 if first_val > 0 else 0.0

    sector_weights: dict[str, list[float]] = defaultdict(list)
    for _, row in df.iterrows():
        for sector, weight in row["sector_breakdown"].items():
            sector_weights[sector].append(float(weight))

    contributions = [
        {
            "sector": sector,
            "avg_weight_pct": _r(float(np.mean(weights)), 2),
            "contribution_pct": _r(float(np.mean(weights)) / 100.0 * overall_return, 3),
        }
        for sector, weights in sector_weights.items()
    ]
    return sorted(contributions, key=lambda x: (x["contribution_pct"] or 0.0), reverse=True)


def calculate_top_contributors(snapshots: list) -> dict:
    """Top-5 and worst-5 holdings by unrealized P&L % from the most recent snapshot."""
    _empty: dict = {
        "top_contributors": [],
        "worst_contributors": [],
        "snapshot_date": None,
    }
    if not snapshots:
        return _empty

    for snap in sorted(snapshots, key=lambda s: s.snapshot_date, reverse=True):
        if not snap.holdings_json:
            continue
        try:
            holdings = json.loads(snap.holdings_json)
        except Exception:
            continue
        if not holdings:
            continue

        ranked = sorted(
            holdings,
            key=lambda h: float(h.get("unrealized_pnl_pct") or 0),
            reverse=True,
        )

        def _fmt(h: dict) -> dict:
            return {
                "symbol": h.get("symbol"),
                "unrealized_pnl_pct": h.get("unrealized_pnl_pct"),
                "unrealized_pnl": h.get("unrealized_pnl"),
                "market_value": h.get("market_value"),
                "sector": h.get("sector"),
            }

        return {
            "top_contributors": [_fmt(h) for h in ranked[:5]],
            "worst_contributors": [_fmt(h) for h in ranked[-5:][::-1]],
            "snapshot_date": snap.snapshot_date,
        }

    return _empty


def calculate_cash_utilization(snapshots: list) -> dict:
    """Average / min / max cash idle % across all snapshots."""
    _empty: dict = {
        "avg_cash_pct": None,
        "min_cash_pct": None,
        "max_cash_pct": None,
        "current_cash_pct": None,
    }
    if not snapshots:
        return _empty

    cash_pcts = [
        (s.cash_balance or 0.0) / (s.total_value or 1.0) * 100
        for s in snapshots
        if (s.total_value or 0) > 0
    ]
    if not cash_pcts:
        return _empty

    arr = np.array(cash_pcts, dtype=float)
    return {
        "avg_cash_pct": _r(float(arr.mean()), 2),
        "min_cash_pct": _r(float(arr.min()), 2),
        "max_cash_pct": _r(float(arr.max()), 2),
        "current_cash_pct": _r(cash_pcts[-1], 2),
    }


def calculate_concentration_risk(snapshots: list) -> dict:
    """Herfindahl-Hirschman Index (0–10000) from the most recent snapshot with holdings."""
    _empty: dict = {
        "hhi": None,
        "hhi_label": None,
        "top_holding_weight_pct": None,
    }
    if not snapshots:
        return _empty

    for snap in sorted(snapshots, key=lambda s: s.snapshot_date, reverse=True):
        if not snap.holdings_json:
            continue
        try:
            holdings = json.loads(snap.holdings_json)
        except Exception:
            continue
        if not holdings:
            continue

        total_mv = sum(float(h.get("market_value") or 0) for h in holdings)
        if total_mv <= 0:
            continue

        weights = [float(h.get("market_value") or 0) / total_mv for h in holdings]
        hhi = float(sum(w ** 2 for w in weights) * 10_000)
        top_w = max(weights) * 100

        if hhi < 1500:
            label = "LOW"
        elif hhi < 2500:
            label = "MEDIUM"
        elif hhi < 4000:
            label = "HIGH"
        else:
            label = "CRITICAL"

        return {
            "hhi": _r(hhi, 1),
            "hhi_label": label,
            "top_holding_weight_pct": _r(top_w, 2),
        }

    return _empty


def build_allocation_metrics(snapshots: list) -> dict:
    """All allocation analytics combined."""
    return {
        "sector_contribution": calculate_sector_contribution(snapshots),
        "top_contributors": calculate_top_contributors(snapshots),
        "cash_utilization": calculate_cash_utilization(snapshots),
        "concentration_risk": calculate_concentration_risk(snapshots),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# E. CHART DATA HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

def build_equity_curve(snapshots: list) -> list[dict]:
    """Recharts-ready equity curve.

    Each row: {date, total_value, cumulative_return_pct, drawdown_pct, daily_return_pct}
    """
    df = _snap_to_df(snapshots)
    if df.empty:
        return []

    base = df.iloc[0]["total_value"]
    running_peak = base
    rows: list[dict] = []

    for _, row in df.iterrows():
        tv = row["total_value"]
        running_peak = max(running_peak, tv)
        cum_ret = (tv - base) / base * 100 if base > 0 else 0.0
        drawdown = (tv - running_peak) / running_peak * 100 if running_peak > 0 else 0.0
        rows.append({
            "date": row["date"],
            "total_value": round(tv, 2),
            "cumulative_return_pct": _r(cum_ret, 3),
            "drawdown_pct": _r(drawdown, 3),
            "daily_return_pct": _r(row.get("daily_return_pct"), 3),
        })
    return rows


def build_rolling_returns(snapshots: list, window: int = 30) -> list[dict]:
    """Rolling N-day portfolio return: [{date, rolling_return_pct, window_days}]"""
    df = _snap_to_df(snapshots)
    if len(df) <= window:
        return []

    values = df["total_value"].values
    dates = df["date"].values
    rows: list[dict] = []

    for i in range(window, len(values)):
        v0 = values[i - window]
        if v0 > 0:
            rows.append({
                "date": str(dates[i]),
                "rolling_return_pct": _r((values[i] - v0) / v0 * 100, 3),
                "window_days": window,
            })
    return rows


def build_sector_evolution(snapshots: list) -> list[dict]:
    """Sector allocation over time: [{date, sector_name: weight_pct, ...}]"""
    df = _snap_to_df(snapshots)
    if df.empty:
        return []

    rows: list[dict] = []
    for _, row in df.iterrows():
        entry: dict[str, Any] = {"date": row["date"]}
        for sector, weight in row["sector_breakdown"].items():
            entry[str(sector)] = round(float(weight), 2)
        rows.append(entry)
    return rows
