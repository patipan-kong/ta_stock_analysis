"""Deterministic repair plan generator — Phase 6.7E.

Public API
----------
GenerationSummary
    Counts of generated operations, skipped findings (by check_id), and
    findings already covered by an active repair.
generate_repair_plan(report, portfolio_id, active_repairs=None, ...)
    -> (RepairPlan | None, GenerationSummary)
    Pure function — no database access, no file I/O.  Inspects a
    LedgerValidationReport and produces a RepairPlan covering only the
    100%-deterministic findings (DUP_INITIAL_POSITION, DUP_TX_FINGERPRINT).
    Returns (None, summary) when there is nothing to generate.
repair_plan_to_dict(plan) -> dict
    Serialize a RepairPlan to the JSON-compatible dict consumed by
    load_repair_plan() / apply_repair.
write_repair_plan(plan, path) -> None
    Write repair_plan_to_dict(plan) to a JSON file.  The only I/O this
    module performs — never touches the database.

Workflow
--------
    validate_ledger  →  generate_repair_plan  →  human review  →  apply_repair

Design constraints
-------------------
* Read-only with respect to the database: this module never queries or
  writes the DB.  Callers pass in an already-computed LedgerValidationReport
  and (optionally) the portfolio's active LedgerRepair rows.
* Auto-repairable check_ids: DUP_INITIAL_POSITION, DUP_TX_FINGERPRINT only.
  Every other check_id is reported in GenerationSummary.skipped_by_check_id
  and never turned into a repair operation — those findings require human
  review (symbol aliases, negative balances, price/holdings mismatches, …).
* Within each duplicate group, the earliest transaction (lowest id) is kept;
  every other transaction in the group is EXCLUDEd.  Nothing is ever deleted.
* Idempotent: a transaction already covered by an active EXCLUDE repair is
  skipped rather than re-included in the generated plan.
* Reuses the RepairPlan / RepairPlanOperation schema from
  services.repair_plan_executor — does not invent a new format.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from services.ledger_validator import LedgerFinding, LedgerValidationReport
from services.repair_plan_executor import RepairPlan, RepairPlanOperation

# check_ids eligible for fully-deterministic auto-repair (Phase 6.7E).
AUTO_REPAIRABLE_CHECK_IDS: frozenset[str] = frozenset({
    "DUP_INITIAL_POSITION",
    "DUP_TX_FINGERPRINT",
})

_SCHEMA_VERSION = "1.0"


@dataclass
class GenerationSummary:
    """Counts produced while scanning a LedgerValidationReport."""
    portfolio_id:         int
    findings_by_severity: dict[str, int] = field(default_factory=dict)
    generated_by_type:    dict[str, int] = field(default_factory=dict)
    skipped_by_check_id:  dict[str, int] = field(default_factory=dict)
    already_active:       int            = 0


def _active_excluded_tx_ids(active_repairs: list[Any] | None) -> set[int]:
    """transaction_ids already covered by an active EXCLUDE repair."""
    return {
        r.transaction_id
        for r in (active_repairs or [])
        if getattr(r, "repair_type", None) == "EXCLUDE"
        and getattr(r, "transaction_id", None) is not None
    }


def _operations_for_duplicate_finding(
    finding: LedgerFinding,
    already_excluded: set[int],
) -> tuple[list[RepairPlanOperation], int]:
    """Build EXCLUDE operations for one DUP_INITIAL_POSITION / DUP_TX_FINGERPRINT finding.

    Keeps the earliest transaction (lowest id) in the group; EXCLUDEs the
    rest.  Transactions already covered by an active EXCLUDE repair are
    counted as already_active and skipped instead of being regenerated.

    Returns:
        (operations, already_active_count)
    """
    tx_ids = sorted(finding.transaction_ids)
    if len(tx_ids) <= 1:
        return [], 0

    keep_id, *duplicate_ids = tx_ids

    operations: list[RepairPlanOperation] = []
    already_active = 0
    for tx_id in duplicate_ids:
        if tx_id in already_excluded:
            already_active += 1
            continue
        operations.append(RepairPlanOperation(
            repair_type    = "EXCLUDE",
            transaction_id = tx_id,
            reason         = f"{finding.title} — duplicate of tx{keep_id}, the earliest record.",
            reason_code    = finding.check_id,
            payload_json   = json.dumps({"keep_tx_id": keep_id}),
        ))
    return operations, already_active


def generate_repair_plan(
    report:          LedgerValidationReport,
    portfolio_id:    int,
    *,
    active_repairs:  list[Any] | None = None,
    repair_plan_id:  str | None       = None,
    generated_at:    str | None       = None,
) -> tuple[RepairPlan | None, GenerationSummary]:
    """Generate a deterministic repair plan from a validation report.

    Pure function: no database access, no file I/O, no side effects.

    Args:
        report:         LedgerValidationReport produced by validate_portfolio_ledger().
        portfolio_id:   Target portfolio (must match report.portfolio_id).
        active_repairs: Currently-active LedgerRepair rows for this portfolio
                        (e.g. from load_active_repairs()).  Used to skip
                        transactions already covered by an active EXCLUDE
                        repair, so re-running the generator is idempotent.
        repair_plan_id: Override the generated plan's UUID (tests only).
        generated_at:   Override the generated_at timestamp (tests only).

    Returns:
        (plan, summary). plan is None when no deterministic repair could be
        generated (clean ledger, or every duplicate already excluded) —
        summary still reflects what was found/skipped.
    """
    summary = GenerationSummary(portfolio_id=portfolio_id)
    for f in report.findings:
        summary.findings_by_severity[f.severity.value] = (
            summary.findings_by_severity.get(f.severity.value, 0) + 1
        )

    already_excluded = _active_excluded_tx_ids(active_repairs)

    operations: list[RepairPlanOperation] = []
    for finding in report.findings:
        if finding.check_id not in AUTO_REPAIRABLE_CHECK_IDS:
            summary.skipped_by_check_id[finding.check_id] = (
                summary.skipped_by_check_id.get(finding.check_id, 0) + 1
            )
            continue

        ops, already_active = _operations_for_duplicate_finding(finding, already_excluded)
        summary.already_active += already_active
        operations.extend(ops)

    if operations:
        for op in operations:
            summary.generated_by_type[op.repair_type] = (
                summary.generated_by_type.get(op.repair_type, 0) + 1
            )

    if not operations:
        return None, summary

    plan = RepairPlan(
        schema_version = _SCHEMA_VERSION,
        portfolio_id   = portfolio_id,
        repair_plan_id = repair_plan_id or str(uuid.uuid4()),
        generated_at   = generated_at or (datetime.utcnow().isoformat() + "Z"),
        operations     = operations,
    )
    return plan, summary


def repair_plan_to_dict(plan: RepairPlan) -> dict[str, Any]:
    """Serialize a RepairPlan to the dict accepted by load_repair_plan()."""
    return {
        "schema_version": plan.schema_version,
        "portfolio_id":   plan.portfolio_id,
        "repair_plan_id": plan.repair_plan_id,
        "generated_at":   plan.generated_at,
        "operations": [
            {
                "repair_type":    op.repair_type,
                "transaction_id": op.transaction_id,
                "reason":         op.reason,
                "reason_code":    op.reason_code,
                "payload_json":   (
                    json.loads(op.payload_json) if isinstance(op.payload_json, str) else op.payload_json
                ),
            }
            for op in plan.operations
        ],
    }


def write_repair_plan(plan: RepairPlan, path: str) -> None:
    """Write a RepairPlan to a JSON file.  The only I/O this module performs."""
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(repair_plan_to_dict(plan), fh, indent=2)
        fh.write("\n")
