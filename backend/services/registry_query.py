"""Asset Registry — cross-historical read queries (Milestone M2).

M1's asset_repository.find_current_identifier only searches *current*
AssetIdentifier rows. It deliberately does not need more than that — M1's
own consumer (attach_identifier's conflict check) only ever cares about
live conflicts. The Registry Service boundary, however, must also answer
"has this identifier ever been used, by anyone, at any time" (a ticker
retired in 2024 must still resolve correctly when a 2023 statement is
imported in 2028 — ASSET_REGISTRY.md Section 2). That is a new read, not a
new rule, so it lives here rather than in asset_repository.py.
"""
from __future__ import annotations

from typing import Sequence

from sqlalchemy.orm import Session

from models.asset import AssetIdentifier


def find_identifier_rows(
    db: Session, identifier_type: str, value: str,
) -> Sequence[AssetIdentifier]:
    """All AssetIdentifier rows — current or historical — matching this
    (type, value) pair, oldest first. May span more than one asset_id if
    the identifier value has been reused over time."""
    return (
        db.query(AssetIdentifier)
        .filter(
            AssetIdentifier.identifier_type == identifier_type,
            AssetIdentifier.value == value,
        )
        .order_by(AssetIdentifier.created_at.asc())
        .all()
    )
