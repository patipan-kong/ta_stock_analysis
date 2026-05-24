"""Seed regime_snapshots with synthetic historical scenarios for testing and validation.

Generates 5 macro scenarios over a 90-day synthetic history:
  1. Bull Market          — sustained RISK_ON with high confidence
  2. Market Crash         — rapid RISK_OFF → HIGH_VOLATILITY spike
  3. Sideways Chop        — SIDEWAYS with VOLATILE stability
  4. Volatility Spike     — HIGH_VOLATILITY followed by stabilisation
  5. Defensive Recession  — DEFENSIVE_REGIME with gradual deterioration

Usage:
    cd backend
    python scripts/seed_regime_scenarios.py [--scenario all|bull|crash|sideways|vol_spike|defensive]

Options:
    --scenario  Which scenario to seed (default: all)
    --days      Days of history per scenario (default: 30)
    --clear     Delete existing regime_snapshots before seeding
"""
from __future__ import annotations

import argparse
import json
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Allow running from repo root or backend/
_here = Path(__file__).parent
_backend = _here.parent if _here.name == "scripts" else _here
sys.path.insert(0, str(_backend))

os.chdir(_backend)

from models.database import SessionLocal, RegimeSnapshot, migrate_legacy_data, init_db


# ─── Scenario builders ────────────────────────────────────────────────────────

def _row(
    date_offset: int,
    base_date: datetime,
    regime: str,
    confidence: float,
    trend: float,
    vol: float,
    drawdown: float,
    momentum: float,
    vol_z: float,
    ema_aln: float,
    duration: int,
    prev: str,
    stability: str,
    signals: dict,
) -> dict:
    d = (base_date + timedelta(days=date_offset)).strftime("%Y-%m-%d")
    return {
        "snapshot_date":        d,
        "regime":               regime,
        "confidence":           round(confidence, 3),
        "trend_score":          round(trend, 1),
        "volatility_score":     round(vol, 1),
        "drawdown_score":       round(drawdown, 1),
        "momentum_score":       round(momentum, 1),
        "vol_z_score":          round(vol_z, 2),
        "ema_alignment":        round(ema_aln, 1),
        "regime_duration_days": duration,
        "previous_regime":      prev,
        "transition_stability": stability,
        "signals_json":         json.dumps(signals),
    }


def _sample_signals(trend: float, vol: float) -> dict:
    return {
        "^GSPC": {
            "ema_trend_score": round(trend, 1),
            "vol_score": round(vol, 1),
            "drawdown_score": 80.0,
            "momentum_score": round(trend * 0.9, 1),
            "vol_z_score": round((100 - vol - 50) / 16, 2),
            "return_20d": round((trend - 50) / 10, 2),
            "realized_vol_20d": round(15 + (100 - vol) * 0.15, 1),
        }
    }


SCENARIOS: dict[str, list[dict]] = {}

# Base date: 90 days ago from today
_BASE = datetime.utcnow() - timedelta(days=90)


# ── 1. Bull Market ────────────────────────────────────────────────────────────
def _build_bull(days: int) -> list[dict]:
    rows = []
    for i in range(days):
        trend    = min(95, 70 + i * 0.6)
        vol      = max(55, 85 - i * 0.4)
        momentum = min(92, 65 + i * 0.5)
        rows.append(_row(
            i, _BASE,
            regime     = "RISK_ON",
            confidence = min(0.92, 0.62 + i * 0.01),
            trend      = trend,
            vol        = vol,
            drawdown   = min(95, 80 + i * 0.2),
            momentum   = momentum,
            vol_z      = max(-1.5, -0.5 - i * 0.03),
            ema_aln    = trend,
            duration   = i + 1,
            prev       = "SIDEWAYS" if i < 3 else "RISK_ON",
            stability  = "STABLE" if i >= 5 else "TRANSITIONING",
            signals    = _sample_signals(trend, vol),
        ))
    return rows


# ── 2. Market Crash ───────────────────────────────────────────────────────────
def _build_crash(days: int) -> list[dict]:
    rows = []
    base_day = days + 2
    for i in range(days):
        frac = i / max(days - 1, 1)
        # First third: normal → risk-off transition
        # Middle: crisis HIGH_VOLATILITY
        # Last third: partial recovery
        if frac < 0.3:
            regime     = "TRANSITION_RISK_OFF"
            trend      = 60 - frac * 50
            vol        = 55 + frac * 30
            conf       = 0.55 + frac * 0.15
            stability  = "TRANSITIONING"
            prev       = "RISK_ON"
            vol_z      = frac * 2.0
        elif frac < 0.65:
            regime     = "HIGH_VOLATILITY"
            crash_frac = (frac - 0.3) / 0.35
            trend      = 25 - crash_frac * 5
            vol        = 12 + crash_frac * 8
            conf       = 0.75 + crash_frac * 0.15
            stability  = "VOLATILE"
            prev       = "TRANSITION_RISK_OFF"
            vol_z      = 2.5 + crash_frac * 1.0
        else:
            regime     = "RISK_OFF"
            recov_frac = (frac - 0.65) / 0.35
            trend      = 20 + recov_frac * 20
            vol        = 30 + recov_frac * 20
            conf       = 0.65 - recov_frac * 0.10
            stability  = "TRANSITIONING" if recov_frac > 0.5 else "STABLE"
            prev       = "HIGH_VOLATILITY"
            vol_z      = 2.0 - recov_frac * 1.5

        rows.append(_row(
            base_day + i, _BASE,
            regime     = regime,
            confidence = conf,
            trend      = trend,
            vol        = vol,
            drawdown   = max(10, 70 - frac * 60),
            momentum   = max(15, 55 - frac * 40),
            vol_z      = vol_z,
            ema_aln    = trend,
            duration   = i + 1,
            prev       = prev,
            stability  = stability,
            signals    = _sample_signals(trend, vol),
        ))
    return rows


# ── 3. Sideways Chop ─────────────────────────────────────────────────────────
def _build_sideways(days: int) -> list[dict]:
    import math
    rows = []
    base_day = days * 2 + 4
    for i in range(days):
        noise = math.sin(i * 0.8) * 6 + math.sin(i * 1.3) * 4
        trend    = 50 + noise
        vol      = 55 + abs(noise) * 0.5
        regimes  = ["SIDEWAYS", "TRANSITION_RISK_ON", "SIDEWAYS", "TRANSITION_RISK_OFF"]
        regime   = regimes[i % len(regimes)]
        rows.append(_row(
            base_day + i, _BASE,
            regime     = regime,
            confidence = 0.40 + abs(noise) * 0.01,
            trend      = trend,
            vol        = vol,
            drawdown   = 65 + noise * 0.3,
            momentum   = 50 + noise * 0.8,
            vol_z      = noise * 0.05,
            ema_aln    = trend,
            duration   = (i % 5) + 1,
            prev       = regimes[(i - 1) % len(regimes)],
            stability  = "VOLATILE",
            signals    = _sample_signals(trend, vol),
        ))
    return rows


# ── 4. Volatility Spike ───────────────────────────────────────────────────────
def _build_vol_spike(days: int) -> list[dict]:
    rows = []
    base_day = days * 3 + 6
    spike_center = days // 3
    for i in range(days):
        dist = abs(i - spike_center)
        spike_intensity = max(0, 1 - dist / (days / 4))

        if spike_intensity > 0.6:
            regime    = "HIGH_VOLATILITY"
            trend     = 40 - spike_intensity * 20
            vol       = 15 + spike_intensity * 10
            vol_z     = 2.0 + spike_intensity * 1.5
            conf      = 0.75 + spike_intensity * 0.15
            stability = "VOLATILE"
            prev      = "SIDEWAYS"
        elif spike_intensity > 0.2:
            regime    = "TRANSITION_RISK_OFF" if i < spike_center else "SIDEWAYS"
            trend     = 50 - spike_intensity * 15
            vol       = 45 + spike_intensity * 15
            vol_z     = spike_intensity * 2.0
            conf      = 0.50 + spike_intensity * 0.20
            stability = "TRANSITIONING"
            prev      = "SIDEWAYS" if i < spike_center else "HIGH_VOLATILITY"
        else:
            regime    = "SIDEWAYS"
            trend     = 55.0
            vol       = 65.0
            vol_z     = 0.1
            conf      = 0.50
            stability = "STABLE"
            prev      = "HIGH_VOLATILITY" if i > spike_center else "RISK_ON"

        rows.append(_row(
            base_day + i, _BASE,
            regime     = regime,
            confidence = conf,
            trend      = trend,
            vol        = vol,
            drawdown   = max(20, 75 - spike_intensity * 50),
            momentum   = max(15, 55 - spike_intensity * 35),
            vol_z      = vol_z,
            ema_aln    = trend,
            duration   = dist + 1,
            prev       = prev,
            stability  = stability,
            signals    = _sample_signals(trend, vol),
        ))
    return rows


# ── 5. Defensive Recession ────────────────────────────────────────────────────
def _build_defensive(days: int) -> list[dict]:
    rows = []
    base_day = days * 4 + 8
    for i in range(days):
        frac = i / max(days - 1, 1)
        if frac < 0.25:
            regime    = "SIDEWAYS"
            trend     = 52 - frac * 20
            vol       = 62 - frac * 10
            stability = "TRANSITIONING"
            prev      = "RISK_ON"
            conf      = 0.48
        elif frac < 0.6:
            regime    = "DEFENSIVE_REGIME"
            trend     = 38 - (frac - 0.25) * 10
            vol       = 60 + (frac - 0.25) * 5
            stability = "STABLE" if frac > 0.4 else "TRANSITIONING"
            prev      = "SIDEWAYS" if i < 10 else "DEFENSIVE_REGIME"
            conf      = 0.60 + (frac - 0.25) * 0.15
        else:
            regime    = "RISK_OFF"
            trend     = 30 - (frac - 0.6) * 8
            vol       = 40 + (frac - 0.6) * 20
            stability = "TRANSITIONING"
            prev      = "DEFENSIVE_REGIME"
            conf      = 0.65

        rows.append(_row(
            base_day + i, _BASE,
            regime     = regime,
            confidence = conf,
            trend      = trend,
            vol        = vol,
            drawdown   = max(25, 75 - frac * 50),
            momentum   = max(20, 58 - frac * 40),
            vol_z      = frac * 1.5,
            ema_aln    = trend,
            duration   = i + 1,
            prev       = prev,
            stability  = stability,
            signals    = _sample_signals(trend, vol),
        ))
    return rows


# ─── DB operations ────────────────────────────────────────────────────────────

def seed(rows: list[dict], clear: bool = False) -> None:
    """Upsert rows into regime_snapshots. Skips rows that would collide with real data."""
    db = SessionLocal()
    try:
        if clear:
            db.query(RegimeSnapshot).delete()
            db.commit()
            print(f"  Cleared existing regime_snapshots")

        inserted = 0
        skipped  = 0
        for row in rows:
            existing = db.query(RegimeSnapshot).filter_by(snapshot_date=row["snapshot_date"]).first()
            if existing:
                skipped += 1
                continue
            db.add(RegimeSnapshot(**row))
            inserted += 1

        db.commit()
        print(f"  Inserted {inserted} rows, skipped {skipped} duplicates")
    finally:
        db.close()


# ─── Main ─────────────────────────────────────────────────────────────────────

SCENARIO_MAP = {
    "bull":      ("Bull Market",        _build_bull),
    "crash":     ("Market Crash",       _build_crash),
    "sideways":  ("Sideways Chop",      _build_sideways),
    "vol_spike": ("Volatility Spike",   _build_vol_spike),
    "defensive": ("Defensive Recession",_build_defensive),
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed regime scenario data")
    parser.add_argument("--scenario", default="all",
                        choices=["all"] + list(SCENARIO_MAP),
                        help="Which scenario to seed")
    parser.add_argument("--days", type=int, default=18,
                        help="Trading days per scenario block (default: 18)")
    parser.add_argument("--clear", action="store_true",
                        help="Delete all existing regime_snapshots before seeding")
    args = parser.parse_args()

    print("Initialising database…")
    init_db()
    migrate_legacy_data()

    to_run = list(SCENARIO_MAP.items()) if args.scenario == "all" else [(args.scenario, SCENARIO_MAP[args.scenario])]

    for key, (name, builder) in to_run:
        print(f"\n[{key}] {name} ({args.days} days)…")
        rows = builder(args.days)
        seed(rows, clear=(args.clear and key == to_run[0][0]))

    print("\nDone. Run the backend and call GET /analytics/market-regime to verify.\n")


if __name__ == "__main__":
    main()
