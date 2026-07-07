"""UX.2D — Structured Override Classifier.

Pure functions only.  No AI calls.  No DB writes.

See OPTIMIZER_PHILOSOPHY.md §13 — an override is the most valuable data
point the system receives; classify it, never discard or overwrite it.
"""
from __future__ import annotations

from typing import Literal

OverrideCategory = Literal[
    "REJECT_SWAP",
    "REPLACE_SYMBOL",
    "INCREASE_CONVICTION",
    "REDUCE_CONVICTION",
    "HOLD_POSITION",
    "CUSTOM",
]

_VALID_CATEGORIES: frozenset[str] = frozenset({
    "REJECT_SWAP",
    "REPLACE_SYMBOL",
    "INCREASE_CONVICTION",
    "REDUCE_CONVICTION",
    "HOLD_POSITION",
    "CUSTOM",
})


def classify_override(raw: str | None) -> str:
    """Normalise and validate an override category string.

    Returns 'CUSTOM' for None or unrecognised values.
    """
    if raw is None:
        return "CUSTOM"
    upper = raw.strip().upper()
    return upper if upper in _VALID_CATEGORIES else "CUSTOM"


def build_override_record(
    override_type: str | None,
    original_symbol: str | None,
    replacement_symbol: str | None,
    reason_category: str | None,
    notes: str | None,
) -> dict:
    """Build a validated override record dict ready for DB storage.

    All structured fields are optional; notes validation is the API layer's concern.
    """
    return {
        "override_type": classify_override(override_type) if override_type else None,
        "original_symbol": original_symbol.strip().upper() if original_symbol else None,
        "replacement_symbol": replacement_symbol.strip().upper() if replacement_symbol else None,
        "reason_category": reason_category.strip() if reason_category else None,
        "override_notes": notes,
    }
