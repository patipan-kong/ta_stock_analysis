"""M27 brief: PROPERTY Canonical Definition Authoring.

PROPERTY_V1 is the sixth canonical Asset Definition — the fourth admitted
after the Runtime architecture (M9-M26) was already in place, following
ETF's (M15-M18), FUND's (M20-M22), and BOND's (M20/M23-M24) precedent. It
differs from every existing definition on four axes simultaneously —
Acquisition (NEGOTIATED_TRANSFER), Settlement (NEGOTIATED_CLOSING),
Valuation (APPRAISAL_ON_EVENT), and Flow Grants (RENT) — the four words M25
designed and M26 shipped as one governed vocabulary extension
(`property_vocabulary_bundle_design.md`).

Coverage, per the brief's "Required Tests":
  1. Definition Conformance — PROPERTY satisfies D1; distinct from every
     existing definition.
  2. Runtime Projection — CapabilityView and GovernanceProjection agree with
     each other and with docs/definitions/asset_definition_property.md's own
     Capability Projection table, row by row.
  3. Fingerprint Integrity — the pinned digest validates; tampering fails
     boot, the same way it already does for CASH/EQUITY/ETF/FUND/BOND.
  4. Registry Integration — DefinitionRegistry.exists("PROPERTY") is True;
     BindingResolver resolves it; unknown bindings remain unresolved.
  5. Readiness — PROPERTY reports DEFINED; other AssetTypes are unchanged.
  6. Regression — CASH, EQUITY, ETF, FUND, and BOND remain byte-identical to
     their pre-M27 declarations and pinned fingerprints.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from services.asset_definitions import BindingResolver, DefinitionRegistry
from services.asset_definitions import library
from services.asset_definitions.fingerprint import compute_fingerprint
from services.asset_definitions.readiness_report import (
    ReadinessStatus,
    readiness_for,
)
from services.asset_definitions.registry import DefinitionRegistryError
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
from services.asset_domain import AssetType


def _resolver():
    return BindingResolver(DefinitionRegistry.build())


# ── 1. Definition Conformance (D1) ──────────────────────────────────────────

def test_property_v1_differs_from_every_existing_definition_on_four_axes():
    """The individuation this whole milestone exists to make: PROPERTY's
    payload must differ from every other canonical definition, on Axis 2
    (acquisition), Axis 3 (settlement), Axis 4 (valuation), and Axis 5
    (flows) simultaneously — the largest D1 margin of any definition
    admitted to the library so far (ETF: one axis; FUND: one axis; BOND:
    two axes; PROPERTY: four)."""
    for other in (library.CASH_V1, library.EQUITY_V1, library.ETF_V1, library.FUND_V1, library.BOND_V1):
        assert library.PROPERTY_V1.acquisition != other.acquisition
        assert library.PROPERTY_V1.settlement != other.settlement
        assert library.PROPERTY_V1.valuation != other.valuation
        assert library.PROPERTY_V1.flows != other.flows

    assert library.PROPERTY_V1.acquisition.semantics == AcquisitionSemantics.NEGOTIATED_TRANSFER
    assert library.PROPERTY_V1.settlement.pattern == SettlementPattern.NEGOTIATED_CLOSING
    assert library.PROPERTY_V1.valuation.question == ValuationQuestion.APPRAISAL_ON_EVENT
    assert library.PROPERTY_V1.flows.granted == frozenset({FlowType.RENT})


def test_property_v1_is_not_equivalent_to_any_existing_definition():
    existing = (library.CASH_V1, library.EQUITY_V1, library.ETF_V1, library.FUND_V1, library.BOND_V1)
    property_fingerprint = compute_fingerprint(library.PROPERTY_V1)
    for other in existing:
        assert property_fingerprint != compute_fingerprint(other)


def test_real_library_boots_clean_with_property_present():
    """D1 is a boot-time check (registry.py's duplicate-declarations rule) —
    the real library actually passing DefinitionRegistry.build() is the
    strongest form of this assertion, stronger than a synthetic fixture."""
    registry = DefinitionRegistry.build()
    assert registry.exists("PROPERTY") is True


# ── 2. Runtime Projection ───────────────────────────────────────────────────
# Row-by-row transcription of asset_definition_property.md's own Capability
# Projection table, mirroring test_asset_definition_bond.py's style.

def test_property_v1_unit_row():
    # | Unit | one property |
    # | Quantity | whole-property only; no fractional or lot refinement; non-negative |
    view = _resolver().resolve("PROPERTY")
    assert view.unit_divisibility() == Divisibility.DISCRETE
    assert view.unit_quantity_equals_value() is False
    assert view.unit_allows_negative() is False
    assert view.unit_permits_fractional_refinement() is False
    assert view.unit_permits_lot_refinement() is False


def test_property_v1_acquisition_row():
    # | Acquisition | negotiated transfer |
    view = _resolver().resolve("PROPERTY")
    assert view.acquisition_semantics() == AcquisitionSemantics.NEGOTIATED_TRANSFER


def test_property_v1_settlement_row():
    # | Settlement | negotiated closing (no cycle-length refinement) |
    view = _resolver().resolve("PROPERTY")
    assert view.settlement_pattern() == SettlementPattern.NEGOTIATED_CLOSING
    assert view.settlement_permits_cycle_length_refinement() is False


def test_property_v1_valuation_row():
    # | Valuation question | appraisal-on-event |
    view = _resolver().resolve("PROPERTY")
    assert view.valuation_question() == ValuationQuestion.APPRAISAL_ON_EVENT


def test_property_v1_flows_row():
    # | Flows admissible | rent |
    view = _resolver().resolve("PROPERTY")
    assert view.grants_flow(FlowType.RENT) is True
    assert view.grants_flow(FlowType.DIVIDEND) is False
    assert view.grants_flow(FlowType.INTEREST) is False
    assert view.grants_flow(FlowType.COUPON) is False


def test_property_v1_event_families_row():
    # | Event families | none |
    view = _resolver().resolve("PROPERTY")
    for family in EventFamily:
        assert view.grants_event_family(family) is False


def test_property_v1_existence_row():
    # | Existence | open-ended; no relationship kind permitted |
    view = _resolver().resolve("PROPERTY")
    assert view.existence_pattern() == ExistencePattern.OPEN_ENDED
    for kind in RelationshipKind:
        assert view.permits_relationship(kind) is False
        assert view.relationship_mandatory(kind) is False


def test_governance_projection_matches_capability_view_for_property():
    registry = DefinitionRegistry.build()
    resolver = BindingResolver(registry)
    view = resolver.resolve("PROPERTY")
    projection = registry.get("PROPERTY").as_dict()

    assert projection["name"] == "Property"
    assert projection["binding"] == AssetType.PROPERTY.value
    assert projection["source_document"] == "docs/definitions/asset_definition_property.md"
    assert projection["unit"]["divisibility"] == view.unit_divisibility().value
    assert projection["acquisition"] == view.acquisition_semantics().value
    assert projection["settlement"]["pattern"] == view.settlement_pattern().value
    assert projection["valuation_question"] == view.valuation_question().value
    assert set(projection["flows_granted"]) == {f.value for f in FlowType if view.grants_flow(f)}
    assert set(projection["event_families_granted"]) == {
        f.value for f in EventFamily if view.grants_event_family(f)
    }
    assert projection["existence"]["pattern"] == view.existence_pattern().value
    assert set(projection["existence"]["permitted_relationships"]) == {
        k.value for k in RelationshipKind if view.permits_relationship(k)
    }


# ── 3. Fingerprint Integrity ────────────────────────────────────────────────

def test_property_pinned_fingerprint_validates():
    assert compute_fingerprint(library.PROPERTY_V1) == library.PINNED_FINGERPRINTS[(AssetType.PROPERTY.value, "v1")]


def test_tampered_property_fingerprint_fails_boot():
    import services.asset_definitions.registry as registry_module

    original = registry_module.library.PINNED_FINGERPRINTS
    try:
        registry_module.library.PINNED_FINGERPRINTS = dict(original)
        registry_module.library.PINNED_FINGERPRINTS[(AssetType.PROPERTY.value, "v1")] = "0" * 64
        with pytest.raises(DefinitionRegistryError) as excinfo:
            DefinitionRegistry.build()
        assert any(
            f.rule == "fingerprint-mismatch" and f.binding == AssetType.PROPERTY.value
            for f in excinfo.value.findings
        )
    finally:
        registry_module.library.PINNED_FINGERPRINTS = original


# ── 4. Registry Integration ─────────────────────────────────────────────────

def test_definition_registry_exists_property():
    assert DefinitionRegistry.build().exists("PROPERTY") is True


def test_binding_resolver_resolves_property():
    view = _resolver().resolve("PROPERTY")
    assert view.acquisition_semantics() == AcquisitionSemantics.NEGOTIATED_TRANSFER


def test_unknown_bindings_still_unresolved_after_property_addition():
    """Adding PROPERTY must not widen resolution to any other still-undefined
    binding — a sibling entry cannot accidentally loosen refusal for
    bindings that never asked for one."""
    from services.asset_definitions import UnresolvedBindingError

    resolver = _resolver()
    for ghost in ("CRYPTO", "COMMODITY", "OTHER"):
        with pytest.raises(UnresolvedBindingError):
            resolver.resolve(ghost)


# ── 5. Readiness ─────────────────────────────────────────────────────────────

def test_property_readiness_is_defined():
    readiness = readiness_for(AssetType.PROPERTY.value)
    assert readiness.status == ReadinessStatus.DEFINED
    assert readiness.missing_requirements == ()


def test_other_asset_types_readiness_unchanged_by_property_authoring():
    assert readiness_for(AssetType.CASH.value).status == ReadinessStatus.DEFINED
    assert readiness_for(AssetType.EQUITY.value).status == ReadinessStatus.DEFINED
    assert readiness_for(AssetType.ETF.value).status == ReadinessStatus.DEFINED
    assert readiness_for(AssetType.FUND.value).status == ReadinessStatus.DEFINED
    assert readiness_for(AssetType.BOND.value).status == ReadinessStatus.DEFINED
    assert readiness_for(AssetType.CRYPTO.value).status == ReadinessStatus.SCOPE_UNDECIDED
    assert readiness_for(AssetType.COMMODITY.value).status == ReadinessStatus.SCOPE_UNDECIDED
    assert readiness_for(AssetType.OTHER.value).status == ReadinessStatus.EXEMPT


# ── 6. Regression: CASH, EQUITY, ETF, FUND, and BOND are untouched ─────────

def test_cash_v1_declarations_and_fingerprint_unchanged():
    assert library.CASH_V1.valuation.question == ValuationQuestion.IDENTITY
    assert compute_fingerprint(library.CASH_V1) == library.PINNED_FINGERPRINTS[(AssetType.CASH.value, "v1")]


def test_equity_v1_declarations_and_fingerprint_unchanged():
    assert library.EQUITY_V1.valuation.question == ValuationQuestion.CONTINUOUS_QUOTATION
    assert compute_fingerprint(library.EQUITY_V1) == library.PINNED_FINGERPRINTS[(AssetType.EQUITY.value, "v1")]


def test_etf_v1_declarations_and_fingerprint_unchanged():
    assert library.ETF_V1.acquisition.semantics == AcquisitionSemantics.VENUE_TRADED
    assert library.ETF_V1.valuation.question == ValuationQuestion.PERIODIC_NAV
    assert compute_fingerprint(library.ETF_V1) == library.PINNED_FINGERPRINTS[(AssetType.ETF.value, "v1")]


def test_fund_v1_declarations_and_fingerprint_unchanged():
    assert library.FUND_V1.acquisition.semantics == AcquisitionSemantics.NAV_WINDOW
    assert library.FUND_V1.valuation.question == ValuationQuestion.PERIODIC_NAV
    assert compute_fingerprint(library.FUND_V1) == library.PINNED_FINGERPRINTS[(AssetType.FUND.value, "v1")]


def test_bond_v1_declarations_and_fingerprint_unchanged():
    assert library.BOND_V1.flows.granted == frozenset({FlowType.COUPON})
    assert library.BOND_V1.existence.pattern == ExistencePattern.SCHEDULED_TERMINAL
    assert compute_fingerprint(library.BOND_V1) == library.PINNED_FINGERPRINTS[(AssetType.BOND.value, "v1")]


def test_definition_ladders_now_exactly_six():
    assert set(library.DEFINITION_LADDERS.keys()) == {
        AssetType.CASH.value, AssetType.EQUITY.value, AssetType.ETF.value,
        AssetType.FUND.value, AssetType.BOND.value, AssetType.PROPERTY.value,
    }
