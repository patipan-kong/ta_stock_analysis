"""Pure, ORM-free Execution Intent domain contracts (M33.2).

This module implements only the immutable identity/snapshot/provenance
contracts designed by
``docs/implementation/M33_1_execution_intent_snapshot_lifecycle_foundation.md``.
It has no SQLAlchemy model, migration, endpoint, repository, or background
writer.  Nothing here is wired into any runtime path; importing this module
has no effect on `RecommendationSnapshot`, `UserExecutionDecision`,
`ShadowPortfolio`, `Transaction`, or portfolio replay.

Authority boundaries preserved from M33.1:

- A recommendation is advisory evidence, never intent.
- A shadow/diagnostic (M31/M32) is a simulated projection, never intent
  evidence; ``SourceKind`` deliberately has no shadow-diagnostic member.
- ``FUTURE_CANONICAL_EXECUTION_PLAN`` is a reserved source kind only; M33.2
  refuses to build a snapshot that cites it, because canonical execution
  planning remains NO-GO per ``docs/implementation/M32_EPIC_CLOSEOUT.md``.
- Terms freeze the exact human-reviewed allocation intent (symbol, side,
  target weight or value).  They never carry an executable quantity, a
  side-aware execution price, a fee, an order, or a broker instruction.

Canonical content hashing
--------------------------
``content_hash`` is computed only from what a human actually reviewed and
could approve:

    terms_schema_version, intent_kind, terms (allocations canonically
    sorted by (symbol, side)), workspace_id, portfolio_id, effective_at,
    expires_at, source_provenance (canonically sorted).

It deliberately excludes ``snapshot_id``, ``intent_id``, ``revision``,
``supersedes_snapshot_id``, ``created_by_actor``, and ``recorded_at``: those
are lineage/bookkeeping metadata, not the reviewed content.  This lets a
resumed/re-approved snapshot with unchanged terms keep the same content hash,
while approval binding (see ``execution_intent_transitions``) still binds to
the exact ``snapshot_id`` in addition to the hash.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

__all__ = [
    "ActorType",
    "Actor",
    "SourceKind",
    "ProvenanceCompleteness",
    "SourceProvenance",
    "IntentKind",
    "TermSide",
    "ExecutionIntentAllocationTerm",
    "ExecutionIntentTerms",
    "LifecycleState",
    "TERMINAL_LIFECYCLE_STATES",
    "ExecutionIntentSnapshot",
    "build_execution_intent_terms",
    "compute_snapshot_content_hash",
    "build_execution_intent_snapshot",
]


_CONTRACT_VERSION = "1"


class ActorType(str, Enum):
    """A human actor authorizes; a system actor may only propose/expire/quarantine."""

    HUMAN = "HUMAN"
    SYSTEM = "SYSTEM"


@dataclass(frozen=True)
class Actor:
    actor_type: ActorType
    actor_id: str


class SourceKind(str, Enum):
    """Typed provenance sources. No shadow/diagnostic member exists by design."""

    LEGACY_RECOMMENDATION_SNAPSHOT = "LEGACY_RECOMMENDATION_SNAPSHOT"
    LEGACY_USER_EXECUTION_DECISION = "LEGACY_USER_EXECUTION_DECISION"
    MANUAL_HUMAN_INPUT = "MANUAL_HUMAN_INPUT"
    # Reserved. Never usable to build a snapshot in M33.1/M33.2 — canonical
    # execution planning remains NO-GO (M32_EPIC_CLOSEOUT.md).
    FUTURE_CANONICAL_EXECUTION_PLAN = "FUTURE_CANONICAL_EXECUTION_PLAN"


class ProvenanceCompleteness(str, Enum):
    EXACT_FROZEN = "EXACT_FROZEN"
    LEGACY_RECONSTRUCTED = "LEGACY_RECONSTRUCTED"
    INCOMPLETE = "INCOMPLETE"


@dataclass(frozen=True)
class SourceProvenance:
    source_kind: SourceKind
    source_local_id: str | None
    source_contract_version: str
    source_created_at: datetime | None
    source_digest: str
    completeness: ProvenanceCompleteness


class IntentKind(str, Enum):
    FOLLOW_RECOMMENDATION = "FOLLOW_RECOMMENDATION"
    PARTIAL_FOLLOW = "PARTIAL_FOLLOW"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"
    MANUAL_INDEPENDENT = "MANUAL_INDEPENDENT"


class TermSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass(frozen=True)
class ExecutionIntentAllocationTerm:
    """One reviewed allocation term. Never an executable quantity/price/order."""

    symbol: str
    side: TermSide
    target_weight: Decimal | None = None
    target_value: Decimal | None = None
    note: str | None = None


@dataclass(frozen=True)
class ExecutionIntentTerms:
    schema_version: str
    allocations: tuple[ExecutionIntentAllocationTerm, ...]
    notes: str | None = None


class LifecycleState(str, Enum):
    PENDING_REVIEW = "PENDING_REVIEW"
    DEFERRED = "DEFERRED"
    APPROVED = "APPROVED"
    QUARANTINED = "QUARANTINED"
    EXECUTION_REQUESTED = "EXECUTION_REQUESTED"
    PARTIALLY_EXECUTED = "PARTIALLY_EXECUTED"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    SUPERSEDED = "SUPERSEDED"


TERMINAL_LIFECYCLE_STATES = frozenset(
    {
        LifecycleState.REJECTED,
        LifecycleState.CANCELLED,
        LifecycleState.EXPIRED,
        LifecycleState.SUPERSEDED,
        LifecycleState.COMPLETED,
    }
)


@dataclass(frozen=True)
class ExecutionIntentSnapshot:
    """One immutable, human-reviewed terms revision.

    ``snapshot_id`` and ``intent_id`` are caller-supplied opaque identities.
    This module never generates a random identity itself, so that identical
    inputs always produce byte-equivalent output.
    """

    contract_version: str
    snapshot_id: str
    intent_id: str
    revision: int
    supersedes_snapshot_id: str | None
    terms_schema_version: str
    intent_kind: IntentKind
    terms: ExecutionIntentTerms
    workspace_id: int
    portfolio_id: int
    source_provenance: tuple[SourceProvenance, ...]
    created_by_actor: Actor
    effective_at: datetime
    recorded_at: datetime
    expires_at: datetime | None
    content_hash: str


def build_execution_intent_terms(
    schema_version: str,
    allocations: tuple[ExecutionIntentAllocationTerm, ...],
    notes: str | None = None,
) -> ExecutionIntentTerms:
    if not allocations:
        raise ValueError("execution intent terms require at least one allocation")
    seen: set[tuple[str, TermSide]] = set()
    for allocation in allocations:
        key = (allocation.symbol, allocation.side)
        if key in seen:
            raise ValueError(f"duplicate allocation term for {allocation.symbol}/{allocation.side.value}")
        seen.add(key)
        has_weight = allocation.target_weight is not None
        has_value = allocation.target_value is not None
        if has_weight == has_value:
            raise ValueError(
                f"allocation term for {allocation.symbol} must set exactly one of "
                "target_weight or target_value"
            )
        for value in (allocation.target_weight, allocation.target_value):
            if value is not None and not (isinstance(value, Decimal) and value > Decimal("0")):
                raise ValueError(f"allocation term for {allocation.symbol} must be a positive Decimal")
    return ExecutionIntentTerms(
        schema_version=schema_version,
        allocations=tuple(allocations),
        notes=notes,
    )


def compute_snapshot_content_hash(
    *,
    terms_schema_version: str,
    intent_kind: IntentKind,
    terms: ExecutionIntentTerms,
    workspace_id: int,
    portfolio_id: int,
    effective_at: datetime,
    expires_at: datetime | None,
    source_provenance: tuple[SourceProvenance, ...],
) -> str:
    """Hash only the reviewed content; see module docstring for the field list."""

    _require_utc(effective_at, "effective_at")
    if expires_at is not None:
        _require_utc(expires_at, "expires_at")

    payload = {
        "contract_version": _CONTRACT_VERSION,
        "terms_schema_version": terms_schema_version,
        "intent_kind": intent_kind.value,
        "terms": _canon_terms(terms),
        "workspace_id": int(workspace_id),
        "portfolio_id": int(portfolio_id),
        "effective_at": _canon_datetime(effective_at),
        "expires_at": _canon_datetime(expires_at) if expires_at is not None else None,
        "source_provenance": _canon_provenance(source_provenance),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_execution_intent_snapshot(
    *,
    snapshot_id: str,
    intent_id: str,
    revision: int,
    supersedes_snapshot_id: str | None,
    terms: ExecutionIntentTerms,
    intent_kind: IntentKind,
    workspace_id: int,
    portfolio_id: int,
    source_provenance: tuple[SourceProvenance, ...],
    created_by_actor: Actor,
    effective_at: datetime,
    recorded_at: datetime,
    expires_at: datetime | None = None,
) -> ExecutionIntentSnapshot:
    """The sole constructor boundary for ``ExecutionIntentSnapshot`` values."""

    if revision < 1:
        raise ValueError("revision must be a positive, gap-free sequence starting at 1")
    if revision == 1 and supersedes_snapshot_id is not None:
        raise ValueError("revision 1 must not declare a predecessor")
    if revision > 1 and supersedes_snapshot_id is None:
        raise ValueError("revision > 1 must declare its exact predecessor snapshot_id")
    if not source_provenance:
        raise ValueError("at least one SourceProvenance is required")
    if any(sp.source_kind == SourceKind.FUTURE_CANONICAL_EXECUTION_PLAN for sp in source_provenance):
        raise ValueError(
            "FUTURE_CANONICAL_EXECUTION_PLAN is reserved; canonical execution "
            "planning is NO-GO and must not be cited as intent provenance"
        )
    _require_utc(recorded_at, "recorded_at")

    content_hash = compute_snapshot_content_hash(
        terms_schema_version=terms.schema_version,
        intent_kind=intent_kind,
        terms=terms,
        workspace_id=workspace_id,
        portfolio_id=portfolio_id,
        effective_at=effective_at,
        expires_at=expires_at,
        source_provenance=source_provenance,
    )
    return ExecutionIntentSnapshot(
        contract_version=_CONTRACT_VERSION,
        snapshot_id=snapshot_id,
        intent_id=intent_id,
        revision=revision,
        supersedes_snapshot_id=supersedes_snapshot_id,
        terms_schema_version=terms.schema_version,
        intent_kind=intent_kind,
        terms=terms,
        workspace_id=workspace_id,
        portfolio_id=portfolio_id,
        source_provenance=tuple(source_provenance),
        created_by_actor=created_by_actor,
        effective_at=effective_at,
        recorded_at=recorded_at,
        expires_at=expires_at,
        content_hash=content_hash,
    )


def _canon_terms(terms: ExecutionIntentTerms) -> dict:
    allocations = sorted(
        terms.allocations,
        key=lambda allocation: (allocation.symbol, allocation.side.value),
    )
    return {
        "schema_version": terms.schema_version,
        "notes": terms.notes,
        "allocations": [
            {
                "symbol": allocation.symbol,
                "side": allocation.side.value,
                "target_weight": _canon_decimal(allocation.target_weight),
                "target_value": _canon_decimal(allocation.target_value),
                "note": allocation.note,
            }
            for allocation in allocations
        ],
    }


def _canon_provenance(source_provenance: tuple[SourceProvenance, ...]) -> list[dict]:
    ordered = sorted(
        source_provenance,
        key=lambda sp: (sp.source_kind.value, sp.source_local_id or ""),
    )
    return [
        {
            "source_kind": sp.source_kind.value,
            "source_local_id": sp.source_local_id,
            "source_contract_version": sp.source_contract_version,
            "source_created_at": _canon_datetime(sp.source_created_at) if sp.source_created_at else None,
            "source_digest": sp.source_digest,
            "completeness": sp.completeness.value,
        }
        for sp in ordered
    ]


def _canon_decimal(value: Decimal | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError("only finite Decimal values are canonical")
    return format(value, "f")


def _canon_datetime(value: datetime) -> str:
    _require_utc(value, "datetime")
    return value.astimezone(timezone.utc).isoformat()


def _require_utc(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field} must be a timezone-aware UTC datetime")
