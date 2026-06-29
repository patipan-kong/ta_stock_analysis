"""Tests for services/repair_plan_executor.py — Phase 6.7D.

All tests are pure-Python and require no database or network connections.
Database objects are simulated with MagicMock / SimpleNamespace.
AsyncMock is used for validate_portfolio_ledger (async function).

Coverage
--------

load_repair_plan — schema validation
  1.  Valid plan JSON returns a fully-populated RepairPlan
  2.  File not found raises RepairPlanError
  3.  Invalid JSON raises RepairPlanError
  4.  Wrong schema_version raises RepairPlanError
  5.  Missing portfolio_id raises RepairPlanError
  6.  Zero portfolio_id raises RepairPlanError
  7.  Missing repair_plan_id raises RepairPlanError
  8.  Empty operations list raises RepairPlanError
  9.  Phase 6.8 type (SYMBOL_RENAME) raises RepairPlanError
  10. Phase 6.8 type (IMPORT_CORRECTION) raises RepairPlanError
  11. Phase 6.8 type (LEDGER_EXCEPTION) raises RepairPlanError
  12. Unknown repair_type raises RepairPlanError
  13. Missing reason raises RepairPlanError
  14. Whitespace-only reason raises RepairPlanError
  15. Non-integer transaction_id raises RepairPlanError
  16. payload_json dict is auto-serialized to JSON string
  17. SUPPRESS_FINDING is accepted
  18. Multiple operations parsed in order

apply_repair_plan — portfolio mismatch
  19. Plan portfolio_id != portfolio_id → error set, no DB writes

apply_repair_plan — dry-run
  20. dry_run=True → db.rollback() called, 0 inserted, inserted_repair_ids empty

apply_repair_plan — successful insert
  21. Single EXCLUDE op inserted and committed; inserted_repair_ids populated

apply_repair_plan — idempotency
  22. Existing active row → already_active incremented; to_insert empty
  23. All operations already active → early exit (no backup, no second validator call)
  24. Partial: one new + one already_active → only new row inserted

apply_repair_plan — backup
  25. Backup called before insert on live run
  26. Backup NOT called on dry_run
  27. Backup NOT called when all operations already active
  28. Backup failure → error set, no inserts

apply_repair_plan — effective validator
  29. Validator called twice (before and after insert)
  30. Confidence before/after populated from validator reports
  31. Validator NOT called second time on early exit (all already active)

apply_repair_plan — rollback on new CRITICALs
  32. New CRITICAL in after_report → rollback=True, 0 inserted
  33. force=True → commit despite new CRITICALs

apply_repair_plan — SUPPRESS_FINDING
  34. SUPPRESS_FINDING op inserted (repair_type stored correctly)
"""
from __future__ import annotations

import asyncio
import json
import os
import tempfile
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from services.ledger_validator import (
    FindingSeverity,
    LedgerFinding,
    LedgerValidationReport,
)
from services.repair_plan_executor import (
    RepairApplyResult,
    RepairPlan,
    RepairPlanError,
    RepairPlanOperation,
    apply_repair_plan,
    load_repair_plan,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _write_plan(tmp_dir: str, data: dict) -> str:
    """Write a dict as JSON to a temp file; return the path."""
    path = os.path.join(tmp_dir, "plan.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh)
    return path


def _valid_plan_dict(
    portfolio_id: int = 1,
    repair_plan_id: str = "plan-uuid-001",
    ops: list | None = None,
) -> dict:
    if ops is None:
        ops = [
            {
                "repair_type":    "EXCLUDE",
                "transaction_id": 10,
                "reason":         "Duplicate buy",
                "reason_code":    "DUPLICATE_SUBMISSION",
                "payload_json":   None,
            }
        ]
    return {
        "schema_version": "1.0",
        "portfolio_id":   portfolio_id,
        "repair_plan_id": repair_plan_id,
        "generated_at":   "2026-06-29T00:00:00Z",
        "operations":     ops,
    }


def _clean_report(portfolio_id: int = 1) -> LedgerValidationReport:
    """A LedgerValidationReport with no findings."""
    return LedgerValidationReport(
        portfolio_id           = portfolio_id,
        portfolio_name         = "Test",
        transactions_inspected = 5,
        findings               = [],
    )


def _critical_report(portfolio_id: int = 1, tx_id: int = 10) -> LedgerValidationReport:
    """A report with one CRITICAL finding."""
    finding = LedgerFinding(
        check_id        = "SELL_WITHOUT_HOLDING",
        severity        = FindingSeverity.CRITICAL,
        portfolio_id    = portfolio_id,
        transaction_ids = [tx_id],
        symbol          = "AAA",
        normalized_symbol = "AAA.BK",
        title           = "SELL without holding",
        explanation     = "test",
        recommendation  = "test",
    )
    return LedgerValidationReport(
        portfolio_id           = portfolio_id,
        portfolio_name         = "Test",
        transactions_inspected = 5,
        findings               = [finding],
    )


def _make_db(existing_repair=None) -> MagicMock:
    """Return a mock SQLAlchemy session.

    existing_repair: the value returned by the idempotency check (.first()).
    None  → operation will be inserted (no duplicate found).
    Any   → operation is already active (duplicate found).
    """
    db = MagicMock()
    q  = MagicMock()
    db.query.return_value = q
    q.filter.return_value = q
    q.order_by.return_value = q
    q.all.return_value   = []
    q.first.return_value = existing_repair
    return db


def _make_plan(
    portfolio_id: int = 1,
    plan_id: str = "plan-uuid-001",
    ops: list[RepairPlanOperation] | None = None,
) -> RepairPlan:
    if ops is None:
        ops = [RepairPlanOperation(
            repair_type    = "EXCLUDE",
            transaction_id = 10,
            reason         = "Duplicate buy",
        )]
    return RepairPlan(
        schema_version = "1.0",
        portfolio_id   = portfolio_id,
        repair_plan_id = plan_id,
        generated_at   = "2026-06-29T00:00:00Z",
        operations     = ops,
    )


def _run(
    plan: RepairPlan,
    db: Any | None = None,
    portfolio_id: int = 1,
    workspace_id: int = 1,
    dry_run: bool = False,
    force: bool = False,
    before_report: LedgerValidationReport | None = None,
    after_report:  LedgerValidationReport | None = None,
    existing_repair: Any = None,
    backup_path: str = "/tmp/backup.json",
    backup_raises: Exception | None = None,
) -> RepairApplyResult:
    """Run apply_repair_plan with common mocks pre-wired."""
    if db is None:
        db = _make_db(existing_repair)
    if before_report is None:
        before_report = _clean_report(portfolio_id)
    if after_report is None:
        after_report = _clean_report(portfolio_id)

    mock_validator = AsyncMock(side_effect=[before_report, after_report])
    mock_load_repairs = MagicMock(return_value=[])

    def mock_backup(db_, pid):
        if backup_raises:
            raise backup_raises
        return backup_path

    with (
        patch("services.repair_plan_executor.validate_portfolio_ledger", mock_validator),
        patch("services.repair_plan_executor.load_active_repairs",        mock_load_repairs),
        patch("services.repair_plan_executor._backup_repairs",            side_effect=mock_backup),
    ):
        return asyncio.run(apply_repair_plan(
            db           = db,
            plan         = plan,
            portfolio_id = portfolio_id,
            workspace_id = workspace_id,
            dry_run      = dry_run,
            force        = force,
        ))


# ──────────────────────────────────────────────────────────────────────────────
# Tests — load_repair_plan
# ──────────────────────────────────────────────────────────────────────────────

def test_load_repair_plan_valid():
    """Valid JSON returns a fully-populated RepairPlan."""
    with tempfile.TemporaryDirectory() as tmp:
        path = _write_plan(tmp, _valid_plan_dict())
        plan = load_repair_plan(path)
    assert isinstance(plan, RepairPlan)
    assert plan.schema_version == "1.0"
    assert plan.portfolio_id   == 1
    assert plan.repair_plan_id == "plan-uuid-001"
    assert plan.generated_at   == "2026-06-29T00:00:00Z"
    assert len(plan.operations) == 1
    op = plan.operations[0]
    assert op.repair_type    == "EXCLUDE"
    assert op.transaction_id == 10
    assert op.reason         == "Duplicate buy"
    assert op.reason_code    == "DUPLICATE_SUBMISSION"
    assert op.payload_json is None


def test_load_repair_plan_file_not_found():
    with pytest.raises(RepairPlanError, match="not found"):
        load_repair_plan("/no/such/file.json")


def test_load_repair_plan_invalid_json():
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "bad.json")
        with open(path, "w") as fh:
            fh.write("{ not valid json }")
        with pytest.raises(RepairPlanError, match="invalid JSON"):
            load_repair_plan(path)


def test_load_repair_plan_wrong_schema_version():
    with tempfile.TemporaryDirectory() as tmp:
        data = _valid_plan_dict()
        data["schema_version"] = "2.0"
        path = _write_plan(tmp, data)
        with pytest.raises(RepairPlanError, match="schema_version"):
            load_repair_plan(path)


def test_load_repair_plan_missing_portfolio_id():
    with tempfile.TemporaryDirectory() as tmp:
        data = _valid_plan_dict()
        del data["portfolio_id"]
        path = _write_plan(tmp, data)
        with pytest.raises(RepairPlanError, match="portfolio_id"):
            load_repair_plan(path)


def test_load_repair_plan_zero_portfolio_id():
    with tempfile.TemporaryDirectory() as tmp:
        data = _valid_plan_dict(portfolio_id=0)
        path = _write_plan(tmp, data)
        with pytest.raises(RepairPlanError, match="portfolio_id"):
            load_repair_plan(path)


def test_load_repair_plan_missing_repair_plan_id():
    with tempfile.TemporaryDirectory() as tmp:
        data = _valid_plan_dict()
        del data["repair_plan_id"]
        path = _write_plan(tmp, data)
        with pytest.raises(RepairPlanError, match="repair_plan_id"):
            load_repair_plan(path)


def test_load_repair_plan_empty_operations():
    with tempfile.TemporaryDirectory() as tmp:
        data = _valid_plan_dict(ops=[])
        path = _write_plan(tmp, data)
        with pytest.raises(RepairPlanError, match="empty"):
            load_repair_plan(path)


def test_load_repair_plan_symbol_rename_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        data = _valid_plan_dict(ops=[{
            "repair_type": "SYMBOL_RENAME", "transaction_id": 1,
            "reason": "alias",
        }])
        path = _write_plan(tmp, data)
        with pytest.raises(RepairPlanError, match="Phase 6.8"):
            load_repair_plan(path)


def test_load_repair_plan_import_correction_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        data = _valid_plan_dict(ops=[{
            "repair_type": "IMPORT_CORRECTION", "transaction_id": 1,
            "reason": "fix import",
        }])
        path = _write_plan(tmp, data)
        with pytest.raises(RepairPlanError, match="Phase 6.8"):
            load_repair_plan(path)


def test_load_repair_plan_ledger_exception_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        data = _valid_plan_dict(ops=[{
            "repair_type": "LEDGER_EXCEPTION", "transaction_id": 1,
            "reason": "exception",
        }])
        path = _write_plan(tmp, data)
        with pytest.raises(RepairPlanError, match="Phase 6.8"):
            load_repair_plan(path)


def test_load_repair_plan_unknown_type_rejected():
    with tempfile.TemporaryDirectory() as tmp:
        data = _valid_plan_dict(ops=[{
            "repair_type": "MAGIC_FIX", "transaction_id": 1, "reason": "test",
        }])
        path = _write_plan(tmp, data)
        with pytest.raises(RepairPlanError, match="valid repair type"):
            load_repair_plan(path)


def test_load_repair_plan_missing_reason():
    with tempfile.TemporaryDirectory() as tmp:
        data = _valid_plan_dict(ops=[{
            "repair_type": "EXCLUDE", "transaction_id": 1,
        }])
        path = _write_plan(tmp, data)
        with pytest.raises(RepairPlanError, match="reason"):
            load_repair_plan(path)


def test_load_repair_plan_whitespace_reason():
    with tempfile.TemporaryDirectory() as tmp:
        data = _valid_plan_dict(ops=[{
            "repair_type": "EXCLUDE", "transaction_id": 1, "reason": "   ",
        }])
        path = _write_plan(tmp, data)
        with pytest.raises(RepairPlanError, match="reason"):
            load_repair_plan(path)


def test_load_repair_plan_non_integer_tx_id():
    with tempfile.TemporaryDirectory() as tmp:
        data = _valid_plan_dict(ops=[{
            "repair_type": "EXCLUDE", "transaction_id": "abc", "reason": "test",
        }])
        path = _write_plan(tmp, data)
        with pytest.raises(RepairPlanError, match="transaction_id"):
            load_repair_plan(path)


def test_load_repair_plan_payload_dict_auto_serialized():
    """Dict payload_json is auto-serialized to a JSON string."""
    with tempfile.TemporaryDirectory() as tmp:
        data = _valid_plan_dict(ops=[{
            "repair_type":    "EXCLUDE",
            "transaction_id": 5,
            "reason":         "test",
            "payload_json":   {"keep_tx_id": 52},
        }])
        path = _write_plan(tmp, data)
        plan = load_repair_plan(path)
    pj = plan.operations[0].payload_json
    assert isinstance(pj, str)
    assert json.loads(pj) == {"keep_tx_id": 52}


def test_load_repair_plan_suppress_finding_accepted():
    with tempfile.TemporaryDirectory() as tmp:
        data = _valid_plan_dict(ops=[{
            "repair_type":    "SUPPRESS_FINDING",
            "transaction_id": 7,
            "reason":         "known safe",
            "reason_code":    "DUP_TX_FINGERPRINT",
        }])
        path = _write_plan(tmp, data)
        plan = load_repair_plan(path)
    assert plan.operations[0].repair_type == "SUPPRESS_FINDING"
    assert plan.operations[0].reason_code  == "DUP_TX_FINGERPRINT"


def test_load_repair_plan_multiple_operations():
    ops = [
        {"repair_type": "EXCLUDE",          "transaction_id": 1, "reason": "dup"},
        {"repair_type": "SUPPRESS_FINDING", "transaction_id": 2, "reason": "safe"},
    ]
    with tempfile.TemporaryDirectory() as tmp:
        path = _write_plan(tmp, _valid_plan_dict(ops=ops))
        plan = load_repair_plan(path)
    assert len(plan.operations) == 2
    assert plan.operations[0].repair_type == "EXCLUDE"
    assert plan.operations[1].repair_type == "SUPPRESS_FINDING"


# ──────────────────────────────────────────────────────────────────────────────
# Tests — apply_repair_plan
# ──────────────────────────────────────────────────────────────────────────────

def test_apply_repair_portfolio_id_mismatch():
    """plan.portfolio_id != portfolio_id → error, no DB writes."""
    plan = _make_plan(portfolio_id=99)
    db   = MagicMock()
    result = _run(plan=plan, db=db, portfolio_id=1)
    assert result.error is not None
    assert "portfolio_id" in result.error
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_apply_repair_dry_run_no_commit():
    """dry_run=True → rollback called, 0 rows inserted."""
    plan   = _make_plan()
    result = _run(plan=plan, dry_run=True)
    assert result.dry_run             is True
    assert result.operations_inserted == 0
    assert result.inserted_repair_ids == []
    assert result.error is None


def test_apply_repair_inserts_new_repair():
    """Single EXCLUDE op: inserted and committed; repair ID in result."""
    plan   = _make_plan()
    db     = _make_db(existing_repair=None)

    # Give the flushed row a mock id.
    inserted_row = MagicMock()
    inserted_row.id = 42
    db.add.side_effect = None

    # After flush, our new_rows list will have the actual LedgerRepair object.
    # Simulate by tracking db.add calls and setting id on the first added object.
    added_rows: list = []
    def _add(row):
        row.id = 42
        added_rows.append(row)
    db.add.side_effect = _add

    result = _run(plan=plan, db=db, dry_run=False)

    assert result.error              is None
    assert result.rollback           is False
    assert result.operations_inserted == 1
    assert 42 in result.inserted_repair_ids
    db.commit.assert_called_once()


def test_apply_repair_idempotency_already_active():
    """Existing active row → already_active=1, nothing inserted."""
    plan     = _make_plan()
    existing = MagicMock()  # non-None → duplicate found
    result   = _run(plan=plan, existing_repair=existing)
    assert result.already_active        == 1
    assert result.operations_inserted   == 0
    assert result.inserted_repair_ids   == []


def test_apply_repair_all_already_active_early_exit():
    """All ops already active → no backup, validator called only once."""
    plan     = _make_plan()
    existing = MagicMock()

    mock_validator    = AsyncMock(return_value=_clean_report())
    mock_load_repairs = MagicMock(return_value=[])
    mock_backup       = MagicMock()
    db                = _make_db(existing_repair=existing)

    with (
        patch("services.repair_plan_executor.validate_portfolio_ledger", mock_validator),
        patch("services.repair_plan_executor.load_active_repairs",        mock_load_repairs),
        patch("services.repair_plan_executor._backup_repairs",            mock_backup),
    ):
        result = asyncio.run(apply_repair_plan(
            db=db, plan=plan, portfolio_id=1, workspace_id=1, dry_run=False,
        ))

    assert result.already_active      == 1
    assert result.operations_inserted == 0
    mock_backup.assert_not_called()
    assert mock_validator.call_count  == 1  # only the baseline call


def test_apply_repair_partial_already_active():
    """One new op + one already active → only the new one inserted."""
    ops = [
        RepairPlanOperation("EXCLUDE",          10, "dup buy"),
        RepairPlanOperation("SUPPRESS_FINDING", 20, "safe"),
    ]
    plan = _make_plan(ops=ops)

    # First call returns None (new), second returns something (duplicate).
    db = MagicMock()
    q  = MagicMock()
    db.query.return_value = q
    q.filter.return_value = q
    q.order_by.return_value = q
    q.all.return_value   = []

    first_op_new  = [None, MagicMock()]  # tx_id=10 → new; tx_id=20 → duplicate
    call_count    = [0]
    def _first():
        v = first_op_new[call_count[0] % len(first_op_new)]
        call_count[0] += 1
        return v
    q.first.side_effect = _first

    added_rows: list = []
    def _add(row):
        row.id = 99
        added_rows.append(row)
    db.add.side_effect = _add

    result = _run(plan=plan, db=db, dry_run=False)

    assert result.operations_inserted == 1
    assert result.already_active      == 1
    assert len(added_rows)            == 1
    assert added_rows[0].repair_type  == "EXCLUDE"


def test_apply_repair_backup_called_on_live_run():
    """Backup function is called once before insert on a live run."""
    plan       = _make_plan()
    mock_backup = MagicMock(return_value="/tmp/bak.json")

    with (
        patch("services.repair_plan_executor.validate_portfolio_ledger",
              AsyncMock(side_effect=[_clean_report(), _clean_report()])),
        patch("services.repair_plan_executor.load_active_repairs", MagicMock(return_value=[])),
        patch("services.repair_plan_executor._backup_repairs", mock_backup),
    ):
        result = asyncio.run(apply_repair_plan(
            db=_make_db(), plan=plan, portfolio_id=1, workspace_id=1, dry_run=False,
        ))

    mock_backup.assert_called_once()
    assert result.backup_path == "/tmp/bak.json"


def test_apply_repair_backup_not_called_on_dry_run():
    """Backup is skipped when dry_run=True."""
    plan       = _make_plan()
    mock_backup = MagicMock(return_value="/tmp/bak.json")

    with (
        patch("services.repair_plan_executor.validate_portfolio_ledger",
              AsyncMock(side_effect=[_clean_report(), _clean_report()])),
        patch("services.repair_plan_executor.load_active_repairs", MagicMock(return_value=[])),
        patch("services.repair_plan_executor._backup_repairs", mock_backup),
    ):
        asyncio.run(apply_repair_plan(
            db=_make_db(), plan=plan, portfolio_id=1, workspace_id=1, dry_run=True,
        ))

    mock_backup.assert_not_called()


def test_apply_repair_backup_failure_aborts():
    """Backup exception → error set, no rows inserted, no commit."""
    plan   = _make_plan()
    db     = _make_db()
    result = _run(
        plan=plan, db=db, dry_run=False,
        backup_raises=OSError("disk full"),
    )
    assert result.error is not None
    assert "Backup failed" in result.error
    assert result.operations_inserted == 0
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_apply_repair_effective_validator_called_twice():
    """validate_portfolio_ledger is called before and after insert."""
    plan          = _make_plan()
    mock_validator = AsyncMock(side_effect=[_clean_report(), _clean_report()])

    with (
        patch("services.repair_plan_executor.validate_portfolio_ledger", mock_validator),
        patch("services.repair_plan_executor.load_active_repairs", MagicMock(return_value=[])),
        patch("services.repair_plan_executor._backup_repairs",     MagicMock(return_value="/b")),
    ):
        asyncio.run(apply_repair_plan(
            db=_make_db(), plan=plan, portfolio_id=1, workspace_id=1, dry_run=False,
        ))

    assert mock_validator.call_count == 2
    # Both calls must pass mode="effective"
    for c in mock_validator.call_args_list:
        assert c.kwargs.get("mode") == "effective"


def test_apply_repair_confidence_populated():
    """confidence_before and confidence_after are set from the two reports."""
    plan = _make_plan()
    # Before: 0 findings → 100%. After: 0 findings → 100%.
    result = _run(plan=plan, dry_run=True)
    assert result.confidence_before == 100.0
    assert result.confidence_after  == 100.0
    assert result.effective_before  is not None
    assert result.effective_after   is not None


def test_apply_repair_rollback_on_new_criticals():
    """New CRITICAL after insert → db.rollback(), rollback=True, 0 inserted."""
    plan         = _make_plan()
    db           = _make_db()
    after_report = _critical_report()    # introduces one CRITICAL

    result = _run(plan=plan, db=db, dry_run=False, after_report=after_report)

    assert result.rollback           is True
    assert "CRITICAL" in result.rollback_reason
    assert result.operations_inserted == 0
    assert result.inserted_repair_ids == []
    db.rollback.assert_called()
    db.commit.assert_not_called()


def test_apply_repair_force_bypasses_rollback():
    """force=True → commit even when new CRITICALs appear."""
    plan         = _make_plan()
    db           = _make_db()
    after_report = _critical_report()

    added_rows: list = []
    def _add(row):
        row.id = 77
        added_rows.append(row)
    db.add.side_effect = _add

    result = _run(plan=plan, db=db, dry_run=False, force=True, after_report=after_report)

    assert result.rollback           is False
    assert result.operations_inserted == 1
    db.commit.assert_called_once()
    db.rollback.assert_not_called()


def test_apply_repair_suppress_finding_repair_type_stored():
    """SUPPRESS_FINDING operation produces a row with repair_type=SUPPRESS_FINDING."""
    ops  = [RepairPlanOperation("SUPPRESS_FINDING", 7, "known safe", "DUP_TX_FINGERPRINT")]
    plan = _make_plan(ops=ops)
    db   = _make_db()

    added_rows: list = []
    def _add(row):
        row.id = 55
        added_rows.append(row)
    db.add.side_effect = _add

    result = _run(plan=plan, db=db, dry_run=False)

    assert result.operations_inserted == 1
    assert len(added_rows)            == 1
    assert added_rows[0].repair_type  == "SUPPRESS_FINDING"
    assert added_rows[0].reason_code  == "DUP_TX_FINGERPRINT"


def test_apply_repair_no_new_criticals_does_not_rollback():
    """When criticals stay the same (both 0), no rollback is triggered."""
    plan   = _make_plan()
    db     = _make_db()
    result = _run(plan=plan, db=db, dry_run=False)
    assert result.rollback is False
    db.commit.assert_called_once()


def test_apply_repair_existing_critical_not_treated_as_new():
    """A CRITICAL present both before and after does NOT trigger rollback."""
    plan          = _make_plan()
    db            = _make_db()
    crit          = _critical_report()
    result        = _run(
        plan=plan, db=db, dry_run=False,
        before_report=crit, after_report=crit,   # same finding in both
    )
    assert result.rollback is False
    db.commit.assert_called_once()


def test_apply_repair_repair_ids_empty_on_dry_run():
    """inserted_repair_ids is always empty after a dry-run."""
    plan   = _make_plan()
    result = _run(plan=plan, dry_run=True)
    assert result.inserted_repair_ids == []
    assert result.operations_inserted  == 0
