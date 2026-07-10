"""Asset Registry — Migration Execution Framework (Milestone M5.2).

Consumes an already-computed MigrationPlan (M5.1, unmodified) and performs
the real, durable Registry writes it implies — strictly limited to writes
that require zero new identity judgment.

Planner decides. Executor executes. Registry owns identity. Resolver owns
matching. Evidence Builders own translation. This module contributes zero
new identity logic: it never imports identity_resolver, never calls
mint_asset or record_merge, and its only branch on ResolutionVerdict is a
mechanical one (RESOLVED or not) — that absence, not a comment, is the
proof that it "must never resolve identities, score candidates, merge
assets automatically, or invent mappings."

Only RESOLVED claim shapes are ever executed
----------------------------------------------
ASSET_REGISTRY.md Section 4's three-position model — decisive evidence
resolves silently, ambiguity is surfaced, absence of evidence is honestly
"unknown" rather than "confidently new" — is why AMBIGUOUS, CONFLICT, and
UNKNOWN claim shapes are always reported as skipped, never acted on here.
Adjudicating them is the pre-existing M2/M3 findings surface's job
(registry_service.resolve_finding), not this executor's.

The one action performed, for each RESOLVED shape: rebuild the claim via
ledger_evidence_builder.build_claim() — the exact pure function the Planner
already called — and attach_identifier() each identifier it produces to the
shape's already-decided resolved_asset_id. Rebuilding rather than
serializing the Planner's claim is deliberate: it is a pure re-derivation
of the same evidence from the same inputs (ADR-004), not new judgment.

Checkpointing: history over state
------------------------------------
See models/migration_execution.py for the full rationale. In short:
MigrationExecutionCheckpoint is an append-only log of attempts, not a
mutable per-shape status row. Resumability ("has this shape completed in
this run?") is always answered by querying the log for an existing
COMPLETED row, computed on read — never by a cached status field. Do not
introduce one; see the model module for why.

Two failure classes, handled differently on purpose
-------------------------------------------------------
- AssetRegistryError (an execute-time identifier conflict) is an EXPECTED
  signal from the Registry. registry_service.attach_identifier() has
  already durably recorded an OPEN IDENTIFIER_CONFLICT finding on the
  session before re-raising it (ASSET_REGISTRY.md Section 7 — "conflicting
  identifiers are first-class findings"). Rolling the session back here
  would silently discard that finding along with any identifiers that DID
  attach successfully earlier in the same claim — an ADR-002 violation
  ("no compensation for defects; fail loud, don't paper over"). So this
  path does NOT roll back: whatever succeeded stays committed, the finding
  survives, and the shape is checkpointed BLOCKED with a note of how many
  identifiers actually attached before the conflict.
- Any other exception is UNEXPECTED (infra failure, programming error). The
  session may be left unusable by it, so this path rolls back first, logs
  the full exception, and persists only a fresh BLOCKED checkpoint — never
  silently retried, never allowed to abort the whole run.

No automatic retries: a BLOCKED shape stays BLOCKED until an operator
explicitly re-invokes execute_migration — nothing in this module loops or
retries on its own. dry_run is the rollback strategy: every stage runs and
is then explicitly rolled back rather than committed, mirroring
repair_plan_executor.apply_repair_plan's own dry_run handling (ADR-004 —
reuse the one proven pattern rather than inventing a second one).

Out of scope, structurally: Transaction, PortfolioItem, and
PortfolioSnapshot are never imported or touched. Replay, accounting, and
the ledger are unreachable from this module.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from models.migration_execution import MigrationExecutionCheckpoint
from services import ledger_evidence_builder as evidence_builder
from services import registry_service
from services.asset_registry import AssetRegistryError
from services.migration_planner import ClaimShape, MigrationPlan
from services.resolver_domain import ResolutionVerdict

__all__ = [
    "ExecutionOutcome",
    "ExecutionStepResult",
    "ExecutionSummary",
    "ExecutionReport",
    "execute_migration",
]

_log = logging.getLogger(__name__)


class ExecutionOutcome(str, Enum):
    """Per-shape outcome of one execute_migration() invocation."""

    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    SKIPPED_NOT_RESOLVED = "SKIPPED_NOT_RESOLVED"
    SKIPPED_ALREADY_DONE = "SKIPPED_ALREADY_DONE"


@dataclass(frozen=True)
class ExecutionStepResult:
    """One claim shape's outcome for this invocation. Not itself persisted
    — the persisted record is MigrationExecutionCheckpoint; this is the
    in-memory read model ExecutionReport hands back to the caller."""

    shape: ClaimShape
    outcome: ExecutionOutcome
    resolved_asset_id: Optional[int]
    identifiers_attached: int
    detail: str


@dataclass(frozen=True)
class ExecutionSummary:
    completed: int
    blocked: int
    skipped_not_resolved: int
    skipped_already_done: int
    total_identifiers_attached: int


@dataclass(frozen=True)
class ExecutionReport:
    run_id: str
    dry_run: bool
    steps: Tuple[ExecutionStepResult, ...]
    summary: ExecutionSummary
    generated_at: datetime


def _shape_sort_key(shape: ClaimShape) -> Tuple[str, str, str]:
    return (shape.raw_symbol, shape.canonical_symbol or "", shape.currency or "")


def _already_completed(db: Session, run_id: str, shape: ClaimShape) -> bool:
    return (
        db.query(MigrationExecutionCheckpoint.id)
        .filter_by(
            run_id=run_id,
            raw_symbol=shape.raw_symbol,
            canonical_symbol=shape.canonical_symbol,
            currency=shape.currency,
            status="COMPLETED",
        )
        .first()
        is not None
    )


def _build_summary(steps: List[ExecutionStepResult]) -> ExecutionSummary:
    return ExecutionSummary(
        completed=sum(1 for s in steps if s.outcome == ExecutionOutcome.COMPLETED),
        blocked=sum(1 for s in steps if s.outcome == ExecutionOutcome.BLOCKED),
        skipped_not_resolved=sum(1 for s in steps if s.outcome == ExecutionOutcome.SKIPPED_NOT_RESOLVED),
        skipped_already_done=sum(1 for s in steps if s.outcome == ExecutionOutcome.SKIPPED_ALREADY_DONE),
        total_identifiers_attached=sum(s.identifiers_attached for s in steps),
    )


def execute_migration(
    db: Session,
    plan: MigrationPlan,
    *,
    run_id: Optional[str] = None,
    dry_run: bool = True,
    requested_by: str = "migration_executor",
) -> ExecutionReport:
    """Executes every RESOLVED claim shape in `plan` against the Registry.

    `run_id` identifies one execution attempt across possibly-many
    invocations. Omit it to start a new run (a fresh UUID is generated and
    returned on the report); pass a prior run's id to resume it — resuming
    is nothing more than calling this function again with the same id, so
    that the checkpoint lookup in the main loop skips already-COMPLETED
    shapes. Callers that want a resumed run to reflect Registry/ledger
    changes since the interrupted run should recompute `plan` (via
    services.migration_planner.plan_migration()) before calling this again,
    rather than reusing a stale plan object — plan_migration() is cheap and
    side-effect-free, and re-planning is what keeps a resume from acting on
    outdated evidence.

    dry_run=True (the default) rolls back every stage — no identifier
    attachment and no checkpoint row survives the call. dry_run=False
    commits per-shape as described in the module docstring.
    """
    resolved_run_id = run_id or str(uuid.uuid4())
    steps: List[ExecutionStepResult] = []

    for resolution in sorted(plan.resolutions, key=lambda r: _shape_sort_key(r.shape)):
        shape = resolution.shape
        result = resolution.result

        if result.verdict != ResolutionVerdict.RESOLVED or result.resolved_asset_id is None:
            steps.append(
                ExecutionStepResult(
                    shape=shape,
                    outcome=ExecutionOutcome.SKIPPED_NOT_RESOLVED,
                    resolved_asset_id=None,
                    identifiers_attached=0,
                    detail=f"verdict={result.verdict.value}; not executable without adjudication",
                )
            )
            continue

        resolved_asset_id = result.resolved_asset_id

        if _already_completed(db, resolved_run_id, shape):
            steps.append(
                ExecutionStepResult(
                    shape=shape,
                    outcome=ExecutionOutcome.SKIPPED_ALREADY_DONE,
                    resolved_asset_id=resolved_asset_id,
                    identifiers_attached=0,
                    detail=f"already completed in run_id={resolved_run_id}",
                )
            )
            continue

        claim = evidence_builder.build_claim(
            shape.raw_symbol,
            shape.canonical_symbol,
            currency=shape.currency,
            requested_by=requested_by,
            note=f"M5.2 migration execution — run {resolved_run_id}",
        )

        attached = 0
        status = "COMPLETED"
        detail = ""
        try:
            for identifier in claim.identifiers:
                registry_service.attach_identifier(db, resolved_asset_id, identifier)
                attached += 1
            detail = f"attached {attached} identifier(s) to asset_id={resolved_asset_id}"
        except AssetRegistryError as exc:
            # Expected conflict signal — do not roll back. Whatever attached
            # successfully before the conflict, and the IDENTIFIER_CONFLICT
            # finding registry_service already recorded, must both survive
            # (see module docstring).
            status = "BLOCKED"
            detail = f"blocked after {attached} identifier(s): {exc}"
        except Exception as exc:  # noqa: BLE001 — deliberate broad catch, see module docstring
            _log.exception(
                "Unexpected failure executing claim shape %s/%s in run_id=%s",
                shape.raw_symbol, shape.canonical_symbol, resolved_run_id,
            )
            db.rollback()
            attached = 0
            status = "BLOCKED"
            detail = f"unexpected failure: {exc}"

        checkpoint = MigrationExecutionCheckpoint(
            run_id=resolved_run_id,
            raw_symbol=shape.raw_symbol,
            canonical_symbol=shape.canonical_symbol,
            currency=shape.currency,
            status=status,
            resolved_asset_id=resolved_asset_id,
            identifiers_attached=attached,
            detail=detail,
        )
        db.add(checkpoint)

        if dry_run:
            db.rollback()
        else:
            db.commit()

        steps.append(
            ExecutionStepResult(
                shape=shape,
                outcome=ExecutionOutcome.COMPLETED if status == "COMPLETED" else ExecutionOutcome.BLOCKED,
                resolved_asset_id=resolved_asset_id,
                identifiers_attached=attached,
                detail=detail,
            )
        )

    return ExecutionReport(
        run_id=resolved_run_id,
        dry_run=dry_run,
        steps=tuple(steps),
        summary=_build_summary(steps),
        generated_at=datetime.now(timezone.utc),
    )
