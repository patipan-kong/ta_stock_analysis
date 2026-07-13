"""M26 brief: Vocabulary Extension Stage (Property Vocabulary Bundle).

Adds `AcquisitionSemantics.NEGOTIATED_TRANSFER`, `SettlementPattern.
NEGOTIATED_CLOSING`, `ValuationQuestion.APPRAISAL_ON_EVENT`, and
`FlowType.RENT` — the four coordinated words M25's design document
(docs/definitions/property_vocabulary_bundle_design.md) found are
PROPERTY's entire remaining vocabulary gap (re-validating and deepening
M20's own gap analysis, asset_model_gap_analysis.md §3.3). This milestone
implements exactly the approved design, unmodified: no word is renamed, no
fifth word is introduced, and no PROPERTY definition is authored.
`library.DEFINITION_LADDERS` is still exactly CASH, EQUITY, ETF, FUND,
BOND, unchanged — PROPERTY remains vocabulary-ready but unauthored, ready
for a future dedicated authoring milestone (M27).

Coverage, per the brief's "Required Tests":
  1. Vocabulary Acceptance — all four words construct, flow through a full
     transcription individually and together, and fingerprint like any
     other word.
  2. Backward Compatibility — the real library still boots; CASH v1/
     Equity v1/ETF v1/Fund v1/Bond v1's declarations and pinned
     fingerprints are byte-identical to before this milestone.
  3. Closed Vocabulary Integrity — an unknown string still fails to
     construct any of the four affected enums; each axis's full member set
     is pinned so a future silent addition/removal is caught here.
  4. Fingerprint Stability — recomputing every pinned definition's
     fingerprint still matches the pinned manifest (a sibling enum member
     cannot move a fingerprint of a transcription that never uses it).
  5. D1 Uniqueness — a property-shaped synthetic transcription (all four
     new words together) individuates against every real canonical
     definition and against a non-property-shaped synthetic; each new word
     individuates alone; sharing all four new words together does not
     bypass D1 duplicate detection when every other axis matches.
  6. Regression — the existing single-word and two-word vocabulary test
     files (M17, M21, M23) continue to pass unmodified; this file adds
     coverage rather than replacing theirs.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from services.asset_definitions import library
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
from services.asset_definitions.governance import GovernanceProjection
from services.asset_definitions.registry import DefinitionRegistry, _validate
from services.asset_definitions.vocabulary import (
    AcquisitionSemantics,
    Divisibility,
    ExistencePattern,
    FlowType,
    SettlementPattern,
    ValuationQuestion,
)


def _synthetic(
    binding,
    acquisition_semantics=AcquisitionSemantics.VENUE_TRADED,
    settlement_pattern=SettlementPattern.CYCLE_BASED,
    valuation_question=ValuationQuestion.CONTINUOUS_QUOTATION,
    flow_type=FlowType.DIVIDEND,
    version="v1",
    effective_from="2026-07-13",
):
    """A minimal, self-consistent transcription — same shape as the other
    vocabulary-extension test files' own `_synthetic` helpers, generalized
    so all four axes this milestone touches can be varied independently
    while the rest stay at an ordinary equity-shaped baseline. Not a real
    definition; feeds `_validate()` directly and is never placed in
    `library.DEFINITION_LADDERS`."""
    return DefinitionTranscription(
        name=f"Synthetic-{binding}",
        version=version,
        binding=binding,
        source_document="test-fixture",
        effective_from=effective_from,
        unit=UnitDeclaration(Divisibility.DISCRETE, False, False, True, True),
        acquisition=AcquisitionDeclaration(acquisition_semantics),
        settlement=SettlementDeclaration(settlement_pattern, False),
        valuation=ValuationDeclaration(valuation_question),
        flows=FlowGrants(frozenset({flow_type})),
        event_families=EventFamilyGrants(frozenset()),
        existence=ExistenceDeclaration(ExistencePattern.OPEN_ENDED, frozenset(), frozenset()),
    )


def _property_shaped(binding):
    """The minimal honest PROPERTY declaration per
    property_vocabulary_bundle_design.md §6 — all four new words together.
    Still not a real definition: PROPERTY remains unauthored."""
    return _synthetic(
        binding,
        acquisition_semantics=AcquisitionSemantics.NEGOTIATED_TRANSFER,
        settlement_pattern=SettlementPattern.NEGOTIATED_CLOSING,
        valuation_question=ValuationQuestion.APPRAISAL_ON_EVENT,
        flow_type=FlowType.RENT,
    )


# ── 1. Vocabulary Acceptance ────────────────────────────────────────────────

def test_negotiated_transfer_is_an_acquisition_semantics_member():
    assert AcquisitionSemantics.NEGOTIATED_TRANSFER.value == "NEGOTIATED_TRANSFER"
    assert AcquisitionSemantics("NEGOTIATED_TRANSFER") is AcquisitionSemantics.NEGOTIATED_TRANSFER


def test_negotiated_closing_is_a_settlement_pattern_member():
    assert SettlementPattern.NEGOTIATED_CLOSING.value == "NEGOTIATED_CLOSING"
    assert SettlementPattern("NEGOTIATED_CLOSING") is SettlementPattern.NEGOTIATED_CLOSING


def test_appraisal_on_event_is_a_valuation_question_member():
    assert ValuationQuestion.APPRAISAL_ON_EVENT.value == "APPRAISAL_ON_EVENT"
    assert ValuationQuestion("APPRAISAL_ON_EVENT") is ValuationQuestion.APPRAISAL_ON_EVENT


def test_rent_is_a_flow_type_member():
    assert FlowType.RENT.value == "RENT"
    assert FlowType("RENT") is FlowType.RENT


@pytest.mark.parametrize(
    "kwargs",
    [
        {"acquisition_semantics": AcquisitionSemantics.NEGOTIATED_TRANSFER},
        {"settlement_pattern": SettlementPattern.NEGOTIATED_CLOSING},
        {"valuation_question": ValuationQuestion.APPRAISAL_ON_EVENT},
        {"flow_type": FlowType.RENT},
    ],
)
def test_each_word_flows_through_a_full_transcription_and_fingerprints(kwargs):
    t = _synthetic("PROPERTY", **kwargs)
    digest = compute_fingerprint(t)
    assert isinstance(digest, str) and len(digest) == 64  # sha256 hexdigest


def test_all_four_words_together_flow_through_a_full_transcription_and_fingerprint():
    t = _property_shaped("PROPERTY")
    assert t.acquisition.semantics == AcquisitionSemantics.NEGOTIATED_TRANSFER
    assert t.settlement.pattern == SettlementPattern.NEGOTIATED_CLOSING
    assert t.valuation.question == ValuationQuestion.APPRAISAL_ON_EVENT
    assert t.flows.granted == frozenset({FlowType.RENT})
    digest = compute_fingerprint(t)
    assert isinstance(digest, str) and len(digest) == 64


def test_all_four_words_surface_through_governance_projection():
    t = _property_shaped("PROPERTY")
    projection = GovernanceProjection(t).as_dict()
    assert projection["acquisition"] == "NEGOTIATED_TRANSFER"
    assert projection["settlement"]["pattern"] == "NEGOTIATED_CLOSING"
    assert projection["valuation_question"] == "APPRAISAL_ON_EVENT"
    assert projection["flows_granted"] == ["RENT"]


# ── 2. Backward Compatibility ───────────────────────────────────────────────

def test_real_library_still_boots_clean():
    registry = DefinitionRegistry.build()
    assert registry.exists("CASH")
    assert registry.exists("EQUITY")
    assert registry.exists("ETF")
    assert registry.exists("FUND")
    assert registry.exists("BOND")
    # M26 was vocabulary-only, per its own non-goals ("do not author
    # PROPERTY") — PROPERTY stayed unresolved until M27 used these four
    # words for real. Updated here rather than left stale, the same
    # discipline this file's own comment once flagged for a future milestone.
    assert registry.exists("PROPERTY") is True


def test_existing_definitions_declarations_are_unchanged():
    """Adding four sibling enum members cannot move a transcription that
    never references them — pinned so a future edit to any of the four
    axes can't silently touch an existing canonical definition."""
    assert library.CASH_V1.acquisition.semantics == AcquisitionSemantics.NOT_TRANSACTABLE
    assert library.EQUITY_V1.acquisition.semantics == AcquisitionSemantics.VENUE_TRADED
    assert library.ETF_V1.acquisition.semantics == AcquisitionSemantics.VENUE_TRADED
    assert library.FUND_V1.acquisition.semantics == AcquisitionSemantics.NAV_WINDOW
    assert library.BOND_V1.acquisition.semantics == AcquisitionSemantics.VENUE_TRADED

    assert library.CASH_V1.settlement.pattern == SettlementPattern.INSTANT
    assert library.EQUITY_V1.settlement.pattern == SettlementPattern.CYCLE_BASED
    assert library.BOND_V1.settlement.pattern == SettlementPattern.CYCLE_BASED

    assert library.CASH_V1.valuation.question == ValuationQuestion.IDENTITY
    assert library.EQUITY_V1.valuation.question == ValuationQuestion.CONTINUOUS_QUOTATION
    assert library.ETF_V1.valuation.question == ValuationQuestion.PERIODIC_NAV
    assert library.FUND_V1.valuation.question == ValuationQuestion.PERIODIC_NAV
    assert library.BOND_V1.valuation.question == ValuationQuestion.CONTINUOUS_QUOTATION

    assert library.CASH_V1.flows.granted == frozenset({FlowType.INTEREST})
    assert library.EQUITY_V1.flows.granted == frozenset({FlowType.DIVIDEND})
    assert library.BOND_V1.flows.granted == frozenset({FlowType.COUPON})


def test_existing_fingerprints_are_unchanged():
    assert compute_fingerprint(library.CASH_V1) == library.PINNED_FINGERPRINTS[("CASH", "v1")]
    assert compute_fingerprint(library.EQUITY_V1) == library.PINNED_FINGERPRINTS[("EQUITY", "v1")]
    assert compute_fingerprint(library.ETF_V1) == library.PINNED_FINGERPRINTS[("ETF", "v1")]
    assert compute_fingerprint(library.FUND_V1) == library.PINNED_FINGERPRINTS[("FUND", "v1")]
    assert compute_fingerprint(library.BOND_V1) == library.PINNED_FINGERPRINTS[("BOND", "v1")]


def test_definition_ladders_untouched_by_this_milestone():
    # True as of M26 (vocabulary-only); M27 later added PROPERTY using these
    # four words — see test_asset_definition_property.py. Updated here
    # rather than left stale.
    assert set(library.DEFINITION_LADDERS.keys()) == {"CASH", "EQUITY", "ETF", "FUND", "BOND", "PROPERTY"}


# ── 3. Closed Vocabulary Integrity ──────────────────────────────────────────

def test_unknown_acquisition_word_still_fails_to_construct():
    with pytest.raises(ValueError):
        AcquisitionSemantics("NOT_A_REAL_ACQUISITION_WORD")


def test_unknown_settlement_word_still_fails_to_construct():
    with pytest.raises(ValueError):
        SettlementPattern("NOT_A_REAL_SETTLEMENT_WORD")


def test_unknown_valuation_word_still_fails_to_construct():
    with pytest.raises(ValueError):
        ValuationQuestion("NOT_A_REAL_VALUATION_WORD")


def test_unknown_flow_word_still_fails_to_construct():
    with pytest.raises(ValueError):
        FlowType("NOT_A_REAL_FLOW_WORD")


def test_acquisition_semantics_member_set_is_pinned():
    assert {m.value for m in AcquisitionSemantics} == {
        "NOT_TRANSACTABLE",
        "VENUE_TRADED",
        "NAV_WINDOW",
        "NEGOTIATED_TRANSFER",
    }


def test_settlement_pattern_member_set_is_pinned():
    assert {m.value for m in SettlementPattern} == {
        "INSTANT",
        "CYCLE_BASED",
        "NEGOTIATED_CLOSING",
    }


def test_valuation_question_member_set_is_pinned():
    assert {m.value for m in ValuationQuestion} == {
        "IDENTITY",
        "CONTINUOUS_QUOTATION",
        "PERIODIC_NAV",
        "APPRAISAL_ON_EVENT",
    }


def test_flow_type_member_set_is_pinned():
    assert {m.value for m in FlowType} == {
        "INTEREST",
        "DIVIDEND",
        "COUPON",
        "RENT",
    }


# ── 4. D1 Uniqueness ─────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "kwargs",
    [
        {"acquisition_semantics": AcquisitionSemantics.NEGOTIATED_TRANSFER},
        {"settlement_pattern": SettlementPattern.NEGOTIATED_CLOSING},
        {"valuation_question": ValuationQuestion.APPRAISAL_ON_EVENT},
        {"flow_type": FlowType.RENT},
    ],
)
def test_each_word_individuates_an_otherwise_identical_transcription(kwargs):
    """Each of the four new words, alone, individuates against an ordinary
    equity-shaped baseline — no existing definition declares any of them
    on any axis today."""
    baseline = _synthetic("EQUITY")
    candidate = _synthetic("PROPERTY", **kwargs)

    findings = _validate(
        {"EQUITY": (baseline,), "PROPERTY": (candidate,)},
        {
            ("EQUITY", "v1"): compute_fingerprint(baseline),
            ("PROPERTY", "v1"): compute_fingerprint(candidate),
        },
    )
    assert not any(f.rule == "duplicate-declarations" for f in findings)


def test_property_shaped_declaration_individuates_from_an_equity_shaped_one():
    """The reason this bundle was added: a property-shaped declaration (all
    four new words) must not collide with an ordinary venue-traded,
    cycle-settled, continuously-quoted, dividend-paying declaration."""
    equity_shaped = _synthetic("EQUITY")
    property_shaped = _property_shaped("PROPERTY")

    findings = _validate(
        {"EQUITY": (equity_shaped,), "PROPERTY": (property_shaped,)},
        {
            ("EQUITY", "v1"): compute_fingerprint(equity_shaped),
            ("PROPERTY", "v1"): compute_fingerprint(property_shaped),
        },
    )
    assert not any(f.rule == "duplicate-declarations" for f in findings)


def test_property_shaped_declaration_individuates_against_the_real_library():
    """A property-shaped synthetic checked against the real, currently
    canonical library — proving the bundle genuinely opens a path to a
    future PROPERTY definition reusing all four words. Bound to "OTHER" (a
    binding with no canonical definition and none anticipated, M9 TDD
    Section 10.2) rather than "PROPERTY" itself, mirroring
    test_vocabulary_bond_lifecycle.py's own precedent for checking a
    hypothetical reuse against the real library without colliding with a
    ladder entry that does not yet exist."""
    property_shaped = _property_shaped("OTHER")
    combined_bindings = dict(library.DEFINITION_LADDERS)
    combined_bindings["OTHER"] = (property_shaped,)
    combined_fingerprints = dict(library.PINNED_FINGERPRINTS)
    combined_fingerprints[("OTHER", "v1")] = compute_fingerprint(property_shaped)

    findings = _validate(combined_bindings, combined_fingerprints)
    assert not any(f.rule == "duplicate-declarations" for f in findings)


def test_sharing_all_four_new_words_together_does_not_bypass_d1():
    """The brief's own explicit requirement, generalized from
    test_vocabulary_bond_lifecycle.py's two-word version to this bundle's
    four: sharing all four new words together, with every other axis
    identical, is still a duplicate — the bundle is not, jointly, an
    identity token any more than any single word within it is."""
    a = _property_shaped("PROPERTY")
    b = _property_shaped("OTHER")

    findings = _validate(
        {"PROPERTY": (a,), "OTHER": (b,)},
        {("PROPERTY", "v1"): compute_fingerprint(a), ("OTHER", "v1"): compute_fingerprint(b)},
    )
    assert any(f.rule == "duplicate-declarations" for f in findings)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"acquisition_semantics": AcquisitionSemantics.NEGOTIATED_TRANSFER},
        {"settlement_pattern": SettlementPattern.NEGOTIATED_CLOSING},
        {"valuation_question": ValuationQuestion.APPRAISAL_ON_EVENT},
        {"flow_type": FlowType.RENT},
    ],
)
def test_each_word_does_not_weaken_d1_when_shared_alone(kwargs):
    """Two transcriptions that share one new word *and* every other axis
    are still an honest duplicate — each word individuates only when it is
    actually the differing declaration, never a blanket exemption from D1."""
    a = _synthetic("PROPERTY", **kwargs)
    b = _synthetic("OTHER", **kwargs)

    findings = _validate(
        {"PROPERTY": (a,), "OTHER": (b,)},
        {("PROPERTY", "v1"): compute_fingerprint(a), ("OTHER", "v1"): compute_fingerprint(b)},
    )
    assert any(f.rule == "duplicate-declarations" for f in findings)


def test_identical_baseline_still_collides_when_everything_matches():
    """Baseline sanity: sharing only existing words (VENUE_TRADED,
    CYCLE_BASED, CONTINUOUS_QUOTATION, DIVIDEND) and every other axis is a
    duplicate too — demonstrating the four new words represent genuine
    differentiation, not that D1 has generally been loosened."""
    a = _synthetic("EQUITY")
    b = _synthetic("ETF")

    findings = _validate(
        {"EQUITY": (a,), "ETF": (b,)},
        {("EQUITY", "v1"): compute_fingerprint(a), ("ETF", "v1"): compute_fingerprint(b)},
    )
    assert any(f.rule == "duplicate-declarations" for f in findings)
