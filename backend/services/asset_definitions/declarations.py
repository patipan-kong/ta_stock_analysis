"""Frozen declaration structures — the transcription target.

Per M9 TDD Section 3.1: a transcription carries a Capability Projection
table's content and nothing else. Every field here corresponds to one cell
of one row of a canonical document's table; no field exists to carry
purpose, reasoning, challenged alternatives, or version-scope prose — the
dataclasses below are structurally incapable of holding that content (M9 TDD
Section 6.1's "the transcription structure is incapable of representing
[logic/prose]" made literal: there is no field to put it in).

Every collection field is a frozenset, never a list — duplicate grants are
not a validation rule here, they are a type that cannot be constructed
(M9 TDD Section 6.1, "duplicate capability ids" collapses to "not
representable").
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import FrozenSet, Optional

from services.asset_definitions.vocabulary import (
    AcquisitionSemantics,
    Divisibility,
    EventFamily,
    ExistencePattern,
    FlowType,
    RelationshipKind,
    SettlementPattern,
    ValuationQuestion,
)


@dataclass(frozen=True)
class UnitDeclaration:
    """Axis 1 — Unit Semantics."""

    divisibility: Divisibility
    quantity_equals_value: bool
    allows_negative: bool
    permits_fractional_refinement: bool
    permits_lot_refinement: bool


@dataclass(frozen=True)
class AcquisitionDeclaration:
    """Axis 2 — Acquisition Semantics."""

    semantics: AcquisitionSemantics


@dataclass(frozen=True)
class SettlementDeclaration:
    """Axis 3 — Settlement Semantics."""

    pattern: SettlementPattern
    permits_cycle_length_refinement: bool


@dataclass(frozen=True)
class ValuationDeclaration:
    """Axis 4 — Valuation Semantics."""

    question: ValuationQuestion


@dataclass(frozen=True)
class FlowGrants:
    """Axis 5 — Flow Grants. An empty frozenset is a declaration (D7), not
    a missing value — see DefinitionTranscription.granted_flows below."""

    granted: FrozenSet[FlowType] = field(default_factory=frozenset)


@dataclass(frozen=True)
class EventFamilyGrants:
    """Axis 6 — Event-Family Grants. Empty is Cash v1's explicit 'none'."""

    granted: FrozenSet[EventFamily] = field(default_factory=frozenset)


@dataclass(frozen=True)
class ExistenceDeclaration:
    """Axis 7 — Existence Pattern.

    mandatory is a subset of permitted by construction (registry boot
    validation enforces this — a relationship cannot be mandatory without
    also being permitted; neither v1 definition declares a mandatory
    relationship, but the field exists because the constitution's axis
    vocabulary names both "permitted" and "mandatory" as independent facts).
    """

    pattern: ExistencePattern
    permitted_relationships: FrozenSet[RelationshipKind] = field(default_factory=frozenset)
    mandatory_relationships: FrozenSet[RelationshipKind] = field(default_factory=frozenset)


@dataclass(frozen=True)
class DefinitionTranscription:
    """One (definition, version) — the complete runtime transcription of one
    canonical document's Capability Projection table, plus the bookkeeping
    the runtime needs to place it on the version ladder (M9 TDD Section 5.2)
    and check it hasn't moved (Section 5.4).

    `name`, `version`, `binding`, and `source_document` are governance-facing
    only (M9 TDD Section 2.4) — GovernanceProjection exposes them,
    CapabilityView never does (Section 2.2).
    """

    name: str
    version: str
    binding: str
    source_document: str
    effective_from: str  # ISO date; the version ladder's ordering key (5.2)

    unit: UnitDeclaration
    acquisition: AcquisitionDeclaration
    settlement: SettlementDeclaration
    valuation: ValuationDeclaration
    flows: FlowGrants
    event_families: EventFamilyGrants
    existence: ExistenceDeclaration

    # Deliberately NOT a field here: a fingerprint stored on the object it
    # fingerprints could be "corrected" by the same edit that moved the
    # declarations, defeating Section 5.4's purpose. The expected digest for
    # each (binding, version) lives only in library.PINNED_FINGERPRINTS — a
    # separate literal the registry compares the live computation against.
