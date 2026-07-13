"""Generic Asset Definition Authoring Framework validation (M19 brief).

These tests validate the *framework's* guarantees against whatever the
library currently contains — they parametrize over library.DEFINITION_LADDERS
and AssetType at collection time and never name a specific binding in an
assertion. A definition's own particular content (its specific declarations,
its D1 comparison against one named neighbor) is validated by that
definition's own dedicated test file (e.g. test_asset_definition_etf.py);
this file validates that *any* definition admitted through the
docs/definitions/asset_definition_authoring_guide.md workflow satisfies the
guarantees the guide promises, so a future definition (FUND, BOND, ...)
inherits this coverage without a new test file needing to be written for it.

Coverage — one section per docs/definitions/definition_review_checklist.md
gate that is mechanically checkable:
  1. D1 — every current-rung definition's declaration payload is unique
     across the whole library (checklist items 2-3).
  2. Fingerprint integrity — every rung has a pinned fingerprint that
     matches computed, and a tampered fingerprint fails boot, for every
     binding the library carries (checklist items 6-7).
  3. Runtime projection — every library binding resolves through
     DefinitionRegistry/BindingResolver, and GovernanceProjection's dump
     agrees with CapabilityView's accessors, field by field (checklist
     item 7).
  4. Readiness — every library binding is reported DEFINED with no missing
     requirements, and no non-library binding is (checklist item 8).
  5. Source integrity — every transcription's source_document actually
     exists on disk.
"""
from __future__ import annotations

import itertools
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from services.asset_definitions import library
from services.asset_definitions.binding_resolver import BindingResolver, UnresolvedBindingError
from services.asset_definitions.capability_view import CapabilityView
from services.asset_definitions.fingerprint import canonical_payload, compute_fingerprint
from services.asset_definitions.readiness_report import ReadinessStatus, readiness_for
from services.asset_definitions.registry import DefinitionRegistry, DefinitionRegistryError
from services.asset_definitions.vocabulary import EventFamily, FlowType, RelationshipKind
from services.asset_domain import AssetType

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

_LIBRARY_BINDINGS = sorted(library.DEFINITION_LADDERS.keys())
_NON_LIBRARY_BINDINGS = sorted({m.value for m in AssetType} - set(_LIBRARY_BINDINGS))
_CURRENT_RUNGS = [ladder[-1] for ladder in library.DEFINITION_LADDERS.values()]


# ── 1. D1: no two current-rung definitions share a declaration payload ─────

def test_registry_boots_clean_against_the_real_library():
    registry = DefinitionRegistry.build()
    assert all(registry.exists(b) for b in _LIBRARY_BINDINGS)


def test_no_two_current_definitions_share_a_declaration_payload():
    payloads = {}
    for transcription in _CURRENT_RUNGS:
        payload = canonical_payload(transcription)
        collision = payloads.get(payload)
        assert collision is None, (
            f"{transcription.binding} declares an identical capability payload to "
            f"{collision} — D1 individuation violated"
        )
        payloads[payload] = transcription.binding


@pytest.mark.parametrize("pair", list(itertools.combinations(_LIBRARY_BINDINGS, 2)))
def test_every_pair_of_definitions_is_individuated(pair):
    a_binding, b_binding = pair
    a = library.DEFINITION_LADDERS[a_binding][-1]
    b = library.DEFINITION_LADDERS[b_binding][-1]
    assert canonical_payload(a) != canonical_payload(b), (
        f"{a_binding} and {b_binding} declare identical capability payloads — D1 violated"
    )


# ── 2. Fingerprint integrity, for every binding the library carries ────────

@pytest.mark.parametrize("binding", _LIBRARY_BINDINGS)
def test_every_rung_has_a_pinned_fingerprint(binding):
    for transcription in library.DEFINITION_LADDERS[binding]:
        key = (binding, transcription.version)
        assert key in library.PINNED_FINGERPRINTS, f"{key} has no pinned fingerprint"


@pytest.mark.parametrize("binding", _LIBRARY_BINDINGS)
def test_every_pinned_fingerprint_matches_computed(binding):
    for transcription in library.DEFINITION_LADDERS[binding]:
        key = (binding, transcription.version)
        expected = library.PINNED_FINGERPRINTS[key]
        assert compute_fingerprint(transcription) == expected


@pytest.mark.parametrize("binding", _LIBRARY_BINDINGS)
def test_tampering_any_definitions_fingerprint_fails_boot(binding):
    original = dict(library.PINNED_FINGERPRINTS)
    try:
        version = library.DEFINITION_LADDERS[binding][-1].version
        library.PINNED_FINGERPRINTS[(binding, version)] = "0" * 64
        with pytest.raises(DefinitionRegistryError) as excinfo:
            DefinitionRegistry.build()
        assert any(
            f.rule == "fingerprint-mismatch" and f.binding == binding
            for f in excinfo.value.findings
        )
    finally:
        library.PINNED_FINGERPRINTS.clear()
        library.PINNED_FINGERPRINTS.update(original)


# ── 3. Runtime projection: registry, resolver, and the two doors agree ─────

@pytest.mark.parametrize("binding", _LIBRARY_BINDINGS)
def test_every_library_binding_resolves_through_binding_resolver(binding):
    registry = DefinitionRegistry.build()
    resolver = BindingResolver(registry)
    view = resolver.resolve(binding)
    assert isinstance(view, CapabilityView)


@pytest.mark.parametrize("binding", _NON_LIBRARY_BINDINGS)
def test_non_library_bindings_refuse_resolution(binding):
    registry = DefinitionRegistry.build()
    resolver = BindingResolver(registry)
    with pytest.raises(UnresolvedBindingError):
        resolver.resolve(binding)


@pytest.mark.parametrize("binding", _LIBRARY_BINDINGS)
def test_governance_projection_and_capability_view_agree(binding):
    """Cross-checks the two doors (M9 TDD Section 2.2 vs 2.4) project the
    same underlying transcription for every library binding — not just
    whichever definition the current milestone happens to be authoring."""
    registry = DefinitionRegistry.build()
    resolver = BindingResolver(registry)
    view = resolver.resolve(binding)
    projection = registry.get(binding)
    dump = projection.as_dict()

    assert dump["unit"]["divisibility"] == view.unit_divisibility().value
    assert dump["unit"]["quantity_equals_value"] == view.unit_quantity_equals_value()
    assert dump["unit"]["allows_negative"] == view.unit_allows_negative()
    assert dump["unit"]["permits_fractional_refinement"] == view.unit_permits_fractional_refinement()
    assert dump["unit"]["permits_lot_refinement"] == view.unit_permits_lot_refinement()
    assert dump["acquisition"] == view.acquisition_semantics().value
    assert dump["settlement"]["pattern"] == view.settlement_pattern().value
    assert (
        dump["settlement"]["permits_cycle_length_refinement"]
        == view.settlement_permits_cycle_length_refinement()
    )
    assert dump["valuation_question"] == view.valuation_question().value
    assert dump["existence"]["pattern"] == view.existence_pattern().value
    for flow_name in dump["flows_granted"]:
        assert view.grants_flow(FlowType(flow_name))
    for family_name in dump["event_families_granted"]:
        assert view.grants_event_family(EventFamily(family_name))
    for rel_name in dump["existence"]["permitted_relationships"]:
        assert view.permits_relationship(RelationshipKind(rel_name))
    for rel_name in dump["existence"]["mandatory_relationships"]:
        assert view.relationship_mandatory(RelationshipKind(rel_name))


# ── 4. Readiness: every library binding is DEFINED, and only those ─────────

@pytest.mark.parametrize("binding", _LIBRARY_BINDINGS)
def test_every_library_binding_is_readiness_defined(binding):
    readiness = readiness_for(binding)
    assert readiness.status == ReadinessStatus.DEFINED
    assert readiness.missing_requirements == ()


@pytest.mark.parametrize("binding", _NON_LIBRARY_BINDINGS)
def test_non_library_bindings_are_never_readiness_defined(binding):
    readiness = readiness_for(binding)
    assert readiness.status != ReadinessStatus.DEFINED


# ── 5. Source integrity: every transcription's document actually exists ────

@pytest.mark.parametrize("binding", _LIBRARY_BINDINGS)
def test_every_transcriptions_source_document_exists_on_disk(binding):
    for transcription in library.DEFINITION_LADDERS[binding]:
        path = os.path.join(_REPO_ROOT, transcription.source_document)
        assert os.path.isfile(path), (
            f"{binding} {transcription.version} references "
            f"{transcription.source_document!r}, which does not exist on disk"
        )
