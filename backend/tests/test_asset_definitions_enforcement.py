"""Stage R1.5 (M13 brief): Runtime Coverage Analysis, Consumer Gap Analysis,
Enforcement Boundary Documentation, and Migration Safety Tests.

Coverage
--------
  1.  Coverage report has exactly one row per AssetType member.
  2.  CASH / EQUITY report defined=True with the right capability facts;
      the other seven report defined=False.
  3.  consumers_affected: asset_registry.mint() is affected by every
      undefined binding; ledger_validator is affected by none (M11 only
      ever resolves EQUITY or the CASH numeraire — both defined).
  4.  Coverage report reflects a broken registry without raising.
  5.  ENFORCEMENT_DECISIONS has exactly one row per AssetType member.
  6.  Migration safety: every NO_GAP decision actually agrees with the
      live runtime today; every non-NO_GAP decision actually disagrees —
      pinned via the real _consult_runtime_for_mint(), not a re-guess.
  7.  OTHER is classified INTENTIONAL_LEGACY_BEHAVIOR / PRESERVE, not
      MIGRATE — the escape-hatch kind is never expected to gain a
      definition (M9 TDD Section 10.2).
  8.  Structural: coverage_report.py is the only asset_definitions module
      importing governance.py outside of registry.py itself — engines
      (asset_registry.py, ledger_validator.py) must keep using the
      anonymous CapabilityView door, never the enumerable one.
"""
from __future__ import annotations

import inspect
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from services.asset_definitions.coverage_report import (
    generate_coverage_report,
    render_text as render_coverage_text,
)
from services.asset_definitions.enforcement_decisions import (
    ENFORCEMENT_DECISIONS,
    FutureAction,
    GapType,
    decision_for,
    render_text as render_decisions_text,
)
from services.asset_definitions.registry import DefinitionRegistry
from services.asset_domain import AssetType

_NO_GAP = {AssetType.CASH.value, AssetType.EQUITY.value}
# M18: ETF_V1 was authored — the runtime now resolves it (registry-defined,
# like CASH/EQUITY), but its enforcement decision is deliberately still
# MIGRATE, not NOT_APPLICABLE (see enforcement_decisions.py's ETF row and
# DECISION_LOG.md's M18 entry) — a definition existing is necessary but not
# sufficient for an enforcement policy decision, which remains separate.
# M22: FUND_V1 was authored one binding later, through the exact same
# lineage (see DECISION_LOG.md's M22 entry) — it joins ETF here for the
# identical reason.
_FUTURE_ENFORCEMENT_CANDIDATES = {AssetType.ETF.value, AssetType.FUND.value}
_DEFINED = _NO_GAP | _FUTURE_ENFORCEMENT_CANDIDATES  # registry.exists() is True
_UNDEFINED = {m.value for m in AssetType} - _DEFINED  # registry.exists() is False
_MIGRATION_REQUIRED_OR_LEGACY = _UNDEFINED  # decision.gap_type != NO_GAP; runtime disagrees


# ── 1-2. Coverage report shape ──────────────────────────────────────────────

def test_coverage_report_has_one_row_per_asset_type():
    report = generate_coverage_report()
    assert {row.binding for row in report.rows} == {m.value for m in AssetType}
    assert report.total_count == len(AssetType)


def test_defined_bindings_report_their_capabilities():
    report = generate_coverage_report()
    by_binding = {row.binding: row for row in report.rows}

    cash = by_binding[AssetType.CASH.value]
    assert cash.defined is True
    assert cash.version == "v1"
    assert "INTEREST" in cash.flows_granted

    equity = by_binding[AssetType.EQUITY.value]
    assert equity.defined is True
    assert "DIVIDEND" in equity.flows_granted
    assert "SAME_ENTITY" in equity.permitted_relationships

    etf = by_binding[AssetType.ETF.value]
    assert etf.defined is True
    assert "DIVIDEND" in etf.flows_granted
    assert "SAME_ENTITY" in etf.permitted_relationships

    fund = by_binding[AssetType.FUND.value]
    assert fund.defined is True
    assert "DIVIDEND" in fund.flows_granted
    assert "SAME_ENTITY" in fund.permitted_relationships

    assert report.defined_count == 4


def test_undefined_bindings_report_empty_capabilities():
    report = generate_coverage_report()
    by_binding = {row.binding: row for row in report.rows}
    for binding in _UNDEFINED:
        row = by_binding[binding]
        assert row.defined is False
        assert row.version is None
        assert row.flows_granted == ()
        assert row.event_families_granted == ()
        assert row.permitted_relationships == ()


# ── 3. Consumer gap analysis ────────────────────────────────────────────────

def test_undefined_bindings_affect_asset_registry_only():
    report = generate_coverage_report()
    by_binding = {row.binding: row for row in report.rows}
    for binding in _UNDEFINED:
        assert by_binding[binding].consumers_affected == ("asset_registry.mint() (M12)",)


def test_defined_bindings_affect_no_consumer():
    report = generate_coverage_report()
    by_binding = {row.binding: row for row in report.rows}
    for binding in _DEFINED:
        assert by_binding[binding].consumers_affected == ()


# ── 4. Broken registry never raises out of the report generator ────────────

def test_coverage_report_reflects_broken_registry_without_raising():
    """generate_coverage_report() accepts a pre-built registry; feeding it
    one whose ladder is missing CASH (rather than monkeypatching
    library.py's module-level PINNED_FINGERPRINTS, which several other test
    files already mutate) proves the report degrades to "not defined"
    rather than crashing.
    """
    empty_registry = DefinitionRegistry(ladders={})
    report = generate_coverage_report(registry=empty_registry)
    assert report.defined_count == 0
    assert all(not row.defined for row in report.rows)


# ── 5. Enforcement decisions: completeness ──────────────────────────────────

def test_enforcement_decisions_has_one_row_per_asset_type():
    assert {d.binding for d in ENFORCEMENT_DECISIONS} == {m.value for m in AssetType}
    assert len(ENFORCEMENT_DECISIONS) == len(AssetType)


def test_decision_for_unknown_binding_raises():
    with pytest.raises(KeyError):
        decision_for("NOT_A_REAL_BINDING")


# ── 6. Migration safety: decisions match the live runtime today ────────────

def test_no_gap_decisions_agree_with_live_runtime():
    from services.asset_registry import _consult_runtime_for_mint

    for binding in _NO_GAP:
        decision = decision_for(binding)
        assert decision.gap_type == GapType.NO_GAP
        assert decision.future_action == FutureAction.NOT_APPLICABLE

        log = _consult_runtime_for_mint(AssetType(binding))
        assert log.consulted == 1
        assert log.agreements == 1
        assert log.findings == ()


def test_future_enforcement_candidates_agree_with_runtime_but_stay_at_migrate():
    """M18: ETF_V1 now exists, so asset_registry.mint()'s shadow consultation
    genuinely agrees with the runtime for this binding — the same way it
    already does for CASH/EQUITY. Unlike those two, ETF's future_action is
    deliberately left at MIGRATE rather than promoted to NOT_APPLICABLE: a
    definition existing closes the *capability* gap this table's gap_type
    axis describes, but does not by itself authorize an enforcement *policy*
    decision — that remains a separate, explicit, human-led step (M18
    brief's non-goal: "do not enable additional enforcement"; see
    DECISION_LOG.md's M18 entry and enforcement_decisions.py's ETF row).
    M22: FUND_V1 joined this same bucket one binding later, for the
    identical reason (see enforcement_decisions.py's FUND row)."""
    from services.asset_registry import _consult_runtime_for_mint

    for binding in _FUTURE_ENFORCEMENT_CANDIDATES:
        decision = decision_for(binding)
        assert decision.gap_type == GapType.FUTURE_ENFORCEMENT_CANDIDATE
        assert decision.future_action == FutureAction.MIGRATE

        log = _consult_runtime_for_mint(AssetType(binding))
        assert log.consulted == 1
        assert log.agreements == 1
        assert log.findings == ()


def test_non_no_gap_decisions_disagree_with_live_runtime():
    from services.asset_registry import _consult_runtime_for_mint

    for binding in _MIGRATION_REQUIRED_OR_LEGACY:
        decision = decision_for(binding)
        assert decision.gap_type != GapType.NO_GAP
        assert decision.gap_type != GapType.FUTURE_ENFORCEMENT_CANDIDATE
        assert decision.future_action != FutureAction.NOT_APPLICABLE

        log = _consult_runtime_for_mint(AssetType(binding))
        assert log.consulted == 1
        assert log.agreements == 0
        assert len(log.findings) == 1
        assert log.findings[0].category == "UnknownCapability"


# ── 7. OTHER is the deliberate, permanent exception ─────────────────────────

def test_other_is_intentional_never_migrate():
    decision = decision_for(AssetType.OTHER.value)
    assert decision.gap_type == GapType.INTENTIONAL_LEGACY_BEHAVIOR
    assert decision.future_action == FutureAction.PRESERVE


def test_missing_definitions_other_than_other_are_all_migrate():
    for binding in _UNDEFINED - {AssetType.OTHER.value}:
        decision = decision_for(binding)
        assert decision.future_action == FutureAction.MIGRATE
        assert decision.gap_type in (GapType.MISSING_DEFINITION, GapType.MIGRATION_REQUIRED)


# ── 8. GovernanceProjection stays out of engine modules ─────────────────────

def test_governance_projection_not_imported_by_engine_consumers():
    """The enumerable door (governance.py) is legitimate for reporting code
    (this milestone's coverage_report.py, via registry.get()/.all()) but
    must never leak into an engine consumer's own imports — that would be
    exactly the D5 "ask never identify" violation CapabilityView's
    enumeration-free surface exists to prevent (capability_view.py's own
    module docstring). A real import-grep CI gate is still deferred to R2
    (governance.py's own docstring); this is the lightweight version that
    can exist now that a legitimate GovernanceProjection caller (this
    milestone) exists to be distinguished from an illegitimate one.
    """
    import services.asset_registry as asset_registry_module
    import services.ledger_validator as ledger_validator_module

    for module in (asset_registry_module, ledger_validator_module):
        source = inspect.getsource(module)
        assert "governance" not in source, (
            f"{module.__name__} must not import GovernanceProjection/governance.py — "
            "engines use CapabilityView only (D5, ask never identify)"
        )


# ── Rendering smoke tests (human-readable output, not asserted line-by-line) ─

def test_render_text_smoke():
    report = generate_coverage_report()
    text = render_coverage_text(report)
    assert "Asset Type Coverage" in text
    assert "CASH" in text and "defined" in text
    assert "ETF" in text  # M18: ETF is now "defined", not "missing" — see test_asset_definition_etf.py
    assert "FUND" in text  # M22: FUND is now "defined" too — see test_asset_definition_fund.py
    assert "BOND" in text and "missing" in text

    decisions_text = render_decisions_text()
    assert "Enforcement Boundary Decisions" in decisions_text
    assert AssetType.OTHER.value in decisions_text
