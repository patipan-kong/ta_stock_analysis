"""M21 brief: Vocabulary Extension Stage (Fund Acquisition Semantics).

Adds `AcquisitionSemantics.NAV_WINDOW` — the mechanism M20's gap analysis
(asset_model_gap_analysis.md §3.1) found is FUND's sole remaining vocabulary
gap: now that FUND and ETF would otherwise share every axis (including
Axis 4's `PERIODIC_NAV`, shipped M17), FUND would be byte-identical to
ETF_V1 without a distinct acquisition mechanism. This milestone adds only
the word. No canonical definition uses it yet: `library.DEFINITION_LADDERS`
is still exactly CASH, EQUITY, ETF, unchanged.

Coverage, per the brief's "Required Tests":
  1. Vocabulary Acceptance — NAV_WINDOW constructs, flows through a full
     transcription, and fingerprints like any other word.
  2. Backward Compatibility — the real library still boots; CASH v1/Equity
     v1/ETF v1's declarations and pinned fingerprints are byte-identical to
     before this milestone.
  3. Closed Vocabulary Integrity — an unknown string still fails to
     construct an AcquisitionSemantics; the axis's full member set is
     pinned so a future silent addition/removal is caught here.
  4. D1 Validation — a synthetic FUND-shaped transcription (NAV_WINDOW,
     PERIODIC_NAV) and a synthetic ETF-shaped transcription (VENUE_TRADED,
     PERIODIC_NAV), otherwise identical, do not collide; two transcriptions
     that share NAV_WINDOW *and* every other axis still do collide — the
     new word represents genuine semantic differentiation, not an identity
     token.
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


def _synthetic(binding, acquisition_semantics, version="v1", effective_from="2026-07-13"):
    """A minimal, self-consistent transcription — same shape as
    test_vocabulary_periodic_nav.py's `_synthetic`, generalized so the
    acquisition axis can be varied while valuation is held at PERIODIC_NAV
    (the axis FUND and ETF already share, per M20's finding). Not a real
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
        settlement=SettlementDeclaration(SettlementPattern.CYCLE_BASED, True),
        valuation=ValuationDeclaration(ValuationQuestion.PERIODIC_NAV),
        flows=FlowGrants(frozenset({FlowType.DIVIDEND})),
        event_families=EventFamilyGrants(frozenset()),
        existence=ExistenceDeclaration(ExistencePattern.OPEN_ENDED, frozenset(), frozenset()),
    )


# ── 1. Vocabulary Acceptance ────────────────────────────────────────────────

def test_nav_window_is_an_acquisition_semantics_member():
    assert AcquisitionSemantics.NAV_WINDOW.value == "NAV_WINDOW"
    assert AcquisitionSemantics("NAV_WINDOW") is AcquisitionSemantics.NAV_WINDOW


def test_nav_window_flows_through_a_full_transcription_and_fingerprints():
    t = _synthetic("FUND", AcquisitionSemantics.NAV_WINDOW)
    assert t.acquisition.semantics == AcquisitionSemantics.NAV_WINDOW
    digest = compute_fingerprint(t)
    assert isinstance(digest, str) and len(digest) == 64  # sha256 hexdigest


def test_nav_window_surfaces_through_governance_projection():
    t = _synthetic("FUND", AcquisitionSemantics.NAV_WINDOW)
    projection = GovernanceProjection(t).as_dict()
    assert projection["acquisition"] == "NAV_WINDOW"


# ── 2. Backward Compatibility ───────────────────────────────────────────────

def test_real_library_still_boots_clean():
    registry = DefinitionRegistry.build()
    assert registry.exists("CASH")
    assert registry.exists("EQUITY")
    assert registry.exists("ETF")
    # As of M21 no definition used the new word yet, so FUND did not exist
    # here. M22 authored asset_definition_fund.md using NAV_WINDOW, so this
    # assertion documents the word's later consequence rather than its own
    # (still true) claim that adding a vocabulary member alone does not
    # author a definition — see test_asset_definition_fund.py for M22's own
    # dedicated coverage of that milestone.
    assert registry.exists("FUND") is True


def test_cash_equity_etf_declarations_are_unchanged():
    """Adding a sibling enum member cannot move a transcription that never
    references it — pinned so a future edit to this axis can't silently
    touch CASH_V1/EQUITY_V1/ETF_V1 by accident."""
    assert library.CASH_V1.acquisition.semantics == AcquisitionSemantics.NOT_TRANSACTABLE
    assert library.EQUITY_V1.acquisition.semantics == AcquisitionSemantics.VENUE_TRADED
    assert library.ETF_V1.acquisition.semantics == AcquisitionSemantics.VENUE_TRADED


def test_cash_equity_etf_fingerprints_are_unchanged():
    assert compute_fingerprint(library.CASH_V1) == library.PINNED_FINGERPRINTS[("CASH", "v1")]
    assert compute_fingerprint(library.EQUITY_V1) == library.PINNED_FINGERPRINTS[("EQUITY", "v1")]
    assert compute_fingerprint(library.ETF_V1) == library.PINNED_FINGERPRINTS[("ETF", "v1")]


def test_definition_ladders_untouched_by_this_milestone():
    # True as of M21; M22 later added FUND using this milestone's word, and
    # M24 later added BOND (a different word, M23's) — see
    # test_asset_definition_fund.py, test_asset_definition_bond.py. Updated
    # here rather than left stale.
    assert set(library.DEFINITION_LADDERS.keys()) == {"CASH", "EQUITY", "ETF", "FUND", "BOND"}


# ── 3. Closed Vocabulary Integrity ──────────────────────────────────────────

def test_unknown_acquisition_word_still_fails_to_construct():
    with pytest.raises(ValueError):
        AcquisitionSemantics("NOT_A_REAL_ACQUISITION_WORD")


def test_acquisition_semantics_member_set_is_pinned():
    """Guards against silent vocabulary drift — any future addition or
    removal on this axis must update this assertion deliberately, the same
    discipline test_vocabulary_periodic_nav.py applies to ValuationQuestion.
    M26 added NEGOTIATED_TRANSFER (Property vocabulary bundle) — updated
    here rather than left stale, the same discipline M22/M24 applied to
    this file's own DEFINITION_LADDERS assertion below."""
    assert {m.value for m in AcquisitionSemantics} == {
        "NOT_TRANSACTABLE",
        "VENUE_TRADED",
        "NAV_WINDOW",
        "NEGOTIATED_TRANSFER",
    }


# ── 4. D1 Validation ────────────────────────────────────────────────────────

def test_nav_window_individuates_a_fund_shaped_declaration_from_an_etf_shaped_one():
    """The reason this word was added: FUND and ETF now share PERIODIC_NAV
    valuation (M17). Two transcriptions identical on every other axis must
    NOT collide once one declares NAV_WINDOW acquisition and the other
    VENUE_TRADED — otherwise FUND remains byte-identical to ETF_V1, the
    exact D1 violation M20's gap analysis found FUND would hit today."""
    etf_shaped = _synthetic("ETF", AcquisitionSemantics.VENUE_TRADED)
    fund_shaped = _synthetic("FUND", AcquisitionSemantics.NAV_WINDOW)

    findings = _validate(
        {"ETF": (etf_shaped,), "FUND": (fund_shaped,)},
        {
            ("ETF", "v1"): compute_fingerprint(etf_shaped),
            ("FUND", "v1"): compute_fingerprint(fund_shaped),
        },
    )
    assert not any(f.rule == "duplicate-declarations" for f in findings)


def test_nav_window_does_not_weaken_d1_when_shared():
    """Two transcriptions that share NAV_WINDOW *and* every other axis are
    still an honest duplicate — the new word individuates only when it is
    actually the differing declaration, never a blanket exemption from D1."""
    a = _synthetic("FUND", AcquisitionSemantics.NAV_WINDOW)
    b = _synthetic("OTHER", AcquisitionSemantics.NAV_WINDOW)

    findings = _validate(
        {"FUND": (a,), "OTHER": (b,)},
        {
            ("FUND", "v1"): compute_fingerprint(a),
            ("OTHER", "v1"): compute_fingerprint(b),
        },
    )
    assert any(f.rule == "duplicate-declarations" for f in findings)


def test_identical_acquisition_semantics_still_collide_when_everything_else_matches():
    """Baseline sanity distinct from the two tests above: sharing an
    *existing* word (VENUE_TRADED) and every other axis is a duplicate too —
    demonstrating the new word represents genuine differentiation, not that
    D1 has generally been loosened by this milestone."""
    a = _synthetic("EQUITY", AcquisitionSemantics.VENUE_TRADED)
    b = _synthetic("ETF", AcquisitionSemantics.VENUE_TRADED)

    findings = _validate(
        {"EQUITY": (a,), "ETF": (b,)},
        {
            ("EQUITY", "v1"): compute_fingerprint(a),
            ("ETF", "v1"): compute_fingerprint(b),
        },
    )
    assert any(f.rule == "duplicate-declarations" for f in findings)
