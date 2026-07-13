"""GovernanceProjection — the enumerable human/audit surface (M9 TDD
Section 2.4).

Same data as CapabilityView, a different door: trust surfaces, audit UIs,
the registry admin API, and conformance tests may enumerate a definition's
full declaration set and ask "what kind is this." Engine modules never may
(D5, "ask never identify" — enforced structurally by CapabilityView simply
not offering these accessors, see capability_view.py).

This module is import-barred to engine code by convention, not by a Python
mechanism — R0 ships the structural half of that boundary (this class lives
in its own module, under its own name, separate from CapabilityView) and
records the mechanical half (an import-grep CI gate) as a later migration-
stage concern (M9 TDD Section 4.3, Section 9 Stage R2) rather than building
it before any engine exists to violate it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from services.asset_definitions.declarations import DefinitionTranscription


@dataclass(frozen=True)
class GovernanceProjection:
    """The full, named dump of one (definition, version)."""

    transcription: DefinitionTranscription

    @property
    def name(self) -> str:
        return self.transcription.name

    @property
    def version(self) -> str:
        return self.transcription.version

    @property
    def binding(self) -> str:
        return self.transcription.binding

    @property
    def source_document(self) -> str:
        return self.transcription.source_document

    @property
    def effective_from(self) -> str:
        return self.transcription.effective_from

    def as_dict(self) -> Dict[str, Any]:
        """The complete enumerable dump — every axis, every grant. Legal
        here (the human surface); would be a D5/discipline-2 violation on
        CapabilityView, which is exactly why the two live in separate
        classes rather than one class with an enumerate() method."""
        t = self.transcription
        return {
            "name": t.name,
            "version": t.version,
            "binding": t.binding,
            "source_document": t.source_document,
            "effective_from": t.effective_from,
            "unit": {
                "divisibility": t.unit.divisibility.value,
                "quantity_equals_value": t.unit.quantity_equals_value,
                "allows_negative": t.unit.allows_negative,
                "permits_fractional_refinement": t.unit.permits_fractional_refinement,
                "permits_lot_refinement": t.unit.permits_lot_refinement,
            },
            "acquisition": t.acquisition.semantics.value,
            "settlement": {
                "pattern": t.settlement.pattern.value,
                "permits_cycle_length_refinement": t.settlement.permits_cycle_length_refinement,
            },
            "valuation_question": t.valuation.question.value,
            "flows_granted": sorted(item.value for item in t.flows.granted),
            "event_families_granted": sorted(item.value for item in t.event_families.granted),
            "existence": {
                "pattern": t.existence.pattern.value,
                "permitted_relationships": sorted(item.value for item in t.existence.permitted_relationships),
                "mandatory_relationships": sorted(item.value for item in t.existence.mandatory_relationships),
            },
        }

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"GovernanceProjection({self.name} {self.version}, binding={self.binding})"
