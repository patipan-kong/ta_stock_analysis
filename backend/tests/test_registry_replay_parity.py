"""Tests for services/registry_replay_parity.py — M5 Track B Stage 1 (Golden
Baseline Capture).

Reference: docs/implementation/M5_TRACK_B_NATIVE_INTEGRATION_TDD.md §5.2, §7
Stage 1, §10.1-10.3.

Coverage
--------
Truth extraction (pure)
  1.  _extract_holdings_truth flattens MISSING-row dict payload
  2.  _extract_holdings_truth uses field-level values for MATCH/DIFFERENT rows
  3.  _extract_holdings_truth skips EXTRA rows (DB-only, not replay truth)
  4.  _extract_snapshot_truth mirrors the same rules for snapshot rows
  5.  _extract_validator_finding_keys returns () for no report
  6.  _extract_validator_finding_keys uses ledger_validator's own _finding_key

Diffing (pure)
  7.  _diff_truth_maps: identical truth -> no diffs
  8.  _diff_truth_maps: value changed -> DIFFERENT
  9.  _diff_truth_maps: baseline-only key -> MISSING
  10. _diff_truth_maps: rebuilt-only key -> EXTRA
  11. _diff_validator_findings: identical -> no diffs
  12. _diff_validator_findings: severity changed -> DIFFERENT
  13. _diff_validator_findings: baseline-only finding -> MISSING
  14. _diff_validator_findings: rebuilt-only finding -> EXTRA

compare_against_baseline (pure)
  15. Bit-identical baseline vs rebuilt -> is_bit_identical=True, no diffs
  16. A holdings diff flips is_bit_identical to False
  17. A validator diff flips is_bit_identical to False

capture_golden_baseline / run_determinism_check (integration, mocked DB)
  18. Simple portfolio (single BUY) — deterministic replay-twice
  19. Multiple buys/sells — deterministic replay-twice
  20. Dividend transactions — deterministic replay-twice
  21. Alias symbols (KBANK / KBANK.BK) — merge under ReplayKey, deterministic
  22. DR security (NVDA01.BK) — deterministic, price_symbol doesn't leak into truth
  23. Cash-only portfolio (DEPOSIT only, no equity) — deterministic
  24. content_hash is stable across two captures of the same state
  25. content_hash changes when holdings truth changes

Storage round-trip
  26. save_baseline / load_baseline preserves every field

Regression report aggregation
  27. generate_regression_report summarizes portfolio_count / bit-identical counts / hashes
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.ledger_validator import FindingSeverity, LedgerFinding, LedgerValidationReport
from services.portfolio_rebuilder import ReconciliationRow, ReconciliationStatus, RebuildResult
from services.registry_replay_parity import (
    GoldenBaseline,
    HoldingDiff,
    ParityReport,
    ValidatorDiff,
    _diff_truth_maps,
    _diff_validator_findings,
    _extract_holdings_truth,
    _extract_snapshot_truth,
    _extract_validator_finding_keys,
    capture_golden_baseline,
    compare_against_baseline,
    generate_regression_report,
    load_baseline,
    run_determinism_check,
    save_baseline,
)
from services.transaction_canonicalizer import CanonicalTransaction


# ── Shared fixtures (mirrors test_portfolio_rebuilder.py's own idiom) ──────────

def _ctx(
    id: int = 1,
    transaction_type: str = "BUY",
    raw_symbol: str | None = "AOT.BK",
    canonical_symbol: str | None = "AOT.BK",
    shares: float = 100.0,
    price_per_share: float = 75.0,
    total_amount: float = 7_550.0,
    fees: float = 50.0,
    taxes: float = 3.50,
    transaction_date: date = date(2026, 1, 15),
    sector: str | None = "Transport",
    realized_pnl: float | None = None,
) -> CanonicalTransaction:
    return CanonicalTransaction(
        id                   = id,
        transaction_type     = transaction_type,
        raw_symbol           = raw_symbol,
        canonical_symbol     = canonical_symbol,
        shares               = Decimal(str(shares)),
        price_per_share      = Decimal(str(price_per_share)),
        total_amount         = Decimal(str(total_amount)),
        fees                 = Decimal(str(fees)),
        taxes                = Decimal(str(taxes)),
        transaction_date     = transaction_date,
        created_at           = None,
        sector               = sector,
        notes                = None,
        qty_correction_delta = None,
        realized_pnl         = realized_pnl,
    )


def _make_portfolio_obj(id: int = 1, name: str = "Test", cash: float = 0.0) -> MagicMock:
    p = MagicMock()
    p.id = id
    p.name = name
    p.cash_balance = cash
    return p


def _make_raw_tx_mock(tx_id: int) -> MagicMock:
    t = MagicMock()
    t.id = tx_id
    return t


def _clean_report(portfolio_id: int = 1) -> LedgerValidationReport:
    return LedgerValidationReport(
        portfolio_id           = portfolio_id,
        portfolio_name         = "Test",
        transactions_inspected = 0,
    )


def _make_rebuild_mock_db(portfolio: MagicMock, raw_txs: list, items: list | None = None) -> MagicMock:
    """Mock DB session sufficient for rebuild_portfolio(skip_snapshots=True, dry_run=True)."""
    from models.database import Portfolio, Transaction, PortfolioItem, PortfolioSnapshot

    items = items or []
    db    = MagicMock()

    def _query(model):
        m = MagicMock()
        if model is Portfolio:
            m.filter_by.return_value.first.return_value = portfolio
        elif model is Transaction:
            m.filter_by.return_value.order_by.return_value.all.return_value = raw_txs
        elif model is PortfolioItem:
            m.filter_by.return_value.all.return_value = items
            m.filter_by.return_value.delete.return_value = None
        elif model is PortfolioSnapshot:
            snap_m = MagicMock()
            snap_m.all.return_value = []
            snap_m.order_by.return_value.all.return_value = []
            snap_m.filter.return_value.all.return_value = []
            m.filter_by.return_value = snap_m
        return m

    db.query.side_effect = _query
    return db


def _capture(ctxs: list[CanonicalTransaction], portfolio: MagicMock, validator_report=None):
    db = _make_rebuild_mock_db(portfolio, [_make_raw_tx_mock(c.id) for c in ctxs])
    with patch("services.portfolio_rebuilder.canonicalize_transactions", return_value=ctxs), \
         patch("services.portfolio_rebuilder.load_active_repairs", return_value=[]), \
         patch("services.portfolio_rebuilder.validate_portfolio_ledger",
               new=AsyncMock(return_value=validator_report or _clean_report(portfolio.id))):
        return asyncio.run(capture_golden_baseline(
            db, portfolio_id=portfolio.id, workspace_id=1, skip_snapshots=True,
        ))


def _determinism_check(ctxs: list[CanonicalTransaction], portfolio: MagicMock, validator_report=None):
    db = _make_rebuild_mock_db(portfolio, [_make_raw_tx_mock(c.id) for c in ctxs])
    with patch("services.portfolio_rebuilder.canonicalize_transactions", return_value=ctxs), \
         patch("services.portfolio_rebuilder.load_active_repairs", return_value=[]), \
         patch("services.portfolio_rebuilder.validate_portfolio_ledger",
               new=AsyncMock(return_value=validator_report or _clean_report(portfolio.id))):
        return asyncio.run(run_determinism_check(
            db, portfolio_id=portfolio.id, workspace_id=1, skip_snapshots=True,
        ))


# ══════════════════════════════════════════════════════════════════════════════
# 1-6. Truth extraction
# ══════════════════════════════════════════════════════════════════════════════

def test_extract_holdings_truth_flattens_missing_dict():
    rows = [ReconciliationRow(
        entity_type="portfolio_item", identifier="AOT.BK", field="*",
        current_value=None, reconstructed_value={"shares": 100.0, "avg_cost": 75.5},
        status=ReconciliationStatus.MISSING,
    )]
    truth = _extract_holdings_truth(rows)
    assert ("AOT.BK", "avg_cost", 75.5) in truth
    assert ("AOT.BK", "shares", 100.0) in truth


def test_extract_holdings_truth_uses_field_level_values():
    rows = [ReconciliationRow(
        entity_type="portfolio_item", identifier="AOT.BK", field="shares",
        current_value=90.0, reconstructed_value=100.0,
        status=ReconciliationStatus.DIFFERENT,
    )]
    truth = _extract_holdings_truth(rows)
    assert truth == (("AOT.BK", "shares", 100.0),)


def test_extract_holdings_truth_skips_extra_rows():
    rows = [ReconciliationRow(
        entity_type="portfolio_item", identifier="STALE.BK", field="*",
        current_value={"shares": 10.0, "avg_cost": 1.0}, reconstructed_value=None,
        status=ReconciliationStatus.EXTRA,
    )]
    assert _extract_holdings_truth(rows) == ()


def test_extract_snapshot_truth_mirrors_holdings_rules():
    rows = [
        ReconciliationRow(
            entity_type="snapshot", identifier="2026-01-15", field="*",
            current_value=None, reconstructed_value={"total_value": 100_000.0},
            status=ReconciliationStatus.MISSING,
        ),
        ReconciliationRow(
            entity_type="snapshot", identifier="2026-01-16", field="*",
            current_value={"total_value": 5.0}, reconstructed_value=None,
            status=ReconciliationStatus.EXTRA,
        ),
    ]
    truth = _extract_snapshot_truth(rows)
    assert truth == (("2026-01-15", "total_value", 100_000.0),)


def test_extract_validator_finding_keys_none_report():
    assert _extract_validator_finding_keys(None) == ()


def test_extract_validator_finding_keys_uses_finding_key():
    report = LedgerValidationReport(
        portfolio_id=1, portfolio_name="P", transactions_inspected=2,
        findings=[LedgerFinding(
            check_id="SYMBOL_ALIAS", severity=FindingSeverity.CRITICAL,
            portfolio_id=1, transaction_ids=[5, 3], symbol="KBANK",
            normalized_symbol="KBANK.BK", title="t", explanation="e", recommendation="r",
        )],
    )
    keys = _extract_validator_finding_keys(report)
    assert keys == (("SYMBOL_ALIAS:3,5", "CRITICAL"),)


# ══════════════════════════════════════════════════════════════════════════════
# 7-14. Diffing
# ══════════════════════════════════════════════════════════════════════════════

def test_diff_truth_maps_identical_no_diffs():
    t = (("AOT.BK", "shares", 100.0),)
    assert _diff_truth_maps(t, t, HoldingDiff, "symbol") == ()


def test_diff_truth_maps_value_changed_different():
    baseline = (("AOT.BK", "shares", 100.0),)
    rebuilt  = (("AOT.BK", "shares", 150.0),)
    diffs = _diff_truth_maps(baseline, rebuilt, HoldingDiff, "symbol")
    assert len(diffs) == 1
    assert diffs[0].status == ReconciliationStatus.DIFFERENT
    assert diffs[0].baseline_value == 100.0
    assert diffs[0].rebuilt_value == 150.0


def test_diff_truth_maps_baseline_only_missing():
    baseline = (("AOT.BK", "shares", 100.0),)
    diffs = _diff_truth_maps(baseline, (), HoldingDiff, "symbol")
    assert len(diffs) == 1
    assert diffs[0].status == ReconciliationStatus.MISSING


def test_diff_truth_maps_rebuilt_only_extra():
    rebuilt = (("AOT.BK", "shares", 100.0),)
    diffs = _diff_truth_maps((), rebuilt, HoldingDiff, "symbol")
    assert len(diffs) == 1
    assert diffs[0].status == ReconciliationStatus.EXTRA


def test_diff_validator_findings_identical_no_diffs():
    keys = (("SYMBOL_ALIAS:1", "CRITICAL"),)
    assert _diff_validator_findings(keys, keys) == ()


def test_diff_validator_findings_severity_changed():
    baseline = (("SYMBOL_ALIAS:1", "WARNING"),)
    rebuilt  = (("SYMBOL_ALIAS:1", "CRITICAL"),)
    diffs = _diff_validator_findings(baseline, rebuilt)
    assert diffs == (ValidatorDiff("SYMBOL_ALIAS:1", ReconciliationStatus.DIFFERENT, "WARNING", "CRITICAL"),)


def test_diff_validator_findings_baseline_only_missing():
    baseline = (("SYMBOL_ALIAS:1", "CRITICAL"),)
    diffs = _diff_validator_findings(baseline, ())
    assert diffs == (ValidatorDiff("SYMBOL_ALIAS:1", ReconciliationStatus.MISSING, "CRITICAL", None),)


def test_diff_validator_findings_rebuilt_only_extra():
    rebuilt = (("SYMBOL_ALIAS:1", "CRITICAL"),)
    diffs = _diff_validator_findings((), rebuilt)
    assert diffs == (ValidatorDiff("SYMBOL_ALIAS:1", ReconciliationStatus.EXTRA, None, "CRITICAL"),)


# ══════════════════════════════════════════════════════════════════════════════
# 15-17. compare_against_baseline
# ══════════════════════════════════════════════════════════════════════════════

def _baseline(**overrides) -> GoldenBaseline:
    defaults = dict(
        portfolio_id=1, portfolio_name="P", captured_at="2026-01-01T00:00:00+00:00",
        success=True, transactions_replayed=1, effective_transaction_count=1,
        excluded_transaction_count=0, reconstructed_holdings_count=1,
        reconstructed_cash=1000.0, snapshots_processed=0,
        holdings_truth=(("AOT.BK", "shares", 100.0),),
        snapshot_truth=(), validator_finding_keys=(),
        validator_overall_severity="PASS", content_hash="deadbeef",
    )
    defaults.update(overrides)
    return GoldenBaseline(**defaults)


def _rebuild_result(reconciliation_report=None, validator_report=None) -> RebuildResult:
    return RebuildResult(
        portfolio_id=1, portfolio_name="P", success=True,
        reconciliation_report=reconciliation_report or [],
        validator_report=validator_report,
    )


def test_compare_bit_identical():
    baseline = _baseline()
    rows = [ReconciliationRow(
        entity_type="portfolio_item", identifier="AOT.BK", field="shares",
        current_value=100.0, reconstructed_value=100.0, status=ReconciliationStatus.MATCH,
    )]
    result = _rebuild_result(reconciliation_report=rows)
    report = compare_against_baseline(baseline, result)
    assert report.is_bit_identical is True
    assert report.holding_diffs == ()
    assert report.validator_diffs == ()


def test_compare_holdings_diff_breaks_identity():
    baseline = _baseline()
    rows = [ReconciliationRow(
        entity_type="portfolio_item", identifier="AOT.BK", field="shares",
        current_value=100.0, reconstructed_value=150.0, status=ReconciliationStatus.DIFFERENT,
    )]
    result = _rebuild_result(reconciliation_report=rows)
    report = compare_against_baseline(baseline, result)
    assert report.is_bit_identical is False
    assert len(report.holding_diffs) == 1


def test_compare_validator_diff_breaks_identity():
    baseline = _baseline(holdings_truth=())
    validator_report = LedgerValidationReport(
        portfolio_id=1, portfolio_name="P", transactions_inspected=1,
        findings=[LedgerFinding(
            check_id="SYMBOL_ALIAS", severity=FindingSeverity.CRITICAL,
            portfolio_id=1, transaction_ids=[1], symbol="KBANK",
            normalized_symbol="KBANK.BK", title="t", explanation="e", recommendation="r",
        )],
    )
    result = _rebuild_result(validator_report=validator_report)
    report = compare_against_baseline(baseline, result)
    assert report.is_bit_identical is False
    assert len(report.validator_diffs) == 1
    assert report.validator_diffs[0].status == ReconciliationStatus.EXTRA


# ══════════════════════════════════════════════════════════════════════════════
# 18-23. capture_golden_baseline / run_determinism_check (mocked-DB integration)
# ══════════════════════════════════════════════════════════════════════════════

def test_simple_portfolio_deterministic():
    portfolio = _make_portfolio_obj(cash=100_000.0)
    ctxs = [_ctx(id=1, transaction_type="BUY", shares=100.0, total_amount=7_550.0)]
    baseline, report = _determinism_check(ctxs, portfolio)
    assert baseline.reconstructed_holdings_count == 1
    assert report.is_bit_identical is True


def test_multiple_buys_sells_deterministic():
    portfolio = _make_portfolio_obj(cash=200_000.0)
    ctxs = [
        _ctx(id=1, transaction_type="BUY", shares=100.0, total_amount=7_550.0),
        _ctx(id=2, transaction_type="BUY", shares=50.0, total_amount=3_800.0),
        _ctx(id=3, transaction_type="SELL", shares=60.0, total_amount=4_700.0, realized_pnl=200.0),
    ]
    baseline, report = _determinism_check(ctxs, portfolio)
    assert baseline.reconstructed_holdings_count == 1
    assert report.is_bit_identical is True


def test_dividend_deterministic():
    portfolio = _make_portfolio_obj(cash=50_000.0)
    ctxs = [
        _ctx(id=1, transaction_type="BUY", shares=100.0, total_amount=7_550.0),
        _ctx(id=2, transaction_type="DIVIDEND", raw_symbol="AOT.BK", canonical_symbol="AOT.BK",
             shares=0.0, total_amount=350.0),
    ]
    baseline, report = _determinism_check(ctxs, portfolio)
    assert baseline.reconstructed_cash is not None
    assert report.is_bit_identical is True


def test_alias_symbols_merge_deterministic():
    """The ADR-005 regression case (KBANK / KBANK.BK) captured as a golden
    baseline: the two raw spellings must merge into a single holding under
    ReplayKey, and that merged state must itself be a deterministic replay."""
    portfolio = _make_portfolio_obj(cash=100_000.0)
    ctxs = [
        _ctx(id=1, transaction_type="BUY", raw_symbol="KBANK", canonical_symbol="KBANK.BK",
             shares=100.0, total_amount=14_000.0),
        _ctx(id=2, transaction_type="BUY", raw_symbol="KBANK.BK", canonical_symbol="KBANK.BK",
             shares=50.0, total_amount=7_100.0),
    ]
    baseline, report = _determinism_check(ctxs, portfolio)
    assert baseline.reconstructed_holdings_count == 1
    symbols_in_truth = {sym for sym, _, _ in baseline.holdings_truth}
    assert symbols_in_truth == {"KBANK.BK"}
    assert report.is_bit_identical is True


def test_dr_security_deterministic():
    """DR certificates key by canonical_symbol (the US underlying) for replay
    identity; price_symbol is an internal replay-engine detail and must not
    leak into the golden-baseline truth (which only reflects reconciled
    PortfolioItem fields: shares/avg_cost)."""
    portfolio = _make_portfolio_obj(cash=100_000.0)
    ctxs = [_ctx(id=1, transaction_type="BUY", raw_symbol="NVDA01.BK", canonical_symbol="NVDA",
                 shares=10.0, total_amount=5_000.0)]
    baseline, report = _determinism_check(ctxs, portfolio)
    symbols_in_truth = {sym for sym, _, _ in baseline.holdings_truth}
    assert symbols_in_truth == {"NVDA"}
    fields_in_truth = {fld for _, fld, _ in baseline.holdings_truth}
    assert fields_in_truth == {"shares", "avg_cost"}
    assert report.is_bit_identical is True


def test_cash_only_portfolio_deterministic():
    portfolio = _make_portfolio_obj(cash=0.0)
    ctxs = [_ctx(id=1, transaction_type="DEPOSIT", raw_symbol=None, canonical_symbol=None,
                 shares=0.0, total_amount=10_000.0)]
    baseline, report = _determinism_check(ctxs, portfolio)
    assert baseline.reconstructed_holdings_count == 0
    assert baseline.holdings_truth == ()
    assert report.is_bit_identical is True


# ══════════════════════════════════════════════════════════════════════════════
# 24-25. content_hash
# ══════════════════════════════════════════════════════════════════════════════

def test_content_hash_stable_across_captures():
    portfolio = _make_portfolio_obj(cash=100_000.0)
    ctxs = [_ctx(id=1, transaction_type="BUY", shares=100.0, total_amount=7_550.0)]
    b1 = _capture(ctxs, portfolio)
    b2 = _capture(ctxs, portfolio)
    assert b1.content_hash == b2.content_hash


def test_content_hash_changes_with_holdings():
    portfolio = _make_portfolio_obj(cash=100_000.0)
    ctxs_a = [_ctx(id=1, transaction_type="BUY", shares=100.0, total_amount=7_550.0)]
    ctxs_b = [_ctx(id=1, transaction_type="BUY", shares=200.0, total_amount=15_100.0)]
    b1 = _capture(ctxs_a, portfolio)
    b2 = _capture(ctxs_b, portfolio)
    assert b1.content_hash != b2.content_hash


# ══════════════════════════════════════════════════════════════════════════════
# 26. Storage round-trip
# ══════════════════════════════════════════════════════════════════════════════

def test_save_and_load_baseline_round_trip(tmp_path):
    portfolio = _make_portfolio_obj(id=7, cash=100_000.0)
    ctxs = [_ctx(id=1, transaction_type="BUY", shares=100.0, total_amount=7_550.0)]
    baseline = _capture(ctxs, portfolio)

    baseline_dir = str(tmp_path / "golden_baselines")
    path = save_baseline(baseline, baseline_dir=baseline_dir)
    assert os.path.exists(path)

    loaded = load_baseline(7, baseline_dir=baseline_dir)
    assert loaded == baseline


def test_load_baseline_missing_returns_none(tmp_path):
    assert load_baseline(999, baseline_dir=str(tmp_path)) is None


# ══════════════════════════════════════════════════════════════════════════════
# 27. generate_regression_report
# ══════════════════════════════════════════════════════════════════════════════

def test_generate_regression_report_aggregates_multiple_portfolios():
    """A single mocked DB session routes queries by portfolio_id so
    generate_regression_report can drive two distinct portfolios through
    its normal per-portfolio db.query(...).filter_by(...) calls, exactly as
    rebuild_portfolio() issues them against a real session."""
    from models.database import Portfolio, Transaction, PortfolioItem, PortfolioSnapshot

    portfolios = {1: _make_portfolio_obj(id=1, cash=100_000.0),
                  2: _make_portfolio_obj(id=2, cash=50_000.0)}
    raw_txs_by_pid = {1: [_make_raw_tx_mock(1)], 2: [_make_raw_tx_mock(2)]}
    ctxs_by_pid = {
        1: [_ctx(id=1, transaction_type="BUY", shares=100.0, total_amount=7_550.0)],
        2: [_ctx(id=2, transaction_type="DEPOSIT", raw_symbol=None, canonical_symbol=None,
                 shares=0.0, total_amount=5_000.0)],
    }

    router_db = MagicMock()

    def _query(model):
        m = MagicMock()
        if model is Portfolio:
            m.filter_by.side_effect = lambda **kw: MagicMock(
                first=MagicMock(return_value=portfolios.get(kw.get("id")))
            )
        elif model is Transaction:
            m.filter_by.side_effect = lambda **kw: MagicMock(
                order_by=MagicMock(return_value=MagicMock(
                    all=MagicMock(return_value=raw_txs_by_pid.get(kw.get("portfolio_id"), []))
                ))
            )
        elif model is PortfolioItem:
            m.filter_by.side_effect = lambda **kw: MagicMock(
                all=MagicMock(return_value=[]), delete=MagicMock(return_value=None)
            )
        elif model is PortfolioSnapshot:
            m.filter_by.side_effect = lambda **kw: MagicMock(
                all=MagicMock(return_value=[]),
                order_by=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))),
                filter=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))),
            )
        return m

    router_db.query.side_effect = _query

    def _canon(raw_txs):
        for pid, txs in raw_txs_by_pid.items():
            if raw_txs is txs:
                return ctxs_by_pid[pid]
        return []

    with patch("services.portfolio_rebuilder.canonicalize_transactions", side_effect=_canon), \
         patch("services.portfolio_rebuilder.load_active_repairs", return_value=[]), \
         patch("services.portfolio_rebuilder.validate_portfolio_ledger",
               new=AsyncMock(side_effect=lambda **kw: _clean_report(kw["portfolio_id"]))):
        result = asyncio.run(generate_regression_report(
            router_db, workspace_id=1, portfolio_ids=[1, 2], skip_snapshots=True,
        ))

    assert result.portfolio_count == 2
    assert result.portfolios_bit_identical == 2
    assert result.portfolios_with_diffs == 0
    assert {e.portfolio_id for e in result.entries} == {1, 2}
    assert all(e.is_bit_identical for e in result.entries)
