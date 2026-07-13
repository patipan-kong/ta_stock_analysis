"""CapabilityView — what engines hold (M9 TDD Section 2.2).

The treaty surface: exactly the question forms of the M9 TDD Section 4.1
table, nothing else. Deliberately does NOT expose:
  - the definition's name, kind, or binding spelling (D5)
  - the version (engines behave identically under every version)
  - any enumeration of its own grants (discipline 2 — require, never
    enumerate; engines ask about the words their operation contract names,
    by name, via the has_*() methods below)
  - metadata, classification, instance facts, or the source document

A view is a thin, immutable wrapper over a DefinitionTranscription's
declarations. It is constructed only by BindingResolver (binding_resolver.py)
and DefinitionRegistry never hands one out directly to a caller holding a
kind name — resolution is the only door (Section 2.3).
"""
from __future__ import annotations

from services.asset_definitions.declarations import DefinitionTranscription
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


class CapabilityView:
    """Anonymous, version-blind, non-enumerable. See module docstring."""

    __slots__ = ("_t",)

    def __init__(self, transcription: DefinitionTranscription) -> None:
        self._t = transcription

    # -- Axis 1: Unit --------------------------------------------------

    def unit_divisibility(self) -> Divisibility:
        return self._t.unit.divisibility

    def unit_quantity_equals_value(self) -> bool:
        return self._t.unit.quantity_equals_value

    def unit_allows_negative(self) -> bool:
        return self._t.unit.allows_negative

    def unit_permits_fractional_refinement(self) -> bool:
        return self._t.unit.permits_fractional_refinement

    def unit_permits_lot_refinement(self) -> bool:
        return self._t.unit.permits_lot_refinement

    # -- Axis 2: Acquisition --------------------------------------------

    def acquisition_semantics(self) -> AcquisitionSemantics:
        return self._t.acquisition.semantics

    # -- Axis 3: Settlement ----------------------------------------------

    def settlement_pattern(self) -> SettlementPattern:
        return self._t.settlement.pattern

    def settlement_permits_cycle_length_refinement(self) -> bool:
        return self._t.settlement.permits_cycle_length_refinement

    # -- Axis 4: Valuation -------------------------------------------------

    def valuation_question(self) -> ValuationQuestion:
        return self._t.valuation.question

    # -- Axis 5: Flows — membership query only, never enumerated -----------

    def grants_flow(self, flow: FlowType) -> bool:
        return flow in self._t.flows.granted

    # -- Axis 6: Event families — membership query only ---------------------

    def grants_event_family(self, family: EventFamily) -> bool:
        return family in self._t.event_families.granted

    # -- Axis 7: Existence — pattern + membership queries only -------------

    def existence_pattern(self) -> ExistencePattern:
        return self._t.existence.pattern

    def permits_relationship(self, kind: RelationshipKind) -> bool:
        return kind in self._t.existence.permitted_relationships

    def relationship_mandatory(self, kind: RelationshipKind) -> bool:
        return kind in self._t.existence.mandatory_relationships

    # -- Deliberately absent: no name(), no version(), no list_flows(),
    # no list_event_families(), no list_relationships(), no is_a()/kind_of().
    # See governance.GovernanceProjection for the surface that has them.

    def __repr__(self) -> str:
        return "<CapabilityView>"

    def __str__(self) -> str:
        return "<CapabilityView>"
