"""M24 brief: BOND Canonical Definition Authoring.

BOND_V1 is the fifth canonical Asset Definition — the third admitted after
the Runtime architecture (M9-M23) was already in place, following ETF's
(M15-M18) and FUND's (M20-M22) precedent two bindings later. It differs from
Equity v1 on exactly two axes (Flow Grants: COUPON, not DIVIDEND; Existence
Pattern: SCHEDULED_TERMINAL, not OPEN_ENDED) — the two declarations M23's
governed vocabulary extension made possible, per asset_model_gap_analysis.md
§3.2's finding that both words, together, are BOND's entire remaining gap.

Coverage, per the brief's "Required Tests":
  1. Definition Conformance — BOND satisfies D1; distinct from every
     existing definition.
  2. Runtime Projection — CapabilityView and GovernanceProjection agree with
     each other and with docs/definitions/asset_definition_bond.md's own
     Capability Projection table, row by row.
  3. Fingerprint Integrity — the pinned digest validates; tampering fails
     boot, the same way it already does for CASH/EQUITY/ETF/FUND.
  4. Registry Integration — DefinitionRegistry.exists("BOND") is True;
     BindingResolver resolves it; unknown bindings remain unresolved.
  5. Readiness — BOND reports DEFINED; other AssetTypes are unchanged.
  6. Regression — CASH, EQUITY, ETF, and FUND remain byte-identical to their
     pre-M24 declarations and pinned fingerprints.
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

def test_bond_v1_differs_from_equity_v1_on_exactly_two_axes():
    """The individuation this whole milestone exists to make: BOND's payload
    must differ from Equity's, and the difference must be exactly Axis 5
    (flows) and Axis 7 (existence) — proving the definition is neither an
    accidental duplicate (D1) nor over-differentiated (the brief's "minimal
    semantic differentiation")."""
    assert library.BOND_V1.unit == library.EQUITY_V1.unit
    assert library.BOND_V1.acquisition == library.EQUITY_V1.acquisition
    assert library.BOND_V1.settlement == library.EQUITY_V1.settlement
    assert library.BOND_V1.valuation == library.EQUITY_V1.valuation
    assert library.BOND_V1.event_families == library.EQUITY_V1.event_families

    assert library.BOND_V1.flows != library.EQUITY_V1.flows
    assert library.BOND_V1.flows.granted == frozenset({FlowType.COUPON})
    assert library.EQUITY_V1.flows.granted == frozenset({FlowType.DIVIDEND})

    assert library.BOND_V1.existence != library.EQUITY_V1.existence
    assert library.BOND_V1.existence.pattern == ExistencePattern.SCHEDULED_TERMINAL
    assert library.EQUITY_V1.existence.pattern == ExistencePattern.OPEN_ENDED


def test_bond_v1_is_not_equivalent_to_any_existing_definition():
    existing = (library.CASH_V1, library.EQUITY_V1, library.ETF_V1, library.FUND_V1)
    bond_fingerprint = compute_fingerprint(library.BOND_V1)
    for other in existing:
        assert bond_fingerprint != compute_fingerprint(other)


def test_real_library_boots_clean_with_bond_present():
    """D1 is a boot-time check (registry.py's duplicate-declarations rule) —
    the real library actually passing DefinitionRegistry.build() is the
    strongest form of this assertion, stronger than a synthetic fixture."""
    registry = DefinitionRegistry.build()
    assert registry.exists("BOND") is True


# ── 2. Runtime Projection ───────────────────────────────────────────────────
# Row-by-row transcription of asset_definition_bond.md's own Capability
# Projection table, mirroring test_asset_definition_fund.py's style.

def test_bond_v1_unit_row():
    # | Unit | one bond |
    # | Quantity | whole-bond default; fractional/lot: instance facts; non-negative |
    view = _resolver().resolve("BOND")
    assert view.unit_divisibility() == Divisibility.DISCRETE
    assert view.unit_quantity_equals_value() is False
    assert view.unit_allows_negative() is False
    assert view.unit_permits_fractional_refinement() is True
    assert view.unit_permits_lot_refinement() is True


def test_bond_v1_acquisition_row():
    # | Acquisition | venue-traded |
    view = _resolver().resolve("BOND")
    assert view.acquisition_semantics() == AcquisitionSemantics.VENUE_TRADED


def test_bond_v1_settlement_row():
    # | Settlement | cycle-based (length: instance fact) |
    view = _resolver().resolve("BOND")
    assert view.settlement_pattern() == SettlementPattern.CYCLE_BASED
    assert view.settlement_permits_cycle_length_refinement() is True


def test_bond_v1_valuation_row():
    # | Valuation question | continuous quotation |
    view = _resolver().resolve("BOND")
    assert view.valuation_question() == ValuationQuestion.CONTINUOUS_QUOTATION


def test_bond_v1_flows_row():
    # | Flows admissible | coupon |
    view = _resolver().resolve("BOND")
    assert view.grants_flow(FlowType.COUPON) is True
    assert view.grants_flow(FlowType.DIVIDEND) is False
    assert view.grants_flow(FlowType.INTEREST) is False


def test_bond_v1_event_families_row():
    # | Event families | split, merger, spin-off, rename, suspension, delisting |
    view = _resolver().resolve("BOND")
    granted = {
        EventFamily.SPLIT, EventFamily.MERGER, EventFamily.SPIN_OFF,
        EventFamily.RENAME, EventFamily.SUSPENSION, EventFamily.DELISTING,
    }
    for family in EventFamily:
        assert view.grants_event_family(family) is (family in granted)


def test_bond_v1_existence_row():
    # | Existence | scheduled-terminal; may relate: same-entity, wraps, successor-of |
    view = _resolver().resolve("BOND")
    assert view.existence_pattern() == ExistencePattern.SCHEDULED_TERMINAL
    permitted = {RelationshipKind.SAME_ENTITY, RelationshipKind.WRAPS, RelationshipKind.SUCCESSOR_OF}
    for kind in RelationshipKind:
        assert view.permits_relationship(kind) is (kind in permitted)
        assert view.relationship_mandatory(kind) is False


def test_governance_projection_matches_capability_view_for_bond():
    registry = DefinitionRegistry.build()
    resolver = BindingResolver(registry)
    view = resolver.resolve("BOND")
    projection = registry.get("BOND").as_dict()

    assert projection["name"] == "Bond"
    assert projection["binding"] == AssetType.BOND.value
    assert projection["source_document"] == "docs/definitions/asset_definition_bond.md"
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

def test_bond_pinned_fingerprint_validates():
    assert compute_fingerprint(library.BOND_V1) == library.PINNED_FINGERPRINTS[(AssetType.BOND.value, "v1")]


def test_tampered_bond_fingerprint_fails_boot():
    import services.asset_definitions.registry as registry_module

    original = registry_module.library.PINNED_FINGERPRINTS
    try:
        registry_module.library.PINNED_FINGERPRINTS = dict(original)
        registry_module.library.PINNED_FINGERPRINTS[(AssetType.BOND.value, "v1")] = "0" * 64
        with pytest.raises(DefinitionRegistryError) as excinfo:
            DefinitionRegistry.build()
        assert any(
            f.rule == "fingerprint-mismatch" and f.binding == AssetType.BOND.value
            for f in excinfo.value.findings
        )
    finally:
        registry_module.library.PINNED_FINGERPRINTS = original


# ── 4. Registry Integration ─────────────────────────────────────────────────

def test_definition_registry_exists_bond():
    assert DefinitionRegistry.build().exists("BOND") is True


def test_binding_resolver_resolves_bond():
    view = _resolver().resolve("BOND")
    assert view.existence_pattern() == ExistencePattern.SCHEDULED_TERMINAL


def test_unknown_bindings_still_unresolved_after_bond_addition():
    """Adding BOND must not widen resolution to any other still-undefined
    binding — a sibling entry cannot accidentally loosen refusal for
    bindings that never asked for one."""
    from services.asset_definitions import UnresolvedBindingError

    resolver = _resolver()
    # M27: PROPERTY is now defined too — see test_asset_definition_property.py.
    for ghost in ("CRYPTO", "COMMODITY", "OTHER"):
        with pytest.raises(UnresolvedBindingError):
            resolver.resolve(ghost)


# ── 5. Readiness ─────────────────────────────────────────────────────────────

def test_bond_readiness_is_defined():
    readiness = readiness_for(AssetType.BOND.value)
    assert readiness.status == ReadinessStatus.DEFINED
    assert readiness.missing_requirements == ()


def test_other_asset_types_readiness_unchanged_by_bond_authoring():
    assert readiness_for(AssetType.CASH.value).status == ReadinessStatus.DEFINED
    assert readiness_for(AssetType.EQUITY.value).status == ReadinessStatus.DEFINED
    assert readiness_for(AssetType.ETF.value).status == ReadinessStatus.DEFINED
    assert readiness_for(AssetType.FUND.value).status == ReadinessStatus.DEFINED
    # M27: PROPERTY is now DEFINED too — see test_asset_definition_property.py.
    assert readiness_for(AssetType.PROPERTY.value).status == ReadinessStatus.DEFINED
    assert readiness_for(AssetType.CRYPTO.value).status == ReadinessStatus.SCOPE_UNDECIDED
    assert readiness_for(AssetType.COMMODITY.value).status == ReadinessStatus.SCOPE_UNDECIDED
    assert readiness_for(AssetType.OTHER.value).status == ReadinessStatus.EXEMPT


# ── 6. Regression: CASH, EQUITY, ETF, and FUND are untouched ────────────────

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


def test_definition_ladders_now_exactly_five():
    # M27: PROPERTY was subsequently added — see
    # test_asset_definition_property.py's own version of this assertion.
    assert set(library.DEFINITION_LADDERS.keys()) == {
        AssetType.CASH.value, AssetType.EQUITY.value, AssetType.ETF.value,
        AssetType.FUND.value, AssetType.BOND.value, AssetType.PROPERTY.value,
    }
