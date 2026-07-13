"""Stage R2 Expansion (M15 brief): Policy Activation Preparation.

Coverage
--------
  1. Decision integrity: the current (binding, future_action) shape of
     ENFORCEMENT_DECISIONS is pinned. Any transition (e.g. ETF's MIGRATE
     becoming REJECT) fails this test until it is intentionally updated —
     the "explicit and reviewable" gate the M15 brief asks for.
  2. Definition readiness: a binding whose definition is incomplete
     (VOCABULARY_GAP / SCOPE_UNDECIDED) can never be marked REJECT — an
     incomplete definition cannot be enforceable, structurally, not just by
     convention. Also: DEFINITION_READINESS is complete (one row per
     AssetType) and consistent with library.py's actual DEFINITION_LADDERS.
  3. Existing behavior: mint() and evaluate_mint_enforcement() are
     unaffected by this milestone — still byte-identical to the M14
     baseline for every AssetType.
  4. Enforcement isolation: readiness_report.py has no edge into the
     enforcement/mint call path — this milestone's tooling cannot affect
     runtime modes even in principle.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base
import models.asset  # noqa: F401 — registers Asset* tables on Base.metadata
from services import asset_registry as registry
from services.asset_definitions import library
from services.asset_definitions.enforcement_decisions import (
    ENFORCEMENT_DECISIONS,
    FutureAction,
)
from services.asset_definitions.enforcement_gate import (
    EnforcementMode,
    evaluate_mint_enforcement,
)
from services.asset_definitions.readiness_report import (
    DEFINITION_READINESS,
    ReadinessStatus,
    generate_enforcement_readiness_report,
    readiness_for,
    render_text,
)
from services.asset_domain import AssetClaim, AssetType

_ALL_TYPES = tuple(AssetType)

_INCOMPLETE_STATUSES = (ReadinessStatus.VOCABULARY_GAP, ReadinessStatus.SCOPE_UNDECIDED)


def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _claim(**overrides):
    defaults = dict(
        canonical_symbol="KBANK",
        asset_type=AssetType.EQUITY,
        market="TH",
        exchange="SET",
        currency="THB",
    )
    defaults.update(overrides)
    return AssetClaim(**defaults)


# ── 1. Decision integrity: pinned snapshot of the current decision table ───

_PINNED_FUTURE_ACTIONS = {
    AssetType.CASH.value:     FutureAction.NOT_APPLICABLE,
    AssetType.EQUITY.value:   FutureAction.NOT_APPLICABLE,
    AssetType.ETF.value:      FutureAction.MIGRATE,
    AssetType.FUND.value:     FutureAction.MIGRATE,
    AssetType.BOND.value:     FutureAction.MIGRATE,
    AssetType.CRYPTO.value:   FutureAction.MIGRATE,
    AssetType.COMMODITY.value: FutureAction.MIGRATE,
    AssetType.PROPERTY.value: FutureAction.MIGRATE,
    AssetType.OTHER.value:    FutureAction.PRESERVE,
}


def test_enforcement_decision_table_matches_pinned_snapshot():
    actual = {d.binding: d.future_action for d in ENFORCEMENT_DECISIONS}
    assert actual == _PINNED_FUTURE_ACTIONS, (
        "ENFORCEMENT_DECISIONS has changed since this snapshot was pinned — "
        "if this is an intentional, reviewed policy transition, update "
        "_PINNED_FUTURE_ACTIONS deliberately; do not let it change silently."
    )


def test_no_binding_is_reject_today():
    """Same fact M14 already relies on, re-asserted here as this milestone's
    own decision-integrity tripwire."""
    assert all(d.future_action != FutureAction.REJECT for d in ENFORCEMENT_DECISIONS)


# ── 2. Definition readiness ─────────────────────────────────────────────────

def test_readiness_table_has_exactly_one_row_per_asset_type():
    bindings = [row.binding for row in DEFINITION_READINESS]
    assert sorted(bindings) == sorted(member.value for member in AssetType)
    assert len(bindings) == len(set(bindings))


@pytest.mark.parametrize("asset_type", _ALL_TYPES)
def test_defined_status_matches_library_ladders(asset_type):
    readiness = readiness_for(asset_type.value)
    has_ladder = asset_type.value in library.DEFINITION_LADDERS
    if readiness.status == ReadinessStatus.DEFINED:
        assert has_ladder, f"{asset_type} marked DEFINED but has no library.DEFINITION_LADDERS entry"
    else:
        assert not has_ladder, f"{asset_type} has a library.DEFINITION_LADDERS entry but is not marked DEFINED"


def test_etf_reached_defined_through_m16_m17_m18_lineage():
    """The full arc, pinned so no step can silently regress: M15 wrongly
    classified ETF VOCABULARY_READY; M16 attempted authoring, found it
    blocked by D1 (see DECISION_LOG.md M16 entry), and corrected the
    classification to VOCABULARY_GAP; M17 added the missing vocabulary word
    (ValuationQuestion.PERIODIC_NAV); M18 used it to actually author
    asset_definition_etf.md and transcribe ETF_V1 into library.py. Readiness
    now correctly reports DEFINED, matching library.DEFINITION_LADDERS."""
    readiness = readiness_for(AssetType.ETF.value)
    assert readiness.status == ReadinessStatus.DEFINED
    assert AssetType.ETF.value in library.DEFINITION_LADDERS
    assert readiness.missing_requirements == ()


@pytest.mark.parametrize("asset_type", [AssetType.FUND, AssetType.BOND, AssetType.PROPERTY])
def test_vocabulary_gap_bindings_have_missing_requirements_listed(asset_type):
    readiness = readiness_for(asset_type.value)
    assert readiness.status == ReadinessStatus.VOCABULARY_GAP
    assert len(readiness.missing_requirements) > 0


@pytest.mark.parametrize("asset_type", [AssetType.CRYPTO, AssetType.COMMODITY])
def test_scope_undecided_bindings_have_missing_requirements_listed(asset_type):
    readiness = readiness_for(asset_type.value)
    assert readiness.status == ReadinessStatus.SCOPE_UNDECIDED
    assert len(readiness.missing_requirements) > 0


def test_incomplete_definitions_are_never_marked_reject():
    """The M15 brief's own words: 'Incomplete definitions cannot be marked
    enforceable.' A binding whose domain model is not yet complete must
    never have future_action=REJECT — REJECT is exactly the transition that
    would make it enforceable (see enforcement_gate.py)."""
    for row in generate_enforcement_readiness_report():
        if row.readiness_status in _INCOMPLETE_STATUSES:
            assert row.future_action != FutureAction.REJECT, (
                f"{row.binding} is {row.readiness_status.value} but marked REJECT — "
                "an incomplete definition must not be enforceable"
            )
            assert row.safe_to_enforce_today is False


def test_exempt_binding_is_preserve_not_reject():
    row = readiness_for(AssetType.OTHER.value)
    assert row.status == ReadinessStatus.EXEMPT
    decision = next(d for d in ENFORCEMENT_DECISIONS if d.binding == AssetType.OTHER.value)
    assert decision.future_action == FutureAction.PRESERVE


def test_render_text_answers_the_four_required_questions():
    text = render_text()
    assert "Safe to enforce today" in text
    assert "Vocabulary-ready, awaiting authoring" in text
    assert "Blocked (definition incomplete)" in text
    assert "Intentionally exempt" in text
    assert AssetType.FUND.value in text  # M18: ETF is DEFINED now, no longer a "blocked" example
    assert AssetType.OTHER.value in text


# ── 3. Existing behavior: unaffected by this milestone ─────────────────────

@pytest.mark.parametrize("asset_type", _ALL_TYPES)
def test_mint_still_succeeds_for_every_asset_type(asset_type):
    db = make_session()
    asset = registry.mint(
        db, _claim(canonical_symbol=f"R2X_{asset_type.value}", asset_type=asset_type),
        enforcement_mode=EnforcementMode.ENFORCE,
    )
    assert asset.id is not None


@pytest.mark.parametrize("asset_type", _ALL_TYPES)
def test_enforcement_outcomes_unchanged_from_m14_baseline(asset_type):
    outcome = evaluate_mint_enforcement(asset_type, mode=EnforcementMode.ENFORCE)
    assert outcome.blocked is False


# ── 4. Enforcement isolation ────────────────────────────────────────────────

def test_readiness_report_module_is_not_imported_by_enforcement_gate():
    import inspect
    import services.asset_definitions.enforcement_gate as gate_module
    source = inspect.getsource(gate_module)
    assert "readiness_report" not in source


def test_readiness_report_module_is_not_imported_by_asset_registry():
    import services.asset_registry as registry_module
    import inspect
    source = inspect.getsource(registry_module)
    assert "readiness_report" not in source
