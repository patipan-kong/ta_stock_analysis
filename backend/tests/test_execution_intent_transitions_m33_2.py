"""Focused pure M33.2 Execution Intent transition validator tests."""
from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from services.execution_intent_contracts import (
    Actor,
    ActorType,
    ExecutionIntentAllocationTerm,
    IntentKind,
    LifecycleState,
    ProvenanceCompleteness,
    SourceKind,
    SourceProvenance,
    TermSide,
    build_execution_intent_snapshot,
    build_execution_intent_terms,
)
from services.execution_intent_transitions import (
    AdmittedLedgerEvidence,
    FulfillmentOutcome,
    IdempotencyOutcome,
    IdempotencyRecord,
    LedgerEvidenceEntry,
    SnapshotLifecycleContext,
    TransitionCommand,
    TransitionCommandType,
    TransitionOutcome,
    TransitionRefusalReason,
    assess_fulfillment,
    compute_command_content_hash,
    resolve_idempotency,
    validate_transition,
)


_T0 = datetime(2026, 7, 16, 3, 0, tzinfo=timezone.utc)
_HUMAN = Actor(ActorType.HUMAN, "user:42")
_OTHER_HUMAN = Actor(ActorType.HUMAN, "user:99")
_SYSTEM = Actor(ActorType.SYSTEM, "system:expiry-policy")
_RECORDED_AT = _T0 + timedelta(seconds=1)


def _provenance(completeness=ProvenanceCompleteness.EXACT_FROZEN) -> SourceProvenance:
    return SourceProvenance(
        source_kind=SourceKind.LEGACY_RECOMMENDATION_SNAPSHOT,
        source_local_id="rec-1",
        source_contract_version="1",
        source_created_at=_T0 - timedelta(hours=1),
        source_digest="digest-abc",
        completeness=completeness,
    )


def _terms():
    return build_execution_intent_terms(
        "1",
        (
            ExecutionIntentAllocationTerm("KBANK.BK", TermSide.BUY, target_weight=Decimal("0.10")),
            ExecutionIntentAllocationTerm("PTT.BK", TermSide.SELL, target_value=Decimal("5000")),
        ),
    )


def _snapshot(**overrides):
    values = dict(
        snapshot_id="snap-1",
        intent_id="intent-1",
        revision=1,
        supersedes_snapshot_id=None,
        terms=_terms(),
        intent_kind=IntentKind.FOLLOW_RECOMMENDATION,
        workspace_id=1,
        portfolio_id=7,
        source_provenance=(_provenance(),),
        created_by_actor=_HUMAN,
        effective_at=_T0,
        recorded_at=_RECORDED_AT,
        expires_at=None,
    )
    values.update(overrides)
    return build_execution_intent_snapshot(**values)


def _ctx(snapshot, state, sequence=0) -> SnapshotLifecycleContext:
    return SnapshotLifecycleContext(snapshot=snapshot, current_state=state, current_transition_sequence=sequence)


def _cmd(command_type, *, actor=_HUMAN, expected_prior_state, expected_prior_sequence=0, **kwargs):
    kwargs.setdefault("idempotency_key", "key-1")
    kwargs.setdefault("occurred_at", _T0 + timedelta(minutes=5))
    return TransitionCommand(
        command_type=command_type,
        actor=actor,
        expected_prior_state=expected_prior_state,
        expected_prior_transition_sequence=expected_prior_sequence,
        **kwargs,
    )


def _entry(symbol, side, ref="tx-1", quantity=Decimal("100")) -> LedgerEvidenceEntry:
    return LedgerEvidenceEntry(
        transaction_ref=ref,
        symbol=symbol,
        side=side,
        quantity=quantity,
        recorded_at=_T0 + timedelta(minutes=10),
    )


class TestImmutability:
    def test_event_is_frozen(self):
        snapshot = _snapshot()
        result = validate_transition(
            _ctx(None, None),
            _cmd(TransitionCommandType.SUBMIT, expected_prior_state=None, submitted_snapshot=snapshot),
            recorded_at=_RECORDED_AT,
        )
        with pytest.raises(FrozenInstanceError):
            result.events[0].to_state = LifecycleState.APPROVED  # type: ignore[misc]


class TestSubmit:
    def test_creates_pending_review(self):
        snapshot = _snapshot()
        result = validate_transition(
            _ctx(None, None),
            _cmd(TransitionCommandType.SUBMIT, expected_prior_state=None, submitted_snapshot=snapshot),
            recorded_at=_RECORDED_AT,
        )
        assert result.outcome == TransitionOutcome.ACCEPTED
        (event,) = result.events
        assert event.from_state is None
        assert event.to_state == LifecycleState.PENDING_REVIEW
        assert event.transition_sequence == 1

    def test_refuses_when_context_already_has_a_snapshot(self):
        snapshot = _snapshot()
        result = validate_transition(
            _ctx(snapshot, LifecycleState.PENDING_REVIEW),
            _cmd(TransitionCommandType.SUBMIT, expected_prior_state=None, submitted_snapshot=snapshot),
            recorded_at=_RECORDED_AT,
        )
        assert result.outcome == TransitionOutcome.REFUSED
        assert result.refusal.reason == TransitionRefusalReason.UNEXPECTED_PAYLOAD

    def test_refuses_missing_submitted_snapshot(self):
        result = validate_transition(
            _ctx(None, None),
            _cmd(TransitionCommandType.SUBMIT, expected_prior_state=None),
            recorded_at=_RECORDED_AT,
        )
        assert result.refusal.reason == TransitionRefusalReason.MISSING_SUBMITTED_SNAPSHOT


class TestAllowedTransitionTable:
    @pytest.mark.parametrize(
        "from_state,command_type,to_state,actor",
        [
            (LifecycleState.PENDING_REVIEW, TransitionCommandType.DEFER, LifecycleState.DEFERRED, _HUMAN),
            (LifecycleState.PENDING_REVIEW, TransitionCommandType.REJECT, LifecycleState.REJECTED, _HUMAN),
            (LifecycleState.PENDING_REVIEW, TransitionCommandType.CANCEL, LifecycleState.CANCELLED, _HUMAN),
            (LifecycleState.DEFERRED, TransitionCommandType.RESUME, LifecycleState.PENDING_REVIEW, _HUMAN),
            (LifecycleState.DEFERRED, TransitionCommandType.CANCEL, LifecycleState.CANCELLED, _HUMAN),
            (LifecycleState.APPROVED, TransitionCommandType.DEFER, LifecycleState.DEFERRED, _HUMAN),
            (LifecycleState.APPROVED, TransitionCommandType.CANCEL, LifecycleState.CANCELLED, _HUMAN),
            (LifecycleState.APPROVED, TransitionCommandType.QUARANTINE, LifecycleState.QUARANTINED, _SYSTEM),
            (LifecycleState.APPROVED, TransitionCommandType.REQUEST_EXECUTION, LifecycleState.EXECUTION_REQUESTED, _SYSTEM),
            (LifecycleState.QUARANTINED, TransitionCommandType.RESOLVE_QUARANTINE, LifecycleState.PENDING_REVIEW, _HUMAN),
            (LifecycleState.QUARANTINED, TransitionCommandType.CANCEL, LifecycleState.CANCELLED, _HUMAN),
            (LifecycleState.EXECUTION_REQUESTED, TransitionCommandType.CANCEL, LifecycleState.CANCELLED, _HUMAN),
            (LifecycleState.EXECUTION_REQUESTED, TransitionCommandType.QUARANTINE, LifecycleState.QUARANTINED, _SYSTEM),
            (LifecycleState.PARTIALLY_EXECUTED, TransitionCommandType.CANCEL, LifecycleState.CANCELLED, _HUMAN),
            (LifecycleState.PARTIALLY_EXECUTED, TransitionCommandType.QUARANTINE, LifecycleState.QUARANTINED, _SYSTEM),
        ],
    )
    def test_allowed_transition_accepted(self, from_state, command_type, to_state, actor):
        snapshot = _snapshot()
        kwargs = {}
        if command_type in (TransitionCommandType.EXPIRE, TransitionCommandType.QUARANTINE):
            kwargs["policy_reference"] = "policy:v1"
        result = validate_transition(
            _ctx(snapshot, from_state, sequence=3),
            _cmd(command_type, actor=actor, expected_prior_state=from_state, expected_prior_sequence=3, **kwargs),
            recorded_at=_RECORDED_AT,
        )
        assert result.outcome == TransitionOutcome.ACCEPTED, result.refusal
        (event,) = result.events
        assert event.to_state == to_state
        assert event.transition_sequence == 4

    @pytest.mark.parametrize(
        "from_state,command_type",
        [
            (LifecycleState.PENDING_REVIEW, TransitionCommandType.RESUME),
            (LifecycleState.PENDING_REVIEW, TransitionCommandType.REQUEST_EXECUTION),
            (LifecycleState.PENDING_REVIEW, TransitionCommandType.RECORD_COMPLETION),
            (LifecycleState.DEFERRED, TransitionCommandType.APPROVE),
            (LifecycleState.APPROVED, TransitionCommandType.RESUME),
            (LifecycleState.APPROVED, TransitionCommandType.RECORD_COMPLETION),
            (LifecycleState.QUARANTINED, TransitionCommandType.APPROVE),
            (LifecycleState.EXECUTION_REQUESTED, TransitionCommandType.APPROVE),
            (LifecycleState.EXECUTION_REQUESTED, TransitionCommandType.SUPERSEDE_WITH_REPLACEMENT),
            (LifecycleState.PARTIALLY_EXECUTED, TransitionCommandType.SUPERSEDE_WITH_REPLACEMENT),
            (LifecycleState.PARTIALLY_EXECUTED, TransitionCommandType.REJECT),
        ],
    )
    def test_invalid_transition_refused(self, from_state, command_type):
        snapshot = _snapshot()
        result = validate_transition(
            _ctx(snapshot, from_state),
            _cmd(command_type, expected_prior_state=from_state),
            recorded_at=_RECORDED_AT,
        )
        assert result.outcome == TransitionOutcome.REFUSED
        assert result.refusal.reason in (
            TransitionRefusalReason.INVALID_TRANSITION,
            TransitionRefusalReason.ACTOR_NOT_AUTHORIZED,
        )

    @pytest.mark.parametrize(
        "terminal_state",
        [
            LifecycleState.REJECTED,
            LifecycleState.CANCELLED,
            LifecycleState.EXPIRED,
            LifecycleState.SUPERSEDED,
            LifecycleState.COMPLETED,
        ],
    )
    def test_terminal_states_accept_nothing(self, terminal_state):
        snapshot = _snapshot()
        result = validate_transition(
            _ctx(snapshot, terminal_state),
            _cmd(TransitionCommandType.CANCEL, expected_prior_state=terminal_state),
            recorded_at=_RECORDED_AT,
        )
        assert result.outcome == TransitionOutcome.REFUSED
        assert result.refusal.reason == TransitionRefusalReason.TERMINAL_STATE
        assert result.events == ()


class TestPriorStateAndSequence:
    def test_prior_state_mismatch_refused(self):
        snapshot = _snapshot()
        result = validate_transition(
            _ctx(snapshot, LifecycleState.PENDING_REVIEW),
            _cmd(TransitionCommandType.APPROVE, expected_prior_state=LifecycleState.APPROVED),
            recorded_at=_RECORDED_AT,
        )
        assert result.refusal.reason == TransitionRefusalReason.PRIOR_STATE_MISMATCH
        assert result.events == ()

    def test_prior_sequence_mismatch_refused(self):
        snapshot = _snapshot()
        result = validate_transition(
            _ctx(snapshot, LifecycleState.PENDING_REVIEW, sequence=2),
            _cmd(
                TransitionCommandType.REJECT,
                expected_prior_state=LifecycleState.PENDING_REVIEW,
                expected_prior_sequence=1,
            ),
            recorded_at=_RECORDED_AT,
        )
        assert result.refusal.reason == TransitionRefusalReason.PRIOR_SEQUENCE_MISMATCH
        assert result.events == ()


class TestApprovalHashBinding:
    def test_approve_requires_hash(self):
        snapshot = _snapshot()
        result = validate_transition(
            _ctx(snapshot, LifecycleState.PENDING_REVIEW),
            _cmd(TransitionCommandType.APPROVE, expected_prior_state=LifecycleState.PENDING_REVIEW),
            recorded_at=_RECORDED_AT,
        )
        assert result.refusal.reason == TransitionRefusalReason.APPROVAL_HASH_REQUIRED

    def test_approve_hash_mismatch_refused(self):
        snapshot = _snapshot()
        result = validate_transition(
            _ctx(snapshot, LifecycleState.PENDING_REVIEW),
            _cmd(
                TransitionCommandType.APPROVE,
                expected_prior_state=LifecycleState.PENDING_REVIEW,
                approval_content_hash="sha256:wrong",
            ),
            recorded_at=_RECORDED_AT,
        )
        assert result.refusal.reason == TransitionRefusalReason.APPROVAL_HASH_MISMATCH

    def test_approve_binds_exact_hash(self):
        snapshot = _snapshot()
        result = validate_transition(
            _ctx(snapshot, LifecycleState.PENDING_REVIEW),
            _cmd(
                TransitionCommandType.APPROVE,
                expected_prior_state=LifecycleState.PENDING_REVIEW,
                approval_content_hash=snapshot.content_hash,
            ),
            recorded_at=_RECORDED_AT,
        )
        assert result.outcome == TransitionOutcome.ACCEPTED
        assert result.events[0].content_hash == snapshot.content_hash

    def test_system_actor_cannot_approve(self):
        snapshot = _snapshot()
        result = validate_transition(
            _ctx(snapshot, LifecycleState.PENDING_REVIEW),
            _cmd(
                TransitionCommandType.APPROVE,
                actor=_SYSTEM,
                expected_prior_state=LifecycleState.PENDING_REVIEW,
                approval_content_hash=snapshot.content_hash,
            ),
            recorded_at=_RECORDED_AT,
        )
        assert result.refusal.reason == TransitionRefusalReason.ACTOR_NOT_AUTHORIZED

    def test_approve_refuses_incomplete_provenance(self):
        snapshot = _snapshot(source_provenance=(_provenance(ProvenanceCompleteness.INCOMPLETE),))
        result = validate_transition(
            _ctx(snapshot, LifecycleState.PENDING_REVIEW),
            _cmd(
                TransitionCommandType.APPROVE,
                expected_prior_state=LifecycleState.PENDING_REVIEW,
                approval_content_hash=snapshot.content_hash,
            ),
            recorded_at=_RECORDED_AT,
        )
        assert result.refusal.reason == TransitionRefusalReason.INCOMPLETE_PROVENANCE_CANNOT_APPROVE


class TestDeferResumeRequiresFreshReview:
    def test_deferred_resume_returns_to_pending_review_not_approved(self):
        snapshot = _snapshot()
        result = validate_transition(
            _ctx(snapshot, LifecycleState.DEFERRED),
            _cmd(TransitionCommandType.RESUME, expected_prior_state=LifecycleState.DEFERRED),
            recorded_at=_RECORDED_AT,
        )
        assert result.outcome == TransitionOutcome.ACCEPTED
        assert result.events[0].to_state == LifecycleState.PENDING_REVIEW

    def test_approved_cannot_be_resumed_directly(self):
        snapshot = _snapshot()
        result = validate_transition(
            _ctx(snapshot, LifecycleState.APPROVED),
            _cmd(TransitionCommandType.RESUME, expected_prior_state=LifecycleState.APPROVED),
            recorded_at=_RECORDED_AT,
        )
        assert result.outcome == TransitionOutcome.REFUSED


class TestExpiryAndQuarantinePolicy:
    def test_expire_requires_policy_reference(self):
        snapshot = _snapshot()
        result = validate_transition(
            _ctx(snapshot, LifecycleState.PENDING_REVIEW),
            _cmd(TransitionCommandType.EXPIRE, actor=_SYSTEM, expected_prior_state=LifecycleState.PENDING_REVIEW),
            recorded_at=_RECORDED_AT,
        )
        assert result.refusal.reason == TransitionRefusalReason.POLICY_REFERENCE_REQUIRED

    def test_expire_by_human_actor_refused(self):
        snapshot = _snapshot()
        result = validate_transition(
            _ctx(snapshot, LifecycleState.PENDING_REVIEW),
            _cmd(
                TransitionCommandType.EXPIRE,
                actor=_HUMAN,
                expected_prior_state=LifecycleState.PENDING_REVIEW,
                policy_reference="policy:v1",
            ),
            recorded_at=_RECORDED_AT,
        )
        assert result.refusal.reason == TransitionRefusalReason.ACTOR_NOT_AUTHORIZED

    def test_quarantine_by_human_actor_refused(self):
        snapshot = _snapshot()
        result = validate_transition(
            _ctx(snapshot, LifecycleState.APPROVED),
            _cmd(
                TransitionCommandType.QUARANTINE,
                actor=_HUMAN,
                expected_prior_state=LifecycleState.APPROVED,
                policy_reference="policy:v1",
            ),
            recorded_at=_RECORDED_AT,
        )
        assert result.refusal.reason == TransitionRefusalReason.ACTOR_NOT_AUTHORIZED


class TestFulfillmentAssessment:
    def test_no_evidence(self):
        assert assess_fulfillment(_terms(), AdmittedLedgerEvidence(())) == FulfillmentOutcome.NO_EVIDENCE

    def test_partial(self):
        evidence = AdmittedLedgerEvidence((_entry("KBANK.BK", TermSide.BUY),))
        assert assess_fulfillment(_terms(), evidence) == FulfillmentOutcome.PARTIAL

    def test_complete(self):
        evidence = AdmittedLedgerEvidence(
            (
                _entry("KBANK.BK", TermSide.BUY),
                _entry("PTT.BK", TermSide.SELL, ref="tx-2"),
            )
        )
        assert assess_fulfillment(_terms(), evidence) == FulfillmentOutcome.COMPLETE

    def test_conflict_on_unrelated_symbol(self):
        evidence = AdmittedLedgerEvidence((_entry("UNRELATED.BK", TermSide.BUY),))
        assert assess_fulfillment(_terms(), evidence) == FulfillmentOutcome.CONFLICT


class TestExecutionEvidenceGating:
    def test_record_partial_requires_ledger_evidence(self):
        snapshot = _snapshot()
        result = validate_transition(
            _ctx(snapshot, LifecycleState.EXECUTION_REQUESTED),
            _cmd(
                TransitionCommandType.RECORD_PARTIAL_EXECUTION,
                actor=_SYSTEM,
                expected_prior_state=LifecycleState.EXECUTION_REQUESTED,
            ),
            recorded_at=_RECORDED_AT,
        )
        assert result.refusal.reason == TransitionRefusalReason.LEDGER_EVIDENCE_REQUIRED

    def test_record_partial_accepted_with_partial_coverage(self):
        snapshot = _snapshot()
        evidence = AdmittedLedgerEvidence((_entry("KBANK.BK", TermSide.BUY),))
        result = validate_transition(
            _ctx(snapshot, LifecycleState.EXECUTION_REQUESTED),
            _cmd(
                TransitionCommandType.RECORD_PARTIAL_EXECUTION,
                actor=_SYSTEM,
                expected_prior_state=LifecycleState.EXECUTION_REQUESTED,
                ledger_evidence=evidence,
            ),
            recorded_at=_RECORDED_AT,
        )
        assert result.outcome == TransitionOutcome.ACCEPTED
        assert result.events[0].to_state == LifecycleState.PARTIALLY_EXECUTED
        assert result.events[0].ledger_evidence_ref == ("tx-1",)

    def test_record_partial_refused_when_evidence_is_actually_complete(self):
        snapshot = _snapshot()
        evidence = AdmittedLedgerEvidence(
            (
                _entry("KBANK.BK", TermSide.BUY),
                _entry("PTT.BK", TermSide.SELL, ref="tx-2"),
            )
        )
        result = validate_transition(
            _ctx(snapshot, LifecycleState.EXECUTION_REQUESTED),
            _cmd(
                TransitionCommandType.RECORD_PARTIAL_EXECUTION,
                actor=_SYSTEM,
                expected_prior_state=LifecycleState.EXECUTION_REQUESTED,
                ledger_evidence=evidence,
            ),
            recorded_at=_RECORDED_AT,
        )
        assert result.refusal.reason == TransitionRefusalReason.LEDGER_EVIDENCE_INSUFFICIENT

    def test_record_completion_accepted_with_full_coverage(self):
        snapshot = _snapshot()
        evidence = AdmittedLedgerEvidence(
            (
                _entry("KBANK.BK", TermSide.BUY),
                _entry("PTT.BK", TermSide.SELL, ref="tx-2"),
            )
        )
        result = validate_transition(
            _ctx(snapshot, LifecycleState.EXECUTION_REQUESTED),
            _cmd(
                TransitionCommandType.RECORD_COMPLETION,
                actor=_SYSTEM,
                expected_prior_state=LifecycleState.EXECUTION_REQUESTED,
                ledger_evidence=evidence,
            ),
            recorded_at=_RECORDED_AT,
        )
        assert result.outcome == TransitionOutcome.ACCEPTED
        assert result.events[0].to_state == LifecycleState.COMPLETED

    def test_record_completion_refused_on_conflicting_evidence(self):
        snapshot = _snapshot()
        evidence = AdmittedLedgerEvidence((_entry("UNRELATED.BK", TermSide.BUY),))
        result = validate_transition(
            _ctx(snapshot, LifecycleState.EXECUTION_REQUESTED),
            _cmd(
                TransitionCommandType.RECORD_COMPLETION,
                actor=_SYSTEM,
                expected_prior_state=LifecycleState.EXECUTION_REQUESTED,
                ledger_evidence=evidence,
            ),
            recorded_at=_RECORDED_AT,
        )
        assert result.refusal.reason == TransitionRefusalReason.LEDGER_EVIDENCE_CONFLICT

    def test_human_actor_cannot_record_completion(self):
        snapshot = _snapshot()
        evidence = AdmittedLedgerEvidence(
            (
                _entry("KBANK.BK", TermSide.BUY),
                _entry("PTT.BK", TermSide.SELL, ref="tx-2"),
            )
        )
        result = validate_transition(
            _ctx(snapshot, LifecycleState.EXECUTION_REQUESTED),
            _cmd(
                TransitionCommandType.RECORD_COMPLETION,
                actor=_HUMAN,
                expected_prior_state=LifecycleState.EXECUTION_REQUESTED,
                ledger_evidence=evidence,
            ),
            recorded_at=_RECORDED_AT,
        )
        assert result.refusal.reason == TransitionRefusalReason.ACTOR_NOT_AUTHORIZED


class TestSupersession:
    def _replacement(self, current, **overrides):
        values = dict(
            snapshot_id="snap-2",
            intent_id=current.intent_id,
            revision=current.revision + 1,
            supersedes_snapshot_id=current.snapshot_id,
            terms=_terms(),
            intent_kind=IntentKind.MANUAL_OVERRIDE,
            workspace_id=current.workspace_id,
            portfolio_id=current.portfolio_id,
            source_provenance=(_provenance(),),
            created_by_actor=_HUMAN,
            effective_at=_T0 + timedelta(hours=1),
            recorded_at=_RECORDED_AT + timedelta(hours=1),
            expires_at=None,
        )
        values.update(overrides)
        return build_execution_intent_snapshot(**values)

    def test_supersede_pending_review_produces_two_events(self):
        current = _snapshot()
        replacement = self._replacement(current)
        result = validate_transition(
            _ctx(current, LifecycleState.PENDING_REVIEW),
            _cmd(
                TransitionCommandType.SUPERSEDE_WITH_REPLACEMENT,
                expected_prior_state=LifecycleState.PENDING_REVIEW,
                replacement_snapshot=replacement,
            ),
            recorded_at=_RECORDED_AT,
        )
        assert result.outcome == TransitionOutcome.ACCEPTED
        assert len(result.events) == 2
        superseded, created = result.events
        assert superseded.snapshot_id == current.snapshot_id
        assert superseded.to_state == LifecycleState.SUPERSEDED
        assert created.snapshot_id == replacement.snapshot_id
        assert created.to_state == LifecycleState.PENDING_REVIEW

    def test_supersede_approved_requires_human_actor(self):
        current = _snapshot()
        replacement = self._replacement(current)
        result = validate_transition(
            _ctx(current, LifecycleState.APPROVED),
            _cmd(
                TransitionCommandType.SUPERSEDE_WITH_REPLACEMENT,
                actor=_SYSTEM,
                expected_prior_state=LifecycleState.APPROVED,
                replacement_snapshot=replacement,
            ),
            recorded_at=_RECORDED_AT,
        )
        assert result.refusal.reason == TransitionRefusalReason.SUPERSESSION_REQUIRES_HUMAN_ACT
        assert result.events == ()

    def test_supersede_approved_by_human_accepted(self):
        current = _snapshot()
        replacement = self._replacement(current)
        result = validate_transition(
            _ctx(current, LifecycleState.APPROVED),
            _cmd(
                TransitionCommandType.SUPERSEDE_WITH_REPLACEMENT,
                actor=_HUMAN,
                expected_prior_state=LifecycleState.APPROVED,
                replacement_snapshot=replacement,
            ),
            recorded_at=_RECORDED_AT,
        )
        assert result.outcome == TransitionOutcome.ACCEPTED

    def test_supersede_with_atomic_approval(self):
        current = _snapshot()
        replacement = self._replacement(current)
        result = validate_transition(
            _ctx(current, LifecycleState.PENDING_REVIEW),
            _cmd(
                TransitionCommandType.SUPERSEDE_WITH_REPLACEMENT,
                expected_prior_state=LifecycleState.PENDING_REVIEW,
                replacement_snapshot=replacement,
                also_approve_replacement=True,
                approval_content_hash=replacement.content_hash,
            ),
            recorded_at=_RECORDED_AT,
        )
        assert result.outcome == TransitionOutcome.ACCEPTED
        assert len(result.events) == 3
        assert result.events[2].to_state == LifecycleState.APPROVED

    def test_supersede_with_atomic_approval_hash_mismatch_refuses_all_events(self):
        current = _snapshot()
        replacement = self._replacement(current)
        result = validate_transition(
            _ctx(current, LifecycleState.PENDING_REVIEW),
            _cmd(
                TransitionCommandType.SUPERSEDE_WITH_REPLACEMENT,
                expected_prior_state=LifecycleState.PENDING_REVIEW,
                replacement_snapshot=replacement,
                also_approve_replacement=True,
                approval_content_hash="sha256:wrong",
            ),
            recorded_at=_RECORDED_AT,
        )
        assert result.outcome == TransitionOutcome.REFUSED
        assert result.events == ()

    def test_supersede_rejects_mismatched_lineage(self):
        current = _snapshot()
        replacement = self._replacement(current, supersedes_snapshot_id="some-other-snapshot", revision=2)
        result = validate_transition(
            _ctx(current, LifecycleState.PENDING_REVIEW),
            _cmd(
                TransitionCommandType.SUPERSEDE_WITH_REPLACEMENT,
                expected_prior_state=LifecycleState.PENDING_REVIEW,
                replacement_snapshot=replacement,
            ),
            recorded_at=_RECORDED_AT,
        )
        assert result.refusal.reason == TransitionRefusalReason.INVALID_REPLACEMENT_LINEAGE

    def test_supersede_rejects_revision_gap(self):
        current = _snapshot()
        replacement = self._replacement(current, revision=3)
        result = validate_transition(
            _ctx(current, LifecycleState.PENDING_REVIEW),
            _cmd(
                TransitionCommandType.SUPERSEDE_WITH_REPLACEMENT,
                expected_prior_state=LifecycleState.PENDING_REVIEW,
                replacement_snapshot=replacement,
            ),
            recorded_at=_RECORDED_AT,
        )
        assert result.refusal.reason == TransitionRefusalReason.INVALID_REPLACEMENT_REVISION

    def test_supersede_rejects_scope_change(self):
        current = _snapshot()
        replacement = self._replacement(current, portfolio_id=current.portfolio_id + 1)
        result = validate_transition(
            _ctx(current, LifecycleState.PENDING_REVIEW),
            _cmd(
                TransitionCommandType.SUPERSEDE_WITH_REPLACEMENT,
                expected_prior_state=LifecycleState.PENDING_REVIEW,
                replacement_snapshot=replacement,
            ),
            recorded_at=_RECORDED_AT,
        )
        assert result.refusal.reason == TransitionRefusalReason.SCOPE_IMMUTABLE

    def test_supersede_missing_replacement_refused(self):
        current = _snapshot()
        result = validate_transition(
            _ctx(current, LifecycleState.PENDING_REVIEW),
            _cmd(
                TransitionCommandType.SUPERSEDE_WITH_REPLACEMENT,
                expected_prior_state=LifecycleState.PENDING_REVIEW,
            ),
            recorded_at=_RECORDED_AT,
        )
        assert result.refusal.reason == TransitionRefusalReason.MISSING_REPLACEMENT_SNAPSHOT


class TestByteEquivalentOutput:
    def test_identical_inputs_produce_equal_events(self):
        snapshot = _snapshot()
        command = _cmd(
            TransitionCommandType.APPROVE,
            expected_prior_state=LifecycleState.PENDING_REVIEW,
            approval_content_hash=snapshot.content_hash,
        )
        result_a = validate_transition(_ctx(snapshot, LifecycleState.PENDING_REVIEW), command, recorded_at=_RECORDED_AT)
        result_b = validate_transition(_ctx(snapshot, LifecycleState.PENDING_REVIEW), command, recorded_at=_RECORDED_AT)
        assert result_a == result_b


class TestIdempotency:
    def test_new_key_is_new(self):
        snapshot = _snapshot()
        command = _cmd(
            TransitionCommandType.APPROVE,
            expected_prior_state=LifecycleState.PENDING_REVIEW,
            approval_content_hash=snapshot.content_hash,
        )
        resolution = resolve_idempotency(command, {})
        assert resolution.outcome == IdempotencyOutcome.NEW

    def test_same_key_same_content_replays(self):
        snapshot = _snapshot()
        command = _cmd(
            TransitionCommandType.APPROVE,
            expected_prior_state=LifecycleState.PENDING_REVIEW,
            approval_content_hash=snapshot.content_hash,
        )
        result = validate_transition(_ctx(snapshot, LifecycleState.PENDING_REVIEW), command, recorded_at=_RECORDED_AT)
        prior = {command.idempotency_key: IdempotencyRecord(compute_command_content_hash(command), result)}

        replay_command = _cmd(
            TransitionCommandType.APPROVE,
            expected_prior_state=LifecycleState.PENDING_REVIEW,
            approval_content_hash=snapshot.content_hash,
            occurred_at=command.occurred_at,
        )
        resolution = resolve_idempotency(replay_command, prior)
        assert resolution.outcome == IdempotencyOutcome.REPLAYED
        assert resolution.result == result

    def test_same_key_different_content_conflicts(self):
        snapshot = _snapshot()
        command = _cmd(
            TransitionCommandType.APPROVE,
            expected_prior_state=LifecycleState.PENDING_REVIEW,
            approval_content_hash=snapshot.content_hash,
        )
        result = validate_transition(_ctx(snapshot, LifecycleState.PENDING_REVIEW), command, recorded_at=_RECORDED_AT)
        prior = {command.idempotency_key: IdempotencyRecord(compute_command_content_hash(command), result)}

        different_command = _cmd(
            TransitionCommandType.REJECT,
            expected_prior_state=LifecycleState.PENDING_REVIEW,
        )
        resolution = resolve_idempotency(different_command, prior)
        assert resolution.outcome == IdempotencyOutcome.CONFLICT
        assert resolution.result is None
