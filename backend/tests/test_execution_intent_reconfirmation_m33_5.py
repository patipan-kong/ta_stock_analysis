"""Pure M33.5 proposal and reconfirmation contract tests."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from services.execution_intent_authority import (
    AuthorityLevel,
    AuthorityReasonCode,
    AuthorityScope,
    AuthorityVerificationResult,
    RevocationStatus,
)
from services.execution_intent_contracts import (
    Actor,
    ActorType,
    ExecutionIntentAllocationTerm,
    IntentKind,
    ProvenanceCompleteness,
    SourceKind,
    SourceProvenance,
    TermSide,
)
from services.execution_intent_reconfirmation import (
    ProposalCompleteness,
    ProposalDecision,
    ProposalDecisionKind,
    ProposalOrigin,
    ProposalOutcome,
    ProposalRefusalReason,
    ProposalWarning,
    ProposalWarningCode,
    ProposalWarningSeverity,
    build_proposal_candidate,
    compute_proposal_candidate_digest,
    finalize_proposal_for_review,
    validate_proposal_eligibility,
)


_T0 = datetime(2026, 7, 17, 3, 0, tzinfo=timezone.utc)
_CERT_DIGEST = "sha256:" + ("c" * 64)


def _scope(**overrides) -> AuthorityScope:
    values = dict(
        workspace_id=1,
        portfolio_id=7,
        authority_namespace="deployment:test",
        environment_id="env:test",
    )
    values.update(overrides)
    return AuthorityScope(**values)


def _authority_result(
    level: AuthorityLevel = AuthorityLevel.CERTIFIED_PROPOSAL_ONLY,
    *,
    may_build_proposal: bool | None = None,
    reasons: tuple[AuthorityReasonCode, ...] | None = None,
    verified_scope: AuthorityScope | None = None,
) -> AuthorityVerificationResult:
    exact = level == AuthorityLevel.CERTIFIED_EXACT
    if may_build_proposal is None:
        may_build_proposal = level in (
            AuthorityLevel.CERTIFIED_EXACT,
            AuthorityLevel.CERTIFIED_PROPOSAL_ONLY,
        )
    if reasons is None:
        reasons = () if exact else (AuthorityReasonCode.FRESH_RECONFIRMATION_REQUIRED,)
    return AuthorityVerificationResult(
        verification_contract_version="1",
        certificate_id="certificate:1" if level != AuthorityLevel.UNVERIFIABLE else None,
        certificate_digest=_CERT_DIGEST if level != AuthorityLevel.UNVERIFIABLE else None,
        authority_level=level,
        reason_codes=reasons,
        verified_evidence_ids=("approved",),
        rejected_evidence_ids=(),
        verified_scope=verified_scope if verified_scope is not None else _scope(),
        verified_historical_actor_id="user:historical" if exact else None,
        verified_approval_occurred_at=_T0 if exact else None,
        verified_target_snapshot_id="snapshot:target" if exact else None,
        verified_target_content_hash=("sha256:" + ("a" * 64)) if exact else None,
        revocation_status=RevocationStatus.NOT_REVOKED,
        provenance_completeness=(
            ProvenanceCompleteness.EXACT_FROZEN
            if exact
            else (
                ProvenanceCompleteness.LEGACY_RECONSTRUCTED
                if level == AuthorityLevel.CERTIFIED_PROPOSAL_ONLY
                else ProvenanceCompleteness.INCOMPLETE
            )
        ),
        may_build_exact_snapshot=exact,
        may_build_proposal=may_build_proposal,
        requires_reconfirmation=may_build_proposal and not exact,
        may_recreate_historical_approval=exact,
    )


def _allocations(weight: str = "0.10") -> tuple[ExecutionIntentAllocationTerm, ...]:
    return (
        ExecutionIntentAllocationTerm(
            "KBANK.BK",
            TermSide.BUY,
            target_weight=Decimal(weight),
        ),
        ExecutionIntentAllocationTerm(
            "PTT.BK",
            TermSide.SELL,
            target_value=Decimal("5000"),
        ),
    )


def _provenance(
    completeness: ProvenanceCompleteness = ProvenanceCompleteness.LEGACY_RECONSTRUCTED,
    *,
    source_kind: SourceKind = SourceKind.LEGACY_RECOMMENDATION_SNAPSHOT,
) -> SourceProvenance:
    return SourceProvenance(
        source_kind=source_kind,
        source_local_id="recommendation:1",
        source_contract_version="1",
        source_created_at=_T0 - timedelta(days=1),
        source_digest="legacy-source-digest",
        completeness=completeness,
    )


def _candidate_result(**overrides):
    values = dict(
        proposal_candidate_id="proposal:1",
        authority_result=_authority_result(),
        origins=frozenset({ProposalOrigin.LEGACY_RECOMMENDATION_CANDIDATE}),
        intent_kind=IntentKind.FOLLOW_RECOMMENDATION,
        candidate_allocations=_allocations(),
        terms_schema_version="1",
        scope=_scope(),
        source_provenance=(_provenance(),),
        created_at=_T0,
        effective_at=_T0 + timedelta(days=1),
        expires_at=None,
        notes=None,
        warnings=(),
    )
    values.update(overrides)
    return build_proposal_candidate(**values)


def _candidate(**overrides):
    result = _candidate_result(**overrides)
    assert result.accepted, result.refusal
    return result.candidate


def _decision(candidate, **overrides) -> ProposalDecision:
    values = dict(
        contract_version="1",
        decision_kind=ProposalDecisionKind.FINALIZE_FOR_REVIEW,
        proposal_candidate_id=candidate.proposal_candidate_id,
        expected_candidate_digest=candidate.candidate_digest,
        actor=Actor(ActorType.HUMAN, "user:current"),
        occurred_at=_T0 + timedelta(hours=1),
        confirmed_workspace_id=candidate.scope.workspace_id,
        confirmed_portfolio_id=candidate.scope.portfolio_id,
        acknowledged_warning_codes=frozenset(warning.code for warning in candidate.warnings),
        final_terms_schema_version="1",
        final_allocations=_allocations(),
        final_notes=None,
        final_intent_kind=IntentKind.FOLLOW_RECOMMENDATION,
        effective_at=_T0 + timedelta(days=1),
        expires_at=None,
        reason=None,
    )
    values.update(overrides)
    return ProposalDecision(**values)


class TestProposalEligibility:
    def test_exact_certificate_may_optionally_produce_proposal(self):
        result = _candidate_result(
            authority_result=_authority_result(AuthorityLevel.CERTIFIED_EXACT),
            source_provenance=(_provenance(ProvenanceCompleteness.EXACT_FROZEN),),
        )
        assert result.accepted
        assert result.candidate.authority_level == AuthorityLevel.CERTIFIED_EXACT
        assert ProposalWarningCode.FRESH_APPROVAL_REQUIRED in {
            warning.code for warning in result.candidate.warnings
        }

    def test_proposal_only_authority_produces_warning_rich_candidate(self):
        candidate = _candidate()
        warning_codes = {warning.code for warning in candidate.warnings}
        assert ProposalWarningCode.HISTORICAL_APPROVAL_UNVERIFIED in warning_codes
        assert ProposalWarningCode.HISTORICAL_ACTOR_UNVERIFIED in warning_codes
        assert ProposalWarningCode.RECOMMENDATION_ONLY_NOT_ACCEPTED_TERMS in warning_codes
        assert ProposalWarningCode.FRESH_APPROVAL_REQUIRED in warning_codes

    def test_unverifiable_complete_candidate_can_be_explicitly_eligible(self):
        result = _candidate_result(
            authority_result=_authority_result(
                AuthorityLevel.UNVERIFIABLE,
                may_build_proposal=True,
                reasons=(
                    AuthorityReasonCode.CERTIFICATE_MISSING,
                    AuthorityReasonCode.FRESH_RECONFIRMATION_REQUIRED,
                ),
            )
        )
        assert result.accepted
        assert result.candidate.authority_level == AuthorityLevel.UNVERIFIABLE

    @pytest.mark.parametrize(
        "level,reason",
        [
            (AuthorityLevel.CONFLICTING, ProposalRefusalReason.AUTHORITY_CONFLICTING),
            (AuthorityLevel.OUT_OF_SCOPE, ProposalRefusalReason.AUTHORITY_OUT_OF_SCOPE),
        ],
    )
    def test_conflicting_and_out_of_scope_authority_refused(self, level, reason):
        authority = _authority_result(level, may_build_proposal=False)
        result = validate_proposal_eligibility(
            authority,
            frozenset({ProposalOrigin.LEGACY_RECOMMENDATION_CANDIDATE}),
        )
        assert result.outcome == ProposalOutcome.REFUSED
        assert result.refusal.reason == reason

    @pytest.mark.parametrize(
        "origin",
        [
            ProposalOrigin.SHADOW_PORTFOLIO,
            ProposalOrigin.TRANSACTION_LINK,
            ProposalOrigin.TRANSACTION_ROW,
            ProposalOrigin.CURRENT_PORTFOLIO_HOLDINGS,
            ProposalOrigin.FUTURE_CANONICAL_EXECUTION_PLAN,
        ],
    )
    def test_prohibited_origins_refused(self, origin):
        result = _candidate_result(origins=frozenset({origin}))
        assert result.outcome == ProposalOutcome.REFUSED
        assert result.refusal.reason == ProposalRefusalReason.PROHIBITED_ORIGIN

    def test_future_plan_source_provenance_refused(self):
        result = _candidate_result(
            source_provenance=(
                _provenance(source_kind=SourceKind.FUTURE_CANONICAL_EXECUTION_PLAN),
            )
        )
        assert result.refusal.reason == ProposalRefusalReason.PROHIBITED_ORIGIN

    def test_non_exact_authority_cannot_overstate_legacy_provenance(self):
        result = _candidate_result(
            source_provenance=(_provenance(ProvenanceCompleteness.EXACT_FROZEN),)
        )
        assert result.refusal.reason == ProposalRefusalReason.PROVENANCE_AUTHORITY_OVERSTATED

    def test_verified_scope_mismatch_refused(self):
        result = _candidate_result(scope=_scope(portfolio_id=8))
        assert result.refusal.reason == ProposalRefusalReason.SCOPE_MISMATCH


class TestCandidateConstructionAndHashing:
    def test_complete_candidate_marked_reviewable(self):
        candidate = _candidate()
        assert candidate.completeness == ProposalCompleteness.COMPLETE_REVIEWABLE
        assert candidate.candidate_terms is not None

    @pytest.mark.parametrize(
        "allocations",
        [
            None,
            (),
            (
                ExecutionIntentAllocationTerm("KBANK.BK", TermSide.BUY),
            ),
        ],
    )
    def test_incomplete_candidate_marked_edit_required(self, allocations):
        candidate = _candidate(candidate_allocations=allocations)
        assert candidate.completeness == ProposalCompleteness.EDIT_REQUIRED
        assert candidate.candidate_terms is None
        assert ProposalWarningCode.FINAL_TERMS_EDIT_REQUIRED in {
            warning.code for warning in candidate.warnings
        }

    def test_candidate_is_frozen(self):
        candidate = _candidate()
        with pytest.raises(FrozenInstanceError):
            candidate.completeness = ProposalCompleteness.UNUSABLE  # type: ignore[misc]

    def test_candidate_digest_deterministic(self):
        assert _candidate().candidate_digest == _candidate().candidate_digest

    def test_candidate_digest_allocation_order_independent(self):
        forward = _candidate(candidate_allocations=_allocations())
        backward = _candidate(candidate_allocations=tuple(reversed(_allocations())))
        assert forward.candidate_digest == backward.candidate_digest

    def test_warning_order_independent(self):
        warning_a = ProposalWarning(
            ProposalWarningCode.TARGET_UNIT_REVIEW_REQUIRED,
            "Review units.",
            ProposalWarningSeverity.WARNING,
        )
        warning_b = ProposalWarning(
            ProposalWarningCode.ACTION_MAPPING_REVIEW_REQUIRED,
            "Review actions.",
            ProposalWarningSeverity.WARNING,
        )
        forward = _candidate(warnings=(warning_a, warning_b))
        backward = _candidate(warnings=(warning_b, warning_a))
        assert forward.candidate_digest == backward.candidate_digest

    @pytest.mark.parametrize(
        "mutator",
        [
            lambda item: replace(item, proposal_candidate_id="proposal:2"),
            lambda item: replace(item, intent_kind=IntentKind.MANUAL_OVERRIDE),
            lambda item: replace(item, scope=_scope(environment_id="other")),
            lambda item: replace(item, created_at=item.created_at + timedelta(seconds=1)),
            lambda item: replace(item, effective_at=item.effective_at + timedelta(seconds=1)),
            lambda item: replace(item, completeness=ProposalCompleteness.EDIT_REQUIRED),
        ],
    )
    def test_candidate_digest_sensitive_to_included_fields(self, mutator):
        candidate = _candidate()
        assert compute_proposal_candidate_digest(candidate) != compute_proposal_candidate_digest(mutator(candidate))

    def test_candidate_digest_excludes_stored_digest(self):
        candidate = _candidate()
        changed = replace(candidate, candidate_digest="sha256:" + ("f" * 64))
        assert compute_proposal_candidate_digest(candidate) == compute_proposal_candidate_digest(changed)

    def test_naive_candidate_datetime_rejected(self):
        with pytest.raises(ValueError):
            _candidate_result(created_at=datetime(2026, 7, 17, 3, 0))


class TestProposalFinalization:
    def test_stale_candidate_digest_refused(self):
        candidate = _candidate()
        result = finalize_proposal_for_review(
            candidate,
            _decision(candidate, expected_candidate_digest="sha256:" + ("d" * 64)),
        )
        assert result.refusal.reason == ProposalRefusalReason.STALE_CANDIDATE_DIGEST

    def test_mutated_candidate_content_digest_refused(self):
        candidate = _candidate()
        tampered = replace(candidate, intent_kind=IntentKind.MANUAL_OVERRIDE)
        result = finalize_proposal_for_review(tampered, _decision(tampered))
        assert result.refusal.reason == ProposalRefusalReason.CANDIDATE_DIGEST_MISMATCH

    def test_missing_warning_acknowledgement_refused(self):
        candidate = _candidate()
        result = finalize_proposal_for_review(
            candidate,
            _decision(candidate, acknowledged_warning_codes=frozenset()),
        )
        assert result.refusal.reason == ProposalRefusalReason.REQUIRED_WARNING_NOT_ACKNOWLEDGED

    @pytest.mark.parametrize(
        "overrides",
        [
            {"confirmed_workspace_id": 2},
            {"confirmed_portfolio_id": 8},
        ],
    )
    def test_scope_mismatch_refused(self, overrides):
        candidate = _candidate()
        result = finalize_proposal_for_review(candidate, _decision(candidate, **overrides))
        assert result.refusal.reason == ProposalRefusalReason.SCOPE_MISMATCH

    @pytest.mark.parametrize(
        "actor",
        [
            Actor(ActorType.SYSTEM, "system:proposal"),
            Actor(ActorType.HUMAN, ""),
        ],
    )
    def test_current_human_actor_required(self, actor):
        candidate = _candidate()
        result = finalize_proposal_for_review(candidate, _decision(candidate, actor=actor))
        assert result.refusal.reason == ProposalRefusalReason.CURRENT_HUMAN_ACTOR_REQUIRED

    def test_final_terms_required(self):
        candidate = _candidate()
        result = finalize_proposal_for_review(
            candidate,
            _decision(candidate, final_allocations=()),
        )
        assert result.refusal.reason == ProposalRefusalReason.FINAL_TERMS_REQUIRED

    @pytest.mark.parametrize(
        "allocations",
        [
            (
                ExecutionIntentAllocationTerm("KBANK.BK", TermSide.BUY, target_weight=Decimal("0.1")),
                ExecutionIntentAllocationTerm("KBANK.BK", TermSide.BUY, target_weight=Decimal("0.2")),
            ),
            (
                ExecutionIntentAllocationTerm(
                    "KBANK.BK",
                    TermSide.BUY,
                    target_weight=Decimal("Infinity"),
                ),
            ),
        ],
    )
    def test_final_terms_validation_returns_typed_refusal(self, allocations):
        candidate = _candidate()
        result = finalize_proposal_for_review(
            candidate,
            _decision(candidate, final_allocations=allocations),
        )
        assert result.outcome == ProposalOutcome.REFUSED
        assert result.refusal.reason == ProposalRefusalReason.FINAL_TERMS_INVALID

    def test_finalization_requires_effective_time(self):
        candidate = _candidate()
        result = finalize_proposal_for_review(candidate, _decision(candidate, effective_at=None))
        assert result.refusal.reason == ProposalRefusalReason.EFFECTIVE_TIME_REQUIRED

    def test_non_finalize_decision_does_not_prepare_snapshot(self):
        candidate = _candidate()
        result = finalize_proposal_for_review(
            candidate,
            _decision(candidate, decision_kind=ProposalDecisionKind.REJECT_PROPOSAL),
        )
        assert result.refusal.reason == ProposalRefusalReason.DECISION_NOT_FINALIZE
        assert result.preparation is None

    def test_incomplete_provenance_refused_before_preparation(self):
        candidate = _candidate(
            source_provenance=(_provenance(ProvenanceCompleteness.INCOMPLETE),)
        )
        result = finalize_proposal_for_review(candidate, _decision(candidate))
        assert result.refusal.reason == ProposalRefusalReason.INCOMPLETE_PROVENANCE

    def test_finalization_returns_preparation_data_only(self):
        candidate = _candidate()
        result = finalize_proposal_for_review(candidate, _decision(candidate))
        assert result.accepted
        preparation = result.preparation
        assert preparation.final_terms.allocations == _allocations()
        assert preparation.workspace_id == 1
        assert preparation.portfolio_id == 7
        assert preparation.fresh_intent_id_required is True
        assert preparation.fresh_snapshot_id_required is True
        assert preparation.pending_review_submission_required is True
        assert preparation.separate_fresh_approval_required is True
        assert preparation.historical_approval_inherited is False
        assert preparation.historical_lifecycle_state_inherited is False

        field_names = {field.name for field in fields(preparation)}
        assert "intent_id" not in field_names
        assert "snapshot_id" not in field_names
        assert "content_hash" not in field_names
        assert "approval_event" not in field_names
        assert "lifecycle_state" not in field_names

    def test_legacy_approval_and_history_are_not_inherited(self):
        candidate = _candidate()
        preparation = finalize_proposal_for_review(candidate, _decision(candidate)).preparation
        assert preparation.current_actor.actor_id == "user:current"
        assert preparation.legacy_source_provenance[0].completeness == ProvenanceCompleteness.LEGACY_RECONSTRUCTED
        assert preparation.manual_human_input_provenance_required is True

    def test_finalization_with_human_edits_uses_final_terms(self):
        candidate = _candidate()
        edited = (
            ExecutionIntentAllocationTerm(
                "KBANK.BK",
                TermSide.BUY,
                target_weight=Decimal("0.25"),
            ),
        )
        result = finalize_proposal_for_review(
            candidate,
            _decision(
                candidate,
                final_allocations=edited,
                final_intent_kind=IntentKind.MANUAL_OVERRIDE,
            ),
        )
        assert result.accepted
        assert result.preparation.final_terms.allocations == edited
        assert result.preparation.final_intent_kind == IntentKind.MANUAL_OVERRIDE

    def test_naive_decision_datetime_rejected_as_malformed_primitive(self):
        candidate = _candidate()
        with pytest.raises(ValueError):
            _decision(candidate, occurred_at=datetime(2026, 7, 17, 3, 0))
