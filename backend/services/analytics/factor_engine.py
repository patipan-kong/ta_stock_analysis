"""Institutional-grade factor exposure analysis engine — pure pandas/numpy, no AI.

Computes 5 portfolio-level factor exposures using percentile-rank normalization
across the current portfolio universe.  Cross-market bias (Thai SET vs US stocks)
is eliminated because all normalization is relative within the portfolio itself.

Factor definitions
──────────────────
  Growth    — revenue growth (50%) + earnings growth (50%)
  Value     — inverse P/E (50%) + inverse P/B (30%) + inverse EV/EBITDA (20%)
  Dividend  — yield (70%) + payout-ratio optimality (30%)
  Momentum  — 30-day return (40%) + 90-day return (20%) + MA alignment (30%) + RSI (10%)
  Quality   — ROE (40%) + net margin (40%) + inverse D/E leverage (20%)

All sub-metrics are percentile-ranked within the universe before aggregation.
Missing metrics are excluded and weights redistributed proportionally.

Entry point
───────────
  compute_portfolio_factor_exposure(db, portfolio_id, workspace_id) -> dict

Result is cached for 15 minutes in the shared quant_engine in-process cache.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np

from models.database import Portfolio, PortfolioItem
from services.data_fetcher import (
    fetch_info,
    fetch_history,
    fetch_price_info,
    normalize_dr_symbol,
    is_dr_symbol,
)
from services.analytics.quant_engine import get_cached, set_cached

log = logging.getLogger(__name__)
_CACHE_GROUP = "factor"


# ─────────────────────────────────────────────────────────────────────────────
# Data containers
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class RawMetrics:
    """Per-stock un-normalised factor inputs."""
    symbol: str
    sector: str | None = None
    weight: float = 0.0            # current portfolio weight 0-1

    # Growth
    revenue_growth: float | None = None    # e.g. 0.12 = 12%
    earnings_growth: float | None = None

    # Value (lower is better → inverted before ranking)
    pe_ratio: float | None = None
    price_to_book: float | None = None
    ev_ebitda: float | None = None

    # Dividend
    dividend_yield: float | None = None    # e.g. 0.032 = 3.2%
    payout_ratio: float | None = None      # e.g. 0.45 = 45%

    # Momentum
    return_30d: float | None = None        # fraction
    return_90d: float | None = None
    ma_alignment: float | None = None      # -1 (bearish) … +1 (bullish)
    rsi_14: float | None = None            # 0-100

    # Quality
    roe: float | None = None               # fraction
    net_margin: float | None = None        # fraction
    debt_equity: float | None = None       # raw (e.g. 150 = D/E of 1.5)

    # Metadata
    data_coverage: float = 0.0            # fraction of 13 metrics that are non-None


@dataclass
class NormalizedScores:
    """Per-stock percentile-ranked factor scores (0–100)."""
    symbol: str
    weight: float = 0.0
    growth: float | None = None
    value: float | None = None
    dividend: float | None = None
    momentum: float | None = None
    quality: float | None = None
    data_coverage: float = 0.0


# ─────────────────────────────────────────────────────────────────────────────
# Low-level helpers
# ─────────────────────────────────────────────────────────────────────────────

def _safe(v: Any) -> float | None:
    """Return float or None; reject NaN/inf/zero-division sentinels."""
    if v is None:
        return None
    try:
        f = float(v)
        return None if (math.isnan(f) or math.isinf(f)) else f
    except (TypeError, ValueError):
        return None


def _pct_rank(universe: list[float | None], target: float | None) -> float | None:
    """Percentile rank of target within the universe [0, 100].

    Uses the midpoint formula so ties each get (rank ± 0.5) treatment.
    Returns None if target is None or the universe has < 2 valid values.
    """
    if target is None:
        return None
    clean = [v for v in universe if v is not None]
    if len(clean) < 2:
        # With a single-stock universe every metric is at the 50th percentile.
        return 50.0 if len(clean) == 1 else None
    below = sum(1 for v in clean if v < target)
    equal = sum(1 for v in clean if v == target)
    return round((below + 0.5 * equal) / len(clean) * 100, 1)


def _weighted_factor(
    scores: list[float | None],
    base_weights: list[float],
) -> float | None:
    """Weighted average that skips None values and redistributes weights.

    scores and base_weights must have the same length.
    Returns None if no score is available.
    """
    total_w = 0.0
    total_s = 0.0
    for s, w in zip(scores, base_weights):
        if s is not None:
            total_w += w
            total_s += s * w
    if total_w <= 0:
        return None
    return round(total_s / total_w, 1)


def _r(v: float | None, n: int = 2) -> float | None:
    if v is None:
        return None
    return round(v, n)


# ─────────────────────────────────────────────────────────────────────────────
# Data gathering
# ─────────────────────────────────────────────────────────────────────────────

def _gather_info(symbol: str) -> dict:
    """Fetch yfinance .info for a symbol, resolving DR symbols automatically."""
    yf_sym = normalize_dr_symbol(symbol)
    return fetch_info(yf_sym)


def _gather_momentum(symbol: str) -> dict:
    """Compute momentum metrics from 3-month daily price history.

    Returns dict with: return_30d, return_90d, ma_alignment, rsi_14.
    All values are None if history is unavailable.
    """
    result: dict[str, float | None] = {
        "return_30d":   None,
        "return_90d":   None,
        "ma_alignment": None,
        "rsi_14":       None,
    }
    yf_sym = normalize_dr_symbol(symbol)
    df = fetch_history(yf_sym, period="3mo", interval="1d")
    if df is None or df.empty or "Close" not in df.columns:
        return result

    closes = df["Close"].dropna()
    n = len(closes)
    if n < 5:
        return result

    # Price returns
    last_price = float(closes.iloc[-1])
    if n >= 30:
        price_30 = float(closes.iloc[-30])
        if price_30 > 0:
            result["return_30d"] = _safe((last_price - price_30) / price_30)
    if n >= 60:
        price_60 = float(closes.iloc[-60])
        if price_60 > 0:
            result["return_90d"] = _safe((last_price - price_60) / price_60)
    elif n >= 2:
        # Fallback: full-history return if < 60 bars
        price_0 = float(closes.iloc[0])
        if price_0 > 0:
            result["return_90d"] = _safe((last_price - price_0) / price_0)

    # MA alignment: compare price vs EMA20 and EMA50
    try:
        ema20 = float(closes.ewm(span=20, adjust=False).mean().iloc[-1])
        alignment = 0.0
        if last_price > ema20:
            alignment += 0.5
        if n >= 50:
            ema50 = float(closes.ewm(span=50, adjust=False).mean().iloc[-1])
            if last_price > ema50:
                alignment += 0.5
        elif n >= 30:
            ema30 = float(closes.ewm(span=30, adjust=False).mean().iloc[-1])
            if last_price > ema30:
                alignment += 0.5
        result["ma_alignment"] = alignment - 0.5  # -0.5…+0.5 then scaled to -1…+1
        result["ma_alignment"] = _safe(result["ma_alignment"] * 2)  # → -1..+1
    except Exception:
        pass

    # RSI(14)
    try:
        if n >= 15:
            delta = closes.diff().dropna()
            gain = delta.clip(lower=0)
            loss = (-delta).clip(lower=0)
            avg_gain = gain.ewm(com=13, adjust=False).mean()
            avg_loss = loss.ewm(com=13, adjust=False).mean()
            last_gain = float(avg_gain.iloc[-1])
            last_loss = float(avg_loss.iloc[-1])
            if last_loss > 0:
                rs = last_gain / last_loss
                result["rsi_14"] = _safe(100 - 100 / (1 + rs))
            else:
                result["rsi_14"] = 100.0
    except Exception:
        pass

    return result


def _extract_raw_metrics(
    symbol: str,
    sector: str | None,
    weight: float,
    info: dict,
    momentum: dict,
) -> RawMetrics:
    """Build a RawMetrics record from yfinance info + momentum dict."""

    def g(key: str) -> float | None:
        return _safe(info.get(key))

    pe = g("trailingPE") or g("forwardPE")
    # Reject negative or absurdly high P/E (>1000) as they corrupt value scoring
    if pe is not None and (pe <= 0 or pe > 1000):
        pe = None

    pb = g("priceToBook")
    if pb is not None and (pb <= 0 or pb > 500):
        pb = None

    ev_ebitda = g("enterpriseToEbitda")
    if ev_ebitda is not None and (ev_ebitda <= 0 or ev_ebitda > 500):
        ev_ebitda = None

    roe = g("returnOnEquity")
    # Clamp extreme ROE values (leveraged companies can show 300%+)
    if roe is not None:
        roe = max(-2.0, min(roe, 5.0))

    de = g("debtToEquity")
    if de is not None and de < 0:
        de = None    # negative D/E is accounting artifact

    div_yield = g("dividendYield")
    if div_yield is not None and (div_yield < 0 or div_yield > 1.0):
        div_yield = None  # reject obviously wrong values

    payout = g("payoutRatio")
    if payout is not None and (payout < 0 or payout > 5.0):
        payout = None

    # Revenue / earnings growth: yfinance returns decimals (0.12 = 12%)
    rev_growth = g("revenueGrowth")
    earn_growth = g("earningsGrowth") or g("earningsQuarterlyGrowth")

    net_margin = g("profitMargins")

    raw = RawMetrics(
        symbol=symbol,
        sector=sector,
        weight=weight,
        revenue_growth=rev_growth,
        earnings_growth=earn_growth,
        pe_ratio=pe,
        price_to_book=pb,
        ev_ebitda=ev_ebitda,
        dividend_yield=div_yield,
        payout_ratio=payout,
        return_30d=momentum.get("return_30d"),
        return_90d=momentum.get("return_90d"),
        ma_alignment=momentum.get("ma_alignment"),
        rsi_14=momentum.get("rsi_14"),
        roe=roe,
        net_margin=net_margin,
        debt_equity=de,
    )

    # Data coverage: fraction of 13 primary metrics that are non-None
    _METRICS = [
        raw.revenue_growth, raw.earnings_growth,
        raw.pe_ratio, raw.price_to_book,
        raw.dividend_yield, raw.payout_ratio,
        raw.return_30d, raw.ma_alignment, raw.rsi_14,
        raw.roe, raw.net_margin, raw.debt_equity,
        raw.ev_ebitda,
    ]
    raw.data_coverage = round(sum(1 for m in _METRICS if m is not None) / len(_METRICS), 3)
    return raw


# ─────────────────────────────────────────────────────────────────────────────
# Normalization
# ─────────────────────────────────────────────────────────────────────────────

def _normalize_all(raw_list: list[RawMetrics]) -> list[NormalizedScores]:
    """Percentile-rank all factor sub-metrics across the universe, then aggregate."""
    n = len(raw_list)
    if n == 0:
        return []

    # Extract universe-wide value lists (preserving None)
    rev_g    = [r.revenue_growth  for r in raw_list]
    earn_g   = [r.earnings_growth for r in raw_list]
    pe_inv   = [-r.pe_ratio       if r.pe_ratio       is not None else None for r in raw_list]
    pb_inv   = [-r.price_to_book  if r.price_to_book  is not None else None for r in raw_list]
    ev_inv   = [-r.ev_ebitda      if r.ev_ebitda      is not None else None for r in raw_list]
    div_y    = [r.dividend_yield  for r in raw_list]
    payout   = [_payout_score(r.payout_ratio) for r in raw_list]  # transformed
    ret30    = [r.return_30d      for r in raw_list]
    ret90    = [r.return_90d      for r in raw_list]
    ma_aln   = [r.ma_alignment    for r in raw_list]
    rsi      = [r.rsi_14          for r in raw_list]
    roe      = [r.roe             for r in raw_list]
    margin   = [r.net_margin      for r in raw_list]
    de_inv   = [-r.debt_equity    if r.debt_equity is not None else None for r in raw_list]

    out: list[NormalizedScores] = []
    for i, r in enumerate(raw_list):
        # Growth
        g_rev  = _pct_rank(rev_g,  rev_g[i])
        g_earn = _pct_rank(earn_g, earn_g[i])
        growth = _weighted_factor([g_rev, g_earn], [0.5, 0.5])

        # Value
        v_pe  = _pct_rank(pe_inv,  pe_inv[i])
        v_pb  = _pct_rank(pb_inv,  pb_inv[i])
        v_ev  = _pct_rank(ev_inv,  ev_inv[i])
        value = _weighted_factor([v_pe, v_pb, v_ev], [0.50, 0.30, 0.20])

        # Dividend
        d_yld = _pct_rank(div_y,  div_y[i])
        d_pay = _pct_rank(payout, payout[i]) if payout[i] is not None else None
        dividend = _weighted_factor([d_yld, d_pay], [0.70, 0.30])

        # Momentum
        m_30  = _pct_rank(ret30,  ret30[i])
        m_90  = _pct_rank(ret90,  ret90[i])
        m_ma  = _pct_rank(ma_aln, ma_aln[i])
        m_rsi = _pct_rank(rsi,    rsi[i])
        momentum = _weighted_factor([m_30, m_90, m_ma, m_rsi], [0.40, 0.20, 0.30, 0.10])

        # Quality
        q_roe    = _pct_rank(roe,    roe[i])
        q_margin = _pct_rank(margin, margin[i])
        q_de     = _pct_rank(de_inv, de_inv[i])
        quality = _weighted_factor([q_roe, q_margin, q_de], [0.40, 0.40, 0.20])

        out.append(NormalizedScores(
            symbol=r.symbol,
            weight=r.weight,
            growth=growth,
            value=value,
            dividend=dividend,
            momentum=momentum,
            quality=quality,
            data_coverage=r.data_coverage,
        ))
    return out


def _payout_score(payout: float | None) -> float | None:
    """Transform raw payout ratio into a dividend-quality score (higher = better).

    Ideal range: 20-60%.  Above 80% is potentially unsustainable.
    """
    if payout is None:
        return None
    p = payout  # already a fraction (0.45 = 45%)
    if 0.20 <= p <= 0.60:
        return 1.0
    if p < 0.20:
        return p / 0.20          # 0→0, 0.20→1.0
    if p <= 0.80:
        return 1.0 - (p - 0.60) / 0.20 * 0.5   # 0.60→1.0, 0.80→0.5
    return max(0.0, 0.5 - (p - 0.80) / 0.40 * 0.5)   # 0.80→0.5, 1.20→0


# ─────────────────────────────────────────────────────────────────────────────
# Portfolio-level weighted exposure
# ─────────────────────────────────────────────────────────────────────────────

def _portfolio_exposure(scores: list[NormalizedScores]) -> dict[str, float | None]:
    """Compute weight-average factor exposure for the full portfolio (0-100 scale)."""
    factors = ("growth", "value", "dividend", "momentum", "quality")
    result: dict[str, float | None] = {}
    for f in factors:
        total_w = 0.0
        total_s = 0.0
        for s in scores:
            v = getattr(s, f)
            if v is not None and s.weight > 0:
                total_w += s.weight
                total_s += v * s.weight
        result[f] = round(total_s / total_w, 1) if total_w > 0 else None
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Style classification
# ─────────────────────────────────────────────────────────────────────────────

_FACTOR_LABELS = {
    "growth":   "Growth",
    "value":    "Value",
    "dividend": "Dividend",
    "momentum": "Momentum",
    "quality":  "Quality",
}

_DUAL_STYLE_NAMES: dict[frozenset, str] = {
    frozenset({"growth",  "quality"}):   "Quality Growth",
    frozenset({"growth",  "momentum"}):  "Momentum Growth",
    frozenset({"growth",  "value"}):     "GARP",               # Growth at a Reasonable Price
    frozenset({"value",   "dividend"}):  "Value Income",
    frozenset({"value",   "quality"}):   "Conservative Quality",
    frozenset({"dividend","quality"}):   "Quality Income",
    frozenset({"momentum","quality"}):   "Momentum Quality",
    frozenset({"growth",  "dividend"}):  "Dividend Growth",
    frozenset({"momentum","value"}):     "Tactical Value",
    frozenset({"momentum","dividend"}):  "Tactical Income",
}

_SINGLE_STYLE_NAMES = {
    "growth":   "Growth Tilt",
    "value":    "Value Defensive",
    "dividend": "Dividend Income",
    "momentum": "Momentum Aggressive",
    "quality":  "Quality Core",
}


def _classify_style(exposure: dict[str, float | None]) -> dict:
    """Derive portfolio style dynamically from factor exposure scores.

    Returns: {primary, secondary, confidence, dominant_factors, rationale}
    """
    # Work only with factors that have a score
    valid = {k: v for k, v in exposure.items() if v is not None}
    if not valid:
        return {
            "primary": "Undetermined",
            "secondary": None,
            "confidence": "low",
            "dominant_factors": [],
            "rationale": "Insufficient data to classify portfolio style.",
        }

    sorted_factors = sorted(valid.items(), key=lambda x: x[1], reverse=True)
    top_k, top_v   = sorted_factors[0]
    sec_k, sec_v   = sorted_factors[1] if len(sorted_factors) > 1 else (None, 0.0)
    third_k, third_v = sorted_factors[2] if len(sorted_factors) > 2 else (None, 0.0)

    avg_score = sum(valid.values()) / len(valid)
    spread    = top_v - (third_v if third_v else avg_score)

    # Confidence: based on data breadth and score differentiation
    universe_size = len(valid)
    if universe_size >= 4 and spread >= 20:
        confidence = "high"
    elif universe_size >= 3 and spread >= 10:
        confidence = "medium"
    else:
        confidence = "low"

    # All factors within 15 points of each other → balanced
    if top_v - (sorted_factors[-1][1] if sorted_factors else 0) < 15:
        if avg_score < 40:
            primary = "Defensive Conservative"
            rationale = "Portfolio shows uniformly low factor exposures, suggesting a conservative stance or defensive positioning."
        else:
            primary = "Balanced Core"
            rationale = "No single factor dominates; portfolio provides balanced exposure across growth, value, and quality."
        return {
            "primary": primary,
            "secondary": None,
            "confidence": confidence,
            "dominant_factors": [k for k, v in sorted_factors if v >= avg_score],
            "rationale": rationale,
        }

    # Single dominant factor: top > second by ≥ 15 points AND top ≥ 60
    if sec_k and (top_v - sec_v) >= 15 and top_v >= 60:
        primary = _SINGLE_STYLE_NAMES.get(top_k, f"{top_k.title()} Tilt")
        rationale = (
            f"Portfolio is primarily driven by {_FACTOR_LABELS[top_k].lower()} characteristics "
            f"(score {top_v:.0f}/100), with {_FACTOR_LABELS.get(sec_k,'').lower()} "
            f"as a secondary influence ({sec_v:.0f}/100)."
        )
        return {
            "primary": primary,
            "secondary": _FACTOR_LABELS.get(sec_k),
            "confidence": confidence,
            "dominant_factors": [top_k],
            "rationale": rationale,
        }

    # Dual-factor style: top two within 15 points, both ≥ 50
    if sec_k and (top_v - sec_v) < 15 and top_v >= 50 and sec_v >= 50:
        key = frozenset({top_k, sec_k})
        primary = _DUAL_STYLE_NAMES.get(key, f"{_FACTOR_LABELS[top_k]}-{_FACTOR_LABELS[sec_k]} Blend")
        rationale = (
            f"Portfolio shows dual-factor dominance: {_FACTOR_LABELS[top_k].lower()} "
            f"({top_v:.0f}/100) and {_FACTOR_LABELS[sec_k].lower()} ({sec_v:.0f}/100) "
            f"are both elevated, suggesting a blend of these characteristics."
        )
        return {
            "primary": primary,
            "secondary": None,
            "confidence": confidence,
            "dominant_factors": [top_k, sec_k],
            "rationale": rationale,
        }

    # Fallback: top factor is leading but not decisively
    primary = _SINGLE_STYLE_NAMES.get(top_k, f"{top_k.title()} Leaning")
    rationale = (
        f"Portfolio leans toward {_FACTOR_LABELS.get(top_k,'').lower()} characteristics "
        f"({top_v:.0f}/100) but without strong factor separation."
    )
    return {
        "primary": primary,
        "secondary": _FACTOR_LABELS.get(sec_k) if sec_k else None,
        "confidence": confidence,
        "dominant_factors": [top_k],
        "rationale": rationale,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Sector concentration
# ─────────────────────────────────────────────────────────────────────────────

def _sector_concentration(raw_list: list[RawMetrics]) -> dict:
    """Compute sector weights, HHI, diversification score, and risk flags."""
    sector_weights: dict[str, float] = {}
    for r in raw_list:
        sec = r.sector or "Other"
        sector_weights[sec] = sector_weights.get(sec, 0.0) + r.weight

    if not sector_weights:
        return {
            "sector_weights":      {},
            "top_sector":          None,
            "top_sector_weight":   None,
            "diversification_score": None,
            "hhi":                 None,
            "hhi_label":           None,
            "concentration_flags": [],
        }

    # Normalise weights (should sum to ~1 but floating point)
    total = sum(sector_weights.values())
    if total > 0:
        sector_weights = {k: round(v / total * 100, 2) for k, v in sector_weights.items()}

    top_sector = max(sector_weights, key=lambda k: sector_weights[k])
    top_weight = sector_weights[top_sector]

    # Sector-level Herfindahl-Hirschman Index (0-10000)
    hhi = round(sum((w / 100) ** 2 for w in sector_weights.values()) * 10_000, 1)

    n_sectors = len(sector_weights)
    if n_sectors > 1:
        min_hhi = 10_000 / n_sectors  # equally distributed
        div_score = round((10_000 - hhi) / (10_000 - min_hhi) * 100, 1)
        div_score = max(0.0, min(100.0, div_score))
    else:
        div_score = 0.0  # single sector = zero diversification

    if hhi < 1500:
        hhi_label = "LOW"
    elif hhi < 2500:
        hhi_label = "MEDIUM"
    elif hhi < 4000:
        hhi_label = "HIGH"
    else:
        hhi_label = "CRITICAL"

    flags: list[str] = []
    if top_weight > 50:
        flags.append(f"DOMINANT_SECTOR:{top_sector.upper().replace(' ','_')}")
    if top_weight > 35:
        flags.append("SECTOR_OVER_35_PCT")
    if n_sectors == 1:
        flags.append("SINGLE_SECTOR")
    elif n_sectors == 2:
        flags.append("ONLY_TWO_SECTORS")

    return {
        "sector_weights":        dict(sorted(sector_weights.items(), key=lambda x: -x[1])),
        "top_sector":            top_sector,
        "top_sector_weight":     round(top_weight, 2),
        "diversification_score": div_score,
        "hhi":                   hhi,
        "hhi_label":             hhi_label,
        "concentration_flags":   flags,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Factor score descriptors
# ─────────────────────────────────────────────────────────────────────────────

def _score_label(score: float | None) -> str:
    if score is None:
        return "Unavailable"
    if score >= 75:
        return "Strong"
    if score >= 55:
        return "Moderate-High"
    if score >= 40:
        return "Moderate"
    if score >= 25:
        return "Moderate-Low"
    return "Weak"


_FACTOR_DESCRIPTIONS: dict[str, dict[str, str]] = {
    "growth": {
        "Strong":        "Portfolio holds high-growth companies with strong revenue and earnings expansion.",
        "Moderate-High": "Above-average growth characteristics; portfolio likely includes some fast-growing names.",
        "Moderate":      "Balanced growth profile; mix of growth and mature companies.",
        "Moderate-Low":  "Below-average growth; portfolio leans toward slower-growing or ex-growth businesses.",
        "Weak":          "Low or declining growth across holdings; portfolio does not emphasise growth.",
        "Unavailable":   "Insufficient data to assess growth exposure.",
    },
    "value": {
        "Strong":        "Portfolio trades at attractive valuations relative to peers (low P/E, P/B).",
        "Moderate-High": "Holdings are reasonably priced; moderate discount to intrinsic value.",
        "Moderate":      "Mixed valuation profile — some cheap names offset by fairly-valued ones.",
        "Moderate-Low":  "Holdings are above average in valuation; limited margin of safety.",
        "Weak":          "Portfolio concentrated in premium-valued stocks; low margin of safety.",
        "Unavailable":   "Insufficient data to assess value exposure.",
    },
    "dividend": {
        "Strong":        "Portfolio generates significant income through high and consistent dividend yields.",
        "Moderate-High": "Above-average dividend income; includes several dividend-paying stocks.",
        "Moderate":      "Some dividend income present but not a dominant characteristic.",
        "Moderate-Low":  "Below-average dividend yield; portfolio is not primarily income-oriented.",
        "Weak":          "Portfolio has minimal dividend income; growth or capital-gain focused.",
        "Unavailable":   "Insufficient data to assess dividend exposure.",
    },
    "momentum": {
        "Strong":        "Holdings are trending strongly upward with positive price momentum.",
        "Moderate-High": "Portfolio shows above-average positive price momentum across holdings.",
        "Moderate":      "Mixed momentum signals; some positions trending, others flat.",
        "Moderate-Low":  "Below-average momentum; several holdings show signs of fading trends.",
        "Weak":          "Portfolio is under price pressure; poor recent performance trend.",
        "Unavailable":   "Insufficient data to assess momentum exposure.",
    },
    "quality": {
        "Strong":        "Portfolio holds high-quality businesses with strong returns, margins, and balance sheets.",
        "Moderate-High": "Above-average quality; mix of solid and good businesses.",
        "Moderate":      "Average quality profile; a balanced mix of business calibres.",
        "Moderate-Low":  "Below-average quality; some holdings have weaker profitability or higher leverage.",
        "Weak":          "Portfolio includes lower-quality businesses; elevated fundamental risk.",
        "Unavailable":   "Insufficient data to assess quality exposure.",
    },
}


def _factor_detail(factor: str, score: float | None) -> dict:
    label = _score_label(score)
    desc  = _FACTOR_DESCRIPTIONS.get(factor, {}).get(label, "")
    return {"score": score, "label": label, "description": desc}


# ─────────────────────────────────────────────────────────────────────────────
# Raw metrics summary (for API explainability)
# ─────────────────────────────────────────────────────────────────────────────

def _raw_summary(raw_list: list[RawMetrics]) -> dict:
    """Portfolio-level averages of key raw metrics for the UI summary strip."""
    def _avg(vals: list[float | None]) -> float | None:
        clean = [v for v in vals if v is not None]
        return _r(sum(clean) / len(clean), 4) if clean else None

    return {
        "avg_pe":              _avg([r.pe_ratio       for r in raw_list]),
        "avg_price_to_book":   _avg([r.price_to_book  for r in raw_list]),
        "avg_revenue_growth":  _r(_avg([r.revenue_growth  for r in raw_list]), 4),
        "avg_earnings_growth": _r(_avg([r.earnings_growth for r in raw_list]), 4),
        "avg_roe":             _r(_avg([r.roe             for r in raw_list]), 4),
        "avg_net_margin":      _r(_avg([r.net_margin      for r in raw_list]), 4),
        "avg_debt_equity":     _avg([r.debt_equity    for r in raw_list]),
        "avg_dividend_yield":  _r(_avg([r.dividend_yield  for r in raw_list]), 4),
        "avg_return_30d":      _r(_avg([r.return_30d      for r in raw_list]), 4),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def compute_portfolio_factor_exposure(db, portfolio_id: int, workspace_id: int) -> dict:
    """Compute full factor exposure for a portfolio.

    Synchronous — wrap in asyncio.to_thread() from async endpoints.
    Caches result for 15 minutes in the shared quant_engine in-process cache.

    Returns a dict ready for direct JSON serialisation with the following shape:
        {
          portfolio_id, portfolio_name, generated_at,
          factor_exposures: {growth, value, dividend, momentum, quality},
          style_classification: {primary, secondary, confidence, dominant_factors, rationale},
          per_stock_scores: [{symbol, weight, scores: {5 factors}, data_coverage}],
          raw_metrics_summary: {avg_pe, avg_roe, ...},
          sector_concentration: {sector_weights, diversification_score, hhi, ...},
          metadata: {universe_size, data_quality_flags, normalization_method, computed_at},
        }
    """
    # Cache check
    cached = get_cached(portfolio_id, _CACHE_GROUP)
    if cached:
        return cached

    # Load portfolio
    portfolio = (
        db.query(Portfolio)
        .filter(Portfolio.id == portfolio_id, Portfolio.workspace_id == workspace_id)
        .first()
    )
    if not portfolio:
        return {"error": "portfolio_not_found"}

    items: list[PortfolioItem] = (
        db.query(PortfolioItem)
        .filter(
            PortfolioItem.portfolio_id == portfolio_id,
            PortfolioItem.workspace_id == workspace_id,
        )
        .all()
    )
    if not items:
        return {
            "portfolio_id":         portfolio_id,
            "portfolio_name":       portfolio.name,
            "generated_at":         datetime.utcnow().isoformat() + "Z",
            "factor_exposures":     {},
            "style_classification": {"primary": "Empty Portfolio"},
            "per_stock_scores":     [],
            "raw_metrics_summary":  {},
            "sector_concentration": {},
            "metadata":             {"universe_size": 0},
        }

    # ── Get current prices to compute weights ─────────────────────────────────
    market_values: dict[str, float] = {}
    for item in items:
        yf_sym = normalize_dr_symbol(item.symbol)
        price_data = fetch_price_info(yf_sym)
        price = price_data.get("current_price") or 0.0
        if price <= 0:
            price = float(item.avg_cost)  # fallback to cost basis
        market_values[item.symbol] = price * float(item.shares)

    total_mv = sum(market_values.values())
    if total_mv <= 0:
        total_mv = 1.0  # guard against zero division

    # ── Gather data and build RawMetrics for each holding ─────────────────────
    data_quality_flags: list[str] = []
    raw_list: list[RawMetrics] = []

    for item in items:
        weight = market_values[item.symbol] / total_mv
        info   = _gather_info(item.symbol)
        mom    = _gather_momentum(item.symbol)
        raw    = _extract_raw_metrics(item.symbol, item.sector, weight, info, mom)
        raw_list.append(raw)

        if raw.data_coverage < 0.30:
            data_quality_flags.append(f"{item.symbol}:LOW_DATA_COVERAGE")
        elif raw.data_coverage < 0.60:
            data_quality_flags.append(f"{item.symbol}:PARTIAL_DATA")

    # ── Normalize and score ───────────────────────────────────────────────────
    normalized = _normalize_all(raw_list)
    exposure   = _portfolio_exposure(normalized)

    # ── Style classification ──────────────────────────────────────────────────
    style = _classify_style(exposure)

    # ── Sector concentration ──────────────────────────────────────────────────
    sector_data = _sector_concentration(raw_list)

    # ── Per-stock scores for the frontend table / radar ───────────────────────
    per_stock = [
        {
            "symbol":        s.symbol,
            "sector":        next((r.sector for r in raw_list if r.symbol == s.symbol), None),
            "weight":        round(s.weight * 100, 2),  # convert to %
            "scores": {
                "growth":   s.growth,
                "value":    s.value,
                "dividend": s.dividend,
                "momentum": s.momentum,
                "quality":  s.quality,
            },
            "data_coverage": round(s.data_coverage * 100, 1),  # %
        }
        for s in normalized
    ]

    # ── Factor exposure detail ────────────────────────────────────────────────
    factor_exposures = {
        f: _factor_detail(f, exposure.get(f))
        for f in ("growth", "value", "dividend", "momentum", "quality")
    }

    result = {
        "portfolio_id":   portfolio_id,
        "portfolio_name": portfolio.name,
        "generated_at":   datetime.utcnow().isoformat() + "Z",

        "factor_exposures":     factor_exposures,
        "style_classification": style,

        "per_stock_scores":    per_stock,
        "raw_metrics_summary": _raw_summary(raw_list),

        "sector_concentration": sector_data,

        "metadata": {
            "universe_size":        len(items),
            "data_quality_flags":   data_quality_flags,
            "normalization_method": "percentile_rank_within_universe",
            "computed_at":          datetime.utcnow().isoformat() + "Z",
        },
    }

    set_cached(portfolio_id, _CACHE_GROUP, result)
    return result
