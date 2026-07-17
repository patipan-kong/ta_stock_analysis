"""Pure pre-snapshot proposal and reconfirmation contracts (M33.5).

Proposal candidates are review inputs only.  This module never allocates an
intent/snapshot id, constructs an ExecutionIntentSnapshot, calls lifecycle
validation, or approves anything.  FINALIZE_FOR_REVIEW returns preparation
data for a future caller; a fresh M33.2 PENDING_REVIEW submission and separate
human approval remain required.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum

from services.execution_intent_authority import (
    AuthorityLevel,
    AuthorityReasonCode,
    AuthorityScope,
    AuthorityVerificationResult,
)
from services.execution_intent_contracts import (
    Actor,
    ActorType,
    ExecutionIntentAllocationTerm,
    ExecutionIntentTerms,
    IntentKind,
    ProvenanceCompleteness,
    SourceKind,
    SourceProvenance,
    build_execution_intent_terms,
)

__all__ = [
    "PROPOSAL_CONTRACT_VERSION",
    "ProposalOrigin",
    "ProposalWarningCode",
    "ProposalWarningSeverity",
    "ProposalCompleteness",
    "ProposalReviewRequirement",
    "ProposalDecisionKind",
    "ProposalOutcome",
    "ProposalRefusalReason",
    "ProposalWarning",
    "ProposalCandidate",
    "ProposalDecision",
    "ReconfirmationPreparation",
    "ProposalRefusal",
    "ProposalValidationResult",
    "compute_proposal_candidate_digest",
    "validate_proposal_eligibility",
    "build_proposal_candidate",
    "finalize_proposal_for_review",
]


PROPOSAL_CONTRACT_VERSION = "1"
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_ZERO_DIGEST = "sha256:" + ("0" * 64)


class ProposalOrigin(str, Enum):
    CERTIFIED_DECISION_PAYLOAD = "CERTIFIED_DECISION_PAYLOAD"
    LEGACY_DECISION_CANDIDATE = "LEGACY_DECISION_CANDIDATE"
    LEGACY_RECOMMENDATION_CANDIDATE = "LEGACY_RECOMMENDATION_CANDIDATE"
    OPTIMIZER_HISTORY_CANDIDATE = "OPTIMIZER_HISTORY_CANDIDATE"
    EXTERNAL_ARCHIVE_CANDIDATE = "EXTERNAL_ARCHIVE_CANDIDATE"
    MANUAL_HUMAN_INPUT = "MANUAL_HUMAN_INPUT"
    SHADOW_PORTFOLIO = "SHADOW_PORTFOLIO"
    TRANSACTION_LINK = "TRANSACTION_LINK"
    TRANSACTION_ROW = "TRANSACTION_ROW"
    CURRENT_PORTFOLIO_HOLDINGS = "CURRENT_PORTFOLIO_HOLDINGS"
    FUTURE_CANONICAL_EXECUTION_PLAN = "FUTURE_CANONICAL_EXECUTION_PLAN"


class ProposalWarningCode(str, Enum):
    HISTORICAL_APPROVAL_UNVERIFIED = "HISTORICAL_APPROVAL_UNVERIFIED"
    HISTORICAL_ACTOR_UNVERIFIED = "HISTORICAL_ACTOR_UNVERIFIED"
    RECOMMENDATION_ONLY_NOT_ACCEPTED_TERMS = "RECOMMENDATION_ONLY_NOT_ACCEPTED_TERMS"
    LEGACY_PAYLOAD_SEMANTICS_UNCERTIFIED = "LEGACY_PAYLOAD_SEMANTICS_UNCERTIFIED"
    TIMEZONE_UNVERIFIED = "TIMEZONE_UNVERIFIED"
    TARGET_UNIT_REVIEW_REQUIRED = "TARGET_UNIT_REVIEW_REQUIRED"
    ACTION_MAPPING_REVIEW_REQUIRED = "ACTION_MAPPING_REVIEW_REQUIRED"
    SOURCE_MISSING = "SOURCE_MISSING"
    SOURCE_CONFLICT = "SOURCE_CONFLICT"
    SCOPE_RECONFIRMATION_REQUIRED = "SCOPE_RECONFIRMATION_REQUIRED"
    FRESH_APPROVAL_REQUIRED = "FRESH_APPROVAL_REQUIRED"
    FINAL_TERMS_EDIT_REQUIRED = "FINAL_TERMS_EDIT_REQUIRED"


class ProposalWarningSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    BLOCKING = "BLOCKING"


class ProposalCompleteness(str, Enum):
    COMPLETE_REVIEWABLE = "COMPLETE_REVIEWABLE"
    EDIT_REQUIRED = "EDIT_REQUIRED"
    CONFLICTING = "CONFLICTING"
    UNUSABLE = "UNUSABLE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class ProposalReviewRequirement(str, Enum):
    DISPLAY_EXACT_CANDIDATE_TERMS = "DISPLAY_EXACT_CANDIDATE_TERMS"
    DISPLAY_ALL_ORIGINS_AND_WARNINGS = "DISPLAY_ALL_ORIGINS_AND_WARNINGS"
    CONFIRM_WORKSPACE_AND_PORTFOLIO_SCOPE = "CONFIRM_WORKSPACE_AND_PORTFOLIO_SCOPE"
    CONFIRM_INTENT_KIND = "CONFIRM_INTENT_KIND"
    CONFIRM_EFFECTIVE_AND_EXPIRY_TIMES = "CONFIRM_EFFECTIVE_AND_EXPIRY_TIMES"
    FREEZE_FINAL_TERMS_BEFORE_APPROVAL = "FREEZE_FINAL_TERMS_BEFORE_APPROVAL"
    USE_CURRENT_VERIFIED_HUMAN_ACTOR = "USE_CURRENT_VERIFIED_HUMAN_ACTOR"
    BIND_FRESH_APPROVAL_TO_NEW_SNAPSHOT_ID_AND_HASH = (
        "BIND_FRESH_APPROVAL_TO_NEW_SNAPSHOT_ID_AND_HASH"
    )


class ProposalDecisionKind(str, Enum):
    FINALIZE_FOR_REVIEW = "FINALIZE_FOR_REVIEW"
    REJECT_PROPOSAL = "REJECT_PROPOSAL"
    ABANDON_PROPOSAL = "ABANDON_PROPOSAL"
    DEFER_PROPOSAL = "DEFER_PROPOSAL"


class ProposalOutcome(str, Enum):
    ACCEPTED = "ACCEPTED"
    REFUSED = "REFUSED"


class ProposalRefusalReason(str, Enum):
    UNSUPPORTED_CONTRACT_VERSION = "UNSUPPORTED_CONTRACT_VERSION"
    AUTHORITY_NOT_PROPOSAL_ELIGIBLE = "AUTHORITY_NOT_PROPOSAL_ELIGIBLE"
    AUTHORITY_CONFLICTING = "AUTHORITY_CONFLICTING"
    AUTHORITY_OUT_OF_SCOPE = "AUTHORITY_OUT_OF_SCOPE"
    PROHIBITED_ORIGIN = "PROHIBITED_ORIGIN"
    PROVENANCE_AUTHORITY_OVERSTATED = "PROVENANCE_AUTHORITY_OVERSTATED"
    CANDIDATE_DIGEST_MISMATCH = "CANDIDATE_DIGEST_MISMATCH"
    STALE_CANDIDATE_DIGEST = "STALE_CANDIDATE_DIGEST"
    REQUIRED_WARNING_NOT_ACKNOWLEDGED = "REQUIRED_WARNING_NOT_ACKNOWLEDGED"
    SCOPE_MISMATCH = "SCOPE_MISMATCH"
    CURRENT_HUMAN_ACTOR_REQUIRED = "CURRENT_HUMAN_ACTOR_REQUIRED"
    DECISION_NOT_FINALIZE = "DECISION_NOT_FINALIZE"
    FINAL_TERMS_REQUIRED = "FINAL_TERMS_REQUIRED"
    FINAL_TERMS_INVALID = "FINAL_TERMS_INVALID"
    FINAL_INTENT_KIND_REQUIRED = "FINAL_INTENT_KIND_REQUIRED"
    EFFECTIVE_TIME_REQUIRED = "EFFECTIVE_TIME_REQUIRED"
    INCOMPLETE_PROVENANCE = "INCOMPLETE_PROVENANCE"


@dataclass(frozen=True)
class ProposalWarning:
    code: ProposalWarningCode
    detail: str
    severity: ProposalWarningSeverity
    related_reference_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_enum(self.code, ProposalWarningCode, "code")
        _require_enum(self.severity, ProposalWarningSeverity, "severity")
        _require_text(self.detail, "detail")
        if not isinstance(self.related_reference_ids, tuple):
            raise ValueError("related_reference_ids must be a tuple")
        for reference_id in self.related_reference_ids:
            _require_text(reference_id, "related_reference_id")
        object.__setattr__(self, "related_reference_ids", tuple(sorted(set(self.related_reference_ids))))


@dataclass(frozen=True)
class ProposalCandidate:
    contract_version: str
    proposal_candidate_id: str
    authority_level: AuthorityLevel
    authority_certificate_id: str | None
    authority_certificate_digest: str | None
    authority_reason_codes: tuple[AuthorityReasonCode, ...]
    origins: frozenset[ProposalOrigin]
    intent_kind: IntentKind
    candidate_terms: ExecutionIntentTerms | None
    scope: AuthorityScope
    completeness: ProposalCompleteness
    warnings: tuple[ProposalWarning, ...]
    source_provenance: tuple[SourceProvenance, ...]
    review_requirements: frozenset[ProposalReviewRequirement]
    created_at: datetime
    effective_at: datetime
    expires_at: datetime | None
    candidate_digest: str

    def __post_init__(self) -> None:
        _require_text(self.contract_version, "contract_version")
        _require_text(self.proposal_candidate_id, "proposal_candidate_id")
        _require_enum(self.authority_level, AuthorityLevel, "authority_level")
        if self.authority_certificate_id is not None:
            _require_text(self.authority_certificate_id, "authority_certificate_id")
        if self.authority_certificate_digest is not None:
            _require_digest(self.authority_certificate_digest, "authority_certificate_digest")
        if not isinstance(self.authority_reason_codes, tuple):
            raise ValueError("authority_reason_codes must be a tuple")
        if any(not isinstance(reason, AuthorityReasonCode) for reason in self.authority_reason_codes):
            raise ValueError("authority_reason_codes contains an invalid value")
        object.__setattr__(
            self,
            "authority_reason_codes",
            tuple(sorted(set(self.authority_reason_codes), key=lambda reason: reason.value)),
        )
        if not isinstance(self.origins, frozenset) or not self.origins:
            raise ValueError("origins must be a non-empty frozenset")
        if any(not isinstance(origin, ProposalOrigin) for origin in self.origins):
            raise ValueError("origins contains an invalid value")
        _require_enum(self.intent_kind, IntentKind, "intent_kind")
        _require_enum(self.completeness, ProposalCompleteness, "completeness")
        if not isinstance(self.warnings, tuple):
            raise ValueError("warnings must be a tuple")
        object.__setattr__(self, "warnings", _ordered_warnings(self.warnings))
        if not isinstance(self.source_provenance, tuple):
            raise ValueError("source_provenance must be a tuple")
        if not isinstance(self.review_requirements, frozenset) or not self.review_requirements:
            raise ValueError("review_requirements must be a non-empty frozenset")
        if any(
            not isinstance(requirement, ProposalReviewRequirement)
            for requirement in self.review_requirements
        ):
            raise ValueError("review_requirements contains an invalid value")
        _require_utc(self.created_at, "created_at")
        _require_utc(self.effective_at, "effective_at")
        if self.expires_at is not None:
            _require_utc(self.expires_at, "expires_at")
        _require_digest(self.candidate_digest, "candidate_digest")


@dataclass(frozen=True)
class ProposalDecision:
    contract_version: str
    decision_kind: ProposalDecisionKind
    proposal_candidate_id: str
    expected_candidate_digest: str
    actor: Actor
    occurred_at: datetime
    confirmed_workspace_id: int
    confirmed_portfolio_id: int
    acknowledged_warning_codes: frozenset[ProposalWarningCode]
    final_terms_schema_version: str | None = None
    final_allocations: tuple[ExecutionIntentAllocationTerm, ...] = ()
    final_notes: str | None = None
    final_intent_kind: IntentKind | None = None
    effective_at: datetime | None = None
    expires_at: datetime | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.contract_version, "contract_version")
        _require_enum(self.decision_kind, ProposalDecisionKind, "decision_kind")
        _require_text(self.proposal_candidate_id, "proposal_candidate_id")
        _require_digest(self.expected_candidate_digest, "expected_candidate_digest")
        _require_utc(self.occurred_at, "occurred_at")
        if not isinstance(self.confirmed_workspace_id, int) or not isinstance(self.confirmed_portfolio_id, int):
            raise ValueError("confirmed workspace/portfolio ids must be integers")
        if not isinstance(self.acknowledged_warning_codes, frozenset):
            raise ValueError("acknowledged_warning_codes must be a frozenset")
        if any(
            not isinstance(code, ProposalWarningCode)
            for code in self.acknowledged_warning_codes
        ):
            raise ValueError("acknowledged_warning_codes contains an invalid value")
        if not isinstance(self.final_allocations, tuple):
            raise ValueError("final_allocations must be a tuple")
        if self.final_terms_schema_version is not None:
            _require_text(self.final_terms_schema_version, "final_terms_schema_version")
        if self.final_intent_kind is not None:
            _require_enum(self.final_intent_kind, IntentKind, "final_intent_kind")
        if self.effective_at is not None:
            _require_utc(self.effective_at, "effective_at")
        if self.expires_at is not None:
            _require_utc(self.expires_at, "expires_at")


@dataclass(frozen=True)
class ReconfirmationPreparation:
    proposal_candidate_id: str
    proposal_candidate_digest: str
    final_terms: ExecutionIntentTerms
    final_intent_kind: IntentKind
    workspace_id: int
    portfolio_id: int
    legacy_source_provenance: tuple[SourceProvenance, ...]
    current_actor: Actor
    effective_at: datetime
    expires_at: datetime | None
    review_requirements: frozenset[ProposalReviewRequirement]
    acknowledged_warning_codes: frozenset[ProposalWarningCode]
    authority_certificate_id: str | None
    authority_certificate_digest: str | None
    fresh_intent_id_required: bool = True
    fresh_snapshot_id_required: bool = True
    pending_review_submission_required: bool = True
    separate_fresh_approval_required: bool = True
    manual_human_input_provenance_required: bool = True
    historical_approval_inherited: bool = False
    historical_lifecycle_state_inherited: bool = False

    def __post_init__(self) -> None:
        _require_text(self.proposal_candidate_id, "proposal_candidate_id")
        _require_digest(self.proposal_candidate_digest, "proposal_candidate_digest")
        _require_finite_terms(self.final_terms)
        _require_enum(self.final_intent_kind, IntentKind, "final_intent_kind")
        if self.current_actor.actor_type != ActorType.HUMAN or not self.current_actor.actor_id.strip():
            raise ValueError("reconfirmation preparation requires a current HUMAN actor")
        _require_utc(self.effective_at, "effective_at")
        if self.expires_at is not None:
            _require_utc(self.expires_at, "expires_at")
        if self.authority_certificate_id is not None:
            _require_text(self.authority_certificate_id, "authority_certificate_id")
        if self.authority_certificate_digest is not None:
            _require_digest(self.authority_certificate_digest, "authority_certificate_digest")
        if self.historical_approval_inherited or self.historical_lifecycle_state_inherited:
            raise ValueError("reconfirmation preparation cannot inherit historical authority state")


@dataclass(frozen=True)
class ProposalRefusal:
    reason: ProposalRefusalReason
    detail: str


@dataclass(frozen=True)
class ProposalValidationResult:
    outcome: ProposalOutcome
    eligible_origins: frozenset[ProposalOrigin] | None = None
    candidate: ProposalCandidate | None = None
    preparation: ReconfirmationPreparation | None = None
    refusal: ProposalRefusal | None = None

    def __post_init__(self) -> None:
        payload_count = sum(
            value is not None
            for value in (self.eligible_origins, self.candidate, self.preparation)
        )
        if self.outcome == ProposalOutcome.ACCEPTED:
            if self.refusal is not None or payload_count != 1:
                raise ValueError("accepted proposal result requires exactly one result payload")
        elif self.refusal is None or payload_count:
            raise ValueError("refused proposal result requires one refusal and no result payload")

    @property
    def accepted(self) -> bool:
        return self.outcome == ProposalOutcome.ACCEPTED


_REQUIRED_REVIEW_REQUIREMENTS = frozenset(ProposalReviewRequirement)
_PROHIBITED_ORIGINS = frozenset(
    {
        ProposalOrigin.SHADOW_PORTFOLIO,
        ProposalOrigin.TRANSACTION_LINK,
        ProposalOrigin.TRANSACTION_ROW,
        ProposalOrigin.CURRENT_PORTFOLIO_HOLDINGS,
        ProposalOrigin.FUTURE_CANONICAL_EXECUTION_PLAN,
    }
)


def validate_proposal_eligibility(
    authority_result: AuthorityVerificationResult,
    origins: frozenset[ProposalOrigin],
) -> ProposalValidationResult:
    if not isinstance(origins, frozenset) or not origins:
        return _refuse(
            ProposalRefusalReason.AUTHORITY_NOT_PROPOSAL_ELIGIBLE,
            "at least one proposal origin is required",
        )
    prohibited = origins & _PROHIBITED_ORIGINS
    if prohibited:
        names = ", ".join(sorted(origin.value for origin in prohibited))
        return _refuse(
            ProposalRefusalReason.PROHIBITED_ORIGIN,
            f"prohibited proposal origins: {names}",
        )
    if authority_result.authority_level == AuthorityLevel.CONFLICTING:
        return _refuse(
            ProposalRefusalReason.AUTHORITY_CONFLICTING,
            "conflicting authority cannot automatically create a proposal",
        )
    if authority_result.authority_level == AuthorityLevel.OUT_OF_SCOPE:
        return _refuse(
            ProposalRefusalReason.AUTHORITY_OUT_OF_SCOPE,
            "out-of-scope authority creates no proposal",
        )
    if not authority_result.may_build_proposal:
        return _refuse(
            ProposalRefusalReason.AUTHORITY_NOT_PROPOSAL_ELIGIBLE,
            "authority result does not permit proposal construction",
        )
    return ProposalValidationResult(
        ProposalOutcome.ACCEPTED,
        eligible_origins=origins,
    )


def build_proposal_candidate(
    *,
    proposal_candidate_id: str,
    authority_result: AuthorityVerificationResult,
    origins: frozenset[ProposalOrigin],
    intent_kind: IntentKind,
    candidate_allocations: tuple[ExecutionIntentAllocationTerm, ...] | None,
    terms_schema_version: str,
    scope: AuthorityScope,
    source_provenance: tuple[SourceProvenance, ...],
    created_at: datetime,
    effective_at: datetime,
    expires_at: datetime | None = None,
    notes: str | None = None,
    warnings: tuple[ProposalWarning, ...] = (),
) -> ProposalValidationResult:
    _require_text(terms_schema_version, "terms_schema_version")
    eligibility = validate_proposal_eligibility(authority_result, origins)
    if not eligibility.accepted:
        return eligibility
    if authority_result.verified_scope is not None and authority_result.verified_scope != scope:
        return _refuse(
            ProposalRefusalReason.SCOPE_MISMATCH,
            "proposal scope differs from the verified authority scope",
        )
    if any(sp.source_kind == SourceKind.FUTURE_CANONICAL_EXECUTION_PLAN for sp in source_provenance):
        return _refuse(
            ProposalRefusalReason.PROHIBITED_ORIGIN,
            "FUTURE_CANONICAL_EXECUTION_PLAN is prohibited proposal provenance",
        )
    if authority_result.authority_level != AuthorityLevel.CERTIFIED_EXACT and any(
        sp.source_kind
        in (
            SourceKind.LEGACY_RECOMMENDATION_SNAPSHOT,
            SourceKind.LEGACY_USER_EXECUTION_DECISION,
        )
        and sp.completeness == ProvenanceCompleteness.EXACT_FROZEN
        for sp in source_provenance
    ):
        return _refuse(
            ProposalRefusalReason.PROVENANCE_AUTHORITY_OVERSTATED,
            "non-exact authority cannot label legacy provenance EXACT_FROZEN",
        )

    candidate_terms: ExecutionIntentTerms | None = None
    completeness = ProposalCompleteness.EDIT_REQUIRED
    generated_warnings = list(warnings)
    if candidate_allocations:
        try:
            candidate_terms = build_execution_intent_terms(
                terms_schema_version,
                candidate_allocations,
                notes,
            )
            _require_finite_terms(candidate_terms)
            completeness = ProposalCompleteness.COMPLETE_REVIEWABLE
        except ValueError:
            generated_warnings.append(
                ProposalWarning(
                    ProposalWarningCode.FINAL_TERMS_EDIT_REQUIRED,
                    "Candidate terms are incomplete or invalid and require explicit human editing.",
                    ProposalWarningSeverity.BLOCKING,
                )
            )
    else:
        generated_warnings.append(
            ProposalWarning(
                ProposalWarningCode.FINAL_TERMS_EDIT_REQUIRED,
                "Candidate terms are missing and require explicit human entry.",
                ProposalWarningSeverity.BLOCKING,
            )
        )

    generated_warnings.extend(_required_authority_warnings(authority_result, origins))
    candidate = ProposalCandidate(
        contract_version=PROPOSAL_CONTRACT_VERSION,
        proposal_candidate_id=proposal_candidate_id,
        authority_level=authority_result.authority_level,
        authority_certificate_id=authority_result.certificate_id,
        authority_certificate_digest=authority_result.certificate_digest,
        authority_reason_codes=authority_result.reason_codes,
        origins=origins,
        intent_kind=intent_kind,
        candidate_terms=candidate_terms,
        scope=scope,
        completeness=completeness,
        warnings=_ordered_warnings(tuple(generated_warnings)),
        source_provenance=source_provenance,
        review_requirements=_REQUIRED_REVIEW_REQUIREMENTS,
        created_at=created_at,
        effective_at=effective_at,
        expires_at=expires_at,
        candidate_digest=_ZERO_DIGEST,
    )
    candidate = replace(candidate, candidate_digest=compute_proposal_candidate_digest(candidate))
    return ProposalValidationResult(ProposalOutcome.ACCEPTED, candidate=candidate)


def compute_proposal_candidate_digest(candidate: ProposalCandidate) -> str:
    payload = {
        "contract_version": candidate.contract_version,
        "proposal_candidate_id": candidate.proposal_candidate_id,
        "authority_level": candidate.authority_level.value,
        "authority_certificate_id": candidate.authority_certificate_id,
        "authority_certificate_digest": candidate.authority_certificate_digest,
        "authority_reason_codes": sorted(reason.value for reason in candidate.authority_reason_codes),
        "origins": sorted(origin.value for origin in candidate.origins),
        "intent_kind": candidate.intent_kind.value,
        "candidate_terms": _terms_dict(candidate.candidate_terms),
        "scope": _scope_dict(candidate.scope),
        "completeness": candidate.completeness.value,
        "warnings": [_warning_dict(warning) for warning in _ordered_warnings(candidate.warnings)],
        "source_provenance": _provenance_dicts(candidate.source_provenance),
        "review_requirements": sorted(requirement.value for requirement in candidate.review_requirements),
        "created_at": _canon_datetime(candidate.created_at),
        "effective_at": _canon_datetime(candidate.effective_at),
        "expires_at": _canon_datetime(candidate.expires_at) if candidate.expires_at else None,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    domain = f"M33.5:proposal-candidate:{candidate.contract_version}\n"
    return "sha256:" + hashlib.sha256((domain + canonical).encode("utf-8")).hexdigest()


def finalize_proposal_for_review(
    candidate: ProposalCandidate,
    decision: ProposalDecision,
) -> ProposalValidationResult:
    if candidate.contract_version != PROPOSAL_CONTRACT_VERSION or decision.contract_version != PROPOSAL_CONTRACT_VERSION:
        return _refuse(
            ProposalRefusalReason.UNSUPPORTED_CONTRACT_VERSION,
            "unsupported proposal or decision contract version",
        )
    if decision.decision_kind != ProposalDecisionKind.FINALIZE_FOR_REVIEW:
        return _refuse(
            ProposalRefusalReason.DECISION_NOT_FINALIZE,
            "finalize_proposal_for_review requires FINALIZE_FOR_REVIEW",
        )
    if decision.proposal_candidate_id != candidate.proposal_candidate_id:
        return _refuse(
            ProposalRefusalReason.STALE_CANDIDATE_DIGEST,
            "decision references a different proposal candidate",
        )
    computed_candidate_digest = compute_proposal_candidate_digest(candidate)
    if computed_candidate_digest != candidate.candidate_digest:
        return _refuse(
            ProposalRefusalReason.CANDIDATE_DIGEST_MISMATCH,
            "stored candidate digest does not match canonical candidate content",
        )
    if decision.expected_candidate_digest != candidate.candidate_digest:
        return _refuse(
            ProposalRefusalReason.STALE_CANDIDATE_DIGEST,
            "decision expected_candidate_digest is stale",
        )
    if decision.actor.actor_type != ActorType.HUMAN or not decision.actor.actor_id.strip():
        return _refuse(
            ProposalRefusalReason.CURRENT_HUMAN_ACTOR_REQUIRED,
            "FINALIZE_FOR_REVIEW requires a current verified HUMAN actor",
        )
    if (
        decision.confirmed_workspace_id != candidate.scope.workspace_id
        or decision.confirmed_portfolio_id != candidate.scope.portfolio_id
    ):
        return _refuse(
            ProposalRefusalReason.SCOPE_MISMATCH,
            "confirmed workspace/portfolio differs from the proposal scope",
        )
    required_warning_codes = frozenset(warning.code for warning in candidate.warnings)
    missing_acknowledgements = required_warning_codes - decision.acknowledged_warning_codes
    if missing_acknowledgements:
        names = ", ".join(sorted(code.value for code in missing_acknowledgements))
        return _refuse(
            ProposalRefusalReason.REQUIRED_WARNING_NOT_ACKNOWLEDGED,
            f"required proposal warnings were not acknowledged: {names}",
        )
    if not decision.final_terms_schema_version or not decision.final_allocations:
        return _refuse(
            ProposalRefusalReason.FINAL_TERMS_REQUIRED,
            "FINALIZE_FOR_REVIEW requires complete final allocation terms",
        )
    try:
        final_terms = build_execution_intent_terms(
            decision.final_terms_schema_version,
            decision.final_allocations,
            decision.final_notes,
        )
        _require_finite_terms(final_terms)
    except ValueError as exc:
        return _refuse(
            ProposalRefusalReason.FINAL_TERMS_INVALID,
            str(exc),
        )
    if decision.final_intent_kind is None:
        return _refuse(
            ProposalRefusalReason.FINAL_INTENT_KIND_REQUIRED,
            "FINALIZE_FOR_REVIEW requires final_intent_kind",
        )
    if decision.effective_at is None:
        return _refuse(
            ProposalRefusalReason.EFFECTIVE_TIME_REQUIRED,
            "FINALIZE_FOR_REVIEW requires a UTC effective_at",
        )
    if any(sp.completeness == ProvenanceCompleteness.INCOMPLETE for sp in candidate.source_provenance):
        return _refuse(
            ProposalRefusalReason.INCOMPLETE_PROVENANCE,
            "incomplete legacy provenance must be resolved before snapshot preparation",
        )

    preparation = ReconfirmationPreparation(
        proposal_candidate_id=candidate.proposal_candidate_id,
        proposal_candidate_digest=candidate.candidate_digest,
        final_terms=final_terms,
        final_intent_kind=decision.final_intent_kind,
        workspace_id=candidate.scope.workspace_id,
        portfolio_id=candidate.scope.portfolio_id,
        legacy_source_provenance=candidate.source_provenance,
        current_actor=decision.actor,
        effective_at=decision.effective_at,
        expires_at=decision.expires_at,
        review_requirements=candidate.review_requirements,
        acknowledged_warning_codes=decision.acknowledged_warning_codes,
        authority_certificate_id=candidate.authority_certificate_id,
        authority_certificate_digest=candidate.authority_certificate_digest,
    )
    return ProposalValidationResult(ProposalOutcome.ACCEPTED, preparation=preparation)


def _required_authority_warnings(
    authority_result: AuthorityVerificationResult,
    origins: frozenset[ProposalOrigin],
) -> tuple[ProposalWarning, ...]:
    warnings: list[ProposalWarning] = [
        ProposalWarning(
            ProposalWarningCode.FRESH_APPROVAL_REQUIRED,
            "This proposal requires a new approval of a newly frozen snapshot.",
            ProposalWarningSeverity.WARNING,
        ),
        ProposalWarning(
            ProposalWarningCode.SCOPE_RECONFIRMATION_REQUIRED,
            "Workspace and portfolio scope must be reconfirmed explicitly.",
            ProposalWarningSeverity.WARNING,
        ),
    ]
    if authority_result.authority_level != AuthorityLevel.CERTIFIED_EXACT:
        warnings.append(
            ProposalWarning(
                ProposalWarningCode.HISTORICAL_APPROVAL_UNVERIFIED,
                "Historical approval is not authoritative for this proposal.",
                ProposalWarningSeverity.WARNING,
            )
        )
    if (
        authority_result.verified_historical_actor_id is None
        or AuthorityReasonCode.HISTORICAL_ACTOR_MISSING in authority_result.reason_codes
        or AuthorityReasonCode.HISTORICAL_ACTOR_AMBIGUOUS in authority_result.reason_codes
    ):
        warnings.append(
            ProposalWarning(
                ProposalWarningCode.HISTORICAL_ACTOR_UNVERIFIED,
                "The historical approving actor is unavailable or unverified.",
                ProposalWarningSeverity.WARNING,
            )
        )
    if ProposalOrigin.LEGACY_RECOMMENDATION_CANDIDATE in origins:
        warnings.append(
            ProposalWarning(
                ProposalWarningCode.RECOMMENDATION_ONLY_NOT_ACCEPTED_TERMS,
                "Recommendation terms are proposal input, not accepted historical terms.",
                ProposalWarningSeverity.WARNING,
            )
        )
    if AuthorityReasonCode.TIMEZONE_AMBIGUOUS in authority_result.reason_codes:
        warnings.append(
            ProposalWarning(
                ProposalWarningCode.TIMEZONE_UNVERIFIED,
                "Historical time or timezone semantics are ambiguous.",
                ProposalWarningSeverity.WARNING,
            )
        )
    if AuthorityReasonCode.LOSSLESS_MAPPING_UNPROVEN in authority_result.reason_codes:
        warnings.extend(
            (
                ProposalWarning(
                    ProposalWarningCode.TARGET_UNIT_REVIEW_REQUIRED,
                    "Target units require explicit human review.",
                    ProposalWarningSeverity.WARNING,
                ),
                ProposalWarning(
                    ProposalWarningCode.ACTION_MAPPING_REVIEW_REQUIRED,
                    "Legacy actions require explicit human review.",
                    ProposalWarningSeverity.WARNING,
                ),
            )
        )
    return tuple(warnings)


def _terms_dict(terms: ExecutionIntentTerms | None) -> dict | None:
    if terms is None:
        return None
    _require_finite_terms(terms)
    allocations = sorted(terms.allocations, key=lambda item: (item.symbol, item.side.value))
    return {
        "schema_version": terms.schema_version,
        "notes": terms.notes,
        "allocations": [
            {
                "symbol": item.symbol,
                "side": item.side.value,
                "target_weight": _decimal_text(item.target_weight),
                "target_value": _decimal_text(item.target_value),
                "note": item.note,
            }
            for item in allocations
        ],
    }


def _warning_dict(warning: ProposalWarning) -> dict:
    return {
        "code": warning.code.value,
        "detail": warning.detail,
        "severity": warning.severity.value,
        "related_reference_ids": list(warning.related_reference_ids),
    }


def _scope_dict(scope: AuthorityScope) -> dict:
    return {
        "workspace_id": scope.workspace_id,
        "portfolio_id": scope.portfolio_id,
        "authority_namespace": scope.authority_namespace,
        "environment_id": scope.environment_id,
    }


def _provenance_dicts(provenance: tuple[SourceProvenance, ...]) -> list[dict]:
    ordered = sorted(
        provenance,
        key=lambda item: (item.source_kind.value, item.source_local_id or "", item.source_digest),
    )
    return [
        {
            "source_kind": item.source_kind.value,
            "source_local_id": item.source_local_id,
            "source_contract_version": item.source_contract_version,
            "source_created_at": (
                _canon_datetime(item.source_created_at)
                if item.source_created_at is not None
                else None
            ),
            "source_digest": item.source_digest,
            "completeness": item.completeness.value,
        }
        for item in ordered
    ]


def _ordered_warnings(warnings: tuple[ProposalWarning, ...]) -> tuple[ProposalWarning, ...]:
    unique = {
        (warning.code, warning.detail, warning.severity, warning.related_reference_ids): warning
        for warning in warnings
    }
    return tuple(
        sorted(
            unique.values(),
            key=lambda warning: (
                warning.code.value,
                warning.severity.value,
                warning.detail,
                warning.related_reference_ids,
            ),
        )
    )


def _require_finite_terms(terms: ExecutionIntentTerms) -> None:
    for allocation in terms.allocations:
        for value in (allocation.target_weight, allocation.target_value):
            if value is not None and (not isinstance(value, Decimal) or not value.is_finite()):
                raise ValueError("final allocation terms require finite Decimal values")


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ValueError("proposal terms require finite Decimal values")
    return format(value, "f")


def _refuse(reason: ProposalRefusalReason, detail: str) -> ProposalValidationResult:
    return ProposalValidationResult(
        ProposalOutcome.REFUSED,
        refusal=ProposalRefusal(reason, detail),
    )


def _canon_datetime(value: datetime) -> str:
    _require_utc(value, "datetime")
    return value.astimezone(timezone.utc).isoformat()


def _require_utc(value: datetime, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None or value.utcoffset() != timedelta(0):
        raise ValueError(f"{field_name} must be a timezone-aware UTC datetime")


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_digest(value: str, field_name: str) -> None:
    if not isinstance(value, str) or _DIGEST_RE.fullmatch(value) is None:
        raise ValueError(f"{field_name} must use lowercase sha256:<64-hex> syntax")


def _require_enum(value: Enum, enum_type: type[Enum], field_name: str) -> None:
    if not isinstance(value, enum_type):
        raise ValueError(f"{field_name} must be a {enum_type.__name__} value")
