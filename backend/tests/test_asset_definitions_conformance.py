"""Conformance corpus (M9 TDD Section 1.1, Section 6.1 milestone deliverable
"Conformance Tests"): every row of every canonical document's Capability
Projection table becomes one assertion here, against BOTH runtime doors —
CapabilityView (the engine surface) and GovernanceProjection (the human/
audit surface). From this file's existence, drift between the library and
the runtime is a test failure, not a silent discovery.

Each test's docstring/comment cites the exact table row it transcribes, so
a reviewer can compare this file to the source document line by line:
  docs/definitions/asset_definition_cash.md   -- "Capability Projection"
  docs/definitions/asset_definition_equity.md -- "Capability Projection"
  docs/definitions/asset_definition_etf.md    -- "Capability Projection"

If a document changes, this file must change in the same review, or CI
catches the mismatch here. ETF's row-by-row transcription lives in this
file's own block below; its individuation-specific coverage (D1, fingerprint
integrity, readiness, regression) lives in the milestone's dedicated
test_asset_definition_etf.py (M18), the same split test_vocabulary_periodic_nav.py
(M17) already established for a milestone-scoped corpus.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.asset_definitions import BindingResolver, DefinitionRegistry
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


def _resolver():
    return BindingResolver(DefinitionRegistry.build())


# ── Cash v1 — docs/definitions/asset_definition_cash.md ──────────────────

def test_cash_v1_unit_row():
    # | Unit | one currency unit; quantity ≡ native value |
    # | Quantity | continuous (precision: instance fact); non-negative |
    view = _resolver().resolve("CASH")
    assert view.unit_divisibility() == Divisibility.CONTINUOUS
    assert view.unit_quantity_equals_value() is True
    assert view.unit_allows_negative() is False


def test_cash_v1_acquisition_row():
    # | Acquisition | not transactable — transfer and counterleg only |
    view = _resolver().resolve("CASH")
    assert view.acquisition_semantics() == AcquisitionSemantics.NOT_TRANSACTABLE


def test_cash_v1_settlement_row():
    # | Settlement | instant |
    view = _resolver().resolve("CASH")
    assert view.settlement_pattern() == SettlementPattern.INSTANT


def test_cash_v1_valuation_row():
    # | Valuation question | none — identity; worth is face amount |
    view = _resolver().resolve("CASH")
    assert view.valuation_question() == ValuationQuestion.IDENTITY


def test_cash_v1_flows_row():
    # | Flows admissible | interest |
    view = _resolver().resolve("CASH")
    assert view.grants_flow(FlowType.INTEREST) is True
    assert view.grants_flow(FlowType.DIVIDEND) is False


def test_cash_v1_event_families_row():
    # | Event families | none |
    view = _resolver().resolve("CASH")
    for family in EventFamily:
        assert view.grants_event_family(family) is False


def test_cash_v1_existence_row():
    # | Existence | open-ended; no relationships |
    view = _resolver().resolve("CASH")
    assert view.existence_pattern() == ExistencePattern.OPEN_ENDED
    for kind in RelationshipKind:
        assert view.permits_relationship(kind) is False
        assert view.relationship_mandatory(kind) is False


# ── Equity v1 — docs/definitions/asset_definition_equity.md ──────────────

def test_equity_v1_unit_row():
    # | Unit | one share |
    # | Quantity | whole-share default; fractional/lot: instance facts; non-negative |
    view = _resolver().resolve("EQUITY")
    assert view.unit_divisibility() == Divisibility.DISCRETE
    assert view.unit_quantity_equals_value() is False
    assert view.unit_allows_negative() is False
    assert view.unit_permits_fractional_refinement() is True
    assert view.unit_permits_lot_refinement() is True


def test_equity_v1_acquisition_row():
    # | Acquisition | venue-traded |
    view = _resolver().resolve("EQUITY")
    assert view.acquisition_semantics() == AcquisitionSemantics.VENUE_TRADED


def test_equity_v1_settlement_row():
    # | Settlement | cycle-based (length: instance fact) |
    view = _resolver().resolve("EQUITY")
    assert view.settlement_pattern() == SettlementPattern.CYCLE_BASED
    assert view.settlement_permits_cycle_length_refinement() is True


def test_equity_v1_valuation_row():
    # | Valuation question | continuous quotation |
    view = _resolver().resolve("EQUITY")
    assert view.valuation_question() == ValuationQuestion.CONTINUOUS_QUOTATION


def test_equity_v1_flows_row():
    # | Flows admissible | dividend |
    view = _resolver().resolve("EQUITY")
    assert view.grants_flow(FlowType.DIVIDEND) is True
    assert view.grants_flow(FlowType.INTEREST) is False


def test_equity_v1_event_families_row():
    # | Event families | split, merger, spin-off, rename, suspension, delisting |
    view = _resolver().resolve("EQUITY")
    granted = {
        EventFamily.SPLIT, EventFamily.MERGER, EventFamily.SPIN_OFF,
        EventFamily.RENAME, EventFamily.SUSPENSION, EventFamily.DELISTING,
    }
    for family in EventFamily:
        assert view.grants_event_family(family) is (family in granted)


def test_equity_v1_existence_row():
    # | Existence | open-ended; may relate: same-entity, wraps, successor-of |
    view = _resolver().resolve("EQUITY")
    assert view.existence_pattern() == ExistencePattern.OPEN_ENDED
    permitted = {RelationshipKind.SAME_ENTITY, RelationshipKind.WRAPS, RelationshipKind.SUCCESSOR_OF}
    for kind in RelationshipKind:
        assert view.permits_relationship(kind) is (kind in permitted)
        assert view.relationship_mandatory(kind) is False  # neither v1 document declares a mandatory relationship


# ── ETF v1 — docs/definitions/asset_definition_etf.md (M18) ──────────────
# Full individuation/fingerprint/readiness/regression coverage lives in
# test_asset_definition_etf.py; these rows exist so this file's own
# row-by-row promise stays true for all three canonical documents.

def test_etf_v1_unit_row():
    # | Unit | one share |
    # | Quantity | whole-share default; fractional/lot: instance facts; non-negative |
    view = _resolver().resolve("ETF")
    assert view.unit_divisibility() == Divisibility.DISCRETE
    assert view.unit_quantity_equals_value() is False
    assert view.unit_allows_negative() is False
    assert view.unit_permits_fractional_refinement() is True
    assert view.unit_permits_lot_refinement() is True


def test_etf_v1_acquisition_row():
    # | Acquisition | venue-traded |
    view = _resolver().resolve("ETF")
    assert view.acquisition_semantics() == AcquisitionSemantics.VENUE_TRADED


def test_etf_v1_settlement_row():
    # | Settlement | cycle-based (length: instance fact) |
    view = _resolver().resolve("ETF")
    assert view.settlement_pattern() == SettlementPattern.CYCLE_BASED
    assert view.settlement_permits_cycle_length_refinement() is True


def test_etf_v1_valuation_row():
    # | Valuation question | periodic NAV |
    view = _resolver().resolve("ETF")
    assert view.valuation_question() == ValuationQuestion.PERIODIC_NAV


def test_etf_v1_flows_row():
    # | Flows admissible | dividend |
    view = _resolver().resolve("ETF")
    assert view.grants_flow(FlowType.DIVIDEND) is True
    assert view.grants_flow(FlowType.INTEREST) is False


def test_etf_v1_event_families_row():
    # | Event families | split, merger, spin-off, rename, suspension, delisting |
    view = _resolver().resolve("ETF")
    granted = {
        EventFamily.SPLIT, EventFamily.MERGER, EventFamily.SPIN_OFF,
        EventFamily.RENAME, EventFamily.SUSPENSION, EventFamily.DELISTING,
    }
    for family in EventFamily:
        assert view.grants_event_family(family) is (family in granted)


def test_etf_v1_existence_row():
    # | Existence | open-ended; may relate: same-entity, wraps, successor-of |
    view = _resolver().resolve("ETF")
    assert view.existence_pattern() == ExistencePattern.OPEN_ENDED
    permitted = {RelationshipKind.SAME_ENTITY, RelationshipKind.WRAPS, RelationshipKind.SUCCESSOR_OF}
    for kind in RelationshipKind:
        assert view.permits_relationship(kind) is (kind in permitted)
        assert view.relationship_mandatory(kind) is False


def test_etf_v1_differs_from_equity_v1_only_on_valuation():
    # The individuating declaration (D1) — every other row above is
    # byte-identical to Equity's own block.
    etf = _resolver().resolve("ETF")
    equity = _resolver().resolve("EQUITY")
    assert etf.valuation_question() != equity.valuation_question()
    assert etf.unit_divisibility() == equity.unit_divisibility()
    assert etf.acquisition_semantics() == equity.acquisition_semantics()
    assert etf.settlement_pattern() == equity.settlement_pattern()
    for f in FlowType:
        assert etf.grants_flow(f) == equity.grants_flow(f)
    for fam in EventFamily:
        assert etf.grants_event_family(fam) == equity.grants_event_family(fam)
    for kind in RelationshipKind:
        assert etf.permits_relationship(kind) == equity.permits_relationship(kind)


# ── GovernanceProjection must agree with CapabilityView exactly ──────────
# (the two doors are two views of one payload — this is the "Library ->
# Runtime Projection remain equivalent" check the milestone brief asks for)

def test_governance_projection_matches_capability_view_for_cash():
    registry = DefinitionRegistry.build()
    resolver = BindingResolver(registry)
    view = resolver.resolve("CASH")
    projection = registry.get("CASH").as_dict()

    assert projection["unit"]["divisibility"] == view.unit_divisibility().value
    assert projection["unit"]["quantity_equals_value"] == view.unit_quantity_equals_value()
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


def test_governance_projection_matches_capability_view_for_equity():
    registry = DefinitionRegistry.build()
    resolver = BindingResolver(registry)
    view = resolver.resolve("EQUITY")
    projection = registry.get("EQUITY").as_dict()

    assert projection["unit"]["divisibility"] == view.unit_divisibility().value
    assert set(projection["flows_granted"]) == {f.value for f in FlowType if view.grants_flow(f)}
    assert set(projection["event_families_granted"]) == {
        f.value for f in EventFamily if view.grants_event_family(f)
    }
    assert set(projection["existence"]["permitted_relationships"]) == {
        k.value for k in RelationshipKind if view.permits_relationship(k)
    }


# ── D7: absence is a declaration, and the two definitions must exercise
# both poles of every axis (asset_definition_library.md Section 2's
# "they span the axes" table) ──────────────────────────────────────────

def test_founding_pair_spans_every_axis_in_both_directions():
    resolver = _resolver()
    cash = resolver.resolve("CASH")
    equity = resolver.resolve("EQUITY")

    assert cash.unit_divisibility() != equity.unit_divisibility()
    assert cash.acquisition_semantics() != equity.acquisition_semantics()
    assert cash.settlement_pattern() != equity.settlement_pattern()
    assert cash.valuation_question() != equity.valuation_question()
    assert cash.grants_flow(FlowType.INTEREST) and not equity.grants_flow(FlowType.INTEREST)
    assert equity.grants_flow(FlowType.DIVIDEND) and not cash.grants_flow(FlowType.DIVIDEND)
    assert not any(cash.grants_event_family(f) for f in EventFamily)
    assert any(equity.grants_event_family(f) for f in EventFamily)
    assert not any(cash.permits_relationship(k) for k in RelationshipKind)
    assert any(equity.permits_relationship(k) for k in RelationshipKind)
