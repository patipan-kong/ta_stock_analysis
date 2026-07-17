"""Pure Execution Intent lifecycle transition validator (M33.2).

Implements the allowed-transition table from
``docs/implementation/M33_1_execution_intent_snapshot_lifecycle_foundation.md``
section 8.8 as a pure function.  It appends nothing and mutates nothing: it
is given a context describing the current state and a command, and it
returns either an immutable append-only ``TransitionResult`` (one or more
``TransitionEvent`` values) or a typed ``TransitionRefusal``.  No database,
ORM, clock, or persistence exists in this module; callers own storage and
append accepted events to their own log.

Authority rules enforced here (see M33.1 section 9 for the full invariant
list):

- A system actor can never approve (``SYSTEM_ACTOR_CANNOT_APPROVE``).
- Approval binds to the *exact* snapshot content hash
  (``APPROVAL_HASH_MISMATCH``/``APPROVAL_HASH_REQUIRED``).
- ``PARTIALLY_EXECUTED``/``COMPLETED`` require explicit admitted ledger
  evidence whose coverage matches the requested target exactly; a shadow or
  diagnostic cannot satisfy this because ``LedgerEvidenceEntry`` has no
  shadow-shaped fields to construct one from.
- Only a human act may supersede an ``APPROVED`` snapshot; a system actor may
  supersede a ``PENDING_REVIEW``/``DEFERRED``/``QUARANTINED`` proposal.
- Terms are immutable after insert: superseding a snapshot never edits it,
  it always creates predecessor ``SUPERSEDED`` + new-revision ``PENDING_REVIEW``
  atomically (and optionally an atomic approval of the replacement), as one
  refuse-or-accept-together result.
- Terminal states accept no further transitions.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Mapping

from services.execution_intent_contracts import (
    Actor,
    ActorType,
    ExecutionIntentSnapshot,
    ExecutionIntentTerms,
    LifecycleState,
    ProvenanceCompleteness,
    TERMINAL_LIFECYCLE_STATES,
    TermSide,
)

__all__ = [
    "TransitionCommandType",
    "LedgerEvidenceEntry",
    "AdmittedLedgerEvidence",
    "FulfillmentOutcome",
    "assess_fulfillment",
    "TransitionCommand",
    "SnapshotLifecycleContext",
    "TransitionEvent",
    "TransitionRefusalReason",
    "TransitionRefusal",
    "TransitionOutcome",
    "TransitionResult",
    "validate_transition",
    "IdempotencyRecord",
    "IdempotencyOutcome",
    "IdempotencyResolution",
    "compute_command_content_hash",
    "resolve_idempotency",
]


class TransitionCommandType(str, Enum):
    SUBMIT = "SUBMIT"
    APPROVE = "APPROVE"
    DEFER = "DEFER"
    RESUME = "RESUME"
    REJECT = "REJECT"
    CANCEL = "CANCEL"
    EXPIRE = "EXPIRE"
    QUARANTINE = "QUARANTINE"
    RESOLVE_QUARANTINE = "RESOLVE_QUARANTINE"
    REQUEST_EXECUTION = "REQUEST_EXECUTION"
    RECORD_PARTIAL_EXECUTION = "RECORD_PARTIAL_EXECUTION"
    RECORD_COMPLETION = "RECORD_COMPLETION"
    SUPERSEDE_WITH_REPLACEMENT = "SUPERSEDE_WITH_REPLACEMENT"


@dataclass(frozen=True)
class LedgerEvidenceEntry:
    """One admitted transaction fact. Never a shadow, diagnostic, or hint."""

    transaction_ref: str
    symbol: str
    side: TermSide
    quantity: Decimal
    recorded_at: datetime


@dataclass(frozen=True)
class AdmittedLedgerEvidence:
    entries: tuple[LedgerEvidenceEntry, ...]

    def symbols(self) -> frozenset[tuple[str, TermSide]]:
        return frozenset((entry.symbol, entry.side) for entry in self.entries)

    def transaction_refs(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(entry.transaction_ref for entry in self.entries))


class FulfillmentOutcome(str, Enum):
    NO_EVIDENCE = "NO_EVIDENCE"
    PARTIAL = "PARTIAL"
    COMPLETE = "COMPLETE"
    CONFLICT = "CONFLICT"


def assess_fulfillment(
    terms: ExecutionIntentTerms,
    evidence: AdmittedLedgerEvidence,
) -> FulfillmentOutcome:
    """Compare admitted-transaction symbol/side coverage against terms.

    This is deliberately coverage-based, not quantity-based: M33 terms carry a
    target weight/value, not an executable admission quantity, so exact
    quantity reconciliation is out of scope for this milestone.
    """

    term_keys = frozenset((allocation.symbol, allocation.side) for allocation in terms.allocations)
    evidence_keys = evidence.symbols()
    if not evidence_keys:
        return FulfillmentOutcome.NO_EVIDENCE
    if evidence_keys - term_keys:
        return FulfillmentOutcome.CONFLICT
    if evidence_keys == term_keys:
        return FulfillmentOutcome.COMPLETE
    return FulfillmentOutcome.PARTIAL


@dataclass(frozen=True)
class TransitionCommand:
    command_type: TransitionCommandType
    idempotency_key: str
    actor: Actor
    occurred_at: datetime
    expected_prior_state: LifecycleState | None
    expected_prior_transition_sequence: int
    reason: str | None = None
    policy_reference: str | None = None
    approval_content_hash: str | None = None
    ledger_evidence: AdmittedLedgerEvidence | None = None
    submitted_snapshot: ExecutionIntentSnapshot | None = None
    replacement_snapshot: ExecutionIntentSnapshot | None = None
    also_approve_replacement: bool = False
    correlation_id: str | None = None


@dataclass(frozen=True)
class SnapshotLifecycleContext:
    """The exact current snapshot/state the command is expected to apply to."""

    snapshot: ExecutionIntentSnapshot | None
    current_state: LifecycleState | None
    current_transition_sequence: int


@dataclass(frozen=True)
class TransitionEvent:
    intent_id: str
    snapshot_id: str
    transition_sequence: int
    from_state: LifecycleState | None
    to_state: LifecycleState
    command_type: TransitionCommandType
    actor: Actor
    occurred_at: datetime
    recorded_at: datetime
    idempotency_key: str
    reason: str | None = None
    policy_reference: str | None = None
    content_hash: str | None = None
    ledger_evidence_ref: tuple[str, ...] = ()
    correlation_id: str | None = None


class TransitionRefusalReason(str, Enum):
    INVALID_TRANSITION = "INVALID_TRANSITION"
    TERMINAL_STATE = "TERMINAL_STATE"
    PRIOR_STATE_MISMATCH = "PRIOR_STATE_MISMATCH"
    PRIOR_SEQUENCE_MISMATCH = "PRIOR_SEQUENCE_MISMATCH"
    ACTOR_NOT_AUTHORIZED = "ACTOR_NOT_AUTHORIZED"
    SYSTEM_ACTOR_CANNOT_APPROVE = "SYSTEM_ACTOR_CANNOT_APPROVE"
    APPROVAL_HASH_REQUIRED = "APPROVAL_HASH_REQUIRED"
    APPROVAL_HASH_MISMATCH = "APPROVAL_HASH_MISMATCH"
    INCOMPLETE_PROVENANCE_CANNOT_APPROVE = "INCOMPLETE_PROVENANCE_CANNOT_APPROVE"
    POLICY_REFERENCE_REQUIRED = "POLICY_REFERENCE_REQUIRED"
    LEDGER_EVIDENCE_REQUIRED = "LEDGER_EVIDENCE_REQUIRED"
    LEDGER_EVIDENCE_INSUFFICIENT = "LEDGER_EVIDENCE_INSUFFICIENT"
    LEDGER_EVIDENCE_CONFLICT = "LEDGER_EVIDENCE_CONFLICT"
    SUPERSESSION_REQUIRES_HUMAN_ACT = "SUPERSESSION_REQUIRES_HUMAN_ACT"
    INVALID_REPLACEMENT_REVISION = "INVALID_REPLACEMENT_REVISION"
    INVALID_REPLACEMENT_LINEAGE = "INVALID_REPLACEMENT_LINEAGE"
    SCOPE_IMMUTABLE = "SCOPE_IMMUTABLE"
    MISSING_SUBMITTED_SNAPSHOT = "MISSING_SUBMITTED_SNAPSHOT"
    MISSING_REPLACEMENT_SNAPSHOT = "MISSING_REPLACEMENT_SNAPSHOT"
    UNEXPECTED_PAYLOAD = "UNEXPECTED_PAYLOAD"


@dataclass(frozen=True)
class TransitionRefusal:
    reason: TransitionRefusalReason
    detail: str


class TransitionOutcome(str, Enum):
    ACCEPTED = "ACCEPTED"
    REFUSED = "REFUSED"


@dataclass(frozen=True)
class TransitionResult:
    outcome: TransitionOutcome
    events: tuple[TransitionEvent, ...] = ()
    refusal: TransitionRefusal | None = None

    @property
    def accepted(self) -> bool:
        return self.outcome == TransitionOutcome.ACCEPTED


_HUMAN_ONLY_COMMANDS = frozenset(
    {
        TransitionCommandType.APPROVE,
        TransitionCommandType.DEFER,
        TransitionCommandType.RESUME,
        TransitionCommandType.REJECT,
        TransitionCommandType.CANCEL,
        TransitionCommandType.RESOLVE_QUARANTINE,
    }
)

_SYSTEM_ONLY_COMMANDS = frozenset(
    {
        TransitionCommandType.EXPIRE,
        TransitionCommandType.QUARANTINE,
        TransitionCommandType.REQUEST_EXECUTION,
        TransitionCommandType.RECORD_PARTIAL_EXECUTION,
        TransitionCommandType.RECORD_COMPLETION,
    }
)

_ALLOWED: dict[LifecycleState, dict[TransitionCommandType, LifecycleState]] = {
    LifecycleState.PENDING_REVIEW: {
        TransitionCommandType.APPROVE: LifecycleState.APPROVED,
        TransitionCommandType.DEFER: LifecycleState.DEFERRED,
        TransitionCommandType.REJECT: LifecycleState.REJECTED,
        TransitionCommandType.CANCEL: LifecycleState.CANCELLED,
        TransitionCommandType.EXPIRE: LifecycleState.EXPIRED,
        TransitionCommandType.SUPERSEDE_WITH_REPLACEMENT: LifecycleState.SUPERSEDED,
    },
    LifecycleState.DEFERRED: {
        TransitionCommandType.RESUME: LifecycleState.PENDING_REVIEW,
        TransitionCommandType.CANCEL: LifecycleState.CANCELLED,
        TransitionCommandType.EXPIRE: LifecycleState.EXPIRED,
        TransitionCommandType.SUPERSEDE_WITH_REPLACEMENT: LifecycleState.SUPERSEDED,
    },
    LifecycleState.APPROVED: {
        TransitionCommandType.DEFER: LifecycleState.DEFERRED,
        TransitionCommandType.QUARANTINE: LifecycleState.QUARANTINED,
        TransitionCommandType.REQUEST_EXECUTION: LifecycleState.EXECUTION_REQUESTED,
        TransitionCommandType.CANCEL: LifecycleState.CANCELLED,
        TransitionCommandType.EXPIRE: LifecycleState.EXPIRED,
        TransitionCommandType.SUPERSEDE_WITH_REPLACEMENT: LifecycleState.SUPERSEDED,
    },
    LifecycleState.QUARANTINED: {
        TransitionCommandType.RESOLVE_QUARANTINE: LifecycleState.PENDING_REVIEW,
        TransitionCommandType.CANCEL: LifecycleState.CANCELLED,
        TransitionCommandType.EXPIRE: LifecycleState.EXPIRED,
        TransitionCommandType.SUPERSEDE_WITH_REPLACEMENT: LifecycleState.SUPERSEDED,
    },
    LifecycleState.EXECUTION_REQUESTED: {
        TransitionCommandType.RECORD_PARTIAL_EXECUTION: LifecycleState.PARTIALLY_EXECUTED,
        TransitionCommandType.RECORD_COMPLETION: LifecycleState.COMPLETED,
        TransitionCommandType.CANCEL: LifecycleState.CANCELLED,
        TransitionCommandType.QUARANTINE: LifecycleState.QUARANTINED,
    },
    LifecycleState.PARTIALLY_EXECUTED: {
        TransitionCommandType.RECORD_COMPLETION: LifecycleState.COMPLETED,
        TransitionCommandType.CANCEL: LifecycleState.CANCELLED,
        TransitionCommandType.QUARANTINE: LifecycleState.QUARANTINED,
    },
}


def validate_transition(
    context: SnapshotLifecycleContext,
    command: TransitionCommand,
    *,
    recorded_at: datetime,
) -> TransitionResult:
    """Validate exactly one command against exactly one prior context.

    Nothing is appended or mutated on refusal; the caller receives a typed
    refusal describing why, and no event is produced.
    """

    _require_utc(recorded_at, "recorded_at")
    _require_utc(command.occurred_at, "command.occurred_at")

    if command.command_type == TransitionCommandType.SUBMIT:
        return _validate_submit(context, command, recorded_at)

    if context.snapshot is None or context.current_state is None:
        return _refuse(
            TransitionRefusalReason.INVALID_TRANSITION,
            "no existing snapshot/state; only SUBMIT may create one",
        )
    if context.current_state in TERMINAL_LIFECYCLE_STATES:
        return _refuse(
            TransitionRefusalReason.TERMINAL_STATE,
            f"{context.current_state.value} accepts no further transitions",
        )
    if command.expected_prior_state != context.current_state:
        return _refuse(
            TransitionRefusalReason.PRIOR_STATE_MISMATCH,
            f"expected {command.expected_prior_state}, current is {context.current_state.value}",
        )
    if command.expected_prior_transition_sequence != context.current_transition_sequence:
        return _refuse(
            TransitionRefusalReason.PRIOR_SEQUENCE_MISMATCH,
            (
                f"expected sequence {command.expected_prior_transition_sequence}, "
                f"current is {context.current_transition_sequence}"
            ),
        )

    allowed_from_state = _ALLOWED.get(context.current_state, {})
    to_state = allowed_from_state.get(command.command_type)
    if to_state is None:
        return _refuse(
            TransitionRefusalReason.INVALID_TRANSITION,
            f"{command.command_type.value} is not allowed from {context.current_state.value}",
        )

    actor_refusal = _check_actor_authority(context, command)
    if actor_refusal is not None:
        return TransitionResult(TransitionOutcome.REFUSED, refusal=actor_refusal)

    if command.command_type == TransitionCommandType.SUPERSEDE_WITH_REPLACEMENT:
        return _validate_supersede(context, command, to_state, recorded_at)

    if command.command_type == TransitionCommandType.APPROVE:
        refusal = _validate_approve(context, command)
        if refusal is not None:
            return TransitionResult(TransitionOutcome.REFUSED, refusal=refusal)

    if command.command_type in (TransitionCommandType.EXPIRE, TransitionCommandType.QUARANTINE):
        if not command.policy_reference:
            return _refuse(
                TransitionRefusalReason.POLICY_REFERENCE_REQUIRED,
                f"{command.command_type.value} requires an explicit policy_reference",
            )

    ledger_ref: tuple[str, ...] = ()
    if command.command_type in (
        TransitionCommandType.RECORD_PARTIAL_EXECUTION,
        TransitionCommandType.RECORD_COMPLETION,
    ):
        refusal, ledger_ref = _validate_ledger_evidence(context, command)
        if refusal is not None:
            return TransitionResult(TransitionOutcome.REFUSED, refusal=refusal)

    event = TransitionEvent(
        intent_id=context.snapshot.intent_id,
        snapshot_id=context.snapshot.snapshot_id,
        transition_sequence=context.current_transition_sequence + 1,
        from_state=context.current_state,
        to_state=to_state,
        command_type=command.command_type,
        actor=command.actor,
        occurred_at=command.occurred_at,
        recorded_at=recorded_at,
        idempotency_key=command.idempotency_key,
        reason=command.reason,
        policy_reference=command.policy_reference,
        content_hash=(command.approval_content_hash if command.command_type == TransitionCommandType.APPROVE else None),
        ledger_evidence_ref=ledger_ref,
        correlation_id=command.correlation_id,
    )
    return TransitionResult(TransitionOutcome.ACCEPTED, events=(event,))


def _validate_submit(
    context: SnapshotLifecycleContext,
    command: TransitionCommand,
    recorded_at: datetime,
) -> TransitionResult:
    if context.snapshot is not None or context.current_state is not None:
        return _refuse(
            TransitionRefusalReason.UNEXPECTED_PAYLOAD,
            "SUBMIT requires an empty context; an existing snapshot already exists",
        )
    if command.expected_prior_state is not None or command.expected_prior_transition_sequence != 0:
        return _refuse(
            TransitionRefusalReason.PRIOR_STATE_MISMATCH,
            "SUBMIT must expect prior_state=None and prior_sequence=0",
        )
    snapshot = command.submitted_snapshot
    if snapshot is None:
        return _refuse(
            TransitionRefusalReason.MISSING_SUBMITTED_SNAPSHOT,
            "SUBMIT requires submitted_snapshot",
        )
    if snapshot.revision != 1 or snapshot.supersedes_snapshot_id is not None:
        return _refuse(
            TransitionRefusalReason.INVALID_REPLACEMENT_REVISION,
            "a first submission must be revision 1 with no predecessor",
        )
    event = TransitionEvent(
        intent_id=snapshot.intent_id,
        snapshot_id=snapshot.snapshot_id,
        transition_sequence=1,
        from_state=None,
        to_state=LifecycleState.PENDING_REVIEW,
        command_type=TransitionCommandType.SUBMIT,
        actor=command.actor,
        occurred_at=command.occurred_at,
        recorded_at=recorded_at,
        idempotency_key=command.idempotency_key,
        reason=command.reason,
        correlation_id=command.correlation_id,
    )
    return TransitionResult(TransitionOutcome.ACCEPTED, events=(event,))


def _check_actor_authority(
    context: SnapshotLifecycleContext,
    command: TransitionCommand,
) -> TransitionRefusal | None:
    command_type = command.command_type
    actor_type = command.actor.actor_type
    if command_type in _HUMAN_ONLY_COMMANDS and actor_type != ActorType.HUMAN:
        return TransitionRefusal(
            TransitionRefusalReason.ACTOR_NOT_AUTHORIZED,
            f"{command_type.value} requires a HUMAN actor",
        )
    if command_type in _SYSTEM_ONLY_COMMANDS and actor_type != ActorType.SYSTEM:
        return TransitionRefusal(
            TransitionRefusalReason.ACTOR_NOT_AUTHORIZED,
            f"{command_type.value} requires a SYSTEM actor",
        )
    if (
        command_type == TransitionCommandType.SUPERSEDE_WITH_REPLACEMENT
        and context.current_state == LifecycleState.APPROVED
        and actor_type != ActorType.HUMAN
    ):
        return TransitionRefusal(
            TransitionRefusalReason.SUPERSESSION_REQUIRES_HUMAN_ACT,
            "only a human act may supersede an APPROVED snapshot",
        )
    return None


def _validate_approve(
    context: SnapshotLifecycleContext,
    command: TransitionCommand,
) -> TransitionRefusal | None:
    if command.actor.actor_type != ActorType.HUMAN:
        return TransitionRefusal(
            TransitionRefusalReason.SYSTEM_ACTOR_CANNOT_APPROVE,
            "a system actor may never approve a snapshot",
        )
    if not command.approval_content_hash:
        return TransitionRefusal(
            TransitionRefusalReason.APPROVAL_HASH_REQUIRED,
            "APPROVE requires approval_content_hash",
        )
    if command.approval_content_hash != context.snapshot.content_hash:
        return TransitionRefusal(
            TransitionRefusalReason.APPROVAL_HASH_MISMATCH,
            "approval_content_hash does not match the exact snapshot content_hash",
        )
    if any(
        sp.completeness == ProvenanceCompleteness.INCOMPLETE
        for sp in context.snapshot.source_provenance
    ):
        return TransitionRefusal(
            TransitionRefusalReason.INCOMPLETE_PROVENANCE_CANNOT_APPROVE,
            "a snapshot with INCOMPLETE source provenance cannot be approved",
        )
    return None


def _validate_ledger_evidence(
    context: SnapshotLifecycleContext,
    command: TransitionCommand,
) -> tuple[TransitionRefusal | None, tuple[str, ...]]:
    evidence = command.ledger_evidence
    if evidence is None or not evidence.entries:
        return (
            TransitionRefusal(
                TransitionRefusalReason.LEDGER_EVIDENCE_REQUIRED,
                f"{command.command_type.value} requires AdmittedLedgerEvidence with at least one entry",
            ),
            (),
        )
    outcome = assess_fulfillment(context.snapshot.terms, evidence)
    if outcome == FulfillmentOutcome.CONFLICT:
        return (
            TransitionRefusal(
                TransitionRefusalReason.LEDGER_EVIDENCE_CONFLICT,
                "ledger evidence references symbols/sides absent from the intent terms",
            ),
            (),
        )
    required = (
        FulfillmentOutcome.PARTIAL
        if command.command_type == TransitionCommandType.RECORD_PARTIAL_EXECUTION
        else FulfillmentOutcome.COMPLETE
    )
    if outcome != required:
        return (
            TransitionRefusal(
                TransitionRefusalReason.LEDGER_EVIDENCE_INSUFFICIENT,
                f"ledger evidence coverage is {outcome.value}, not {required.value}",
            ),
            (),
        )
    return None, evidence.transaction_refs()


def _validate_supersede(
    context: SnapshotLifecycleContext,
    command: TransitionCommand,
    to_state: LifecycleState,
    recorded_at: datetime,
) -> TransitionResult:
    replacement = command.replacement_snapshot
    if replacement is None:
        return _refuse(
            TransitionRefusalReason.MISSING_REPLACEMENT_SNAPSHOT,
            "SUPERSEDE_WITH_REPLACEMENT requires replacement_snapshot",
        )
    current = context.snapshot
    if replacement.intent_id != current.intent_id:
        return _refuse(
            TransitionRefusalReason.INVALID_REPLACEMENT_LINEAGE,
            "replacement_snapshot.intent_id must match the superseded intent",
        )
    if replacement.supersedes_snapshot_id != current.snapshot_id:
        return _refuse(
            TransitionRefusalReason.INVALID_REPLACEMENT_LINEAGE,
            "replacement_snapshot.supersedes_snapshot_id must reference the exact predecessor",
        )
    if replacement.revision != current.revision + 1:
        return _refuse(
            TransitionRefusalReason.INVALID_REPLACEMENT_REVISION,
            "replacement_snapshot.revision must be exactly predecessor revision + 1",
        )
    if replacement.workspace_id != current.workspace_id or replacement.portfolio_id != current.portfolio_id:
        return _refuse(
            TransitionRefusalReason.SCOPE_IMMUTABLE,
            "replacement_snapshot must retain the same workspace_id/portfolio_id scope",
        )

    if command.also_approve_replacement:
        if command.actor.actor_type != ActorType.HUMAN:
            return _refuse(
                TransitionRefusalReason.SYSTEM_ACTOR_CANNOT_APPROVE,
                "also_approve_replacement requires a HUMAN actor",
            )
        if not command.approval_content_hash:
            return _refuse(
                TransitionRefusalReason.APPROVAL_HASH_REQUIRED,
                "also_approve_replacement requires approval_content_hash",
            )
        if command.approval_content_hash != replacement.content_hash:
            return _refuse(
                TransitionRefusalReason.APPROVAL_HASH_MISMATCH,
                "approval_content_hash does not match the replacement snapshot content_hash",
            )
        if any(
            sp.completeness == ProvenanceCompleteness.INCOMPLETE
            for sp in replacement.source_provenance
        ):
            return _refuse(
                TransitionRefusalReason.INCOMPLETE_PROVENANCE_CANNOT_APPROVE,
                "a replacement with INCOMPLETE source provenance cannot be atomically approved",
            )

    superseded_event = TransitionEvent(
        intent_id=current.intent_id,
        snapshot_id=current.snapshot_id,
        transition_sequence=context.current_transition_sequence + 1,
        from_state=context.current_state,
        to_state=to_state,
        command_type=TransitionCommandType.SUPERSEDE_WITH_REPLACEMENT,
        actor=command.actor,
        occurred_at=command.occurred_at,
        recorded_at=recorded_at,
        idempotency_key=command.idempotency_key,
        reason=command.reason,
        correlation_id=command.correlation_id,
    )
    creation_event = TransitionEvent(
        intent_id=replacement.intent_id,
        snapshot_id=replacement.snapshot_id,
        transition_sequence=1,
        from_state=None,
        to_state=LifecycleState.PENDING_REVIEW,
        command_type=TransitionCommandType.SUBMIT,
        actor=command.actor,
        occurred_at=command.occurred_at,
        recorded_at=recorded_at,
        idempotency_key=command.idempotency_key,
        reason=command.reason,
        correlation_id=command.correlation_id,
    )
    events = [superseded_event, creation_event]
    if command.also_approve_replacement:
        events.append(
            TransitionEvent(
                intent_id=replacement.intent_id,
                snapshot_id=replacement.snapshot_id,
                transition_sequence=2,
                from_state=LifecycleState.PENDING_REVIEW,
                to_state=LifecycleState.APPROVED,
                command_type=TransitionCommandType.APPROVE,
                actor=command.actor,
                occurred_at=command.occurred_at,
                recorded_at=recorded_at,
                idempotency_key=command.idempotency_key,
                reason=command.reason,
                content_hash=command.approval_content_hash,
                correlation_id=command.correlation_id,
            )
        )
    return TransitionResult(TransitionOutcome.ACCEPTED, events=tuple(events))


def _refuse(reason: TransitionRefusalReason, detail: str) -> TransitionResult:
    return TransitionResult(TransitionOutcome.REFUSED, refusal=TransitionRefusal(reason, detail))


def _require_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be a timezone-aware UTC datetime")


# --- Idempotency -----------------------------------------------------------


@dataclass(frozen=True)
class IdempotencyRecord:
    command_content_hash: str
    result: TransitionResult


class IdempotencyOutcome(str, Enum):
    NEW = "NEW"
    REPLAYED = "REPLAYED"
    CONFLICT = "CONFLICT"


@dataclass(frozen=True)
class IdempotencyResolution:
    outcome: IdempotencyOutcome
    result: TransitionResult | None = None
    conflict_detail: str | None = None


def compute_command_content_hash(command: TransitionCommand) -> str:
    """Hash the meaningful content of a command for idempotency comparison."""

    payload = {
        "command_type": command.command_type.value,
        "actor": {"actor_type": command.actor.actor_type.value, "actor_id": command.actor.actor_id},
        "occurred_at": command.occurred_at.astimezone(timezone.utc).isoformat(),
        "expected_prior_state": (command.expected_prior_state.value if command.expected_prior_state else None),
        "expected_prior_transition_sequence": command.expected_prior_transition_sequence,
        "reason": command.reason,
        "policy_reference": command.policy_reference,
        "approval_content_hash": command.approval_content_hash,
        "ledger_evidence": (
            sorted(
                (
                    entry.transaction_ref,
                    entry.symbol,
                    entry.side.value,
                    format(entry.quantity, "f"),
                    entry.recorded_at.astimezone(timezone.utc).isoformat(),
                )
                for entry in command.ledger_evidence.entries
            )
            if command.ledger_evidence is not None
            else None
        ),
        "submitted_snapshot": (
            {
                "snapshot_id": command.submitted_snapshot.snapshot_id,
                "content_hash": command.submitted_snapshot.content_hash,
                "revision": command.submitted_snapshot.revision,
            }
            if command.submitted_snapshot is not None
            else None
        ),
        "replacement_snapshot": (
            {
                "snapshot_id": command.replacement_snapshot.snapshot_id,
                "content_hash": command.replacement_snapshot.content_hash,
                "revision": command.replacement_snapshot.revision,
            }
            if command.replacement_snapshot is not None
            else None
        ),
        "also_approve_replacement": command.also_approve_replacement,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def resolve_idempotency(
    command: TransitionCommand,
    prior_records: Mapping[str, IdempotencyRecord],
) -> IdempotencyResolution:
    """Pure lookup: caller owns the ``prior_records`` mapping/store entirely."""

    content_hash = compute_command_content_hash(command)
    existing = prior_records.get(command.idempotency_key)
    if existing is None:
        return IdempotencyResolution(IdempotencyOutcome.NEW)
    if existing.command_content_hash != content_hash:
        return IdempotencyResolution(
            IdempotencyOutcome.CONFLICT,
            conflict_detail="idempotency_key reused with different command content",
        )
    return IdempotencyResolution(IdempotencyOutcome.REPLAYED, result=existing.result)
