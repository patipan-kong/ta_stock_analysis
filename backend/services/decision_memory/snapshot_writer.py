"""snapshot_writer.py — Phase 3B.7

Writes a RecommendationSnapshot row immediately after every successful
3-layer optimizer run.  Called from the analyze_optimizer endpoint in main.py
after OptimizerHistory is committed, before the HTTP response is returned.

Design contract:
  - Idempotent on optimizer_history_id (UNIQUE constraint).
  - Never raises — any failure is logged and swallowed so the optimizer
    response still reaches the client.
  - Stores only serialisable subsets of the full result dict to avoid
    bloating the snapshot with transient / computed UI fields.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_SKIP_TOP_LEVEL_KEYS = frozenset({
    # transient UI fields already persisted in optimizer_history.result_json
    "swap_suggestions", "watchlist_ranking", "no_action_reason",
    "no_action_summary", "blocked_opportunities",
    # heavy raw text not needed for attribution
    "prompt_block",
})


def write_recommendation_snapshot(
    db: Session,
    workspace_id: int,
    portfolio_id: int,
    optimizer_history_id: int,
    optimizer_result: dict[str, Any],
    *,
    persona: str | None = None,
    total_portfolio_value: float | None = None,
    scores_map: dict | None = None,
) -> int | None:
    """Persist a RecommendationSnapshot from the raw optimizer result dict.

    Returns the new snapshot id, or None on failure.
    """
    from models.database import RecommendationSnapshot  # local import avoids circular

    def _j(obj: Any) -> str | None:
        if obj is None:
            return None
        try:
            return json.dumps(obj, default=str)
        except Exception:
            return None

    try:
        # Check idempotency — skip if already written for this run
        existing = (
            db.query(RecommendationSnapshot)
            .filter_by(optimizer_history_id=optimizer_history_id)
            .first()
        )
        if existing:
            return existing.id

        r = optimizer_result

        snap = RecommendationSnapshot(
            workspace_id=workspace_id,
            optimizer_history_id=optimizer_history_id,
            portfolio_id=portfolio_id,
            persona=persona or r.get("target_persona"),
            total_portfolio_value=total_portfolio_value,
            regime_snapshot_json=_j(r.get("market_regime")),
            constraint_envelope_json=_j(r.get("effective_envelope")),
            active_policy_json=_j(r.get("active_policy")),
            layer1_output_json=_j(r.get("layer1")),
            layer2_output_json=_j(r.get("layer2")),
            layer3_output_json=_j(r.get("layer3")),
            consensus_json=_j(r.get("consensus")),
            portfolio_dna_json=_j(r.get("current_portfolio_dna")),
            style_drift_json=_j({
                "drift_score": r.get("style_drift_score"),
                "drift_severity": r.get("style_drift_severity"),
                "factor_alignment_score": r.get("factor_alignment_score"),
                "factor_drift": r.get("factor_drift"),
                "rebalance_urgency": r.get("rebalance_urgency"),
            }),
            scores_map_json=_j(scores_map),
            projected_allocations_json=_j(
                (r.get("layer2") or {}).get("allocations")
            ),
            created_at=datetime.utcnow(),
        )
        db.add(snap)
        db.commit()
        db.refresh(snap)
        logger.info("[DECISION_MEMORY] RecommendationSnapshot written id=%s for optimizer_history_id=%s", snap.id, optimizer_history_id)
        return snap.id

    except Exception as exc:
        logger.warning("[DECISION_MEMORY] Failed to write RecommendationSnapshot: %s", exc)
        db.rollback()
        return None
