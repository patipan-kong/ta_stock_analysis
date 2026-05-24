"""Market Regime Detection Engine — Phase 3B.3.

Classifies the current macro environment into one of 7 regime states using a
multi-signal approach over rolling 30–90 day windows.  Pure pandas/numpy — no AI.

Regime States
─────────────
  RISK_ON             Strong trend, low volatility — deploy capital aggressively
  RISK_OFF            Bearish trend + rising volatility — reduce exposure
  SIDEWAYS            Flat trend, moderate volatility — be selective
  HIGH_VOLATILITY     Extreme vol spike — override all other signals, preserve capital
  DEFENSIVE_REGIME    Bearish trend, low volatility — rotate to quality/dividend
  TRANSITION_RISK_ON  Regime flipping toward risk-on — cautiously increase exposure
  TRANSITION_RISK_OFF Regime flipping toward risk-off — start reducing aggressively

Signals Used
────────────
  1. EMA trend alignment  — EMA20 vs EMA50 gap as % of price (primary trend signal)
  2. Volatility z-score   — 20D realized vol vs 90D rolling mean/std
  3. Rolling drawdown     — max-drawdown from 30D rolling high
  4. Momentum persistence — 20D return vs 60D return (trend continuation)
  5. Return dispersion    — cross-benchmark daily-return std (breadth/divergence)
  6. VIX proxy            — ^VIX if available, else derived from S&P realized vol

Entry points
────────────
  detect_regime(db) -> dict
  get_regime_constraints(regime) -> dict      ← hard allocator constraints
  build_regime_prompt_block(regime_ctx) -> str ← L1/L2 injection block

Caching: 30-minute in-process TTL keyed by "_global_".
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)

_CACHE: dict[str, tuple[dict, float]] = {}
_CACHE_TTL = 1800  # 30 minutes

_BENCHMARKS = ["^GSPC", "^SET.BK", "QQQ"]
_VIX_SYMBOL = "^VIX"

RegimeState = str  # keep as plain str for JSON-safe transport


# ─────────────────────────────────────────────────────────────────────────────
# Regime constants
# ─────────────────────────────────────────────────────────────────────────────

REGIME_RISK_ON            = "RISK_ON"
REGIME_RISK_OFF           = "RISK_OFF"
REGIME_SIDEWAYS           = "SIDEWAYS"
REGIME_HIGH_VOL           = "HIGH_VOLATILITY"
REGIME_DEFENSIVE          = "DEFENSIVE_REGIME"
REGIME_TRANSITION_ON      = "TRANSITION_RISK_ON"
REGIME_TRANSITION_OFF     = "TRANSITION_RISK_OFF"

_ALL_REGIMES = {
    REGIME_RISK_ON, REGIME_RISK_OFF, REGIME_SIDEWAYS,
    REGIME_HIGH_VOL, REGIME_DEFENSIVE,
    REGIME_TRANSITION_ON, REGIME_TRANSITION_OFF,
}

# ─────────────────────────────────────────────────────────────────────────────
# Hard allocator constraints per regime
# ─────────────────────────────────────────────────────────────────────────────

_REGIME_CONSTRAINTS: dict[str, dict[str, Any]] = {
    REGIME_RISK_ON: {
        "min_cash_pct": 2.0,
        "max_single_position_pct": 25.0,
        "turnover_multiplier": 1.2,
        "momentum_bias": True,
        "quality_bias": False,
        "dividend_bias": False,
        "suppress_speculative": False,
        "deployment_stance": "aggressive",
        "mandate": (
            "Market is in a risk-on phase. Capital deployment is encouraged. "
            "Growth and momentum exposure may be increased. Minimum cash: 2%."
        ),
    },
    REGIME_RISK_OFF: {
        "min_cash_pct": 10.0,
        "max_single_position_pct": 20.0,
        "turnover_multiplier": 0.7,
        "momentum_bias": False,
        "quality_bias": True,
        "dividend_bias": True,
        "suppress_speculative": True,
        "deployment_stance": "defensive",
        "mandate": (
            "Market is in a risk-off phase. Reduce exposure to speculative and high-beta assets. "
            "Increase cash reserve to at least 10%. Prioritize quality and dividend stocks."
        ),
    },
    REGIME_SIDEWAYS: {
        "min_cash_pct": 5.0,
        "max_single_position_pct": 22.0,
        "turnover_multiplier": 0.8,
        "momentum_bias": False,
        "quality_bias": False,
        "dividend_bias": True,
        "suppress_speculative": False,
        "deployment_stance": "selective",
        "mandate": (
            "Market is trending sideways. Be selective — only act on high-conviction signals. "
            "Prefer dividend and value stocks over momentum plays. Cash floor: 5%."
        ),
    },
    REGIME_HIGH_VOL: {
        "min_cash_pct": 15.0,
        "max_single_position_pct": 18.0,
        "turnover_multiplier": 0.5,
        "momentum_bias": False,
        "quality_bias": True,
        "dividend_bias": False,
        "suppress_speculative": True,
        "deployment_stance": "preservation",
        "mandate": (
            "ELEVATED VOLATILITY REGIME. Capital preservation is the priority. "
            "Minimum cash 15%. Maximum single-stock position 18%. "
            "Suppress speculative positions. Tighten concentration limits. Reduce portfolio turnover."
        ),
    },
    REGIME_DEFENSIVE: {
        "min_cash_pct": 8.0,
        "max_single_position_pct": 22.0,
        "turnover_multiplier": 0.7,
        "momentum_bias": False,
        "quality_bias": True,
        "dividend_bias": True,
        "suppress_speculative": True,
        "deployment_stance": "defensive",
        "mandate": (
            "Defensive regime — bearish trend with low volatility. "
            "Rotate toward quality, dividend, and value factors. "
            "Suppress momentum and high-beta allocations. Cash floor: 8%."
        ),
    },
    REGIME_TRANSITION_ON: {
        "min_cash_pct": 5.0,
        "max_single_position_pct": 22.0,
        "turnover_multiplier": 0.9,
        "momentum_bias": False,
        "quality_bias": True,
        "dividend_bias": False,
        "suppress_speculative": False,
        "deployment_stance": "cautiously_bullish",
        "mandate": (
            "Regime is transitioning toward risk-on. Cautiously increase exposure. "
            "Prioritize quality names first before adding momentum. Cash floor: 5%."
        ),
    },
    REGIME_TRANSITION_OFF: {
        "min_cash_pct": 8.0,
        "max_single_position_pct": 20.0,
        "turnover_multiplier": 0.8,
        "momentum_bias": False,
        "quality_bias": True,
        "dividend_bias": True,
        "suppress_speculative": True,
        "deployment_stance": "cautiously_defensive",
        "mandate": (
            "Regime is transitioning toward risk-off. Begin reducing aggressive exposure. "
            "Start building cash buffer to 8%. Avoid adding new momentum or speculative positions."
        ),
    },
}


def get_regime_constraints(regime: str) -> dict:
    return _REGIME_CONSTRAINTS.get(regime, _REGIME_CONSTRAINTS[REGIME_SIDEWAYS])


# ─────────────────────────────────────────────────────────────────────────────
# Data fetching helpers
# ─────────────────────────────────────────────────────────────────────────────

def _fetch_benchmark_history(symbol: str, days: int = 95) -> pd.DataFrame:
    """Fetch daily close prices for a benchmark symbol via yfinance.
    Returns a DataFrame with columns ['Close'] indexed by date, or empty DataFrame on failure.
    """
    try:
        import yfinance as yf  # local import — only needed here
        ticker = yf.Ticker(symbol)
        period = "6mo" if days > 90 else "3mo"
        hist = ticker.history(period=period, interval="1d", auto_adjust=True)
        if hist.empty or "Close" not in hist.columns:
            return pd.DataFrame()
        df = hist[["Close"]].copy()
        df.index = pd.to_datetime(df.index).tz_localize(None)
        df = df.sort_index()
        return df.tail(days)
    except Exception as exc:
        log.warning("regime_detector: failed to fetch %s — %s", symbol, exc)
        return pd.DataFrame()


# ─────────────────────────────────────────────────────────────────────────────
# Signal computation
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SignalBundle:
    """Computed intermediate signals for one benchmark series (normalised 0–100)."""
    symbol: str
    ema_trend_score: float = 50.0     # 0=max bearish, 100=max bullish
    vol_score: float = 50.0           # 0=crisis vol, 100=calm
    drawdown_score: float = 50.0      # 0=deep drawdown, 100=no drawdown
    momentum_score: float = 50.0      # 0=no momentum, 100=strong
    vol_z_score: float = 0.0          # raw z-score (signed, unbounded)
    ema20: float = 0.0
    ema50: float = 0.0
    current_price: float = 0.0
    realized_vol_20d: float = 0.0
    drawdown_30d: float = 0.0         # fraction, e.g. -0.12 = -12%
    return_20d: float = 0.0
    return_60d: float = 0.0
    ok: bool = True                   # False if insufficient data


def _compute_signals(symbol: str, df: pd.DataFrame) -> SignalBundle:
    """Derive normalised signals from a daily Close price series."""
    bundle = SignalBundle(symbol=symbol)
    if df.empty or len(df) < 25:
        bundle.ok = False
        return bundle

    closes = df["Close"].dropna()
    if len(closes) < 25:
        bundle.ok = False
        return bundle

    # ── EMA trend ────────────────────────────────────────────────────────────
    ema20 = closes.ewm(span=20, adjust=False).mean()
    ema50 = closes.ewm(span=50, adjust=False).mean()
    bundle.ema20 = float(ema20.iloc[-1])
    bundle.ema50 = float(ema50.iloc[-1])
    bundle.current_price = float(closes.iloc[-1])

    gap_pct = (bundle.ema20 - bundle.ema50) / bundle.ema50 * 100 if bundle.ema50 > 0 else 0
    price_vs_ema50_pct = (bundle.current_price - bundle.ema50) / bundle.ema50 * 100 if bundle.ema50 > 0 else 0

    # Combine: EMA gap (-10%…+10% → 0…100) + price vs EMA50 (same)
    ema_raw = gap_pct * 3 + price_vs_ema50_pct * 2   # -50…+50 typical
    bundle.ema_trend_score = float(np.clip(50 + ema_raw * 2, 0, 100))

    # ── Volatility ───────────────────────────────────────────────────────────
    log_ret = np.log(closes / closes.shift(1)).dropna()
    if len(log_ret) >= 20:
        vol_20d = float(log_ret.iloc[-20:].std() * np.sqrt(252))
        bundle.realized_vol_20d = vol_20d
        if len(log_ret) >= 60:
            vol_rolling = log_ret.rolling(20).std() * np.sqrt(252)
            vol_hist = vol_rolling.dropna()
            if len(vol_hist) >= 30:
                vol_mean = float(vol_hist.mean())
                vol_std = float(vol_hist.std())
                bundle.vol_z_score = (vol_20d - vol_mean) / vol_std if vol_std > 0 else 0.0
        # vol score: z-score -3…+3 → 100…0 (lower vol = higher score)
        bundle.vol_score = float(np.clip(50 - bundle.vol_z_score * 16, 0, 100))

    # ── Rolling max-drawdown (30D) ────────────────────────────────────────────
    window = min(30, len(closes))
    rolling_max = closes.iloc[-window:].cummax()
    rolling_dd = (closes.iloc[-window:] - rolling_max) / rolling_max
    dd = float(rolling_dd.min())
    bundle.drawdown_30d = dd
    # dd -25%…0% → 0…100
    bundle.drawdown_score = float(np.clip(100 + dd * 4, 0, 100))

    # ── Momentum persistence ──────────────────────────────────────────────────
    if len(closes) >= 60:
        bundle.return_20d = float((closes.iloc[-1] / closes.iloc[-21] - 1) * 100)
        bundle.return_60d = float((closes.iloc[-1] / closes.iloc[-61] - 1) * 100)
    elif len(closes) >= 20:
        bundle.return_20d = float((closes.iloc[-1] / closes.iloc[-21] - 1) * 100)

    # Momentum: 20D return (-15%…+15%) → 0…100
    bundle.momentum_score = float(np.clip(50 + bundle.return_20d * 3, 0, 100))

    return bundle


def _compute_dispersion(bundles: list[SignalBundle]) -> float:
    """Cross-benchmark return dispersion — higher = markets diverging (uncertainty).
    Returns a dispersion score 0–100 (0=no divergence, 100=max divergence).
    """
    valid = [b for b in bundles if b.ok]
    if len(valid) < 2:
        return 50.0
    returns = [b.return_20d for b in valid]
    spread = float(np.std(returns))
    # typical spread 0–10% → 0–100
    return float(np.clip(spread * 10, 0, 100))


# ─────────────────────────────────────────────────────────────────────────────
# Regime classification
# ─────────────────────────────────────────────────────────────────────────────

def _classify_regime(
    trend: float,
    vol: float,
    drawdown: float,
    momentum: float,
    dispersion: float,
    vol_z: float,
    vix_level: float | None = None,
) -> tuple[str, float]:
    """Map normalised signals to a regime state and confidence score.

    All inputs are 0-100 except vol_z (raw z-score) and vix_level (raw VIX points).
    Returns (regime, confidence) where confidence is 0.0–1.0.
    """
    # ── Override: HIGH_VOLATILITY ─────────────────────────────────────────────
    high_vol_trigger = (
        vol_z > 2.0
        or (vix_level is not None and vix_level > 30)
        or vol < 20        # vol score below 20 = crisis-level volatility
        or drawdown < 20   # deep drawdown
    )
    if high_vol_trigger:
        severity = max(vol_z, (30 - (vix_level or 25)) / 5)
        conf = float(np.clip(0.55 + min(severity, 3) * 0.10, 0.55, 0.95))
        return REGIME_HIGH_VOL, conf

    # ── Composite alignment score ─────────────────────────────────────────────
    # Weights: trend 40%, vol 25%, drawdown 20%, momentum 15%
    composite = trend * 0.40 + vol * 0.25 + drawdown * 0.20 + momentum * 0.15

    # Spread penalty when markets diverge
    divergence_penalty = (dispersion - 50) * 0.15 if dispersion > 50 else 0
    composite = float(np.clip(composite - divergence_penalty, 0, 100))

    # Confidence: how far composite is from the 50-neutral zone
    distance_from_neutral = abs(composite - 50)
    base_conf = 0.40 + distance_from_neutral / 50 * 0.50   # 0.40–0.90

    # ── RISK_ON ───────────────────────────────────────────────────────────────
    if composite >= 68 and trend >= 65:
        return REGIME_RISK_ON, float(np.clip(base_conf * 1.05, 0.55, 0.95))

    # ── RISK_OFF ──────────────────────────────────────────────────────────────
    if composite <= 35 and trend <= 40 and vol <= 55:
        return REGIME_RISK_OFF, float(np.clip(base_conf * 1.05, 0.55, 0.95))

    # ── DEFENSIVE_REGIME — bearish trend but not panic volatility ─────────────
    if trend <= 42 and vol >= 55:
        return REGIME_DEFENSIVE, float(np.clip(base_conf, 0.45, 0.85))

    # ── SIDEWAYS — trend flat, moderate conditions ────────────────────────────
    if 43 <= trend <= 62 and composite >= 42:
        return REGIME_SIDEWAYS, float(np.clip(0.40 + (1 - distance_from_neutral / 50) * 0.30, 0.35, 0.70))

    # ── TRANSITION states — borderline cases ──────────────────────────────────
    if composite >= 54 and trend >= 52:
        return REGIME_TRANSITION_ON, float(np.clip(base_conf * 0.85, 0.35, 0.70))

    if composite <= 46 and trend <= 48:
        return REGIME_TRANSITION_OFF, float(np.clip(base_conf * 0.85, 0.35, 0.70))

    return REGIME_SIDEWAYS, float(np.clip(base_conf * 0.80, 0.30, 0.65))


# ─────────────────────────────────────────────────────────────────────────────
# Duration + transition stability tracking
# ─────────────────────────────────────────────────────────────────────────────

def _load_recent_snapshots(db, limit: int = 30) -> list:
    """Load recent RegimeSnapshot rows from DB (most recent first)."""
    try:
        from models.database import RegimeSnapshot
        rows = (
            db.query(RegimeSnapshot)
            .order_by(RegimeSnapshot.snapshot_date.desc())
            .limit(limit)
            .all()
        )
        return rows
    except Exception as exc:
        log.warning("regime_detector: failed to load snapshots — %s", exc)
        return []


def _compute_duration_and_stability(
    current_regime: str,
    snapshots: list,
) -> tuple[int, str, str]:
    """Compute how long the current regime has persisted and transition stability.

    Returns:
        duration_days      — consecutive days in current regime
        previous_regime    — last different regime (or "UNKNOWN")
        transition_stability — STABLE | VOLATILE | TRANSITIONING
    """
    duration = 1
    previous_regime = "UNKNOWN"

    for snap in snapshots:
        snap_regime = getattr(snap, "regime", None) or "UNKNOWN"
        if snap_regime == current_regime:
            duration += 1
        else:
            previous_regime = snap_regime
            break

    # Stability: look at last 10 snapshots for consistency
    recent_regimes = [getattr(s, "regime", "UNKNOWN") for s in snapshots[:10]]
    unique_recent = len(set(recent_regimes))

    if unique_recent == 1:
        stability = "STABLE"
    elif unique_recent <= 2:
        stability = "TRANSITIONING"
    else:
        stability = "VOLATILE"

    return duration, previous_regime, stability


# ─────────────────────────────────────────────────────────────────────────────
# DB persistence
# ─────────────────────────────────────────────────────────────────────────────

def _save_regime_snapshot(db, regime_result: dict) -> None:
    """Upsert today's RegimeSnapshot row."""
    try:
        from models.database import RegimeSnapshot
        import json

        today = datetime.utcnow().strftime("%Y-%m-%d")
        existing = (
            db.query(RegimeSnapshot)
            .filter_by(snapshot_date=today)
            .first()
        )
        payload = {
            "snapshot_date":       today,
            "regime":              regime_result["regime"],
            "confidence":          regime_result["confidence"],
            "trend_score":         regime_result.get("trend_score", 50.0),
            "volatility_score":    regime_result.get("volatility_score", 50.0),
            "drawdown_score":      regime_result.get("drawdown_score", 50.0),
            "momentum_score":      regime_result.get("momentum_score", 50.0),
            "vol_z_score":         regime_result.get("vol_z_score", 0.0),
            "ema_alignment":       regime_result.get("ema_alignment", 0.0),
            "regime_duration_days":regime_result.get("regime_duration_days", 1),
            "previous_regime":     regime_result.get("previous_regime", "UNKNOWN"),
            "transition_stability":regime_result.get("transition_stability", "STABLE"),
            "signals_json":        json.dumps(regime_result.get("benchmark_signals", {})),
        }
        if existing:
            for k, v in payload.items():
                setattr(existing, k, v)
        else:
            db.add(RegimeSnapshot(**payload))
        db.commit()
    except Exception as exc:
        log.warning("regime_detector: failed to save snapshot — %s", exc)
        db.rollback()


# ─────────────────────────────────────────────────────────────────────────────
# Historical regime timeline
# ─────────────────────────────────────────────────────────────────────────────

def _build_history_timeline(snapshots: list) -> list[dict]:
    """Build a regime timeline from DB snapshots for the frontend chart."""
    timeline = []
    for snap in reversed(snapshots):  # oldest first
        timeline.append({
            "date":       getattr(snap, "snapshot_date", ""),
            "regime":     getattr(snap, "regime", "UNKNOWN"),
            "confidence": round(float(getattr(snap, "confidence", 0.5) * 100)),
            "trend_score":     round(float(getattr(snap, "trend_score", 50))),
            "volatility_score":round(float(getattr(snap, "volatility_score", 50))),
        })
    return timeline


# ─────────────────────────────────────────────────────────────────────────────
# Transition warnings
# ─────────────────────────────────────────────────────────────────────────────

def _build_transition_warnings(
    regime: str,
    confidence: float,
    stability: str,
    vol_z: float,
    drawdown: float,
) -> list[str]:
    warnings = []

    if stability == "VOLATILE":
        warnings.append("Regime is frequently changing — signals are unstable. Reduce position sizing.")

    if stability == "TRANSITIONING":
        warnings.append(f"Regime is in transition (currently {regime}). Monitor closely before acting.")

    if confidence < 0.55:
        warnings.append(f"Low regime confidence ({confidence:.0%}) — mixed signals. Treat output as exploratory.")

    if vol_z > 1.5:
        warnings.append(f"Volatility is elevated (z-score {vol_z:.1f}σ above average). Tighten position limits.")

    if drawdown < 35:
        warnings.append("Significant drawdown detected across benchmarks. Portfolio drawdown risk is elevated.")

    if regime in (REGIME_TRANSITION_ON, REGIME_TRANSITION_OFF):
        warnings.append(
            "Transition regime detected — wait for stability before significant allocation changes."
        )

    return warnings


# ─────────────────────────────────────────────────────────────────────────────
# Prompt injection block
# ─────────────────────────────────────────────────────────────────────────────

_REGIME_NARRATIVES: dict[str, str] = {
    REGIME_RISK_ON: (
        "Market currently exhibits strong trend persistence and low volatility. "
        "Optimizer is operating in capital-deployment mode."
    ),
    REGIME_RISK_OFF: (
        "Market is in a risk-off phase with deteriorating trend and rising volatility. "
        "Optimizer is prioritizing capital preservation and defensive positioning."
    ),
    REGIME_SIDEWAYS: (
        "Market is trending sideways with moderate signals. "
        "Optimizer is in selective mode — acting only on high-conviction opportunities."
    ),
    REGIME_HIGH_VOL: (
        "Market currently exhibits elevated volatility with weak trend persistence. "
        "Optimizer is operating in capital-preservation mode."
    ),
    REGIME_DEFENSIVE: (
        "Market is in a defensive regime — bearish trend, relatively low volatility. "
        "Optimizer is rotating toward quality and dividend factors."
    ),
    REGIME_TRANSITION_ON: (
        "Market is transitioning toward risk-on conditions. "
        "Optimizer is cautiously increasing exposure, prioritizing quality names first."
    ),
    REGIME_TRANSITION_OFF: (
        "Market shows early signs of risk-off transition. "
        "Optimizer is beginning to reduce aggressive exposure and build cash."
    ),
}


def build_regime_prompt_block(regime_ctx: dict) -> str:
    """Generate the [MARKET REGIME] block injected into L1 and L2 prompts."""
    if not regime_ctx:
        return ""

    regime      = regime_ctx.get("regime", REGIME_SIDEWAYS)
    confidence  = regime_ctx.get("confidence", 0.5)
    stability   = regime_ctx.get("transition_stability", "STABLE")
    duration    = regime_ctx.get("regime_duration_days", 1)
    prev_regime = regime_ctx.get("previous_regime", "UNKNOWN")
    constraints = get_regime_constraints(regime)
    mandate     = constraints["mandate"]
    min_cash    = constraints["min_cash_pct"]
    max_pos     = constraints["max_single_position_pct"]
    suppress    = constraints["suppress_speculative"]
    quality     = constraints["quality_bias"]
    dividend    = constraints["dividend_bias"]
    momentum    = constraints["momentum_bias"]

    factor_guidance = []
    if momentum:
        factor_guidance.append("PRIORITIZE momentum and growth stocks")
    if quality:
        factor_guidance.append("PRIORITIZE quality (high ROE, low debt) stocks")
    if dividend:
        factor_guidance.append("PRIORITIZE dividend and income stocks")
    if suppress:
        factor_guidance.append("SUPPRESS speculative and high-beta positions")

    factor_line = "; ".join(factor_guidance) if factor_guidance else "Balanced factor selection"

    warnings = regime_ctx.get("transition_warnings", [])
    warning_block = ""
    if warnings:
        warning_block = "\nWarnings:\n" + "\n".join(f"  ⚠ {w}" for w in warnings)

    return f"""[MARKET REGIME — MANDATORY ALLOCATION CONTEXT]
Current Regime: {regime} (confidence: {confidence:.0%})
Transition Stability: {stability} ({duration} trading days in current regime)
Previous Regime: {prev_regime}
Volatility Signal: z-score {regime_ctx.get('vol_z_score', 0.0):.1f}σ
Trend Strength: {regime_ctx.get('trend_score', 50.0):.0f}/100

Regime Allocation Mandate:
{mandate}

Hard Constraints (regime-enforced — DO NOT override):
  Minimum cash reserve:    {min_cash:.0f}%
  Max single position:     {max_pos:.0f}%
  Factor stance:           {factor_line}

All allocation proposals MUST respect these regime-derived constraints.
The optimizer MUST NOT recommend cash below {min_cash:.0f}% in this regime.
{warning_block}
"""


# ─────────────────────────────────────────────────────────────────────────────
# Main public API
# ─────────────────────────────────────────────────────────────────────────────

def detect_regime(db) -> dict:
    """Detect the current market regime from live benchmark data.

    Returns a fully populated regime context dict ready for:
      - API response (GET /analytics/market-regime)
      - Optimizer prompt injection (build_regime_prompt_block)
      - Hard constraint extraction (get_regime_constraints)
    """
    cached = _CACHE.get("_global_")
    if cached and cached[1] > time.monotonic():
        return cached[0]

    t0 = time.monotonic()

    # ── 1. Fetch benchmark history ────────────────────────────────────────────
    bundles: list[SignalBundle] = []
    for sym in _BENCHMARKS:
        hist = _fetch_benchmark_history(sym, days=95)
        bundles.append(_compute_signals(sym, hist))

    # ── 2. Optional VIX ───────────────────────────────────────────────────────
    vix_level: float | None = None
    vix_hist = _fetch_benchmark_history(_VIX_SYMBOL, days=5)
    if not vix_hist.empty:
        vix_level = float(vix_hist["Close"].iloc[-1])

    # ── 3. Aggregate signals (primary benchmark = ^GSPC) ─────────────────────
    primary = next((b for b in bundles if b.symbol == "^GSPC" and b.ok), None)
    valid_bundles = [b for b in bundles if b.ok]

    if not valid_bundles:
        # Full fallback — cannot determine regime
        log.warning("regime_detector: no valid benchmark data — returning SIDEWAYS fallback")
        result = _sideways_fallback()
        _CACHE["_global_"] = (result, time.monotonic() + _CACHE_TTL)
        return result

    # Weighted average of signals across available benchmarks
    # ^GSPC gets 50% weight, others share the rest equally
    weights = []
    for b in valid_bundles:
        weights.append(0.50 if b.symbol == "^GSPC" else 0.50 / max(1, len(valid_bundles) - 1))
    total_w = sum(weights)
    weights = [w / total_w for w in weights]

    trend_agg    = sum(b.ema_trend_score * w for b, w in zip(valid_bundles, weights))
    vol_agg      = sum(b.vol_score       * w for b, w in zip(valid_bundles, weights))
    dd_agg       = sum(b.drawdown_score  * w for b, w in zip(valid_bundles, weights))
    mom_agg      = sum(b.momentum_score  * w for b, w in zip(valid_bundles, weights))
    vol_z_agg    = sum(b.vol_z_score     * w for b, w in zip(valid_bundles, weights))
    dispersion   = _compute_dispersion(valid_bundles)

    # Use primary bundle's EMA alignment for the prompt display
    ema_alignment = float(primary.ema_trend_score) if primary else trend_agg

    # ── 4. Classify regime ────────────────────────────────────────────────────
    regime, confidence = _classify_regime(
        trend_agg, vol_agg, dd_agg, mom_agg, dispersion, vol_z_agg, vix_level
    )

    # ── 5. Duration + stability from DB ──────────────────────────────────────
    recent_snaps = _load_recent_snapshots(db, limit=30)
    duration, previous_regime, stability = _compute_duration_and_stability(regime, recent_snaps)

    # ── 6. Build result ───────────────────────────────────────────────────────
    warnings = _build_transition_warnings(regime, confidence, stability, vol_z_agg, dd_agg)
    benchmark_signals = {
        b.symbol: {
            "ema_trend_score": round(b.ema_trend_score, 1),
            "vol_score": round(b.vol_score, 1),
            "drawdown_score": round(b.drawdown_score, 1),
            "momentum_score": round(b.momentum_score, 1),
            "vol_z_score": round(b.vol_z_score, 2),
            "return_20d": round(b.return_20d, 2),
            "realized_vol_20d": round(b.realized_vol_20d * 100, 2),
        }
        for b in valid_bundles
    }

    result = {
        "regime":                regime,
        "confidence":            round(confidence, 3),
        "confidence_pct":        round(confidence * 100, 1),
        "trend_score":           round(trend_agg, 1),
        "volatility_score":      round(vol_agg, 1),
        "drawdown_score":        round(dd_agg, 1),
        "momentum_score":        round(mom_agg, 1),
        "vol_z_score":           round(vol_z_agg, 2),
        "ema_alignment":         round(ema_alignment, 1),
        "vix_level":             round(vix_level, 2) if vix_level else None,
        "regime_duration_days":  duration,
        "previous_regime":       previous_regime,
        "transition_stability":  stability,
        "transition_warnings":   warnings,
        "benchmark_signals":     benchmark_signals,
        "narrative":             _REGIME_NARRATIVES.get(regime, ""),
        "constraints":           get_regime_constraints(regime),
        "regime_history":        _build_history_timeline(recent_snaps),
        "detected_at":           datetime.utcnow().isoformat() + "Z",
        "detection_ms":          round((time.monotonic() - t0) * 1000),
    }

    # ── 7. Persist snapshot ───────────────────────────────────────────────────
    _save_regime_snapshot(db, result)

    _CACHE["_global_"] = (result, time.monotonic() + _CACHE_TTL)
    log.info(
        "regime_detector: %s conf=%.0f%% stability=%s duration=%dd vix=%s elapsed_ms=%d",
        regime, confidence * 100, stability, duration,
        f"{vix_level:.1f}" if vix_level else "N/A",
        result["detection_ms"],
    )
    return result


def _sideways_fallback() -> dict:
    """Return a safe neutral result when all benchmark fetches fail."""
    return {
        "regime":               REGIME_SIDEWAYS,
        "confidence":           0.35,
        "confidence_pct":       35.0,
        "trend_score":          50.0,
        "volatility_score":     50.0,
        "drawdown_score":       50.0,
        "momentum_score":       50.0,
        "vol_z_score":          0.0,
        "ema_alignment":        50.0,
        "vix_level":            None,
        "regime_duration_days": 1,
        "previous_regime":      "UNKNOWN",
        "transition_stability": "VOLATILE",
        "transition_warnings":  ["Benchmark data unavailable — regime detection degraded. Treat output with caution."],
        "benchmark_signals":    {},
        "narrative":            "Regime data unavailable. Operating with neutral assumptions.",
        "constraints":          get_regime_constraints(REGIME_SIDEWAYS),
        "regime_history":       [],
        "detected_at":          datetime.utcnow().isoformat() + "Z",
        "detection_ms":         0,
        "data_error":           True,
    }


def invalidate_cache() -> None:
    _CACHE.pop("_global_", None)
