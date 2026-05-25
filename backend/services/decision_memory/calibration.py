"""calibration.py — Phase 3B.7 structural stub

Confidence Calibration Feedback Loop.

Purpose
-------
Evaluates whether the AI system's confidence scores (consensus_strength_score,
policy_alignment_score, regime confidence) predicted real outcomes over a
lookback window.  The calibration results are stored and the
`feedback_context_json` field is designed to be injected back into future
optimizer AI prompts — closing the feedback loop between past performance
and agent reasoning.

Calibration dimensions
----------------------
1. consensus_strength_calibration : Was a high consensus_strength_score
   predictive of the direction being correct?  Measured by comparing
   signal_history actions to price outcomes after N days.

2. policy_alignment_calibration   : When policy_alignment_score was high,
   did the portfolio stay within mandate constraints?  (No constraint
   violations reported in subsequent runs.)

3. regime_confidence_calibration  : When regime confidence was ≥70%,
   did the regime stay stable over the next N days?  (RegimeSnapshot
   continuity check.)

Overall calibration_score = weighted average of the three dimensions (0–100).

Feedback context block
----------------------
The `feedback_context_json` is a structured dict that the optimizer agent
can be given as context:

{
  "calibration_period": "2026-04-25 → 2026-05-25",
  "calibration_score": 72.4,
  "insights": [
    "Consensus signals ≥80 were directionally correct 84% of the time over the past 30 days.",
    "Regime confidence >70% maintained stability for 26/30 days.",
    "Policy alignment score showed weak predictive power this period — consider regime uncertainty."
  ],
  "recommended_adjustments": {
    "consensus_weight_modifier": 1.05,
    "regime_confidence_threshold": 0.72,
    "policy_strictness_nudge": "NORMAL"
  }
}

Architecture notes
------------------
This is a **structural stub**.  The scaffolding and DB persistence are
complete.  Actual calibration math requires:
  - At least N days of SignalHistory with realized prices (price_at_signal
    + a follow-up price after lookback_days).
  - RegimeSnapshot continuity data.
  - Policy violation tracking across consecutive optimizer runs.

To complete this stub, implement _compute_signal_accuracy(),
_compute_regime_stability(), and _compute_policy_compliance() below.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, date, timedelta
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


# ─── Calibration sub-computations (stubs) ────────────────────────────────────

def _compute_signal_accuracy(
    db: Session,
    workspace_id: int,
    lookback_days: int,
) -> dict[str, Any]:
    """Compare SignalHistory direction predictions to current prices via AgentCache.

    For signals recorded ≥14 days ago with a known entry price, fetches the
    most recent cached technical analysis price for each symbol to evaluate
    whether the direction (BUY/ACCUMULATE → up, SELL/REDUCE → down) was correct.

    Groups accuracy by score_at_signal bucket:
      HIGH   : score ≥ 70
      MEDIUM : 40 ≤ score < 70
      LOW    : score < 40

    Correctness uses only AgentCache data — no yfinance calls, no blocking I/O.
    """
    import json as _json
    from models.database import SignalHistory, AgentCache

    # Only evaluate signals old enough for meaningful outcome (≥14 days)
    min_age_days = 14
    evaluation_cutoff = (date.today() - timedelta(days=min_age_days)).isoformat()
    window_cutoff = (date.today() - timedelta(days=lookback_days)).isoformat()

    rows = (
        db.query(SignalHistory)
        .filter(
            SignalHistory.workspace_id == workspace_id,
            SignalHistory.recorded_at >= window_cutoff,
            SignalHistory.recorded_at <= evaluation_cutoff,
            SignalHistory.price_at_signal.isnot(None),
            SignalHistory.action.in_(["BUY", "ACCUMULATE", "SELL", "REDUCE"]),
        )
        .all()
    )

    if not rows:
        return {
            "total_signals": 0,
            "evaluated": 0,
            "directionally_correct": None,
            "accuracy_pct": None,
            "buckets": {},
            "note": "No signals with entry prices found in evaluation window.",
        }

    # Build symbol → current_price map from AgentCache (technical agent)
    symbols = {r.symbol for r in rows}
    price_map: dict[str, float] = {}
    for sym in symbols:
        cache = db.query(AgentCache).filter_by(symbol=sym, agent="technical").first()
        if not cache:
            continue
        try:
            data = _json.loads(cache.result_json)
            price = (
                data.get("current_price")
                or data.get("price")
                or data.get("close")
            )
            if price and isinstance(price, (int, float)) and price > 0:
                price_map[sym] = float(price)
        except Exception:
            pass

    # Evaluate each signal
    buckets: dict[str, dict[str, Any]] = {
        "HIGH":   {"correct": 0, "total": 0, "score_range": "≥70"},
        "MEDIUM": {"correct": 0, "total": 0, "score_range": "40–69"},
        "LOW":    {"correct": 0, "total": 0, "score_range": "<40"},
    }

    evaluated = 0
    correct_total = 0

    for row in rows:
        current_price = price_map.get(row.symbol)
        if current_price is None:
            continue

        entry_price = row.price_at_signal
        if not entry_price or entry_price <= 0:
            continue

        # Direction check
        bullish_action = row.action in ("BUY", "ACCUMULATE")
        price_went_up = current_price > entry_price
        is_correct = bullish_action == price_went_up

        # Assign to bucket
        score = row.score_at_signal or 50.0
        if score >= 70:
            bucket_key = "HIGH"
        elif score >= 40:
            bucket_key = "MEDIUM"
        else:
            bucket_key = "LOW"

        buckets[bucket_key]["total"] += 1
        if is_correct:
            buckets[bucket_key]["correct"] += 1
            correct_total += 1
        evaluated += 1

    # Compute accuracy per bucket
    for bk in buckets.values():
        bk["accuracy_pct"] = (
            round(bk["correct"] / bk["total"] * 100, 2)
            if bk["total"] > 0 else None
        )

    overall_accuracy = round(correct_total / evaluated * 100, 2) if evaluated > 0 else None

    return {
        "total_signals": len(rows),
        "evaluated": evaluated,
        "symbols_with_price": len(price_map),
        "directionally_correct": correct_total,
        "accuracy_pct": overall_accuracy,
        "buckets": buckets,
        "note": (
            "First-pass signal accuracy using AgentCache prices. "
            "Accuracy improves as more cached prices accumulate."
        ),
    }


def _compute_regime_stability(
    db: Session,
    lookback_days: int,
) -> dict[str, Any]:
    """Check whether high-confidence regime calls remained stable.

    STUB — requires consecutive RegimeSnapshot rows.
    """
    from models.database import RegimeSnapshot
    cutoff = (date.today() - timedelta(days=lookback_days)).isoformat()
    snapshots = (
        db.query(RegimeSnapshot)
        .filter(RegimeSnapshot.snapshot_date >= cutoff)
        .order_by(RegimeSnapshot.snapshot_date)
        .all()
    )
    if len(snapshots) < 2:
        return {"stable_days": None, "total_days": len(snapshots), "stub": True}

    high_conf = [s for s in snapshots if s.confidence >= 0.70]
    stable = sum(
        1 for i in range(1, len(high_conf))
        if high_conf[i].regime == high_conf[i - 1].regime
    )
    return {
        "high_confidence_days": len(high_conf),
        "stable_transitions": stable,
        "stability_rate": round(stable / max(len(high_conf) - 1, 1) * 100, 2) if high_conf else None,
        "stub": False,
    }


def _compute_policy_compliance(
    db: Session,
    workspace_id: int,
    lookback_days: int,
) -> dict[str, Any]:
    """Assess whether high policy_alignment_score runs avoided subsequent violations.

    STUB — requires parsing governance_flags from consecutive OptimizerHistory rows.
    """
    return {"compliance_rate": None, "evaluated_runs": 0, "stub": True}


# ─── Main calibration entry point ─────────────────────────────────────────────

def compute_calibration(
    db: Session,
    workspace_id: int,
    lookback_days: int = 30,
    optimizer_history_id: int | None = None,
    recommendation_snapshot_id: int | None = None,
) -> dict[str, Any]:
    """Run all calibration sub-computations and persist a ConfidenceCalibrationRecord.

    Returns the full calibration result dict including the feedback_context_json
    block ready for injection into AI prompts.
    """
    from models.database import ConfidenceCalibrationRecord

    signal_acc = _compute_signal_accuracy(db, workspace_id, lookback_days)
    regime_stab = _compute_regime_stability(db, lookback_days)
    policy_comp = _compute_policy_compliance(db, workspace_id, lookback_days)

    # Weighted calibration score (equal thirds until non-stub dimensions available)
    scores = []
    if signal_acc.get("accuracy_pct") is not None:
        scores.append(signal_acc["accuracy_pct"])
    if regime_stab.get("stability_rate") is not None:
        scores.append(regime_stab["stability_rate"])
    if policy_comp.get("compliance_rate") is not None:
        scores.append(policy_comp["compliance_rate"])

    calibration_score = round(sum(scores) / len(scores), 2) if scores else None

    period_start = (date.today() - timedelta(days=lookback_days)).isoformat()
    period_end = date.today().isoformat()

    # Build feedback context block for AI prompt injection
    insights = []
    if regime_stab.get("stability_rate") is not None:
        r = regime_stab["stability_rate"]
        insights.append(
            f"Regime calls ≥70% confidence maintained stability {r:.1f}% of the time "
            f"over the past {lookback_days} days."
        )
    if signal_acc.get("accuracy_pct") is not None:
        acc = signal_acc["accuracy_pct"]
        evaluated = signal_acc.get("evaluated", 0)
        insights.append(
            f"Signal directional accuracy: {acc:.1f}% over {evaluated} evaluated signals "
            f"(14-day minimum holding period, {lookback_days}-day window)."
        )
        buckets = signal_acc.get("buckets", {})
        high_acc = buckets.get("HIGH", {}).get("accuracy_pct")
        if high_acc is not None:
            insights.append(
                f"HIGH-confidence signals (score ≥70) were directionally correct "
                f"{high_acc:.1f}% of the time."
            )
    if not insights:
        insights.append(
            f"Calibration period {period_start} → {period_end}: "
            f"insufficient history for full scoring — {lookback_days}-day lookback active."
        )

    feedback_context = {
        "calibration_period": f"{period_start} → {period_end}",
        "lookback_days": lookback_days,
        "calibration_score": calibration_score,
        "signal_accuracy": signal_acc,
        "regime_stability": regime_stab,
        "policy_compliance": policy_comp,
        "insights": insights,
        "recommended_adjustments": {},  # populated by future non-stub computation
    }

    result = {
        "workspace_id": workspace_id,
        "lookback_days": lookback_days,
        "calibration_score": calibration_score,
        "consensus_strength_calibration": signal_acc.get("accuracy_pct"),
        "policy_alignment_calibration": policy_comp.get("compliance_rate"),
        "regime_confidence_calibration": regime_stab.get("stability_rate"),
        "signal_accuracy_json": signal_acc,
        "feedback_context": feedback_context,
        "computed_at": datetime.utcnow().isoformat() + "Z",
    }

    try:
        record = ConfidenceCalibrationRecord(
            workspace_id=workspace_id,
            optimizer_history_id=optimizer_history_id,
            recommendation_snapshot_id=recommendation_snapshot_id,
            lookback_days=lookback_days,
            consensus_strength_calibration=signal_acc.get("accuracy_pct"),
            policy_alignment_calibration=policy_comp.get("compliance_rate"),
            regime_confidence_calibration=regime_stab.get("stability_rate"),
            signal_accuracy_json=json.dumps(signal_acc, default=str),
            calibration_score=calibration_score,
            feedback_context_json=json.dumps(feedback_context, default=str),
            computed_at=datetime.utcnow(),
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        result["calibration_record_id"] = record.id
        logger.info("[CALIBRATION] Record id=%s written for workspace_id=%s lookback=%s", record.id, workspace_id, lookback_days)
    except Exception as exc:
        logger.warning("[CALIBRATION] DB write failed: %s", exc)
        db.rollback()

    return result


def get_latest_calibration(db: Session, workspace_id: int) -> dict[str, Any] | None:
    """Return the most recent calibration record for the workspace as a dict."""
    from models.database import ConfidenceCalibrationRecord

    row = (
        db.query(ConfidenceCalibrationRecord)
        .filter_by(workspace_id=workspace_id)
        .order_by(ConfidenceCalibrationRecord.computed_at.desc())
        .first()
    )
    if not row:
        return None
    return {
        "id": row.id,
        "lookback_days": row.lookback_days,
        "calibration_score": row.calibration_score,
        "consensus_strength_calibration": row.consensus_strength_calibration,
        "policy_alignment_calibration": row.policy_alignment_calibration,
        "regime_confidence_calibration": row.regime_confidence_calibration,
        "feedback_context": (
            json.loads(row.feedback_context_json) if row.feedback_context_json else None
        ),
        "computed_at": row.computed_at.isoformat() + "Z" if row.computed_at else None,
    }
