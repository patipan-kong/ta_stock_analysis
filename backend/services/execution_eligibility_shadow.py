"""Rollback-only Registry resolution for M31.3 eligibility observation.

The authoritative identity resolver may record ambiguity findings as part of
normal Registry adjudication.  A shadow consultation must not persist even
that evidence, so this adapter runs the existing batch facts resolver inside a
savepoint that is always rolled back.  Returned facts are immutable plain
values and remain usable after the savepoint closes.
"""
from __future__ import annotations

from typing import Dict, Sequence

from sqlalchemy.orm import Session

from services.execution_instrument_facts import (
    ExecutionInstrumentFacts,
    resolve_execution_instruments,
)

__all__ = ["resolve_execution_eligibility_shadow_facts"]


def resolve_execution_eligibility_shadow_facts(
    db: Session,
    symbols: Sequence[str],
) -> Dict[str, ExecutionInstrumentFacts]:
    """Resolve a complete shadow symbol set without retaining Registry writes."""

    savepoint = db.begin_nested()
    try:
        resolved = resolve_execution_instruments(db, symbols)
    finally:
        if savepoint.is_active:
            savepoint.rollback()
    return {str(symbol): facts for symbol, facts in resolved.items()}
