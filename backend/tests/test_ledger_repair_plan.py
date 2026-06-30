"""Tests for services/ledger_repair_plan.py — Phase 6.7E.

All tests are pure-Python and require no database or network connections.
CanonicalTransaction fixtures reuse the _tx()/_canonical() pattern from
test_ledger_validator.py.  Production code (services.ledger_repair_plan,
services.repair_plan_executor, services.ledger_validator) is imported by the
tests — never the other way around.

Coverage
--------
generate_repair_plan — DUP_INITIAL_POSITION
  1. Two duplicate INITIAL_POSITION records → one EXCLUDE op, earliest kept
  2. Three duplicates → two EXCLUDE ops, lowest id kept
  3. payload_json carries keep_tx_id; reason_code is the check_id

generate_repair_plan — DUP_TX_FINGERPRINT
  4. Two duplicate fingerprints → one EXCLUDE op, first occurrence kept

generate_repair_plan — idempotency
  5. Active EXCLUDE repair on one duplicate → not regenerated, counted
     in already_active
  6. All duplicates already excluded → plan is None
  7. Re-running generate_repair_plan after a simulated apply is a no-op

generate_repair_plan — non-repairable findings
  8. SYMBOL_ALIAS / CASH_MISMATCH etc. are reported in skipped_by_check_id,
     never turned into operations
  9. Clean report (no findings) → plan is None

generate_repair_plan — JSON round trip
  10. write_repair_plan() + load_repair_plan() round-trips without error
  11. The generated JSON is accepted by apply_repair_plan() unmodified

End-to-end (pure-Python simulation, no DB)
  12. Applying the generated EXCLUDE overlay removes the originating
      DUP_INITIAL_POSITION / DUP_TX_FINGERPRINT findings on re-validation
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.ledger_repair_plan import (
    AUTO_REPAIRABLE_CHECK_IDS,
    GenerationSummary,
    generate_repair_plan,
    repair_plan_to_dict,
    write_repair_plan,
)
from services.ledger_validator import (
    FindingSeverity,
    LedgerFinding,
    LedgerValidationReport,
    _check_duplicate_fingerprints,
    _check_duplicate_initial_positions,
)
from services.ledger_repair import apply_repair_overlay
from services.repair_plan_executor import (
    RepairApplyResult,
    apply_repair_plan,
    load_repair_plan,
)
from services.transaction_canonicalizer import canonicalize_transactions


# ──────────────────────────────────────────────────────────────────────────────
# Helpers — mirror test_ledger_validator.py's _tx()/_canonical()
# ──────────────────────────────────────────────────────────────────────────────

def _tx(
    tx_id: int,
    tx_type: str,
    symbol: str | None = None,
    shares: float | None = None,
    price: float | None = None,
    amount: float = 0.0,
    date_str: str = "2026-01-01",
) -> SimpleNamespace:
    tx_date = datetime.strptime(date_str, "%Y-%m-%d")
    return SimpleNamespace(
        id               = tx_id,
        transaction_type = tx_type,
        symbol           = symbol,
        shares           = shares,
        price_per_share  = price,
        total_amount     = amount,
        fees             = 0.0,
        taxes            = 0.0,
        sector           = None,
        transaction_date = tx_date,
        created_at       = tx_date,
        notes            = None,
    )


def _canonical(txs):
    return list(canonicalize_transactions(txs))


def _report(findings: list[LedgerFinding], portfolio_id: int = 4) -> LedgerValidationReport:
    return LedgerValidationReport(
        portfolio_id           = portfolio_id,
        portfolio_name         = "Test",
        transactions_inspected = len(findings),
        findings               = findings,
    )


def _other_finding(check_id: str, severity: FindingSeverity = FindingSeverity.WARNING) -> LedgerFinding:
    """A non-repairable finding (no transaction_ids needed for these tests)."""
    return LedgerFinding(
        check_id          = check_id,
        severity          = severity,
        portfolio_id      = 4,
        transaction_ids   = [],
        symbol            = None,
        normalized_symbol = None,
        title             = f"{check_id} finding",
        explanation       = "test",
        recommendation    = "test",
    )


def _dup_initial_position_findings() -> list[LedgerFinding]:
    txs = _canonical([
        _tx(21, "INITIAL_POSITION", "GULF.BK", shares=1500, price=124.59, date_str="2026-05-19"),
        _tx(24, "INITIAL_POSITION", "GULF.BK", shares=1500, price=56.25,  date_str="2026-05-19"),
    ])
    return _check_duplicate_initial_positions(4, txs)


def _dup_fingerprint_findings() -> list[LedgerFinding]:
    txs = _canonical([
        _tx(52, "BUY", "NVDA01.BK", shares=1000, price=20.70, date_str="2026-05-29"),
        _tx(53, "BUY", "NVDA01.BK", shares=1000, price=20.70, date_str="2026-05-29"),
    ])
    return _check_duplicate_fingerprints(4, txs)


# ──────────────────────────────────────────────────────────────────────────────
# generate_repair_plan — DUP_INITIAL_POSITION
# ──────────────────────────────────────────────────────────────────────────────

class TestGenerateDuplicateInitialPosition:
    def test_two_duplicates_keeps_earliest(self):
        report = _report(_dup_initial_position_findings())
        plan, summary = generate_repair_plan(report, portfolio_id=4)

        assert plan is not None
        assert len(plan.operations) == 1
        op = plan.operations[0]
        assert op.repair_type    == "EXCLUDE"
        assert op.transaction_id == 24          # higher id excluded
        assert op.reason_code    == "DUP_INITIAL_POSITION"
        assert summary.generated_by_type == {"EXCLUDE": 1}

    def test_three_duplicates_keeps_lowest_id_only(self):
        txs = _canonical([
            _tx(1, "INITIAL_POSITION", "BH.BK", shares=100, price=200.0, date_str="2026-01-01"),
            _tx(2, "INITIAL_POSITION", "BH.BK", shares=100, price=210.0, date_str="2026-01-01"),
            _tx(3, "INITIAL_POSITION", "BH.BK", shares=100, price=220.0, date_str="2026-01-01"),
        ])
        findings = _check_duplicate_initial_positions(4, txs)
        report   = _report(findings)
        plan, summary = generate_repair_plan(report, portfolio_id=4)

        assert plan is not None
        excluded_ids = {op.transaction_id for op in plan.operations}
        assert excluded_ids == {2, 3}            # tx1 (lowest id) kept
        assert summary.generated_by_type == {"EXCLUDE": 2}

    def test_payload_carries_keep_tx_id(self):
        report = _report(_dup_initial_position_findings())
        plan, _ = generate_repair_plan(report, portfolio_id=4)
        op = plan.operations[0]
        assert op.payload_json is not None
        import json
        assert json.loads(op.payload_json) == {"keep_tx_id": 21}


# ──────────────────────────────────────────────────────────────────────────────
# generate_repair_plan — DUP_TX_FINGERPRINT
# ──────────────────────────────────────────────────────────────────────────────

class TestGenerateDuplicateFingerprint:
    def test_two_duplicates_keeps_first_occurrence(self):
        report = _report(_dup_fingerprint_findings())
        plan, summary = generate_repair_plan(report, portfolio_id=4)

        assert plan is not None
        assert len(plan.operations) == 1
        op = plan.operations[0]
        assert op.repair_type    == "EXCLUDE"
        assert op.transaction_id == 53
        assert op.reason_code    == "DUP_TX_FINGERPRINT"


# ──────────────────────────────────────────────────────────────────────────────
# generate_repair_plan — idempotency
# ──────────────────────────────────────────────────────────────────────────────

class TestIdempotency:
    def test_already_excluded_duplicate_not_regenerated(self):
        findings = _dup_initial_position_findings()
        active_repairs = [SimpleNamespace(repair_type="EXCLUDE", transaction_id=24)]
        plan, summary = generate_repair_plan(
            _report(findings), portfolio_id=4, active_repairs=active_repairs,
        )
        assert plan is None
        assert summary.already_active == 1

    def test_partial_idempotency_across_two_findings(self):
        findings = _dup_initial_position_findings() + _dup_fingerprint_findings()
        active_repairs = [SimpleNamespace(repair_type="EXCLUDE", transaction_id=24)]
        plan, summary = generate_repair_plan(
            _report(findings), portfolio_id=4, active_repairs=active_repairs,
        )
        assert plan is not None
        assert len(plan.operations) == 1
        assert plan.operations[0].transaction_id == 53
        assert summary.already_active == 1

    def test_rerun_after_simulated_apply_is_noop(self):
        """Generating, 'applying' (simulated), then regenerating yields nothing new."""
        findings = _dup_initial_position_findings()
        plan1, _ = generate_repair_plan(_report(findings), portfolio_id=4)
        assert plan1 is not None

        # Simulate apply_repair: the generated ops become active LedgerRepair rows.
        active_repairs = [
            SimpleNamespace(repair_type=op.repair_type, transaction_id=op.transaction_id)
            for op in plan1.operations
        ]
        plan2, summary2 = generate_repair_plan(
            _report(findings), portfolio_id=4, active_repairs=active_repairs,
        )
        assert plan2 is None
        assert summary2.already_active == 1


# ──────────────────────────────────────────────────────────────────────────────
# generate_repair_plan — non-repairable findings
# ──────────────────────────────────────────────────────────────────────────────

class TestNonRepairableFindings:
    def test_unsupported_check_ids_are_skipped_not_repaired(self):
        findings = [
            _other_finding("SYMBOL_ALIAS"),
            _other_finding("CASH_MISMATCH", FindingSeverity.ERROR),
            _other_finding("SELL_WITHOUT_HOLDING", FindingSeverity.CRITICAL),
        ]
        plan, summary = generate_repair_plan(_report(findings), portfolio_id=4)

        assert plan is None
        assert summary.skipped_by_check_id == {
            "SYMBOL_ALIAS": 1,
            "CASH_MISMATCH": 1,
            "SELL_WITHOUT_HOLDING": 1,
        }
        assert summary.generated_by_type == {}

    def test_mixed_repairable_and_skipped(self):
        findings = _dup_initial_position_findings() + [_other_finding("SYMBOL_ALIAS")]
        plan, summary = generate_repair_plan(_report(findings), portfolio_id=4)

        assert plan is not None
        assert len(plan.operations) == 1
        assert summary.skipped_by_check_id == {"SYMBOL_ALIAS": 1}

    def test_clean_report_yields_no_plan(self):
        plan, summary = generate_repair_plan(_report([]), portfolio_id=4)
        assert plan is None
        assert summary.skipped_by_check_id == {}
        assert summary.generated_by_type == {}

    def test_auto_repairable_set_is_exactly_the_two_documented_checks(self):
        assert AUTO_REPAIRABLE_CHECK_IDS == frozenset({
            "DUP_INITIAL_POSITION", "DUP_TX_FINGERPRINT",
        })


# ──────────────────────────────────────────────────────────────────────────────
# JSON round trip
# ──────────────────────────────────────────────────────────────────────────────

class TestJsonRoundTrip:
    def test_write_then_load_repair_plan(self):
        report = _report(_dup_initial_position_findings() + _dup_fingerprint_findings())
        plan, _ = generate_repair_plan(
            report, portfolio_id=4, repair_plan_id="fixed-uuid", generated_at="2026-06-30T00:00:00Z",
        )
        assert plan is not None

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "plan.json")
            write_repair_plan(plan, path)
            loaded = load_repair_plan(path)

        assert loaded.schema_version == plan.schema_version
        assert loaded.portfolio_id   == plan.portfolio_id
        assert loaded.repair_plan_id == "fixed-uuid"
        assert len(loaded.operations) == len(plan.operations)
        loaded_ids = {op.transaction_id for op in loaded.operations}
        plan_ids   = {op.transaction_id for op in plan.operations}
        assert loaded_ids == plan_ids

    def test_repair_plan_to_dict_matches_apply_repair_schema(self):
        report = _report(_dup_initial_position_findings())
        plan, _ = generate_repair_plan(report, portfolio_id=4)
        d = repair_plan_to_dict(plan)
        assert set(d.keys()) == {
            "schema_version", "portfolio_id", "repair_plan_id",
            "generated_at", "operations",
        }
        op = d["operations"][0]
        assert set(op.keys()) == {
            "repair_type", "transaction_id", "reason", "reason_code", "payload_json",
        }

    def test_generated_plan_accepted_by_apply_repair_plan(self):
        """The plan JSON loads and applies via apply_repair_plan() with no edits."""
        report = _report(_dup_initial_position_findings())
        plan, _ = generate_repair_plan(report, portfolio_id=4)

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "plan.json")
            write_repair_plan(plan, path)
            loaded = load_repair_plan(path)   # must not raise RepairPlanError

        db = MagicMock()
        q  = MagicMock()
        db.query.return_value = q
        q.filter.return_value = q
        q.order_by.return_value = q
        q.all.return_value   = []
        q.first.return_value = None  # no existing active repair

        clean_report = LedgerValidationReport(
            portfolio_id=4, portfolio_name="Test", transactions_inspected=2, findings=[],
        )
        added_rows: list = []
        def _add(row):
            row.id = 1
            added_rows.append(row)
        db.add.side_effect = _add

        with (
            patch("services.repair_plan_executor.validate_portfolio_ledger",
                  AsyncMock(side_effect=[clean_report, clean_report])),
            patch("services.repair_plan_executor.load_active_repairs", MagicMock(return_value=[])),
            patch("services.repair_plan_executor._backup_repairs", MagicMock(return_value="/tmp/b.json")),
        ):
            result: RepairApplyResult = asyncio.run(apply_repair_plan(
                db=db, plan=loaded, portfolio_id=4, workspace_id=1, dry_run=False,
            ))

        assert result.error is None
        assert result.rollback is False
        assert result.operations_inserted == len(loaded.operations)
        db.commit.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# End-to-end (pure-Python): generated overlay clears the originating findings
# ──────────────────────────────────────────────────────────────────────────────

class TestOverlayResolvesFindings:
    def test_dup_initial_position_resolved_after_overlay(self):
        txs = _canonical([
            _tx(21, "INITIAL_POSITION", "GULF.BK", shares=1500, price=124.59, date_str="2026-05-19"),
            _tx(24, "INITIAL_POSITION", "GULF.BK", shares=1500, price=56.25,  date_str="2026-05-19"),
        ])
        findings_before = _check_duplicate_initial_positions(4, txs)
        assert len(findings_before) == 1

        plan, _ = generate_repair_plan(_report(findings_before), portfolio_id=4)
        assert plan is not None

        active_repairs = [
            SimpleNamespace(repair_type=op.repair_type, transaction_id=op.transaction_id)
            for op in plan.operations
        ]
        effective_txs, _ = apply_repair_overlay(tuple(txs), active_repairs)

        findings_after = _check_duplicate_initial_positions(4, list(effective_txs))
        assert findings_after == []

    def test_dup_tx_fingerprint_resolved_after_overlay(self):
        txs = _canonical([
            _tx(52, "BUY", "NVDA01.BK", shares=1000, price=20.70, date_str="2026-05-29"),
            _tx(53, "BUY", "NVDA01.BK", shares=1000, price=20.70, date_str="2026-05-29"),
        ])
        findings_before = _check_duplicate_fingerprints(4, txs)
        assert len(findings_before) == 1

        plan, _ = generate_repair_plan(_report(findings_before), portfolio_id=4)
        assert plan is not None

        active_repairs = [
            SimpleNamespace(repair_type=op.repair_type, transaction_id=op.transaction_id)
            for op in plan.operations
        ]
        effective_txs, _ = apply_repair_overlay(tuple(txs), active_repairs)

        findings_after = _check_duplicate_fingerprints(4, list(effective_txs))
        assert findings_after == []

    def test_both_finding_types_resolved_together(self):
        txs = _canonical([
            _tx(21, "INITIAL_POSITION", "GULF.BK",   shares=1500, price=124.59, date_str="2026-05-19"),
            _tx(24, "INITIAL_POSITION", "GULF.BK",   shares=1500, price=56.25,  date_str="2026-05-19"),
            _tx(52, "BUY",              "NVDA01.BK", shares=1000, price=20.70,  date_str="2026-05-29"),
            _tx(53, "BUY",              "NVDA01.BK", shares=1000, price=20.70,  date_str="2026-05-29"),
        ])
        findings_before = (
            _check_duplicate_initial_positions(4, txs)
            + _check_duplicate_fingerprints(4, txs)
        )
        assert len(findings_before) == 2

        plan, summary = generate_repair_plan(_report(findings_before), portfolio_id=4)
        assert plan is not None
        assert len(plan.operations) == 2
        assert summary.findings_by_severity == {"CRITICAL": 1, "WARNING": 1}

        active_repairs = [
            SimpleNamespace(repair_type=op.repair_type, transaction_id=op.transaction_id)
            for op in plan.operations
        ]
        effective_txs, _ = apply_repair_overlay(tuple(txs), active_repairs)

        findings_after = (
            _check_duplicate_initial_positions(4, list(effective_txs))
            + _check_duplicate_fingerprints(4, list(effective_txs))
        )
        assert findings_after == []
