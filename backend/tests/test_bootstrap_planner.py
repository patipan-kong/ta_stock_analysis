"""Tests for the Registry Bootstrap Planner (Milestone M5.3).

Pure unit tests against hand-built MigrationPlan fixtures — no database, no
resolver calls, no market/exchange guessing. Validates:
  1. Only UNKNOWN claim shapes are ever classified; RESOLVED / AMBIGUOUS /
     CONFLICT / CANDIDATE shapes pass through untouched (not mintable, not
     quarantined, not duplicate-blocked).
  2. A .BK-suffixed (non-DR) UNKNOWN shape is mintable with market/exchange
     Thailand/SET.
  3. A DR-pattern UNKNOWN shape (with or without .BK) is mintable with
     market/exchange Thailand/SET.
  4. A pure-alphabetic, no-suffix UNKNOWN shape is quarantined, NOT
     assumed to be Thailand/SET (the deliberately conservative choice —
     see services/symbol_market_convention.py).
  5. An UNKNOWN shape with no currency is quarantined.
  6. Two UNKNOWN shapes sharing a canonical_symbol (a potential duplicate
     cluster) are excluded from both mintable and quarantined — reported
     only via duplicate_blocked, reusing migration_report.py's detection
     verbatim.
  7. mint proposals always use raw_symbol as canonical_symbol, never
     shape.canonical_symbol.
  8. Output is deterministically sorted.
"""
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.asset_domain import AssetType
from services.bootstrap_planner import build_bootstrap_plan
from services.migration_planner import CashOnlyGroup, ClaimShape, ClaimShapeResolution, MigrationPlan
from services.resolver_domain import ResolutionCandidate, ResolutionResult, ResolutionVerdict


def _shape(raw, canonical=None, currency="THB") -> ClaimShape:
    return ClaimShape(raw_symbol=raw, canonical_symbol=canonical, currency=currency)


def _result(verdict: ResolutionVerdict, resolved_asset_id=None, candidates=()) -> ResolutionResult:
    return ResolutionResult(
        verdict=verdict,
        resolved_asset_id=resolved_asset_id,
        candidates=tuple(candidates),
        claim_evaluations=(),
    )


def _resolution(shape, result, tx_ids=(1,)) -> ClaimShapeResolution:
    return ClaimShapeResolution(shape=shape, result=result, transaction_ids=tuple(tx_ids), portfolio_ids=(1,))


def _plan(resolutions) -> MigrationPlan:
    total = sum(len(r.transaction_ids) for r in resolutions)
    return MigrationPlan(
        resolutions=tuple(resolutions),
        cash_only=CashOnlyGroup(transaction_ids=(), portfolio_ids=()),
        total_transactions=total,
        portfolios_scanned=(1,),
        generated_at=datetime(2026, 7, 9, tzinfo=timezone.utc),
    )


# ── Only UNKNOWN shapes are bootstrap's concern ─────────────────────────

def test_non_unknown_verdicts_are_never_classified():
    resolutions = [
        _resolution(_shape("RESOLVEDCO"), _result(ResolutionVerdict.RESOLVED, resolved_asset_id=1)),
        _resolution(_shape("AMBIGCO"), _result(ResolutionVerdict.AMBIGUOUS)),
        _resolution(
            _shape("CONFLICTCO"),
            _result(ResolutionVerdict.CONFLICT, candidates=[
                ResolutionCandidate(asset_id=1, score=50.0, contributions=()),
                ResolutionCandidate(asset_id=2, score=50.0, contributions=()),
            ]),
        ),
        _resolution(_shape("CANDIDATECO"), _result(ResolutionVerdict.CANDIDATE)),
    ]
    bp = build_bootstrap_plan(_plan(resolutions))

    assert bp.mintable == ()
    assert bp.quarantined == ()
    assert bp.duplicate_blocked == ()


# ── Mintable: unambiguous venue signal ──────────────────────────────────

def test_bk_suffix_non_dr_symbol_is_mintable_as_thailand_set():
    resolutions = [_resolution(_shape("AOT.BK"), _result(ResolutionVerdict.UNKNOWN))]
    bp = build_bootstrap_plan(_plan(resolutions))

    assert len(bp.mintable) == 1
    candidate = bp.mintable[0]
    assert candidate.shape.raw_symbol == "AOT.BK"
    assert candidate.proposed_claim.market == "Thailand"
    assert candidate.proposed_claim.exchange == "SET"
    assert candidate.proposed_claim.asset_type == AssetType.EQUITY


def test_dr_pattern_symbol_is_mintable_as_thailand_set_with_or_without_bk():
    resolutions = [
        _resolution(_shape("NVDA01"), _result(ResolutionVerdict.UNKNOWN), tx_ids=(1,)),
        _resolution(_shape("MICRON80.BK"), _result(ResolutionVerdict.UNKNOWN), tx_ids=(2,)),
    ]
    bp = build_bootstrap_plan(_plan(resolutions))

    by_symbol = {c.shape.raw_symbol: c for c in bp.mintable}
    assert set(by_symbol) == {"NVDA01", "MICRON80.BK"}
    for candidate in by_symbol.values():
        assert candidate.proposed_claim.market == "Thailand"
        assert candidate.proposed_claim.exchange == "SET"


def test_mint_proposal_uses_raw_symbol_never_shape_canonical_symbol():
    # AOT.BK's shape carries an unrelated canonical_symbol on purpose —
    # proves the field is never read for the Asset's own canonical_symbol.
    resolutions = [_resolution(_shape("AOT.BK", canonical="SOMETHING-ELSE"), _result(ResolutionVerdict.UNKNOWN))]
    bp = build_bootstrap_plan(_plan(resolutions))

    assert bp.mintable[0].proposed_claim.canonical_symbol == "AOT.BK"


# ── Quarantined: no guessing past an unambiguous signal ─────────────────

def test_pure_alphabetic_no_suffix_symbol_is_quarantined_not_assumed():
    resolutions = [_resolution(_shape("GLIF"), _result(ResolutionVerdict.UNKNOWN))]
    bp = build_bootstrap_plan(_plan(resolutions))

    assert bp.mintable == ()
    assert len(bp.quarantined) == 1
    assert bp.quarantined[0].shape.raw_symbol == "GLIF"
    assert "convention" in bp.quarantined[0].reason


def test_missing_currency_is_quarantined():
    resolutions = [_resolution(_shape("AOT.BK", currency=None), _result(ResolutionVerdict.UNKNOWN))]
    bp = build_bootstrap_plan(_plan(resolutions))

    assert bp.mintable == ()
    assert len(bp.quarantined) == 1
    assert "currency" in bp.quarantined[0].reason


def test_unrecognized_suffix_is_quarantined():
    resolutions = [_resolution(_shape("RELIANCE.NS"), _result(ResolutionVerdict.UNKNOWN))]
    bp = build_bootstrap_plan(_plan(resolutions))

    assert bp.mintable == ()
    assert len(bp.quarantined) == 1


# ── Duplicate clusters: excluded from both mintable and quarantined ─────

def test_duplicate_cluster_shapes_are_excluded_from_mintable_and_quarantined():
    resolutions = [
        _resolution(_shape("PTTX", canonical="PTT.BK"), _result(ResolutionVerdict.UNKNOWN), tx_ids=(1,)),
        _resolution(_shape("PTTY", canonical="PTT.BK"), _result(ResolutionVerdict.UNKNOWN), tx_ids=(2,)),
    ]
    bp = build_bootstrap_plan(_plan(resolutions))

    assert bp.mintable == ()
    assert bp.quarantined == ()
    assert len(bp.duplicate_blocked) == 1
    cluster = bp.duplicate_blocked[0]
    assert cluster.canonical_symbol == "PTT.BK"
    assert set(cluster.raw_symbols) == {"PTTX", "PTTY"}


def test_duplicate_detection_reused_verbatim_leaves_non_clustered_shapes_untouched():
    resolutions = [
        _resolution(_shape("PTTX", canonical="PTT.BK"), _result(ResolutionVerdict.UNKNOWN), tx_ids=(1,)),
        _resolution(_shape("PTTY", canonical="PTT.BK"), _result(ResolutionVerdict.UNKNOWN), tx_ids=(2,)),
        _resolution(_shape("AOT.BK"), _result(ResolutionVerdict.UNKNOWN), tx_ids=(3,)),
    ]
    bp = build_bootstrap_plan(_plan(resolutions))

    assert len(bp.duplicate_blocked) == 1
    assert len(bp.mintable) == 1
    assert bp.mintable[0].shape.raw_symbol == "AOT.BK"


# ── Determinism ──────────────────────────────────────────────────────────

def test_mintable_and_quarantined_are_deterministically_sorted():
    resolutions = [
        _resolution(_shape("ZZZ.BK"), _result(ResolutionVerdict.UNKNOWN), tx_ids=(1,)),
        _resolution(_shape("AAA.BK"), _result(ResolutionVerdict.UNKNOWN), tx_ids=(2,)),
        _resolution(_shape("ZZQUARANTINE"), _result(ResolutionVerdict.UNKNOWN), tx_ids=(3,)),
        _resolution(_shape("AAQUARANTINE"), _result(ResolutionVerdict.UNKNOWN), tx_ids=(4,)),
    ]
    bp1 = build_bootstrap_plan(_plan(resolutions))
    bp2 = build_bootstrap_plan(_plan(resolutions))

    assert [c.shape.raw_symbol for c in bp1.mintable] == ["AAA.BK", "ZZZ.BK"]
    assert [q.shape.raw_symbol for q in bp1.quarantined] == ["AAQUARANTINE", "ZZQUARANTINE"]
    assert bp1.mintable == bp2.mintable
    assert bp1.quarantined == bp2.quarantined


def test_empty_plan_produces_empty_bootstrap_plan():
    bp = build_bootstrap_plan(_plan([]))
    assert bp.mintable == ()
    assert bp.quarantined == ()
    assert bp.duplicate_blocked == ()
