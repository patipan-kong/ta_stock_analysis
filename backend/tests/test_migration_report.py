"""Tests for the Migration Report aggregation layer (Milestone M5.1).

Pure unit tests against hand-built MigrationPlan fixtures — no database, no
resolver calls. Validates:
  1. Transaction-level vs claim-shape-level verdict counts are tallied
     separately and correctly.
  2. Resolution %% / Decisive %% are computed over identity-bearing
     transactions only (cash-only excluded from the denominator).
  3. Assets reused counts distinct resolved_asset_id values, not shapes.
  4. Potential duplicate clusters: UNKNOWN shapes sharing a
     canonical_symbol with >1 distinct raw_symbol, and only those.
  5. Potential merge candidates: pairwise asset_id combinations drawn
     directly from CONFLICT verdicts' candidates, deduplicated and
     aggregated across shapes.
  6. Coverage report groups by currency and by provider correctly.
  7. An empty plan produces zeroed statistics, never a division error.
"""
import os
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.asset_domain import AssetId
from services.migration_planner import CashOnlyGroup, ClaimShape, ClaimShapeResolution, MigrationPlan
from services.migration_report import build_migration_report
from services.resolver_domain import ResolutionCandidate, ResolutionResult, ResolutionVerdict


def _shape(raw, canonical=None, currency="THB") -> ClaimShape:
    return ClaimShape(raw_symbol=raw, canonical_symbol=canonical, currency=currency)


def _candidate(asset_id: int, score: float = 100.0) -> ResolutionCandidate:
    return ResolutionCandidate(asset_id=AssetId(asset_id), score=score, contributions=())


def _result(verdict: ResolutionVerdict, resolved_asset_id=None, candidates=()) -> ResolutionResult:
    return ResolutionResult(
        verdict=verdict,
        resolved_asset_id=AssetId(resolved_asset_id) if resolved_asset_id is not None else None,
        candidates=tuple(candidates),
        claim_evaluations=(),
    )


def _resolution(
    shape: ClaimShape,
    result: ResolutionResult,
    tx_ids,
    *,
    portfolio_ids=(1,),
    resolved_market=None,
    resolved_exchange=None,
    resolved_currency=None,
) -> ClaimShapeResolution:
    return ClaimShapeResolution(
        shape=shape,
        result=result,
        transaction_ids=tuple(tx_ids),
        portfolio_ids=tuple(portfolio_ids),
        resolved_market=resolved_market,
        resolved_exchange=resolved_exchange,
        resolved_currency=resolved_currency,
    )


def _plan(resolutions, cash_only_tx_ids=()) -> MigrationPlan:
    total = sum(len(r.transaction_ids) for r in resolutions) + len(cash_only_tx_ids)
    return MigrationPlan(
        resolutions=tuple(resolutions),
        cash_only=CashOnlyGroup(transaction_ids=tuple(cash_only_tx_ids), portfolio_ids=(1,) if cash_only_tx_ids else ()),
        total_transactions=total,
        portfolios_scanned=(1,),
        generated_at=datetime(2026, 7, 9, tzinfo=timezone.utc),
    )


# ── Statistics ───────────────────────────────────────────────────────────

def test_statistics_tallies_transactions_and_claim_shapes_separately():
    resolutions = [
        _resolution(_shape("A"), _result(ResolutionVerdict.RESOLVED, resolved_asset_id=1), [1, 2, 3]),
        _resolution(_shape("A2"), _result(ResolutionVerdict.RESOLVED, resolved_asset_id=1), [4]),
        _resolution(_shape("B"), _result(ResolutionVerdict.AMBIGUOUS), [5, 6]),
        _resolution(
            _shape("C"),
            _result(ResolutionVerdict.CONFLICT, candidates=[_candidate(5), _candidate(6)]),
            [7],
        ),
        _resolution(_shape("X", canonical="X.BK"), _result(ResolutionVerdict.UNKNOWN), [8]),
        _resolution(_shape("X2", canonical="X.BK"), _result(ResolutionVerdict.UNKNOWN), [9]),
        _resolution(_shape("Y"), _result(ResolutionVerdict.UNKNOWN), [10]),
    ]
    plan = _plan(resolutions, cash_only_tx_ids=[11, 12])

    summary = build_migration_report(plan)
    s = summary.statistics

    assert plan.total_transactions == 12
    assert s.cash_only_transactions == 2
    assert s.identity_bearing_transactions == 10

    tv = s.transaction_verdicts
    assert (tv.resolved, tv.candidate, tv.ambiguous, tv.conflict, tv.unknown) == (4, 0, 2, 1, 3)

    cv = s.claim_shape_verdicts
    assert (cv.resolved, cv.candidate, cv.ambiguous, cv.conflict, cv.unknown) == (2, 0, 1, 1, 3)

    assert s.resolution_pct == pytest.approx(40.0)
    assert s.decisive_pct == pytest.approx(40.0)  # candidate is 0, so equals resolution_pct here

    assert s.assets_created_expected == 3  # UNKNOWN claim-shape count
    assert s.assets_reused == 1  # asset_id 1, reused across two shapes, counted once
    assert s.manual_adjudications_required == 2  # 1 ambiguous + 1 conflict shape
    assert s.potential_duplicates == 1  # X/X2 share canonical_symbol X.BK
    assert s.potential_merge_candidates == 1  # asset 5 <-> asset 6


def test_empty_plan_produces_zeroed_statistics_no_division_error():
    plan = _plan([])
    summary = build_migration_report(plan)
    s = summary.statistics

    assert s.total_transactions == 0
    assert s.identity_bearing_transactions == 0
    assert s.resolution_pct == 0.0
    assert s.decisive_pct == 0.0
    assert s.assets_created_expected == 0
    assert s.assets_reused == 0
    assert s.potential_duplicates == 0
    assert s.potential_merge_candidates == 0


def test_caveats_are_present_and_explain_known_limitations():
    summary = build_migration_report(_plan([]))
    caveats = " ".join(summary.statistics.caveats)
    assert len(summary.statistics.caveats) == 3
    assert "CANDIDATE" in caveats
    assert "single bucket" in caveats
    assert "currency as a proxy" in caveats


# ── Potential duplicates ─────────────────────────────────────────────────

def test_unknown_shapes_without_shared_canonical_symbol_are_not_duplicates():
    resolutions = [
        _resolution(_shape("X", canonical="X.BK"), _result(ResolutionVerdict.UNKNOWN), [1]),
        _resolution(_shape("Y", canonical="Y.BK"), _result(ResolutionVerdict.UNKNOWN), [2]),
    ]
    summary = build_migration_report(_plan(resolutions))
    assert summary.statistics.potential_duplicates == 0
    assert summary.potential_duplicate_clusters == ()


def test_resolved_or_ambiguous_shapes_never_count_as_potential_duplicates():
    resolutions = [
        _resolution(_shape("X", canonical="X.BK"), _result(ResolutionVerdict.RESOLVED, resolved_asset_id=1), [1]),
        _resolution(_shape("X2", canonical="X.BK"), _result(ResolutionVerdict.RESOLVED, resolved_asset_id=1), [2]),
    ]
    summary = build_migration_report(_plan(resolutions))
    assert summary.statistics.potential_duplicates == 0


# ── Potential merge candidates ───────────────────────────────────────────

def test_merge_candidates_deduplicate_the_same_pair_across_shapes():
    resolutions = [
        _resolution(
            _shape("C1"), _result(ResolutionVerdict.CONFLICT, candidates=[_candidate(5), _candidate(6)]), [1],
        ),
        _resolution(
            _shape("C2"), _result(ResolutionVerdict.CONFLICT, candidates=[_candidate(6), _candidate(5)]), [2],
        ),
    ]
    summary = build_migration_report(_plan(resolutions))

    assert summary.statistics.potential_merge_candidates == 1
    pmc = summary.conflict_report.potential_merge_candidates[0]
    assert set(pmc.asset_ids) == {5, 6}
    assert set(pmc.transaction_ids) == {1, 2}
    assert len(pmc.claim_shapes) == 2


def test_different_conflict_pairs_produce_separate_merge_candidates():
    resolutions = [
        _resolution(
            _shape("C1"), _result(ResolutionVerdict.CONFLICT, candidates=[_candidate(5), _candidate(6)]), [1],
        ),
        _resolution(
            _shape("C2"), _result(ResolutionVerdict.CONFLICT, candidates=[_candidate(7), _candidate(8)]), [2],
        ),
    ]
    summary = build_migration_report(_plan(resolutions))
    assert summary.statistics.potential_merge_candidates == 2


# ── Coverage report ──────────────────────────────────────────────────────

def test_coverage_report_groups_by_currency_and_provider():
    resolutions = [
        _resolution(_shape("A", currency="USD"), _result(ResolutionVerdict.RESOLVED, resolved_asset_id=1), [1]),
        _resolution(_shape("B", currency="THB"), _result(ResolutionVerdict.UNKNOWN), [2, 3]),
    ]
    summary = build_migration_report(_plan(resolutions))
    cov = summary.coverage_report

    assert len(cov.rows) == 2
    currency_map = dict(cov.by_currency)
    assert currency_map["USD"].resolved == 1
    assert currency_map["THB"].unknown == 2

    provider_map = dict(cov.by_provider)
    assert set(provider_map.keys()) == {"ledger:historical"}
    assert provider_map["ledger:historical"].total == 3
