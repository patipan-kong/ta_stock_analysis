"""expired_writer.py — AI Evaluation M1: EXPIRED decision semantics (P4).

A recommendation snapshot with no recorded UserExecutionDecision becomes
EXPIRED — written as a `UserExecutionDecision(decision="EXPIRED",
is_system_generated=True)` row — when either:

  1. Superseded: a newer snapshot for the same portfolio has received any
     decision (including a prior EXPIRED write), or
  2. Aged out: it is >= evaluation_settings.expiry_days old (default 14),

whichever happens first. EXPIRED counts as "ignored" in Human-vs-AI and
opportunity cost (downstream milestones).

Runs once per scheduler pass, before grade_due_recommendations (a snapshot
that expires today should be gradable as EXPIRED-and-ungraded starting
today, not one day later).

Constraints: see services/evaluation/__init__.py. This module writes
UserExecutionDecision rows — which constraint #1 in PLAN §4 explicitly
carves out as decision-recording, not evaluation — but never touches
RecommendationSnapshot, Transaction, or shadow data. Zero AI calls (P6).

Public API
----------
write_expired_decisions(db) -> dict
    {"written": [{"snapshot_id", "portfolio_id", "reason"}, ...]}
"""
from __future__ import annotations

import logging
from datetime import datetime, date
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def write_expired_decisions(db: Session) -> dict[str, Any]:
    """Write EXPIRED decisions for undecided, superseded-or-aged-out snapshots.

    Processes every workspace. Within each portfolio, walks snapshots newest
    to oldest so that a snapshot EXPIRED earlier in this same pass correctly
    supersedes older undecided siblings in the same pass (no need to wait for
    the next scheduler run to cascade).
    """
    from main import _get_evaluation_settings
    from models.database import RecommendationSnapshot, UserExecutionDecision, Workspace

    written: list[dict] = []
    today = date.today()

    for ws in db.query(Workspace).all():
        settings = _get_evaluation_settings(db, ws.id)
        expiry_days = int(settings.get("expiry_days") or 14)

        snaps = (
            db.query(RecommendationSnapshot)
            .filter(RecommendationSnapshot.workspace_id == ws.id)
            .all()
        )
        decided_snapshot_ids = {
            row.recommendation_snapshot_id
            for row in db.query(UserExecutionDecision.recommendation_snapshot_id)
            .filter(UserExecutionDecision.workspace_id == ws.id)
            .all()
        }

        by_portfolio: dict[int, list] = {}
        for s in snaps:
            by_portfolio.setdefault(s.portfolio_id, []).append(s)

        for portfolio_id, portfolio_snaps in by_portfolio.items():
            portfolio_snaps.sort(key=lambda s: s.created_at or datetime.min, reverse=True)

            has_newer_decided = False
            for snap in portfolio_snaps:
                if snap.id in decided_snapshot_ids:
                    has_newer_decided = True
                    continue

                if not snap.created_at:
                    continue
                age_days = (today - snap.created_at.date()).days

                if has_newer_decided:
                    reason = "superseded"
                elif age_days >= expiry_days:
                    reason = "aged_out"
                else:
                    continue

                decision = UserExecutionDecision(
                    workspace_id=ws.id,
                    recommendation_snapshot_id=snap.id,
                    portfolio_id=portfolio_id,
                    decision="EXPIRED",
                    is_system_generated=True,
                    executed_at=datetime.utcnow(),
                    created_at=datetime.utcnow(),
                )
                try:
                    db.add(decision)
                    db.commit()
                except Exception as exc:
                    db.rollback()
                    logger.warning(
                        "[EVAL] EXPIRED write failed snapshot_id=%s: %s", snap.id, exc,
                    )
                    continue

                decided_snapshot_ids.add(snap.id)
                has_newer_decided = True
                written.append({
                    "snapshot_id": snap.id, "portfolio_id": portfolio_id, "reason": reason,
                })
                logger.info(
                    "[EVAL] Wrote EXPIRED decision for snapshot_id=%s portfolio_id=%s (%s)",
                    snap.id, portfolio_id, reason,
                )

    return {"written": written}
