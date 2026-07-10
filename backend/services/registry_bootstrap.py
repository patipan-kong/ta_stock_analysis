"""Asset Registry — Registry Bootstrap Executor (Milestone M5.3).

Consumes an already-computed BootstrapPlan (M5.3 Planner, unmodified) and
performs the real, durable Registry writes it implies — minting exactly
the `mintable` candidates via registry_service.mint_asset(), and nothing
else. This module contributes zero new identity logic: it never imports
identity_resolver, never calls attach_identifier() against an already-
existing asset (that becomes migration_executor's job, once a shape turns
RESOLVED on the next Planner run), and never touches a duplicate_blocked or
quarantined shape — those are carried straight through to BootstrapReport
for operator visibility, never auto-resolved.

Why duplicate-blocked shapes are never auto-minted
-------------------------------------------------------
A pre-mint duplicate cluster (two UNKNOWN claim shapes sharing a canonical_
symbol) has no asset_id on either side — RegistryFinding.subject_asset_id
is NOT NULL, so the conflict cannot be recorded as a finding before at
least one side is minted. This module deliberately does not resolve that
by minting one side via a tie-break and flagging the other: which spelling
becomes the *permanent* canonical_symbol is itself an identity judgment,
and an automatic, silent one would be exactly the kind of guess ASSET_
REGISTRY.md Section 4 rules out. Both sides are left unminted; an operator
resolves the cluster by hand using the already-existing registry_service.
mint_asset()/attach_identifier() calls directly — no new resolution path
is built for this case, only the detection and reporting of it (reused
verbatim from migration_report.py via bootstrap_planner.py).

Checkpointing: history over state
------------------------------------
See models/registry_bootstrap.py for the full rationale. In short:
RegistryBootstrapCheckpoint is an append-only log of mint attempts, not a
mutable per-shape status row. Resumability ("has this shape been minted in
this run?") is always answered by querying the log for an existing MINTED
row, computed on read — never a cached status field. This is a separate
table from MigrationExecutionCheckpoint (M5.2), not a reuse of it, because
a BLOCKED mint has no asset_id yet — MigrationExecutionCheckpoint.
resolved_asset_id is NOT NULL by design and does not fit that case.

Two failure classes, handled differently on purpose
-------------------------------------------------------
- AssetRegistryError from registry_service.mint_asset() is an EXPECTED
  signal from the Registry — either a live identifier conflict, which
  mint_asset() has already durably recorded as an OPEN DUPLICATE_CLAIM
  finding before re-raising (ASSET_REGISTRY.md Section 7), or a canonical_
  symbol collision (e.g. two claim shapes in the same batch differing only
  by currency both proposing the same raw_symbol), which core.mint() raises
  before any row is created. Either way, rolling back here would risk
  discarding a durably-recorded finding — an ADR-002 violation ("no
  compensation for defects; fail loud, don't paper over"). So this path
  does NOT roll back: whatever the Registry already committed to the
  session stays, and the shape is checkpointed BLOCKED with no asset_id.
- Any other exception is UNEXPECTED (infra failure, programming error). The
  session may be left unusable by it, so this path rolls back first, logs
  the full exception, and persists only a fresh BLOCKED checkpoint — never
  silently retried, never allowed to abort the whole run.

No automatic retries: a BLOCKED shape stays BLOCKED until an operator
explicitly re-invokes bootstrap_registry — nothing in this module loops or
retries on its own. dry_run is the rollback strategy: every stage runs and
is then explicitly rolled back rather than committed, mirroring
services/migration_executor.py's own dry_run handling (ADR-004 — reuse the
one proven pattern rather than inventing a second one).

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

from models.registry_bootstrap import RegistryBootstrapCheckpoint
from services import ledger_evidence_builder as evidence_builder
from services import registry_service
from services.asset_registry import AssetRegistryError
from services.bootstrap_planner import BootstrapPlan, QuarantinedShape
from services.migration_planner import ClaimShape
from services.migration_report import PotentialDuplicateCluster

__all__ = [
    "BootstrapOutcome",
    "BootstrapStepResult",
    "BootstrapSummary",
    "BootstrapReport",
    "bootstrap_registry",
]

_log = logging.getLogger(__name__)


class BootstrapOutcome(str, Enum):
    """Per-shape outcome of one bootstrap_registry() invocation."""

    MINTED = "MINTED"
    BLOCKED = "BLOCKED"
    SKIPPED_ALREADY_DONE = "SKIPPED_ALREADY_DONE"


@dataclass(frozen=True)
class BootstrapStepResult:
    """One mintable candidate's outcome for this invocation. Not itself
    persisted — the persisted record is RegistryBootstrapCheckpoint; this
    is the in-memory read model BootstrapReport hands back to the caller."""

    shape: ClaimShape
    outcome: BootstrapOutcome
    minted_asset_id: Optional[int]
    identifiers_attached: int
    detail: str


@dataclass(frozen=True)
class BootstrapSummary:
    minted: int
    blocked: int
    skipped_already_done: int
    duplicate_blocked_clusters: int
    quarantined: int
    total_identifiers_attached: int


@dataclass(frozen=True)
class BootstrapReport:
    """The complete answer to one bootstrap_registry() invocation.
    duplicate_blocked and quarantined are carried straight through from the
    BootstrapPlan unchanged — this module never acts on them, only reports
    them for manual review."""

    run_id: str
    dry_run: bool
    steps: Tuple[BootstrapStepResult, ...]
    duplicate_blocked: Tuple[PotentialDuplicateCluster, ...]
    quarantined: Tuple[QuarantinedShape, ...]
    summary: BootstrapSummary
    generated_at: datetime


def _shape_sort_key(shape: ClaimShape) -> Tuple[str, str, str]:
    return (shape.raw_symbol, shape.canonical_symbol or "", shape.currency or "")


def _already_minted(db: Session, run_id: str, shape: ClaimShape) -> bool:
    return (
        db.query(RegistryBootstrapCheckpoint.id)
        .filter_by(
            run_id=run_id,
            raw_symbol=shape.raw_symbol,
            canonical_symbol=shape.canonical_symbol,
            currency=shape.currency,
            status="MINTED",
        )
        .first()
        is not None
    )


def _build_summary(steps: List[BootstrapStepResult], plan: BootstrapPlan) -> BootstrapSummary:
    return BootstrapSummary(
        minted=sum(1 for s in steps if s.outcome == BootstrapOutcome.MINTED),
        blocked=sum(1 for s in steps if s.outcome == BootstrapOutcome.BLOCKED),
        skipped_already_done=sum(1 for s in steps if s.outcome == BootstrapOutcome.SKIPPED_ALREADY_DONE),
        duplicate_blocked_clusters=len(plan.duplicate_blocked),
        quarantined=len(plan.quarantined),
        total_identifiers_attached=sum(s.identifiers_attached for s in steps),
    )


def bootstrap_registry(
    db: Session,
    plan: BootstrapPlan,
    *,
    run_id: Optional[str] = None,
    dry_run: bool = True,
    requested_by: str = "registry_bootstrap",
) -> BootstrapReport:
    """Mints every MintCandidate in `plan.mintable` against the Registry.

    `run_id` identifies one bootstrap attempt across possibly-many
    invocations, exactly as services.migration_executor.execute_migration's
    own `run_id` does. Omit it to start a new run; pass a prior run's id to
    resume it. Callers that want a resumed run to reflect Registry/ledger
    changes since the interrupted run should recompute `plan` (via
    services.bootstrap_planner.build_bootstrap_plan() over a freshly
    computed services.migration_planner.plan_migration() result) before
    calling this again, rather than reusing a stale plan object.

    dry_run=True (the default) rolls back every stage — no Asset, no
    identifier, and no checkpoint row survives the call. dry_run=False
    commits per-shape as described in the module docstring.
    """
    resolved_run_id = run_id or str(uuid.uuid4())
    steps: List[BootstrapStepResult] = []

    for candidate in sorted(plan.mintable, key=lambda c: _shape_sort_key(c.shape)):
        shape = candidate.shape

        if _already_minted(db, resolved_run_id, shape):
            steps.append(
                BootstrapStepResult(
                    shape=shape,
                    outcome=BootstrapOutcome.SKIPPED_ALREADY_DONE,
                    minted_asset_id=None,
                    identifiers_attached=0,
                    detail=f"already minted in run_id={resolved_run_id}",
                )
            )
            continue

        claim = evidence_builder.build_claim(
            shape.raw_symbol,
            shape.canonical_symbol,
            currency=shape.currency,
            requested_by=requested_by,
            note=f"M5.3 registry bootstrap — run {resolved_run_id}",
        )

        minted_asset_id: Optional[int] = None
        attached = 0
        status = "MINTED"
        detail = ""
        try:
            asset = registry_service.mint_asset(db, candidate.proposed_claim, identifiers=claim.identifiers)
            minted_asset_id = asset.id
            attached = len(claim.identifiers)
            detail = f"minted asset_id={asset.id} with {attached} identifier(s)"
        except AssetRegistryError as exc:
            # Expected conflict signal — do not roll back. Whatever the
            # Registry already committed to the session (e.g. a
            # DUPLICATE_CLAIM finding) must survive (see module docstring).
            status = "BLOCKED"
            detail = f"blocked: {exc}"
        except Exception as exc:  # noqa: BLE001 — deliberate broad catch, see module docstring
            _log.exception(
                "Unexpected failure bootstrapping claim shape %s/%s in run_id=%s",
                shape.raw_symbol, shape.canonical_symbol, resolved_run_id,
            )
            db.rollback()
            minted_asset_id = None
            attached = 0
            status = "BLOCKED"
            detail = f"unexpected failure: {exc}"

        checkpoint = RegistryBootstrapCheckpoint(
            run_id=resolved_run_id,
            raw_symbol=shape.raw_symbol,
            canonical_symbol=shape.canonical_symbol,
            currency=shape.currency,
            status=status,
            minted_asset_id=minted_asset_id,
            identifiers_attached=attached,
            detail=detail,
        )
        db.add(checkpoint)

        if dry_run:
            db.rollback()
        else:
            db.commit()

        steps.append(
            BootstrapStepResult(
                shape=shape,
                outcome=BootstrapOutcome.MINTED if status == "MINTED" else BootstrapOutcome.BLOCKED,
                minted_asset_id=minted_asset_id,
                identifiers_attached=attached,
                detail=detail,
            )
        )

    return BootstrapReport(
        run_id=resolved_run_id,
        dry_run=dry_run,
        steps=tuple(steps),
        duplicate_blocked=plan.duplicate_blocked,
        quarantined=plan.quarantined,
        summary=_build_summary(steps, plan),
        generated_at=datetime.now(timezone.utc),
    )
