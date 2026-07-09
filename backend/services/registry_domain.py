"""Asset Registry — service-boundary vocabulary (Milestone M2).

Extends services/asset_domain.py (M1, untouched) with the vocabulary needed
for the findings/adjudication surface. Kept in a separate module rather
than appended to asset_domain.py so M1's frozen file stays untouched.
"""
from __future__ import annotations

from enum import Enum


class FindingType(str, Enum):
    """What the Registry observed. A small, closed set — adding a new kind
    of finding is a genuine engineering event, same rationale as the
    structural enums in asset_domain.py."""

    DUPLICATE_CLAIM = "DUPLICATE_CLAIM"
    IDENTIFIER_CONFLICT = "IDENTIFIER_CONFLICT"
    MERGE_RECORDED = "MERGE_RECORDED"


class FindingStatus(str, Enum):
    """Adjudication state of a finding. RESOLVED/DISMISSED findings are
    retained permanently — this is a closure marker, not deletion."""

    OPEN = "OPEN"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"


class FindingResolution(str, Enum):
    """What a human (or a composed operation like record_merge) decided
    about a finding once adjudicated."""

    MERGED = "MERGED"
    CONFIRMED_DISTINCT = "CONFIRMED_DISTINCT"
    DISMISSED = "DISMISSED"
