"""Phase 4C.6A — Allocation Period Engine.

Deterministic timeline construction: groups RecommendationSnapshots for a
portfolio into non-overlapping, non-negative-duration periods.  No AI calls.
No scoring.  Pure calendar arithmetic.

Public API
----------
build_allocation_periods(portfolio_id, workspace_id, db) -> list[AllocationPeriod]
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel
from sqlalchemy.orm import Session


class AllocationPeriod(BaseModel):
    recommendation_snapshot_id: int
    start_date: datetime
    end_date: Optional[datetime]
    days_active: int
    is_current: bool


def build_allocation_periods(
    portfolio_id: int,
    workspace_id: int,
    db: Session,
) -> list[AllocationPeriod]:
    """Return chronologically-sorted, non-overlapping allocation periods.

    Each period spans from one RecommendationSnapshot's created_at to the
    moment the next snapshot replaced it.  The most-recent snapshot is
    open-ended (end_date=None, is_current=True).

    Guarantees:
    - Sorted ascending by start_date
    - No overlaps
    - days_active >= 1 (even for same-day replacements)
    """
    from models.database import RecommendationSnapshot  # local to avoid circular import

    rows = (
        db.query(RecommendationSnapshot)
        .filter_by(portfolio_id=portfolio_id, workspace_id=workspace_id)
        .order_by(RecommendationSnapshot.created_at.asc())
        .all()
    )

    if not rows:
        return []

    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    periods: list[AllocationPeriod] = []

    for i, snap in enumerate(rows):
        start = _to_utc(snap.created_at)
        is_last = i == len(rows) - 1

        if is_last:
            end = None
            days = max(1, (now - start).days + 1)
        else:
            # End is the moment before the next snapshot starts.
            # For day-resolution purposes, end_date = next.created_at.
            end = _to_utc(rows[i + 1].created_at)
            days = max(1, (end - start).days)

        periods.append(
            AllocationPeriod(
                recommendation_snapshot_id=snap.id,
                start_date=start,
                end_date=end,
                days_active=days,
                is_current=is_last,
            )
        )

    return periods


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_utc(dt: datetime) -> datetime:
    """Ensure a datetime is UTC-aware (DB values may be naive UTC)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
