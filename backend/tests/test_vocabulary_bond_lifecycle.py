"""M23 brief: Vocabulary Extension Stage (Bond Lifecycle Semantics).

Adds `FlowType.COUPON` and `ExistencePattern.SCHEDULED_TERMINAL` — the two
words `asset_definitions.md` §9's own Bond walk names as "long anticipated"
("the coupon flow type... and the scheduled-terminal existence pattern"),
and which the M20 gap analysis (asset_model_gap_analysis.md §3.2, §5
concepts C6/C8) confirms are BOND's entire remaining vocabulary gap. This
milestone adds only the two words. No BOND definition is authored:
`library.DEFINITION_LADDERS` is still exactly CASH, EQUITY, ETF, FUND,
unchanged. (M24 subsequently authored BOND_V1 using exactly these two
words — see test_asset_definition_bond.py and this file's own tests below,
updated at that time to reflect BOND's real presence in the library.)

Coverage, per the brief's "Required Tests":
  1. Vocabulary Acceptance — both words construct, flow through a full
     transcription, and fingerprint like any other word.
  2. Backward Compatibility — the real library still boots; CASH v1/Equity
     v1/ETF v1/Fund v1's declarations and pinned fingerprints are
     byte-identical to before this milestone; BOND remains unresolved.
  3. Closed Vocabulary Integrity — an unknown string still fails to
     construct a FlowType or an ExistencePattern; each axis's full member
     set is pinned so a future silent addition/removal is caught here.
  4. D1 Protection — a bond-shaped synthetic transcription (COUPON +
     SCHEDULED_TERMINAL) individuates against a non-bond-shaped one, and
     against the real library, using genuine semantic differences; sharing
     COUPON alone, SCHEDULED_TERMINAL alone, or both together does not by
     itself bypass D1 duplicate detection when every other axis matches.
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
    flow_type=FlowType.DIVIDEND,
    existence_pattern=ExistencePattern.OPEN_ENDED,
    version="v1",
    effective_from="2026-07-13",
):
    """A minimal, self-consistent transcription — same shape as
    test_vocabulary_nav_window_acquisition.py's `_synthetic`, generalized so
    the flow and existence axes can be varied independently. Not a real
    definition; feeds `_validate()` directly and is never placed in
    `library.DEFINITION_LADDERS`."""
    return DefinitionTranscription(
        name=f"Synthetic-{binding}",
        version=version,
        binding=binding,
        source_document="test-fixture",
        effective_from=effective_from,
        unit=UnitDeclaration(Divisibility.DISCRETE, False, False, True, True),
        acquisition=AcquisitionDeclaration(AcquisitionSemantics.VENUE_TRADED),
        settlement=SettlementDeclaration(SettlementPattern.CYCLE_BASED, True),
        valuation=ValuationDeclaration(ValuationQuestion.CONTINUOUS_QUOTATION),
        flows=FlowGrants(frozenset({flow_type})),
        event_families=EventFamilyGrants(frozenset()),
        existence=ExistenceDeclaration(existence_pattern, frozenset(), frozenset()),
    )


# ── 1. Vocabulary Acceptance ────────────────────────────────────────────────

def test_coupon_is_a_flow_type_member():
    assert FlowType.COUPON.value == "COUPON"
    assert FlowType("COUPON") is FlowType.COUPON


def test_scheduled_terminal_is_an_existence_pattern_member():
    assert ExistencePattern.SCHEDULED_TERMINAL.value == "SCHEDULED_TERMINAL"
    assert ExistencePattern("SCHEDULED_TERMINAL") is ExistencePattern.SCHEDULED_TERMINAL


def test_coupon_flows_through_a_full_transcription_and_fingerprints():
    t = _synthetic("BOND", flow_type=FlowType.COUPON)
    assert t.flows.granted == frozenset({FlowType.COUPON})
    digest = compute_fingerprint(t)
    assert isinstance(digest, str) and len(digest) == 64  # sha256 hexdigest


def test_scheduled_terminal_flows_through_a_full_transcription_and_fingerprints():
    t = _synthetic("BOND", existence_pattern=ExistencePattern.SCHEDULED_TERMINAL)
    assert t.existence.pattern == ExistencePattern.SCHEDULED_TERMINAL
    digest = compute_fingerprint(t)
    assert isinstance(digest, str) and len(digest) == 64  # sha256 hexdigest


def test_both_words_surface_through_governance_projection():
    t = _synthetic(
        "BOND",
        flow_type=FlowType.COUPON,
        existence_pattern=ExistencePattern.SCHEDULED_TERMINAL,
    )
    projection = GovernanceProjection(t).as_dict()
    assert projection["flows_granted"] == ["COUPON"]
    assert projection["existence"]["pattern"] == "SCHEDULED_TERMINAL"


# ── 2. Backward Compatibility ───────────────────────────────────────────────

def test_real_library_still_boots_clean():
    registry = DefinitionRegistry.build()
    assert registry.exists("CASH")
    assert registry.exists("EQUITY")
    assert registry.exists("ETF")
    assert registry.exists("FUND")
    # M24: BOND was subsequently authored using exactly these two words —
    # see test_asset_definition_bond.py for that milestone's own coverage.
    assert registry.exists("BOND") is True


def test_cash_equity_etf_fund_declarations_are_unchanged():
    """Adding sibling enum members cannot move a transcription that never
    references them — pinned so a future edit to either axis can't silently
    touch CASH_V1/EQUITY_V1/ETF_V1/FUND_V1 by accident."""
    assert library.CASH_V1.flows.granted == frozenset({FlowType.INTEREST})
    assert library.EQUITY_V1.flows.granted == frozenset({FlowType.DIVIDEND})
    assert library.ETF_V1.flows.granted == frozenset({FlowType.DIVIDEND})
    assert library.FUND_V1.flows.granted == frozenset({FlowType.DIVIDEND})
    assert library.CASH_V1.existence.pattern == ExistencePattern.OPEN_ENDED
    assert library.EQUITY_V1.existence.pattern == ExistencePattern.OPEN_ENDED
    assert library.ETF_V1.existence.pattern == ExistencePattern.OPEN_ENDED
    assert library.FUND_V1.existence.pattern == ExistencePattern.OPEN_ENDED


def test_cash_equity_etf_fund_fingerprints_are_unchanged():
    assert compute_fingerprint(library.CASH_V1) == library.PINNED_FINGERPRINTS[("CASH", "v1")]
    assert compute_fingerprint(library.EQUITY_V1) == library.PINNED_FINGERPRINTS[("EQUITY", "v1")]
    assert compute_fingerprint(library.ETF_V1) == library.PINNED_FINGERPRINTS[("ETF", "v1")]
    assert compute_fingerprint(library.FUND_V1) == library.PINNED_FINGERPRINTS[("FUND", "v1")]


def test_definition_ladders_untouched_by_this_milestone():
    # M24: BOND was subsequently added — see test_asset_definition_bond.py's
    # own version of this assertion for that milestone.
    assert set(library.DEFINITION_LADDERS.keys()) == {"CASH", "EQUITY", "ETF", "FUND", "BOND"}


# ── 3. Closed Vocabulary Integrity ──────────────────────────────────────────

def test_unknown_flow_word_still_fails_to_construct():
    with pytest.raises(ValueError):
        FlowType("NOT_A_REAL_FLOW_WORD")


def test_unknown_existence_word_still_fails_to_construct():
    with pytest.raises(ValueError):
        ExistencePattern("NOT_A_REAL_EXISTENCE_WORD")


def test_flow_type_member_set_is_pinned():
    """Guards against silent vocabulary drift — mirrors the discipline
    test_vocabulary_periodic_nav.py/test_vocabulary_nav_window_acquisition.py
    apply to their own axes."""
    assert {m.value for m in FlowType} == {"INTEREST", "DIVIDEND", "COUPON"}


def test_existence_pattern_member_set_is_pinned():
    assert {m.value for m in ExistencePattern} == {"OPEN_ENDED", "SCHEDULED_TERMINAL"}


# ── 4. D1 Protection ─────────────────────────────────────────────────────────

def test_coupon_individuates_a_bond_shaped_declaration_from_a_dividend_only_one():
    """The reason this word was added: a coupon-paying, otherwise-equity-
    shaped declaration must NOT collide with a dividend-paying one."""
    dividend_only = _synthetic("EQUITY", flow_type=FlowType.DIVIDEND)
    coupon_bearing = _synthetic("BOND", flow_type=FlowType.COUPON)

    findings = _validate(
        {"EQUITY": (dividend_only,), "BOND": (coupon_bearing,)},
        {
            ("EQUITY", "v1"): compute_fingerprint(dividend_only),
            ("BOND", "v1"): compute_fingerprint(coupon_bearing),
        },
    )
    assert not any(f.rule == "duplicate-declarations" for f in findings)


def test_scheduled_terminal_individuates_a_bond_shaped_declaration_from_an_open_ended_one():
    """The reason this word was added: a scheduled-terminal, otherwise-
    equity-shaped declaration must NOT collide with an open-ended one."""
    open_ended = _synthetic("EQUITY", existence_pattern=ExistencePattern.OPEN_ENDED)
    scheduled_terminal = _synthetic("BOND", existence_pattern=ExistencePattern.SCHEDULED_TERMINAL)

    findings = _validate(
        {"EQUITY": (open_ended,), "BOND": (scheduled_terminal,)},
        {
            ("EQUITY", "v1"): compute_fingerprint(open_ended),
            ("BOND", "v1"): compute_fingerprint(scheduled_terminal),
        },
    )
    assert not any(f.rule == "duplicate-declarations" for f in findings)


def test_coupon_does_not_weaken_d1_when_shared():
    """Two transcriptions that share COUPON *and* every other axis are
    still an honest duplicate — the new word individuates only when it is
    actually the differing declaration, never a blanket exemption from D1."""
    a = _synthetic("BOND", flow_type=FlowType.COUPON)
    b = _synthetic("OTHER", flow_type=FlowType.COUPON)

    findings = _validate(
        {"BOND": (a,), "OTHER": (b,)},
        {("BOND", "v1"): compute_fingerprint(a), ("OTHER", "v1"): compute_fingerprint(b)},
    )
    assert any(f.rule == "duplicate-declarations" for f in findings)


def test_scheduled_terminal_does_not_weaken_d1_when_shared():
    """Same guarantee as above, for the existence axis."""
    a = _synthetic("BOND", existence_pattern=ExistencePattern.SCHEDULED_TERMINAL)
    b = _synthetic("OTHER", existence_pattern=ExistencePattern.SCHEDULED_TERMINAL)

    findings = _validate(
        {"BOND": (a,), "OTHER": (b,)},
        {("BOND", "v1"): compute_fingerprint(a), ("OTHER", "v1"): compute_fingerprint(b)},
    )
    assert any(f.rule == "duplicate-declarations" for f in findings)


def test_sharing_both_new_words_together_does_not_bypass_d1():
    """The brief's own explicit requirement: sharing COUPON *and*
    SCHEDULED_TERMINAL together, with every other axis identical, is still
    a duplicate — the pair of new words is not, jointly, an identity
    token any more than either is alone."""
    a = _synthetic(
        "BOND",
        flow_type=FlowType.COUPON,
        existence_pattern=ExistencePattern.SCHEDULED_TERMINAL,
    )
    b = _synthetic(
        "OTHER",
        flow_type=FlowType.COUPON,
        existence_pattern=ExistencePattern.SCHEDULED_TERMINAL,
    )

    findings = _validate(
        {"BOND": (a,), "OTHER": (b,)},
        {("BOND", "v1"): compute_fingerprint(a), ("OTHER", "v1"): compute_fingerprint(b)},
    )
    assert any(f.rule == "duplicate-declarations" for f in findings)


def test_bond_shaped_declaration_individuates_against_the_real_library():
    """A bond-shaped synthetic (COUPON + SCHEDULED_TERMINAL) checked against
    the real, currently-canonical library — proving the two new words
    genuinely open a path to a future definition reusing them, the reuse
    this milestone's brief anticipates. M24 subsequently authored the real
    BOND_V1 using exactly these two words (see
    test_asset_definition_bond.py's own D1 coverage against BOND_V1
    directly) — this synthetic now binds to "OTHER" (a binding with no
    canonical definition and none anticipated, M9 TDD Section 10.2) rather
    than "BOND", so this test keeps checking a *hypothetical* reuse of the
    pair against the real, current library, including the real BOND_V1
    itself, without colliding with BOND's own now-real ladder entry."""
    bond_shaped = _synthetic(
        "OTHER",
        flow_type=FlowType.COUPON,
        existence_pattern=ExistencePattern.SCHEDULED_TERMINAL,
    )
    real = {
        binding: rungs
        for binding, rungs in library.DEFINITION_LADDERS.items()
    }
    fingerprints = dict(library.PINNED_FINGERPRINTS)
    combined_bindings = dict(real)
    combined_bindings["OTHER"] = (bond_shaped,)
    combined_fingerprints = dict(fingerprints)
    combined_fingerprints[("OTHER", "v1")] = compute_fingerprint(bond_shaped)

    findings = _validate(combined_bindings, combined_fingerprints)
    assert not any(f.rule == "duplicate-declarations" for f in findings)


def test_identical_flow_type_still_collides_when_everything_else_matches():
    """Baseline sanity: sharing an *existing* word (DIVIDEND) and every
    other axis is a duplicate too — demonstrating the new words represent
    genuine differentiation, not that D1 has generally been loosened."""
    a = _synthetic("EQUITY", flow_type=FlowType.DIVIDEND)
    b = _synthetic("ETF", flow_type=FlowType.DIVIDEND)

    findings = _validate(
        {"EQUITY": (a,), "ETF": (b,)},
        {("EQUITY", "v1"): compute_fingerprint(a), ("ETF", "v1"): compute_fingerprint(b)},
    )
    assert any(f.rule == "duplicate-declarations" for f in findings)
