"""M17 brief: Vocabulary Extension Stage (Periodic NAV Valuation).

Adds `ValuationQuestion.PERIODIC_NAV` — the word `asset_definitions.md` §9's
own ETF walk names as ETF's individuating declaration against Equity, and
whose absence M16 found blocked ETF authoring outright (D1 duplicate). This
milestone adds only the word. No canonical definition uses it yet:
`library.DEFINITION_LADDERS` is still exactly CASH and EQUITY, unchanged.

Coverage, per the brief's "Required Tests":
  1. Vocabulary Acceptance — PERIODIC_NAV constructs, flows through a full
     transcription, and fingerprints like any other word.
  2. Backward Compatibility — the real library still boots; CASH v1/Equity
     v1's declarations and pinned fingerprints are byte-identical to before
     this milestone (adding a sibling enum member cannot move a definition
     that doesn't use it).
  3. Closed Vocabulary Integrity — an unknown string still fails to
     construct a ValuationQuestion; the axis's full member set is pinned so
     a future silent addition/removal is caught here, not discovered later.
  4. Duplicate Protection (D1) — PERIODIC_NAV successfully individuates two
     otherwise-identical synthetic transcriptions (the reason this word was
     added), and does not weaken D1 for transcriptions that share it too.
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


def _synthetic(binding, valuation_question, version="v1", effective_from="2026-07-13"):
    """A minimal, self-consistent transcription — same shape as
    test_asset_definitions_registry.py's `_cash_like`, generalized so the
    valuation axis can be varied. Not a real definition; feeds `_validate()`
    directly and is never placed in `library.DEFINITION_LADDERS`."""
    return DefinitionTranscription(
        name=f"Synthetic-{binding}",
        version=version,
        binding=binding,
        source_document="test-fixture",
        effective_from=effective_from,
        unit=UnitDeclaration(Divisibility.DISCRETE, False, False, True, True),
        acquisition=AcquisitionDeclaration(AcquisitionSemantics.VENUE_TRADED),
        settlement=SettlementDeclaration(SettlementPattern.CYCLE_BASED, True),
        valuation=ValuationDeclaration(valuation_question),
        flows=FlowGrants(frozenset({FlowType.DIVIDEND})),
        event_families=EventFamilyGrants(frozenset()),
        existence=ExistenceDeclaration(ExistencePattern.OPEN_ENDED, frozenset(), frozenset()),
    )


# ── 1. Vocabulary Acceptance ────────────────────────────────────────────────

def test_periodic_nav_is_a_valuation_question_member():
    assert ValuationQuestion.PERIODIC_NAV.value == "PERIODIC_NAV"
    assert ValuationQuestion("PERIODIC_NAV") is ValuationQuestion.PERIODIC_NAV


def test_periodic_nav_flows_through_a_full_transcription_and_fingerprints():
    t = _synthetic("EQUITY", ValuationQuestion.PERIODIC_NAV)
    assert t.valuation.question == ValuationQuestion.PERIODIC_NAV
    digest = compute_fingerprint(t)
    assert isinstance(digest, str) and len(digest) == 64  # sha256 hexdigest


def test_periodic_nav_surfaces_through_governance_projection():
    t = _synthetic("EQUITY", ValuationQuestion.PERIODIC_NAV)
    projection = GovernanceProjection(t).as_dict()
    assert projection["valuation_question"] == "PERIODIC_NAV"


# ── 2. Backward Compatibility ───────────────────────────────────────────────

def test_real_library_still_boots_clean():
    registry = DefinitionRegistry.build()
    assert registry.exists("CASH")
    assert registry.exists("EQUITY")
    # As of M17 no definition used the new word yet, so ETF did not exist
    # here. M18 authored asset_definition_etf.md using PERIODIC_NAV, so this
    # assertion documents the word's later consequence rather than its own
    # (still true) claim that adding a vocabulary member alone does not
    # author a definition — see test_asset_definition_etf.py for M18's own
    # dedicated coverage of that milestone.
    assert registry.exists("ETF") is True


def test_cash_and_equity_declarations_are_unchanged():
    """Adding a sibling enum member cannot move a transcription that never
    references it — pinned so a future edit to this axis can't silently
    touch CASH_V1/EQUITY_V1 by accident."""
    assert library.CASH_V1.valuation.question == ValuationQuestion.IDENTITY
    assert library.EQUITY_V1.valuation.question == ValuationQuestion.CONTINUOUS_QUOTATION


def test_cash_and_equity_fingerprints_are_unchanged():
    assert compute_fingerprint(library.CASH_V1) == library.PINNED_FINGERPRINTS[("CASH", "v1")]
    assert compute_fingerprint(library.EQUITY_V1) == library.PINNED_FINGERPRINTS[("EQUITY", "v1")]


def test_definition_ladders_untouched_by_this_milestone():
    # True as of M17; M18 later added ETF using this milestone's word, M22
    # later added FUND, which also declares PERIODIC_NAV, M24 later added
    # BOND (which does not — BOND uses CONTINUOUS_QUOTATION), and M27 later
    # added PROPERTY (which does not either — PROPERTY uses
    # APPRAISAL_ON_EVENT) (see test_asset_definition_etf.py,
    # test_asset_definition_fund.py, test_asset_definition_bond.py,
    # test_asset_definition_property.py). Updated here rather than left stale.
    assert set(library.DEFINITION_LADDERS.keys()) == {"CASH", "EQUITY", "ETF", "FUND", "BOND", "PROPERTY"}


# ── 3. Closed Vocabulary Integrity ──────────────────────────────────────────

def test_unknown_valuation_word_still_fails_to_construct():
    with pytest.raises(ValueError):
        ValuationQuestion("NOT_A_REAL_VALUATION_WORD")


def test_valuation_question_member_set_is_pinned():
    """Guards against silent vocabulary drift — any future addition or
    removal on this axis must update this assertion deliberately, the same
    discipline test_definition_readiness.py applies to ENFORCEMENT_DECISIONS.
    M26 added APPRAISAL_ON_EVENT (Property vocabulary bundle) — updated
    here rather than left stale, the same discipline M22/M24 applied to
    this file's own DEFINITION_LADDERS assertion below."""
    assert {m.value for m in ValuationQuestion} == {
        "IDENTITY", "CONTINUOUS_QUOTATION", "PERIODIC_NAV", "APPRAISAL_ON_EVENT",
    }


# ── 4. Duplicate Protection (D1) ────────────────────────────────────────────

def test_periodic_nav_individuates_an_otherwise_identical_transcription():
    """The reason this word was added: two definitions identical on every
    other axis must NOT collide once one declares PERIODIC_NAV and the
    other CONTINUOUS_QUOTATION."""
    quoted = _synthetic("EQUITY", ValuationQuestion.CONTINUOUS_QUOTATION)
    nav = _synthetic("ETF", ValuationQuestion.PERIODIC_NAV)

    findings = _validate(
        {"EQUITY": (quoted,), "ETF": (nav,)},
        {("EQUITY", "v1"): compute_fingerprint(quoted), ("ETF", "v1"): compute_fingerprint(nav)},
    )
    assert not any(f.rule == "duplicate-declarations" for f in findings)


def test_periodic_nav_does_not_weaken_d1_when_shared():
    """Two transcriptions that share PERIODIC_NAV *and* every other axis are
    still an honest duplicate — the new word individuates only when it is
    actually the differing declaration, never a blanket exemption from D1."""
    a = _synthetic("EQUITY", ValuationQuestion.PERIODIC_NAV)
    b = _synthetic("ETF", ValuationQuestion.PERIODIC_NAV)

    findings = _validate(
        {"EQUITY": (a,), "ETF": (b,)},
        {("EQUITY", "v1"): compute_fingerprint(a), ("ETF", "v1"): compute_fingerprint(b)},
    )
    assert any(f.rule == "duplicate-declarations" for f in findings)
