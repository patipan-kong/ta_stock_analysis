"""DefinitionRegistry: boot validation and the public API surface
(M9 TDD Section 2.1, Section 6.1; this milestone's brief Section "4. Boot
Validation" and "Deliverables").

Real-library tests (build() succeeds, exists()/get()/all() behave) live
alongside synthetic-fixture tests that feed deliberately malformed ladders
straight into registry._validate() — every boot-failure class the milestone
brief and the M9 TDD name gets one failing fixture and one assertion that
the registry names the right rule, never merely "invalid".
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

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
from services.asset_definitions.fingerprint import compute_fingerprint
from services.asset_definitions.registry import DefinitionRegistry, DefinitionRegistryError, _validate
from services.asset_definitions.vocabulary import (
    AcquisitionSemantics,
    Divisibility,
    ExistencePattern,
    FlowType,
    RelationshipKind,
    SettlementPattern,
    ValuationQuestion,
)


def _cash_like(binding="CASH", version="v1", effective_from="2026-07-11", mandatory=frozenset()):
    return DefinitionTranscription(
        name="Cash",
        version=version,
        binding=binding,
        source_document="docs/definitions/asset_definition_cash.md",
        effective_from=effective_from,
        unit=UnitDeclaration(Divisibility.CONTINUOUS, True, False, False, False),
        acquisition=AcquisitionDeclaration(AcquisitionSemantics.NOT_TRANSACTABLE),
        settlement=SettlementDeclaration(SettlementPattern.INSTANT, False),
        valuation=ValuationDeclaration(ValuationQuestion.IDENTITY),
        flows=FlowGrants(frozenset({FlowType.INTEREST})),
        event_families=EventFamilyGrants(frozenset()),
        existence=ExistenceDeclaration(ExistencePattern.OPEN_ENDED, frozenset(), mandatory),
    )


# ── The real library boots clean ──────────────────────────────────────────

def test_build_succeeds_against_the_real_library():
    registry = DefinitionRegistry.build()
    assert registry.exists("CASH")
    assert registry.exists("EQUITY")


def test_exists_is_false_for_bindings_with_no_definition():
    registry = DefinitionRegistry.build()
    for ghost in ("ETF", "FUND", "BOND", "CRYPTO", "COMMODITY", "PROPERTY", "OTHER"):
        assert registry.exists(ghost) is False, f"{ghost} has no canonical definition and must not resolve"


def test_get_returns_governance_projection_or_none():
    registry = DefinitionRegistry.build()
    cash = registry.get("CASH")
    assert cash is not None
    assert cash.name == "Cash"
    assert cash.version == "v1"
    assert registry.get("ETF") is None


def test_all_returns_every_loaded_definition_sorted_by_binding():
    registry = DefinitionRegistry.build()
    bindings = [g.binding for g in registry.all()]
    assert bindings == sorted(bindings)
    assert set(bindings) == {"CASH", "EQUITY"}


# ── Boot validation: each defect class refuses with a named rule ─────────

def test_duplicate_declarations_across_definitions_fails_boot():
    a = _cash_like(binding="CASH")
    b = _cash_like(binding="EQUITY")  # different binding, identical payload -> D1 violation
    ladders = {"CASH": (a,), "EQUITY": (b,)}
    pins = {("CASH", "v1"): compute_fingerprint(a), ("EQUITY", "v1"): compute_fingerprint(b)}

    findings = _validate(ladders, pins)
    assert any(f.rule == "duplicate-declarations" for f in findings)


def test_ladder_out_of_order_fails_boot():
    v1 = _cash_like(effective_from="2026-07-11")
    v2 = _cash_like(version="v2", effective_from="2026-01-01")  # earlier than v1 -> not strictly ordered
    ladders = {"CASH": (v1, v2)}
    pins = {("CASH", "v1"): compute_fingerprint(v1), ("CASH", "v2"): compute_fingerprint(v2)}

    findings = _validate(ladders, pins)
    assert any(f.rule == "ladder-ordering" for f in findings)


def test_mandatory_relationship_not_in_permitted_fails_boot():
    bad = DefinitionTranscription(
        name="Cash", version="v1", binding="CASH",
        source_document="docs/definitions/asset_definition_cash.md", effective_from="2026-07-11",
        unit=UnitDeclaration(Divisibility.CONTINUOUS, True, False, False, False),
        acquisition=AcquisitionDeclaration(AcquisitionSemantics.NOT_TRANSACTABLE),
        settlement=SettlementDeclaration(SettlementPattern.INSTANT, False),
        valuation=ValuationDeclaration(ValuationQuestion.IDENTITY),
        flows=FlowGrants(frozenset({FlowType.INTEREST})),
        event_families=EventFamilyGrants(frozenset()),
        existence=ExistenceDeclaration(
            ExistencePattern.OPEN_ENDED,
            permitted_relationships=frozenset(),
            mandatory_relationships=frozenset({RelationshipKind.WRAPS}),  # mandatory but never permitted
        ),
    )
    ladders = {"CASH": (bad,)}
    pins = {("CASH", "v1"): compute_fingerprint(bad)}

    findings = _validate(ladders, pins)
    assert any(f.rule == "invalid-existence-reference" for f in findings)


def test_missing_fingerprint_pin_fails_boot():
    a = _cash_like()
    findings = _validate({"CASH": (a,)}, pinned_fingerprints={})
    assert any(f.rule == "missing-fingerprint-pin" for f in findings)


def test_fingerprint_mismatch_fails_boot():
    a = _cash_like()
    findings = _validate({"CASH": (a,)}, pinned_fingerprints={("CASH", "v1"): "0" * 64})
    assert any(f.rule == "fingerprint-mismatch" for f in findings)


def test_unknown_binding_fails_boot():
    a = _cash_like(binding="DOGE_MEME_COIN")
    findings = _validate(
        {"DOGE_MEME_COIN": (a,)},
        pinned_fingerprints={("DOGE_MEME_COIN", "v1"): compute_fingerprint(a)},
    )
    assert any(f.rule == "unknown-binding" for f in findings)


def test_duplicate_version_within_ladder_fails_boot():
    a = _cash_like(version="v1", effective_from="2026-07-11")
    b = _cash_like(version="v1", effective_from="2026-08-01")
    ladders = {"CASH": (a, b)}
    pins = {("CASH", "v1"): compute_fingerprint(a)}
    findings = _validate(ladders, pins)
    assert any(f.rule == "duplicate-version" for f in findings)


def test_registry_build_raises_aggregated_error_naming_every_finding():
    import services.asset_definitions.registry as registry_module

    original = registry_module.library.PINNED_FINGERPRINTS
    try:
        registry_module.library.PINNED_FINGERPRINTS = dict(original)
        registry_module.library.PINNED_FINGERPRINTS[("CASH", "v1")] = "0" * 64
        with pytest.raises(DefinitionRegistryError) as excinfo:
            DefinitionRegistry.build()
        assert any(f.rule == "fingerprint-mismatch" for f in excinfo.value.findings)
    finally:
        registry_module.library.PINNED_FINGERPRINTS = original
