"""Declaration fingerprints (M9 TDD Section 5.4).

A published (definition, version) transcription is immutable (D8). The
fingerprint is what makes that checkable rather than merely asserted: a
digest over the declaration payload only (never name/version/binding/
source_document/fingerprint itself), computed the same way every time a
canonical serialization can produce. The registry recomputes this at every
boot and compares it against the pinned manifest in library.py — a mismatch
means a published version's declarations moved after publication, and the
platform refuses to start (constitution risk 10.8, retroactive redefinition).

Deliberately excludes name/version/binding/source_document/effective_from:
those are governance bookkeeping, not the treaty itself, and the treaty is
what must never move.
"""
from __future__ import annotations

import hashlib
from typing import Any, Tuple

from services.asset_definitions.declarations import (
    AcquisitionDeclaration,
    DefinitionTranscription,
    EventFamilyGrants,
    ExistenceDeclaration,
    FlowGrants,
    SettlementDeclaration,
    UnitDeclaration,
    ValuationDeclaration,
)


def _canonical(value: Any) -> Any:
    """Recursively reduces a declaration structure to a plain, sorted,
    hashable tuple form — the same shape every time regardless of
    frozenset iteration order or enum identity."""
    if isinstance(value, UnitDeclaration):
        return (
            "UnitDeclaration",
            value.divisibility.value,
            value.quantity_equals_value,
            value.allows_negative,
            value.permits_fractional_refinement,
            value.permits_lot_refinement,
        )
    if isinstance(value, AcquisitionDeclaration):
        return ("AcquisitionDeclaration", value.semantics.value)
    if isinstance(value, SettlementDeclaration):
        return ("SettlementDeclaration", value.pattern.value, value.permits_cycle_length_refinement)
    if isinstance(value, ValuationDeclaration):
        return ("ValuationDeclaration", value.question.value)
    if isinstance(value, FlowGrants):
        return ("FlowGrants", tuple(sorted(item.value for item in value.granted)))
    if isinstance(value, EventFamilyGrants):
        return ("EventFamilyGrants", tuple(sorted(item.value for item in value.granted)))
    if isinstance(value, ExistenceDeclaration):
        return (
            "ExistenceDeclaration",
            value.pattern.value,
            tuple(sorted(item.value for item in value.permitted_relationships)),
            tuple(sorted(item.value for item in value.mandatory_relationships)),
        )
    raise TypeError(f"fingerprint._canonical: unrecognized declaration type {type(value)!r}")


def canonical_payload(transcription: DefinitionTranscription) -> Tuple[Any, ...]:
    """The declaration-only payload a fingerprint is computed over."""
    return (
        _canonical(transcription.unit),
        _canonical(transcription.acquisition),
        _canonical(transcription.settlement),
        _canonical(transcription.valuation),
        _canonical(transcription.flows),
        _canonical(transcription.event_families),
        _canonical(transcription.existence),
    )


def compute_fingerprint(transcription: DefinitionTranscription) -> str:
    payload = repr(canonical_payload(transcription)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
