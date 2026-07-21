"""Tests for Phase 6.7B — Effective Ledger Validation.

All tests are pure-Python (no database, no network, no yfinance).
Database and ORM objects are replaced with SimpleNamespace stubs so every
test is fast and fully deterministic.

Coverage
--------

Backward compatibility (repairs=None)
  1.  validate_portfolio_ledger returns LedgerValidationReport
  2.  repairs=None, mode="effective" behaves identically to raw (no overlay)
  3.  Empty repair list: effective == raw

Effective mode — EXCLUDE
  4.  Excluded transaction disappears from effective canonical list
  5.  Finding about excluded transaction is absent in effective report
  6.  Finding about non-excluded transaction is present in effective report
  7.  Multiple EXCLUDE repairs: all targeted findings removed
  8.  EXCLUDE referencing unknown tx_id is silently ignored

Effective mode — SUPPRESS_FINDING
  9.  SUPPRESS_FINDING suppresses matching finding by check_id + transaction_id
  10. SUPPRESS_FINDING with mismatched check_id does NOT suppress the finding
  11. SUPPRESS_FINDING with mismatched transaction_id does NOT suppress
  12. Mixed EXCLUDE + SUPPRESS_FINDING: both types of resolution work

Effective mode — finding provenance (origin)
  13. All findings in effective report have origin="RAW"
  14. Findings in raw report have origin=None (unchanged)

LedgerValidationComparison
  15. compare_ledger_validation returns LedgerValidationComparison
  16. Resolved findings = present in raw, absent in effective
  17. Remaining findings = present in both
  18. Newly-introduced findings = zero for normal repair usage
  19. Empty repair list: all raw findings appear in remaining; none resolved
  20. resolved + remaining + new = raw total (no double-counting)

Confidence scoring
  21. _ledger_confidence returns 100.0 for a clean report
  22. _ledger_confidence penalises CRITICAL × 25, ERROR × 10, WARNING × 3
  23. _ledger_confidence never goes below 0.0
  24. Effective report confidence improves when findings are resolved

Unknown repair type
  25. Unknown repair_type in repairs is silently ignored (no crash, no finding)

Structural guarantees
  26. LedgerValidationComparison is frozen (immutable)
  27. LedgerFinding.origin is None by default
"""
from __future__ import annotations

import asyncio
import sys
import os
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.ledger_validator import (
    LedgerFinding,
    LedgerValidationComparison,
    LedgerValidationReport,
    FindingSeverity,
    _ledger_confidence,
    _finding_key,
    compare_ledger_validation,
    validate_portfolio_ledger,
)
from services.ledger_repair import apply_repair_overlay


# ══════════════════════════════════════════════════════════════════════════════
# Stub helpers
# ══════════════════════════════════════════════════════════════════════════════

def _make_tx(
    tx_id: int,
    tx_type: str = "INITIAL_POSITION",
    symbol: str  = "KBANK.BK",
    tx_date: date | None = None,
    shares: float = 100.0,
    price:  float = 10.0,
) -> SimpleNamespace:
    """Raw Transaction stub.  Mimics the ORM Transaction object."""
    d = tx_date or date(2026, 1, 10)
    return SimpleNamespace(
        id                   = tx_id,
        portfolio_id         = 1,
        transaction_type     = tx_type,
        symbol               = symbol,
        shares               = Decimal(str(shares)),
        price_per_share      = Decimal(str(price)),
        total_amount         = Decimal(str(shares * price)),
        fees                 = Decimal("0"),
        taxes                = Decimal("0"),
        transaction_date     = d,
        created_at           = datetime(d.year, d.month, d.day, 12),
        notes                = None,
        sector               = None,
        qty_correction_delta = None,
        realized_pnl         = None,
    )


def _make_repair(
    repair_type: str,
    transaction_id: int | None,
    reason_code: str | None = None,
    repair_id: int = 1,
    is_active: bool = True,
) -> SimpleNamespace:
    """LedgerRepair stub."""
    return SimpleNamespace(
        id             = repair_id,
        portfolio_id   = 1,
        transaction_id = transaction_id,
        repair_type    = repair_type,
        reason         = "test",
        reason_code    = reason_code,
        payload_json   = None,
        created_by     = "system",
        created_at     = datetime(2026, 6, 28, 12),
        is_active      = is_active,
        repair_plan_id = "plan-0001",
    )


def _make_db(
    portfolio: SimpleNamespace,
    transactions: list[SimpleNamespace],
    items: list[SimpleNamespace] | None = None,
    snapshots: list[SimpleNamespace] | None = None,
) -> SimpleNamespace:
    """Minimal DB stub that satisfies the query chains used by validate_portfolio_ledger."""
    from unittest.mock import MagicMock

    db   = MagicMock()
    rows = {
        "portfolio": portfolio,
        "transactions": transactions,
        "items": items or [],
        "snapshots": snapshots or [],
    }

    def _query(model):
        qm = MagicMock()
        name = getattr(model, "__name__", str(model))

        def _filter_by(**kw):
            fm = MagicMock()

            def _order_by(*args):
                om = MagicMock()
                if "portfolio" in name.lower() and "item" not in name.lower() and "snapshot" not in name.lower():
                    om.first.return_value = rows["portfolio"]
                elif "transaction" in name.lower():
                    om.all.return_value = rows["transactions"]
                elif "item" in name.lower():
                    om.all.return_value = rows["items"]
                elif "snapshot" in name.lower():
                    om.all.return_value = rows["snapshots"]
                else:
                    om.all.return_value = []
                    om.first.return_value = None
                return om

            fm.order_by = _order_by
            fm.all.return_value = []
            if "portfolio" in name.lower() and "item" not in name.lower() and "snapshot" not in name.lower():
                fm.first.return_value = rows["portfolio"]
            return fm

        def _filter(*args):
            # M36.1 WP4C — services.portfolio_reference.resolve_portfolio_reference
            # queries via db.query(Portfolio).filter(Portfolio.id == ..., ...).first(),
            # not .filter_by(...). Route it to the same stub data as _filter_by.
            return _filter_by()

        qm.filter_by = _filter_by
        qm.filter    = _filter
        qm.order_by  = lambda *a: qm
        qm.all.return_value = []
        return qm

    db.query.side_effect = _query
    return db


def _make_portfolio(pid: int = 1, cash: float = 0.0) -> SimpleNamespace:
    return SimpleNamespace(
        id           = pid,
        workspace_id = 1,
        name         = f"Portfolio {pid}",
        cash_balance = Decimal(str(cash)),
        created_at   = datetime(2025, 1, 1),
    )


def _run(coro):
    """Run a coroutine synchronously."""
    return asyncio.get_event_loop().run_until_complete(coro)


# ══════════════════════════════════════════════════════════════════════════════
# Helper: build a report with one known finding
# ══════════════════════════════════════════════════════════════════════════════

def _make_finding(
    check_id: str = "DUP_INITIAL_POSITION",
    severity: FindingSeverity = FindingSeverity.CRITICAL,
    tx_ids: list[int] | None = None,
) -> LedgerFinding:
    return LedgerFinding(
        check_id          = check_id,
        severity          = severity,
        portfolio_id      = 1,
        transaction_ids   = tx_ids or [10, 20],
        symbol            = "KBANK.BK",
        normalized_symbol = "KBANK.BK",
        title             = f"Test {check_id}",
        explanation       = "test",
        recommendation    = "test",
    )


# ══════════════════════════════════════════════════════════════════════════════
# Backward compatibility (repairs=None)
# ══════════════════════════════════════════════════════════════════════════════

def test_validate_portfolio_ledger_returns_report_type():
    """Test 1 — function returns LedgerValidationReport."""
    portfolio = _make_portfolio()
    tx        = _make_tx(tx_id=10)
    db        = _make_db(portfolio, [tx])
    r = _run(validate_portfolio_ledger(db, portfolio_id=1, workspace_id=1))
    assert isinstance(r, LedgerValidationReport)


def test_repairs_none_mode_effective_behaves_like_raw():
    """Test 2 — repairs=None with mode='effective' must equal raw behaviour."""
    portfolio = _make_portfolio()
    tx        = _make_tx(tx_id=10)
    db        = _make_db(portfolio, [tx])
    raw = _run(validate_portfolio_ledger(db, portfolio_id=1, workspace_id=1, mode="raw"))
    eff = _run(validate_portfolio_ledger(
        db, portfolio_id=1, workspace_id=1, mode="effective", repairs=None
    ))
    # Finding count and check_ids must match
    assert len(raw.findings) == len(eff.findings)
    assert [f.check_id for f in raw.findings] == [f.check_id for f in eff.findings]


def test_empty_repair_list_effective_equals_raw():
    """Test 3 — empty repair list: effective report equals raw report in content."""
    portfolio = _make_portfolio()
    # Two identical INITIAL_POSITION → triggers DUP_INITIAL_POSITION finding
    tx_a = _make_tx(tx_id=10, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    tx_b = _make_tx(tx_id=20, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    db   = _make_db(portfolio, [tx_a, tx_b])
    raw  = _run(validate_portfolio_ledger(db, portfolio_id=1, workspace_id=1))
    eff  = _run(validate_portfolio_ledger(
        db, portfolio_id=1, workspace_id=1, repairs=[], mode="effective"
    ))
    assert [f.check_id for f in raw.findings] == [f.check_id for f in eff.findings]


# ══════════════════════════════════════════════════════════════════════════════
# Effective mode — EXCLUDE
# ══════════════════════════════════════════════════════════════════════════════

def test_exclude_removes_transaction_from_effective_list():
    """Test 4 — EXCLUDE removes the targeted transaction from the canonical list
    used by all checks (verified via DUP_INITIAL_POSITION disappearing)."""
    portfolio = _make_portfolio()
    tx_a = _make_tx(tx_id=10, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    tx_b = _make_tx(tx_id=20, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    db   = _make_db(portfolio, [tx_a, tx_b])

    # Raw mode: DUP_INITIAL_POSITION fires because two identical tx exist.
    raw = _run(validate_portfolio_ledger(db, portfolio_id=1, workspace_id=1))
    assert any(f.check_id == "DUP_INITIAL_POSITION" for f in raw.findings)

    # Effective mode with EXCLUDE on tx_b: only one INITIAL_POSITION remains.
    repair = _make_repair("EXCLUDE", transaction_id=20)
    eff    = _run(validate_portfolio_ledger(
        db, portfolio_id=1, workspace_id=1, repairs=[repair], mode="effective"
    ))
    assert not any(f.check_id == "DUP_INITIAL_POSITION" for f in eff.findings)


def test_excluded_transaction_finding_absent_in_effective():
    """Test 5 — finding for excluded tx is absent in effective report."""
    portfolio = _make_portfolio()
    tx_a = _make_tx(tx_id=10, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    tx_b = _make_tx(tx_id=20, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    db   = _make_db(portfolio, [tx_a, tx_b])
    repair = _make_repair("EXCLUDE", transaction_id=20)
    eff    = _run(validate_portfolio_ledger(
        db, portfolio_id=1, workspace_id=1, repairs=[repair], mode="effective"
    ))
    dup_findings = [f for f in eff.findings if f.check_id == "DUP_INITIAL_POSITION"]
    assert dup_findings == []


def test_finding_about_non_excluded_transaction_remains():
    """Test 6 — finding about a non-excluded tx is still present in effective report."""
    portfolio = _make_portfolio()
    # Three INITIAL_POSITION: exclude tx_id=30 only. tx 10+20 still duplicate.
    tx_a = _make_tx(tx_id=10, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    tx_b = _make_tx(tx_id=20, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    tx_c = _make_tx(tx_id=30, tx_type="INITIAL_POSITION", symbol="AAA.BK")
    db   = _make_db(portfolio, [tx_a, tx_b, tx_c])
    repair = _make_repair("EXCLUDE", transaction_id=30)
    eff    = _run(validate_portfolio_ledger(
        db, portfolio_id=1, workspace_id=1, repairs=[repair], mode="effective"
    ))
    # KBANK.BK duplicate should still fire (neither tx_a nor tx_b is excluded)
    assert any(f.check_id == "DUP_INITIAL_POSITION" for f in eff.findings)


def test_multiple_exclude_repairs_all_respected():
    """Test 7 — multiple EXCLUDE repairs remove all targeted transactions."""
    portfolio = _make_portfolio()
    tx_a = _make_tx(tx_id=10, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    tx_b = _make_tx(tx_id=20, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    tx_c = _make_tx(tx_id=30, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    db   = _make_db(portfolio, [tx_a, tx_b, tx_c])

    raw = _run(validate_portfolio_ledger(db, portfolio_id=1, workspace_id=1))
    assert any(f.check_id == "DUP_INITIAL_POSITION" for f in raw.findings)

    repairs = [
        _make_repair("EXCLUDE", transaction_id=20, repair_id=1),
        _make_repair("EXCLUDE", transaction_id=30, repair_id=2),
    ]
    eff = _run(validate_portfolio_ledger(
        db, portfolio_id=1, workspace_id=1, repairs=repairs, mode="effective"
    ))
    assert not any(f.check_id == "DUP_INITIAL_POSITION" for f in eff.findings)


def test_exclude_unknown_tx_id_ignored_safely():
    """Test 8 — EXCLUDE targeting a tx_id not in the ledger is silently ignored."""
    portfolio = _make_portfolio()
    tx_a = _make_tx(tx_id=10, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    db   = _make_db(portfolio, [tx_a])
    repair = _make_repair("EXCLUDE", transaction_id=999)  # 999 not in ledger
    eff    = _run(validate_portfolio_ledger(
        db, portfolio_id=1, workspace_id=1, repairs=[repair], mode="effective"
    ))
    # Should not crash; tx_a is still in the effective list
    assert eff.transactions_inspected == 1


# ══════════════════════════════════════════════════════════════════════════════
# Effective mode — SUPPRESS_FINDING
# ══════════════════════════════════════════════════════════════════════════════

def test_suppress_finding_suppresses_matching_finding():
    """Test 9 — SUPPRESS_FINDING with matching check_id + tx_id removes the finding."""
    portfolio = _make_portfolio()
    tx_a = _make_tx(tx_id=10, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    tx_b = _make_tx(tx_id=20, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    db   = _make_db(portfolio, [tx_a, tx_b])

    # Suppress DUP_INITIAL_POSITION for tx_id=10
    repair = _make_repair(
        "SUPPRESS_FINDING",
        transaction_id=10,
        reason_code="DUP_INITIAL_POSITION",
    )
    eff = _run(validate_portfolio_ledger(
        db, portfolio_id=1, workspace_id=1, repairs=[repair], mode="effective"
    ))
    dup = [f for f in eff.findings if f.check_id == "DUP_INITIAL_POSITION"]
    assert dup == [], f"Expected DUP_INITIAL_POSITION to be suppressed, got: {dup}"


def test_suppress_finding_mismatched_check_id_does_not_suppress():
    """Test 10 — SUPPRESS_FINDING with wrong reason_code leaves finding intact."""
    portfolio = _make_portfolio()
    tx_a = _make_tx(tx_id=10, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    tx_b = _make_tx(tx_id=20, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    db   = _make_db(portfolio, [tx_a, tx_b])

    repair = _make_repair(
        "SUPPRESS_FINDING",
        transaction_id=10,
        reason_code="NULL_SYMBOL",  # wrong check_id
    )
    eff = _run(validate_portfolio_ledger(
        db, portfolio_id=1, workspace_id=1, repairs=[repair], mode="effective"
    ))
    assert any(f.check_id == "DUP_INITIAL_POSITION" for f in eff.findings)


def test_suppress_finding_mismatched_tx_id_does_not_suppress():
    """Test 11 — SUPPRESS_FINDING with wrong transaction_id leaves finding intact."""
    portfolio = _make_portfolio()
    tx_a = _make_tx(tx_id=10, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    tx_b = _make_tx(tx_id=20, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    db   = _make_db(portfolio, [tx_a, tx_b])

    repair = _make_repair(
        "SUPPRESS_FINDING",
        transaction_id=999,  # wrong tx_id
        reason_code="DUP_INITIAL_POSITION",
    )
    eff = _run(validate_portfolio_ledger(
        db, portfolio_id=1, workspace_id=1, repairs=[repair], mode="effective"
    ))
    assert any(f.check_id == "DUP_INITIAL_POSITION" for f in eff.findings)


def test_mixed_exclude_and_suppress_finding():
    """Test 12 — EXCLUDE + SUPPRESS_FINDING work together."""
    portfolio = _make_portfolio()
    tx_a = _make_tx(tx_id=10, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    tx_b = _make_tx(tx_id=20, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    tx_c = _make_tx(tx_id=30, tx_type="INITIAL_POSITION", symbol="SCB.BK")
    tx_d = _make_tx(tx_id=40, tx_type="INITIAL_POSITION", symbol="SCB.BK")
    db   = _make_db(portfolio, [tx_a, tx_b, tx_c, tx_d])

    # KBANK.BK duplicates resolved by EXCLUDE on tx_b
    # SCB.BK duplicates resolved by SUPPRESS_FINDING on tx_c
    repairs = [
        _make_repair("EXCLUDE", transaction_id=20, repair_id=1),
        _make_repair("SUPPRESS_FINDING", transaction_id=30,
                     reason_code="DUP_INITIAL_POSITION", repair_id=2),
    ]
    eff = _run(validate_portfolio_ledger(
        db, portfolio_id=1, workspace_id=1, repairs=repairs, mode="effective"
    ))
    dup_findings = [f for f in eff.findings if f.check_id == "DUP_INITIAL_POSITION"]
    assert dup_findings == []


# ══════════════════════════════════════════════════════════════════════════════
# Effective mode — finding provenance (origin)
# ══════════════════════════════════════════════════════════════════════════════

def test_effective_findings_have_origin_raw():
    """Test 13 — All findings in the effective report carry origin='RAW'."""
    portfolio = _make_portfolio()
    tx_a = _make_tx(tx_id=10, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    tx_b = _make_tx(tx_id=20, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    db   = _make_db(portfolio, [tx_a, tx_b])
    eff  = _run(validate_portfolio_ledger(
        db, portfolio_id=1, workspace_id=1, repairs=[], mode="effective"
    ))
    for f in eff.findings:
        assert f.origin == "RAW", f"Expected origin='RAW', got {f.origin!r} for {f.check_id}"


def test_raw_findings_have_origin_none():
    """Test 14 — All findings in raw mode carry origin=None (unchanged)."""
    portfolio = _make_portfolio()
    tx_a = _make_tx(tx_id=10, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    tx_b = _make_tx(tx_id=20, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    db   = _make_db(portfolio, [tx_a, tx_b])
    raw  = _run(validate_portfolio_ledger(db, portfolio_id=1, workspace_id=1))
    for f in raw.findings:
        assert f.origin is None, f"Expected origin=None in raw mode, got {f.origin!r}"


# ══════════════════════════════════════════════════════════════════════════════
# LedgerValidationComparison
# ══════════════════════════════════════════════════════════════════════════════

def test_compare_ledger_validation_returns_comparison():
    """Test 15 — compare_ledger_validation returns LedgerValidationComparison."""
    portfolio = _make_portfolio()
    tx_a = _make_tx(tx_id=10, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    db   = _make_db(portfolio, [tx_a])
    c = _run(compare_ledger_validation(
        db, portfolio_id=1, workspace_id=1, repairs=[]
    ))
    assert isinstance(c, LedgerValidationComparison)


def test_comparison_resolved_findings():
    """Test 16 — EXCLUDE resolves a finding: it appears in resolved_findings."""
    portfolio = _make_portfolio()
    tx_a = _make_tx(tx_id=10, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    tx_b = _make_tx(tx_id=20, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    db   = _make_db(portfolio, [tx_a, tx_b])
    repair = _make_repair("EXCLUDE", transaction_id=20)
    c = _run(compare_ledger_validation(
        db, portfolio_id=1, workspace_id=1, repairs=[repair]
    ))
    # DUP_INITIAL_POSITION should be in resolved (was in raw, gone in effective)
    assert any("DUP_INITIAL_POSITION" in key for key in c.resolved_findings), (
        f"resolved_findings={c.resolved_findings}"
    )


def test_comparison_remaining_findings():
    """Test 17 — findings not covered by any repair appear in remaining_findings."""
    portfolio = _make_portfolio()
    # Two duplicates for KBANK + one for SCB.  Only fix KBANK.
    tx_a = _make_tx(tx_id=10, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    tx_b = _make_tx(tx_id=20, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    tx_c = _make_tx(tx_id=30, tx_type="INITIAL_POSITION", symbol="SCB.BK")
    tx_d = _make_tx(tx_id=40, tx_type="INITIAL_POSITION", symbol="SCB.BK")
    db   = _make_db(portfolio, [tx_a, tx_b, tx_c, tx_d])
    repair = _make_repair("EXCLUDE", transaction_id=20)  # only fixes KBANK
    c = _run(compare_ledger_validation(
        db, portfolio_id=1, workspace_id=1, repairs=[repair]
    ))
    # SCB duplicate remains
    assert any("DUP_INITIAL_POSITION" in key for key in c.remaining_findings), (
        f"remaining_findings={c.remaining_findings}"
    )


def test_comparison_no_newly_introduced_findings():
    """Test 18 — newly_introduced_findings is empty for a valid repair set."""
    portfolio = _make_portfolio()
    tx_a = _make_tx(tx_id=10, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    tx_b = _make_tx(tx_id=20, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    db   = _make_db(portfolio, [tx_a, tx_b])
    repair = _make_repair("EXCLUDE", transaction_id=20)
    c = _run(compare_ledger_validation(
        db, portfolio_id=1, workspace_id=1, repairs=[repair]
    ))
    assert c.newly_introduced_findings == (), (
        f"Expected no new findings, got: {c.newly_introduced_findings}"
    )


def test_comparison_empty_repairs_all_in_remaining():
    """Test 19 — empty repair list: all raw findings appear in remaining; none resolved."""
    portfolio = _make_portfolio()
    tx_a = _make_tx(tx_id=10, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    tx_b = _make_tx(tx_id=20, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    db   = _make_db(portfolio, [tx_a, tx_b])
    c = _run(compare_ledger_validation(
        db, portfolio_id=1, workspace_id=1, repairs=[]
    ))
    assert c.resolved_findings == ()
    assert len(c.remaining_findings) == len(c.raw_report.findings)
    assert c.newly_introduced_findings == ()


def test_comparison_finding_counts_add_up():
    """Test 20 — resolved + remaining + new == number of unique raw finding keys."""
    portfolio = _make_portfolio()
    tx_a = _make_tx(tx_id=10, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    tx_b = _make_tx(tx_id=20, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    db   = _make_db(portfolio, [tx_a, tx_b])
    repair = _make_repair("EXCLUDE", transaction_id=20)
    c = _run(compare_ledger_validation(
        db, portfolio_id=1, workspace_id=1, repairs=[repair]
    ))
    total_accounted = (
        len(c.resolved_findings)
        + len(c.remaining_findings)
        + len(c.newly_introduced_findings)
    )
    raw_keys_count = len({_finding_key(f) for f in c.raw_report.findings})
    assert total_accounted == raw_keys_count, (
        f"resolved={len(c.resolved_findings)} remaining={len(c.remaining_findings)} "
        f"new={len(c.newly_introduced_findings)} raw_unique={raw_keys_count}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Confidence scoring
# ══════════════════════════════════════════════════════════════════════════════

def _make_report_with_findings(*findings: LedgerFinding) -> LedgerValidationReport:
    r = LedgerValidationReport(
        portfolio_id=1, portfolio_name="Test", transactions_inspected=10
    )
    r.findings = list(findings)
    return r


def test_confidence_clean_report_is_100():
    """Test 21 — clean report yields 100.0 confidence."""
    r = LedgerValidationReport(
        portfolio_id=1, portfolio_name="Test", transactions_inspected=5
    )
    assert _ledger_confidence(r) == 100.0


def test_confidence_penalty_weights():
    """Test 22 — CRITICAL × 25, ERROR × 10, WARNING × 3."""
    crit = _make_finding("A", FindingSeverity.CRITICAL, [1])
    err  = _make_finding("B", FindingSeverity.ERROR,    [2])
    warn = _make_finding("C", FindingSeverity.WARNING,  [3])
    r = _make_report_with_findings(crit, err, warn)
    expected = 100.0 - (1 * 25 + 1 * 10 + 1 * 3)
    assert _ledger_confidence(r) == expected


def test_confidence_never_below_zero():
    """Test 23 — confidence is clamped to 0.0 even with many criticals."""
    findings = [_make_finding(f"F{i}", FindingSeverity.CRITICAL, [i]) for i in range(10)]
    r = _make_report_with_findings(*findings)
    assert _ledger_confidence(r) == 0.0


def test_effective_confidence_improves_after_resolution():
    """Test 24 — effective report confidence is higher than raw when findings are resolved."""
    portfolio = _make_portfolio()
    tx_a = _make_tx(tx_id=10, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    tx_b = _make_tx(tx_id=20, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    db   = _make_db(portfolio, [tx_a, tx_b])
    repair = _make_repair("EXCLUDE", transaction_id=20)
    c = _run(compare_ledger_validation(
        db, portfolio_id=1, workspace_id=1, repairs=[repair]
    ))
    raw_conf = _ledger_confidence(c.raw_report)
    eff_conf = _ledger_confidence(c.effective_report)
    assert eff_conf >= raw_conf, (
        f"Effective confidence {eff_conf} should be >= raw {raw_conf}"
    )


# ══════════════════════════════════════════════════════════════════════════════
# Unknown repair type
# ══════════════════════════════════════════════════════════════════════════════

def test_unknown_repair_type_ignored_in_effective_mode():
    """Test 25 — unknown repair_type does not crash and does not affect findings."""
    portfolio = _make_portfolio()
    tx_a = _make_tx(tx_id=10, tx_type="INITIAL_POSITION", symbol="KBANK.BK")
    db   = _make_db(portfolio, [tx_a])
    repair = _make_repair("FUTURE_REPAIR_TYPE_9999", transaction_id=10)
    eff    = _run(validate_portfolio_ledger(
        db, portfolio_id=1, workspace_id=1, repairs=[repair], mode="effective"
    ))
    # tx_a is still in effective list (unknown type is a no-op)
    assert eff.transactions_inspected == 1


# ══════════════════════════════════════════════════════════════════════════════
# Structural guarantees
# ══════════════════════════════════════════════════════════════════════════════

def test_ledger_validation_comparison_is_frozen():
    """Test 26 — LedgerValidationComparison is immutable (frozen dataclass)."""
    r = LedgerValidationReport(
        portfolio_id=1, portfolio_name="X", transactions_inspected=0
    )
    c = LedgerValidationComparison(
        raw_report=r,
        effective_report=r,
        resolved_findings=(),
        remaining_findings=(),
        newly_introduced_findings=(),
    )
    with pytest.raises((AttributeError, TypeError)):
        c.resolved_findings = ("new",)  # type: ignore


def test_ledger_finding_origin_defaults_to_none():
    """Test 27 — LedgerFinding.origin defaults to None in raw mode."""
    f = _make_finding()
    assert f.origin is None
