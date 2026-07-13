"""M22 brief: FUND Canonical Definition Authoring.

FUND_V1 is the fourth canonical Asset Definition — the second admitted after
the Runtime architecture (M9-M21) was already in place, following ETF's
(M15-M18) exact precedent one binding later. It differs from ETF v1 on
exactly one axis (Acquisition Semantics: NAV_WINDOW, not VENUE_TRADED) — the
declaration M21's governed vocabulary extension made possible, per
asset_model_gap_analysis.md §3.1's finding that FUND and ETF already share
ValuationQuestion.PERIODIC_NAV (M17) and would otherwise collide under D1.

Coverage, per the brief's "Required Tests":
  1. Constitution Conformance — FUND satisfies D1; not equivalent to ETF.
  2. Runtime Projection — CapabilityView and GovernanceProjection agree with
     each other and with docs/definitions/asset_definition_fund.md's own
     Capability Projection table, row by row.
  3. Fingerprint Integrity — the pinned digest validates; tampering fails
     boot, the same way it already does for CASH/EQUITY/ETF.
  4. Registry Integration — DefinitionRegistry.exists("FUND") is True;
     BindingResolver resolves it; unknown bindings remain unresolved.
  5. Readiness Transition — FUND reports DEFINED; other AssetTypes are
     unchanged.
  6. Regression — CASH, EQUITY, and ETF remain byte-identical to their
     pre-M22 declarations and pinned fingerprints.
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


# ── 1. Constitution Conformance (D1) ────────────────────────────────────────

def test_fund_v1_differs_from_etf_v1_on_exactly_one_axis():
    """The individuation this whole milestone exists to make: FUND's payload
    must differ from ETF's, and the difference must be Axis 2 alone —
    proving the definition is neither an accidental duplicate (D1) nor
    over-differentiated (the brief's "minimal semantic differentiation")."""
    assert library.FUND_V1.unit == library.ETF_V1.unit
    assert library.FUND_V1.settlement == library.ETF_V1.settlement
    assert library.FUND_V1.valuation == library.ETF_V1.valuation
    assert library.FUND_V1.flows == library.ETF_V1.flows
    assert library.FUND_V1.event_families == library.ETF_V1.event_families
    assert library.FUND_V1.existence == library.ETF_V1.existence

    assert library.FUND_V1.acquisition != library.ETF_V1.acquisition
    assert library.FUND_V1.acquisition.semantics == AcquisitionSemantics.NAV_WINDOW
    assert library.ETF_V1.acquisition.semantics == AcquisitionSemantics.VENUE_TRADED


def test_fund_v1_is_not_equivalent_to_etf_v1():
    assert compute_fingerprint(library.FUND_V1) != compute_fingerprint(library.ETF_V1)


def test_real_library_boots_clean_with_fund_present():
    """D1 is a boot-time check (registry.py's duplicate-declarations rule) —
    the real library actually passing DefinitionRegistry.build() is the
    strongest form of this assertion, stronger than a synthetic fixture."""
    registry = DefinitionRegistry.build()
    assert registry.exists("FUND") is True


# ── 2. Runtime Projection ───────────────────────────────────────────────────
# Row-by-row transcription of asset_definition_fund.md's own Capability
# Projection table, mirroring test_asset_definition_etf.py's style.

def test_fund_v1_unit_row():
    # | Unit | one fund unit |
    # | Quantity | whole-unit default; fractional/lot: instance facts; non-negative |
    view = _resolver().resolve("FUND")
    assert view.unit_divisibility() == Divisibility.DISCRETE
    assert view.unit_quantity_equals_value() is False
    assert view.unit_allows_negative() is False
    assert view.unit_permits_fractional_refinement() is True
    assert view.unit_permits_lot_refinement() is True


def test_fund_v1_acquisition_row():
    # | Acquisition | NAV-window subscription/redemption |
    view = _resolver().resolve("FUND")
    assert view.acquisition_semantics() == AcquisitionSemantics.NAV_WINDOW


def test_fund_v1_settlement_row():
    # | Settlement | cycle-based (length: instance fact) |
    view = _resolver().resolve("FUND")
    assert view.settlement_pattern() == SettlementPattern.CYCLE_BASED
    assert view.settlement_permits_cycle_length_refinement() is True


def test_fund_v1_valuation_row():
    # | Valuation question | periodic NAV |
    view = _resolver().resolve("FUND")
    assert view.valuation_question() == ValuationQuestion.PERIODIC_NAV


def test_fund_v1_flows_row():
    # | Flows admissible | dividend |
    view = _resolver().resolve("FUND")
    assert view.grants_flow(FlowType.DIVIDEND) is True
    assert view.grants_flow(FlowType.INTEREST) is False


def test_fund_v1_event_families_row():
    # | Event families | split, merger, spin-off, rename, suspension, delisting |
    view = _resolver().resolve("FUND")
    granted = {
        EventFamily.SPLIT, EventFamily.MERGER, EventFamily.SPIN_OFF,
        EventFamily.RENAME, EventFamily.SUSPENSION, EventFamily.DELISTING,
    }
    for family in EventFamily:
        assert view.grants_event_family(family) is (family in granted)


def test_fund_v1_existence_row():
    # | Existence | open-ended; may relate: same-entity, wraps, successor-of |
    view = _resolver().resolve("FUND")
    assert view.existence_pattern() == ExistencePattern.OPEN_ENDED
    permitted = {RelationshipKind.SAME_ENTITY, RelationshipKind.WRAPS, RelationshipKind.SUCCESSOR_OF}
    for kind in RelationshipKind:
        assert view.permits_relationship(kind) is (kind in permitted)
        assert view.relationship_mandatory(kind) is False


def test_governance_projection_matches_capability_view_for_fund():
    registry = DefinitionRegistry.build()
    resolver = BindingResolver(registry)
    view = resolver.resolve("FUND")
    projection = registry.get("FUND").as_dict()

    assert projection["name"] == "Fund"
    assert projection["binding"] == AssetType.FUND.value
    assert projection["source_document"] == "docs/definitions/asset_definition_fund.md"
    assert projection["unit"]["divisibility"] == view.unit_divisibility().value
    assert projection["acquisition"] == view.acquisition_semantics().value
    assert projection["settlement"]["pattern"] == view.settlement_pattern().value
    assert projection["valuation_question"] == view.valuation_question().value
    assert set(projection["flows_granted"]) == {f.value for f in FlowType if view.grants_flow(f)}
    assert set(projection["event_families_granted"]) == {
        f.value for f in EventFamily if view.grants_event_family(f)
    }
    assert set(projection["existence"]["permitted_relationships"]) == {
        k.value for k in RelationshipKind if view.permits_relationship(k)
    }


# ── 3. Fingerprint Integrity ────────────────────────────────────────────────

def test_fund_pinned_fingerprint_validates():
    assert compute_fingerprint(library.FUND_V1) == library.PINNED_FINGERPRINTS[(AssetType.FUND.value, "v1")]


def test_tampered_fund_fingerprint_fails_boot():
    import services.asset_definitions.registry as registry_module

    original = registry_module.library.PINNED_FINGERPRINTS
    try:
        registry_module.library.PINNED_FINGERPRINTS = dict(original)
        registry_module.library.PINNED_FINGERPRINTS[(AssetType.FUND.value, "v1")] = "0" * 64
        with pytest.raises(DefinitionRegistryError) as excinfo:
            DefinitionRegistry.build()
        assert any(
            f.rule == "fingerprint-mismatch" and f.binding == AssetType.FUND.value
            for f in excinfo.value.findings
        )
    finally:
        registry_module.library.PINNED_FINGERPRINTS = original


# ── 4. Registry Integration ─────────────────────────────────────────────────

def test_definition_registry_exists_fund():
    assert DefinitionRegistry.build().exists("FUND") is True


def test_binding_resolver_resolves_fund():
    view = _resolver().resolve("FUND")
    assert view.acquisition_semantics() == AcquisitionSemantics.NAV_WINDOW


def test_unknown_bindings_still_unresolved_after_fund_addition():
    """Adding FUND must not widen resolution to any other still-undefined
    binding — a sibling entry cannot accidentally loosen refusal for
    bindings that never asked for one."""
    from services.asset_definitions import UnresolvedBindingError

    resolver = _resolver()
    for ghost in ("BOND", "CRYPTO", "COMMODITY", "PROPERTY", "OTHER"):
        with pytest.raises(UnresolvedBindingError):
            resolver.resolve(ghost)


# ── 5. Readiness ─────────────────────────────────────────────────────────────

def test_fund_readiness_is_defined():
    readiness = readiness_for(AssetType.FUND.value)
    assert readiness.status == ReadinessStatus.DEFINED
    assert readiness.missing_requirements == ()


def test_other_asset_types_readiness_unchanged_by_fund_authoring():
    assert readiness_for(AssetType.CASH.value).status == ReadinessStatus.DEFINED
    assert readiness_for(AssetType.EQUITY.value).status == ReadinessStatus.DEFINED
    assert readiness_for(AssetType.ETF.value).status == ReadinessStatus.DEFINED
    assert readiness_for(AssetType.BOND.value).status == ReadinessStatus.VOCABULARY_GAP
    assert readiness_for(AssetType.PROPERTY.value).status == ReadinessStatus.VOCABULARY_GAP
    assert readiness_for(AssetType.CRYPTO.value).status == ReadinessStatus.SCOPE_UNDECIDED
    assert readiness_for(AssetType.COMMODITY.value).status == ReadinessStatus.SCOPE_UNDECIDED
    assert readiness_for(AssetType.OTHER.value).status == ReadinessStatus.EXEMPT


# ── 6. Regression: CASH, EQUITY, and ETF are untouched ──────────────────────

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


def test_definition_ladders_now_exactly_four():
    assert set(library.DEFINITION_LADDERS.keys()) == {
        AssetType.CASH.value, AssetType.EQUITY.value, AssetType.ETF.value, AssetType.FUND.value,
    }
