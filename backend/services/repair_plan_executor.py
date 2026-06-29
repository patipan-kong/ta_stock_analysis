"""Durable repair plan execution — Phase 6.7D.

Public API
----------
RepairPlanError
    Raised when a plan file fails schema or logic validation.
RepairPlanOperation
    One operation from the plan JSON (repair_type, transaction_id, reason, …).
RepairPlan
    Fully-validated plan loaded from disk.
RepairApplyResult
    Per-run outcome: operation counts, rollback state, validator reports,
    confidence before/after.
load_repair_plan(path) -> RepairPlan
    Load and validate a JSON repair plan file.
apply_repair_plan(db, plan, portfolio_id, workspace_id, dry_run, force)
    -> RepairApplyResult (async)
    Apply the plan: backup → idempotency check → insert → validate →
    commit or rollback.

Design constraints
------------------
* Transaction rows are NEVER modified.  All access to the Transaction table
  is strictly read-only.  Only LedgerRepair rows are written.
* CanonicalTransaction objects are never mutated.
* Only EXCLUDE and SUPPRESS_FINDING are supported in Phase 6.7D.
  SYMBOL_RENAME, IMPORT_CORRECTION, LEDGER_EXCEPTION → RepairPlanError
  (deferred to Phase 6.8).
* Inserts are idempotent: an existing active row with the same
  (portfolio_id, repair_plan_id, transaction_id, repair_type) is counted as
  already_active — not re-inserted.
* All inserts execute inside one DB transaction; rolled back unconditionally
  when new CRITICAL findings appear after insertion (unless force=True).
* Backup is written before any insert; backup failure aborts the apply.
* LedgerRepair is append-only: no UPDATE or DELETE issued by this module.
  Deactivation (is_active=False) belongs to Phase 6.8 admin paths.

RepairPlan JSON schema (schema_version "1.0")
---------------------------------------------
{
    "schema_version": "1.0",
    "portfolio_id":   4,
    "repair_plan_id": "<uuid>",
    "generated_at":   "<ISO-8601>",
    "operations": [
        {
            "repair_type":    "EXCLUDE",
            "transaction_id": 42,
            "reason":         "Duplicate buy transaction",
            "reason_code":    "DUPLICATE_SUBMISSION",
            "payload_json":   null
        }
    ]
}
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from models.database import LedgerRepair
from services.ledger_repair import load_active_repairs
from services.ledger_validator import (
    LedgerValidationReport,
    _finding_key,
    _ledger_confidence,
    validate_portfolio_ledger,
)

_log = logging.getLogger(__name__)

# Repair types supported in Phase 6.7D.
_PHASE_67D_SUPPORTED: frozenset[str] = frozenset({"EXCLUDE", "SUPPRESS_FINDING"})

# Repair types reserved for Phase 6.8 — rejected with an informative message.
_PHASE_68_DEFERRED: frozenset[str] = frozenset({
    "SYMBOL_RENAME",
    "IMPORT_CORRECTION",
    "LEDGER_EXCEPTION",
})

_SCHEMA_VERSION = "1.0"


# ── Public exceptions ─────────────────────────────────────────────────────────

class RepairPlanError(ValueError):
    """Raised when a repair plan file fails schema or logic validation."""


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class RepairPlanOperation:
    """One operation entry from the plan JSON."""
    repair_type:    str
    transaction_id: int | None
    reason:         str
    reason_code:    str | None = None
    payload_json:   str | None = None


@dataclass
class RepairPlan:
    """Fully validated repair plan loaded from a JSON file."""
    schema_version: str
    portfolio_id:   int
    repair_plan_id: str
    generated_at:   str
    operations:     list[RepairPlanOperation] = field(default_factory=list)


@dataclass
class RepairApplyResult:
    """Outcome of one apply_repair_plan() call."""
    portfolio_id:         int
    repair_plan_id:       str
    dry_run:              bool
    # Operation counts
    operations_requested: int                         = 0
    operations_inserted:  int                         = 0
    already_active:       int                         = 0
    skipped:              int                         = 0
    # Rollback
    rollback:             bool                        = False
    rollback_reason:      str                         = ""
    # Validator reports
    effective_before:     LedgerValidationReport | None = None
    effective_after:      LedgerValidationReport | None = None
    # Confidence scores
    confidence_before:    float                       = 0.0
    confidence_after:     float                       = 0.0
    # Backup
    backup_path:          str | None                  = None
    # Inserted row IDs (empty when dry_run or rollback)
    inserted_repair_ids:  list[int]                   = field(default_factory=list)
    # Fatal error (pre-insert failures: portfolio mismatch, backup failure)
    error:                str | None                  = None


# ── Internal backup wrapper ───────────────────────────────────────────────────

def _backup_repairs(db: Any, portfolio_id: int) -> str:
    """Export current portfolio state to JSON backup using the rebuild pipeline.

    Wraps the private _export_backup from portfolio_rebuilder so tests can
    patch 'services.repair_plan_executor._backup_repairs' without touching
    the rebuilder module.
    """
    from services.portfolio_rebuilder import _export_backup
    return _export_backup(db, portfolio_id)


# ── Plan loader ───────────────────────────────────────────────────────────────

def load_repair_plan(path: str) -> RepairPlan:
    """Load and validate a RepairPlan JSON file.

    Raises:
        RepairPlanError: If the file is missing, contains invalid JSON, or
                         fails schema validation (missing fields, wrong types,
                         unsupported repair_type, empty operations list, …).
    """
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        raise RepairPlanError(f"Plan file not found: {path}")
    except json.JSONDecodeError as exc:
        raise RepairPlanError(f"Plan file contains invalid JSON: {exc}")

    if not isinstance(data, dict):
        raise RepairPlanError("Plan must be a JSON object")

    # ── schema_version ────────────────────────────────────────────────────────
    sv = data.get("schema_version")
    if sv != _SCHEMA_VERSION:
        raise RepairPlanError(
            f"Unsupported schema_version {sv!r}; expected {_SCHEMA_VERSION!r}"
        )

    # ── portfolio_id ──────────────────────────────────────────────────────────
    pid = data.get("portfolio_id")
    if not isinstance(pid, int) or pid <= 0:
        raise RepairPlanError("portfolio_id must be a positive integer")

    # ── repair_plan_id ────────────────────────────────────────────────────────
    rpid = data.get("repair_plan_id")
    if not isinstance(rpid, str) or not rpid.strip():
        raise RepairPlanError("repair_plan_id must be a non-empty string")

    # ── operations ────────────────────────────────────────────────────────────
    ops_raw = data.get("operations")
    if not isinstance(ops_raw, list):
        raise RepairPlanError("operations must be a list")
    if not ops_raw:
        raise RepairPlanError("operations list must not be empty")

    operations: list[RepairPlanOperation] = []
    for i, op in enumerate(ops_raw):
        if not isinstance(op, dict):
            raise RepairPlanError(f"operations[{i}] must be a JSON object")

        rt = op.get("repair_type")
        if not isinstance(rt, str):
            raise RepairPlanError(
                f"operations[{i}].repair_type must be a string"
            )
        if rt in _PHASE_68_DEFERRED:
            raise RepairPlanError(
                f"operations[{i}].repair_type={rt!r} is deferred to Phase 6.8 "
                f"and not supported in Phase 6.7D"
            )
        if rt not in _PHASE_67D_SUPPORTED:
            raise RepairPlanError(
                f"operations[{i}].repair_type={rt!r} is not a valid repair type"
            )

        reason = op.get("reason", "")
        if not isinstance(reason, str) or not reason.strip():
            raise RepairPlanError(
                f"operations[{i}].reason must be a non-empty string"
            )

        tx_id = op.get("transaction_id")
        if tx_id is not None and not isinstance(tx_id, int):
            raise RepairPlanError(
                f"operations[{i}].transaction_id must be an integer or null"
            )

        # payload_json: accept a pre-serialized string or auto-serialize dict/list.
        pj = op.get("payload_json")
        if pj is not None and not isinstance(pj, str):
            pj = json.dumps(pj)

        operations.append(RepairPlanOperation(
            repair_type    = rt,
            transaction_id = tx_id,
            reason         = reason,
            reason_code    = op.get("reason_code") or None,
            payload_json   = pj,
        ))

    return RepairPlan(
        schema_version = sv,
        portfolio_id   = pid,
        repair_plan_id = rpid,
        generated_at   = data.get("generated_at", ""),
        operations     = operations,
    )


# ── Plan executor ─────────────────────────────────────────────────────────────

async def apply_repair_plan(
    db:           Any,
    plan:         RepairPlan,
    portfolio_id: int,
    workspace_id: int,
    dry_run:      bool = True,
    force:        bool = False,
) -> RepairApplyResult:
    """Apply a validated repair plan to the database.

    Writes LedgerRepair rows only.  Transaction rows are never modified.

    Execution sequence
    ------------------
    1.  Cross-check plan.portfolio_id == portfolio_id.
    2.  Run effective validator baseline (current active repairs, before any
        new inserts).
    3.  Per-operation idempotency: existing active row with the same
        (portfolio_id, repair_plan_id, transaction_id, repair_type) → already_active.
    4.  Early exit when every operation is already active (no backup needed).
    5.  Pre-insert backup (when not dry_run).  Failure aborts the apply.
    6.  Insert new LedgerRepair rows + db.flush() (within-session visibility).
    7.  Run effective validator post-insert.
    8.  Rollback check: if new CRITICAL findings appear and not force → rollback.
    9.  Dry-run path: db.rollback() (counts reset to 0, no permanent writes).
    10. Live path: db.commit().

    Args:
        db:           SQLAlchemy Session (caller manages lifecycle).
        plan:         Validated RepairPlan from load_repair_plan().
        portfolio_id: Target portfolio.  Must match plan.portfolio_id.
        workspace_id: Forwarded to validate_portfolio_ledger().
        dry_run:      Run all stages but roll back at step 9.
        force:        When True, skip the rollback check at step 8
                      (commit even if new CRITICALs appear).

    Returns:
        RepairApplyResult — never raises; fatal errors are stored in result.error.
    """
    result = RepairApplyResult(
        portfolio_id         = portfolio_id,
        repair_plan_id       = plan.repair_plan_id,
        dry_run              = dry_run,
        operations_requested = len(plan.operations),
    )

    # ── 1. Portfolio ID cross-check ───────────────────────────────────────────
    if plan.portfolio_id != portfolio_id:
        result.error = (
            f"Plan portfolio_id={plan.portfolio_id} does not match "
            f"--portfolio {portfolio_id}"
        )
        return result

    # ── 2. Baseline effective validation (before any inserts) ─────────────────
    current_repairs = load_active_repairs(db, portfolio_id)
    before_report = await validate_portfolio_ledger(
        db           = db,
        portfolio_id = portfolio_id,
        workspace_id = workspace_id,
        repairs      = current_repairs,
        mode         = "effective",
    )
    result.effective_before  = before_report
    result.confidence_before = _ledger_confidence(before_report)

    # ── 3. Per-operation idempotency check ────────────────────────────────────
    to_insert: list[RepairPlanOperation] = []
    for op in plan.operations:
        existing = (
            db.query(LedgerRepair)
            .filter(
                LedgerRepair.portfolio_id   == portfolio_id,
                LedgerRepair.repair_plan_id == plan.repair_plan_id,
                LedgerRepair.transaction_id == op.transaction_id,
                LedgerRepair.repair_type    == op.repair_type,
                LedgerRepair.is_active.is_(True),
            )
            .first()
        )
        if existing is not None:
            result.already_active += 1
        else:
            to_insert.append(op)

    # ── 4. Early exit when all operations already active ──────────────────────
    if not to_insert:
        result.effective_after  = before_report
        result.confidence_after = result.confidence_before
        return result

    # ── 5. Pre-insert backup ──────────────────────────────────────────────────
    if not dry_run:
        try:
            result.backup_path = _backup_repairs(db, portfolio_id)
        except Exception as exc:
            _log.error(
                "apply_repair backup failed portfolio=%d: %s", portfolio_id, exc
            )
            result.error = f"Backup failed (apply aborted): {exc}"
            return result

    # ── 6. Insert new LedgerRepair rows + flush ───────────────────────────────
    now = datetime.utcnow()
    new_rows: list[LedgerRepair] = []
    for op in to_insert:
        row = LedgerRepair(
            portfolio_id   = portfolio_id,
            transaction_id = op.transaction_id,
            repair_plan_id = plan.repair_plan_id,
            repair_type    = op.repair_type,
            reason         = op.reason,
            reason_code    = op.reason_code,
            payload_json   = op.payload_json,
            created_by     = "manage.py:apply_repair",
            created_at     = now,
            is_active      = True,
        )
        db.add(row)
        new_rows.append(row)

    db.flush()  # write within this session; not yet committed to persistent storage

    for row in new_rows:
        result.inserted_repair_ids.append(row.id)
    result.operations_inserted = len(new_rows)

    # ── 7. Post-insert effective validation ───────────────────────────────────
    updated_repairs = load_active_repairs(db, portfolio_id)
    after_report = await validate_portfolio_ledger(
        db           = db,
        portfolio_id = portfolio_id,
        workspace_id = workspace_id,
        repairs      = updated_repairs,
        mode         = "effective",
    )
    result.effective_after  = after_report
    result.confidence_after = _ledger_confidence(after_report)

    # ── 8. Rollback check: abort on newly introduced CRITICAL findings ─────────
    before_crit_keys: set[str] = {
        _finding_key(f) for f in before_report.criticals
    }
    after_crit_keys: set[str] = {
        _finding_key(f) for f in after_report.criticals
    }
    new_critical_keys = after_crit_keys - before_crit_keys

    if new_critical_keys and not force:
        db.rollback()
        result.rollback        = True
        result.rollback_reason = (
            f"{len(new_critical_keys)} new CRITICAL finding(s) introduced; "
            f"use --force to override"
        )
        result.operations_inserted = 0
        result.inserted_repair_ids = []
        return result

    # ── 9 / 10. Dry-run rollback or live commit ───────────────────────────────
    if dry_run:
        db.rollback()
        result.operations_inserted = 0
        result.inserted_repair_ids = []
    else:
        db.commit()
        _log.info(
            "apply_repair committed portfolio=%d plan=%s inserted=%d",
            portfolio_id, plan.repair_plan_id, len(new_rows),
        )

    return result
