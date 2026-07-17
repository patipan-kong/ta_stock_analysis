"""Pure historical-authority contracts and verifier (M33.5).

This module is deliberately ORM-free and side-effect free.  It does not load
keys, verify cryptography, read a trust store, fetch evidence, access a
database, construct an ExecutionIntentSnapshot, or call lifecycle validation.
All trust/signature/revocation/conflict facts are supplied by the caller.

The M33.2 snapshot content hash is treated only as an opaque target fact.  No
certificate data is inserted into M33.2 source provenance and this module does
not import or redefine M33.2 snapshot hashing.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

from services.execution_intent_contracts import ProvenanceCompleteness

__all__ = [
    "AUTHORITY_CONTRACT_VERSION",
    "VERIFICATION_POLICY_VERSION",
    "AuthorityIssuerKind",
    "AuthorityEvidenceKind",
    "AuthorityEvidenceRole",
    "HistoricalSourceAct",
    "PayloadRelationship",
    "DigestAlgorithm",
    "SignatureAlgorithm",
    "AuthorityCompleteness",
    "AuthorityLevel",
    "RevocationStatus",
    "AuthorityReasonCode",
    "AuthorityIssuer",
    "AuthoritySourceReference",
    "AuthorityEvidence",
    "AuthorityScope",
    "AuthorityBinding",
    "AuthorityCertificate",
    "DetachedEvidenceFact",
    "SignatureVerificationFact",
    "IssuerTrustFact",
    "RevocationEvidence",
    "RevocationVerificationFact",
    "AuthorityConflictFact",
    "TargetSnapshotFact",
    "VerificationPolicy",
    "AuthorityVerificationResult",
    "canonicalize_authority_evidence",
    "compute_authority_evidence_digest",
    "canonicalize_authority_certificate",
    "compute_authority_certificate_digest",
    "verify_authority",
]


AUTHORITY_CONTRACT_VERSION = "1"
VERIFICATION_POLICY_VERSION = "1"
_DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class AuthorityIssuerKind(str, Enum):
    TRUSTED_AUDIT_SYSTEM = "TRUSTED_AUDIT_SYSTEM"
    EXTERNAL_SIGNED_ARCHIVE = "EXTERNAL_SIGNED_ARCHIVE"
    FUTURE_CERTIFICATION_SERVICE = "FUTURE_CERTIFICATION_SERVICE"
    HUMAN_OPERATOR = "HUMAN_OPERATOR"


class AuthorityEvidenceKind(str, Enum):
    LEGACY_USER_EXECUTION_DECISION = "LEGACY_USER_EXECUTION_DECISION"
    LEGACY_RECOMMENDATION_SNAPSHOT = "LEGACY_RECOMMENDATION_SNAPSHOT"
    OPTIMIZER_HISTORY = "OPTIMIZER_HISTORY"
    TRANSACTION_LINK = "TRANSACTION_LINK"
    TRANSACTION_ROW = "TRANSACTION_ROW"
    SHADOW_PORTFOLIO = "SHADOW_PORTFOLIO"
    CURRENT_PORTFOLIO_HOLDINGS = "CURRENT_PORTFOLIO_HOLDINGS"
    AUDIT_LOG = "AUDIT_LOG"
    API_REQUEST_ARCHIVE = "API_REQUEST_ARCHIVE"
    EXTERNAL_SIGNED_ARCHIVE = "EXTERNAL_SIGNED_ARCHIVE"
    FUTURE_AUTHORITY_CERTIFICATE = "FUTURE_AUTHORITY_CERTIFICATE"
    MANUAL_OPERATOR_STATEMENT = "MANUAL_OPERATOR_STATEMENT"


class AuthorityEvidenceRole(str, Enum):
    REVIEWED_PAYLOAD = "REVIEWED_PAYLOAD"
    APPROVED_PAYLOAD = "APPROVED_PAYLOAD"
    ACTOR_IDENTITY = "ACTOR_IDENTITY"
    ACTOR_AUTHORITY = "ACTOR_AUTHORITY"
    SCOPE = "SCOPE"
    EVENT_TIME = "EVENT_TIME"
    RECOMMENDATION_LINK = "RECOMMENDATION_LINK"
    DECISION_LINK = "DECISION_LINK"


class HistoricalSourceAct(str, Enum):
    APPROVED = "APPROVED"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"
    PARTIAL_EXECUTION = "PARTIAL_EXECUTION"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


class PayloadRelationship(str, Enum):
    IDENTICAL = "IDENTICAL"
    LOSSLESS_TRANSFORMATION = "LOSSLESS_TRANSFORMATION"


class DigestAlgorithm(str, Enum):
    SHA256 = "SHA256"


class SignatureAlgorithm(str, Enum):
    ED25519 = "ED25519"
    RSA_PSS_SHA256 = "RSA_PSS_SHA256"
    ECDSA_SHA256 = "ECDSA_SHA256"


class AuthorityCompleteness(str, Enum):
    EXACT = "EXACT"
    PROPOSAL_ONLY = "PROPOSAL_ONLY"
    INCOMPLETE = "INCOMPLETE"
    CONFLICTING = "CONFLICTING"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class AuthorityLevel(str, Enum):
    CERTIFIED_EXACT = "CERTIFIED_EXACT"
    CERTIFIED_PROPOSAL_ONLY = "CERTIFIED_PROPOSAL_ONLY"
    UNVERIFIABLE = "UNVERIFIABLE"
    CONFLICTING = "CONFLICTING"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class RevocationStatus(str, Enum):
    NOT_REVOKED = "NOT_REVOKED"
    REVOKED = "REVOKED"
    UNKNOWN = "UNKNOWN"
    CONFLICTING = "CONFLICTING"


class AuthorityReasonCode(str, Enum):
    OUT_OF_SCOPE_DECISION = "OUT_OF_SCOPE_DECISION"
    CERTIFICATE_MISSING = "CERTIFICATE_MISSING"
    UNSUPPORTED_CONTRACT_VERSION = "UNSUPPORTED_CONTRACT_VERSION"
    UNSUPPORTED_DIGEST_ALGORITHM = "UNSUPPORTED_DIGEST_ALGORITHM"
    UNSUPPORTED_SIGNATURE_ALGORITHM = "UNSUPPORTED_SIGNATURE_ALGORITHM"
    CERTIFICATE_ID_REUSED = "CERTIFICATE_ID_REUSED"
    CONFLICTING_CERTIFICATES = "CONFLICTING_CERTIFICATES"
    CERTIFICATE_DIGEST_MISMATCH = "CERTIFICATE_DIGEST_MISMATCH"
    EVIDENCE_DIGEST_MISMATCH = "EVIDENCE_DIGEST_MISMATCH"
    EVIDENCE_PAYLOAD_MISSING = "EVIDENCE_PAYLOAD_MISSING"
    SHADOW_EVIDENCE_PROHIBITED = "SHADOW_EVIDENCE_PROHIBITED"
    TRANSACTION_EVIDENCE_PROHIBITED = "TRANSACTION_EVIDENCE_PROHIBITED"
    PORTFOLIO_HOLDINGS_EVIDENCE_PROHIBITED = "PORTFOLIO_HOLDINGS_EVIDENCE_PROHIBITED"
    SIGNATURE_INVALID = "SIGNATURE_INVALID"
    ISSUER_UNTRUSTED = "ISSUER_UNTRUSTED"
    TRUST_POLICY_UNAVAILABLE = "TRUST_POLICY_UNAVAILABLE"
    TRUST_POLICY_MISMATCH = "TRUST_POLICY_MISMATCH"
    CERTIFICATE_REVOKED = "CERTIFICATE_REVOKED"
    REVOCATION_STATUS_UNKNOWN = "REVOCATION_STATUS_UNKNOWN"
    REVOCATION_STATUS_CONFLICT = "REVOCATION_STATUS_CONFLICT"
    WORKSPACE_SCOPE_MISMATCH = "WORKSPACE_SCOPE_MISMATCH"
    PORTFOLIO_SCOPE_MISMATCH = "PORTFOLIO_SCOPE_MISMATCH"
    AUTHORITY_NAMESPACE_MISMATCH = "AUTHORITY_NAMESPACE_MISMATCH"
    ENVIRONMENT_SCOPE_MISMATCH = "ENVIRONMENT_SCOPE_MISMATCH"
    RECOMMENDATION_BINDING_MISSING = "RECOMMENDATION_BINDING_MISSING"
    DECISION_BINDING_MISSING = "DECISION_BINDING_MISSING"
    LINEAGE_AMBIGUOUS = "LINEAGE_AMBIGUOUS"
    REVIEWED_PAYLOAD_MISSING = "REVIEWED_PAYLOAD_MISSING"
    APPROVED_PAYLOAD_MISSING = "APPROVED_PAYLOAD_MISSING"
    REVIEWED_APPROVED_PAYLOAD_CONFLICT = "REVIEWED_APPROVED_PAYLOAD_CONFLICT"
    LOSSLESS_MAPPING_UNPROVEN = "LOSSLESS_MAPPING_UNPROVEN"
    HISTORICAL_ACTOR_MISSING = "HISTORICAL_ACTOR_MISSING"
    HISTORICAL_ACTOR_AMBIGUOUS = "HISTORICAL_ACTOR_AMBIGUOUS"
    ACTOR_IDENTITY_UNPROVEN = "ACTOR_IDENTITY_UNPROVEN"
    ACTOR_AUTHORITY_UNPROVEN = "ACTOR_AUTHORITY_UNPROVEN"
    APPROVAL_TIME_MISSING = "APPROVAL_TIME_MISSING"
    TIMEZONE_AMBIGUOUS = "TIMEZONE_AMBIGUOUS"
    PARTIAL_EXECUTION_NOT_INTENT_AUTHORITY = "PARTIAL_EXECUTION_NOT_INTENT_AUTHORITY"
    TARGET_INTENT_BINDING_MISSING = "TARGET_INTENT_BINDING_MISSING"
    TARGET_INTENT_ID_MISMATCH = "TARGET_INTENT_ID_MISMATCH"
    TARGET_SNAPSHOT_BINDING_MISSING = "TARGET_SNAPSHOT_BINDING_MISSING"
    TARGET_SNAPSHOT_ID_MISMATCH = "TARGET_SNAPSHOT_ID_MISMATCH"
    TARGET_CONTENT_HASH_MISSING = "TARGET_CONTENT_HASH_MISSING"
    TARGET_CONTENT_HASH_MISMATCH = "TARGET_CONTENT_HASH_MISMATCH"
    FRESH_RECONFIRMATION_REQUIRED = "FRESH_RECONFIRMATION_REQUIRED"


@dataclass(frozen=True)
class AuthorityIssuer:
    issuer_id: str
    issuer_kind: AuthorityIssuerKind
    authority_namespace: str
    trust_policy_version: str
    signing_key_id: str
    signature_algorithm: SignatureAlgorithm

    def __post_init__(self) -> None:
        _require_text(self.issuer_id, "issuer_id")
        _require_enum(self.issuer_kind, AuthorityIssuerKind, "issuer_kind")
        _require_text(self.authority_namespace, "authority_namespace")
        _require_text(self.trust_policy_version, "trust_policy_version")
        _require_text(self.signing_key_id, "signing_key_id")
        _require_enum(self.signature_algorithm, SignatureAlgorithm, "signature_algorithm")


@dataclass(frozen=True)
class AuthoritySourceReference:
    source_local_id: str
    source_digest: str

    def __post_init__(self) -> None:
        _require_text(self.source_local_id, "source_local_id")
        _require_digest(self.source_digest, "source_digest")


@dataclass(frozen=True)
class AuthorityEvidence:
    evidence_id: str
    evidence_kind: AuthorityEvidenceKind
    evidence_roles: frozenset[AuthorityEvidenceRole]
    source_local_id: str
    source_contract_version: str
    canonical_payload: str | None
    source_digest_algorithm: DigestAlgorithm
    source_digest: str
    occurred_at: datetime | None
    recorded_at: datetime
    source_timezone: str | None = None
    source_local_time_text: str | None = None
    locator: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.evidence_id, "evidence_id")
        _require_enum(self.evidence_kind, AuthorityEvidenceKind, "evidence_kind")
        if not isinstance(self.evidence_roles, frozenset) or not self.evidence_roles:
            raise ValueError("evidence_roles must be a non-empty frozenset")
        if any(not isinstance(role, AuthorityEvidenceRole) for role in self.evidence_roles):
            raise ValueError("evidence_roles must contain only AuthorityEvidenceRole values")
        _require_text(self.source_local_id, "source_local_id")
        _require_text(self.source_contract_version, "source_contract_version")
        if self.canonical_payload is not None and not isinstance(self.canonical_payload, str):
            raise ValueError("canonical_payload must be an exact UTF-8 string or None")
        _require_enum(self.source_digest_algorithm, DigestAlgorithm, "source_digest_algorithm")
        _require_digest(self.source_digest, "source_digest")
        if self.occurred_at is not None:
            _require_utc(self.occurred_at, "occurred_at")
        _require_utc(self.recorded_at, "recorded_at")
        if self.source_local_time_text is not None and not self.source_timezone:
            raise ValueError("source_timezone is required when source_local_time_text is retained")


@dataclass(frozen=True)
class AuthorityScope:
    workspace_id: int
    portfolio_id: int
    authority_namespace: str
    environment_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.workspace_id, int) or not isinstance(self.portfolio_id, int):
            raise ValueError("workspace_id and portfolio_id must be integers")
        _require_text(self.authority_namespace, "authority_namespace")
        if self.environment_id is not None:
            _require_text(self.environment_id, "environment_id")


@dataclass(frozen=True)
class AuthorityBinding:
    source_act: HistoricalSourceAct
    reviewed_payload_schema_version: str | None = None
    reviewed_payload_digest: str | None = None
    approved_payload_schema_version: str | None = None
    approved_payload_digest: str | None = None
    payload_relationship: PayloadRelationship | None = None
    transformation_contract_version: str | None = None
    historical_actor_id: str | None = None
    historical_actor_authority_ref: str | None = None
    recommendation_ref: AuthoritySourceReference | None = None
    decision_ref: AuthoritySourceReference | None = None
    approval_event_id: str | None = None
    approval_occurred_at: datetime | None = None
    source_timezone_semantics: str | None = None
    approval_time_was_converted: bool = False
    approval_time_ambiguous: bool = False
    historical_actor_ambiguous: bool = False
    lineage_ambiguous: bool = False
    target_intent_id: str | None = None
    target_snapshot_id: str | None = None
    target_content_hash: str | None = None

    def __post_init__(self) -> None:
        _require_enum(self.source_act, HistoricalSourceAct, "source_act")
        if self.payload_relationship is not None:
            _require_enum(self.payload_relationship, PayloadRelationship, "payload_relationship")
        for field_name in (
            "reviewed_payload_schema_version",
            "approved_payload_schema_version",
            "transformation_contract_version",
            "historical_actor_id",
            "historical_actor_authority_ref",
            "approval_event_id",
            "source_timezone_semantics",
            "target_intent_id",
            "target_snapshot_id",
        ):
            value = getattr(self, field_name)
            if value is not None:
                _require_text(value, field_name)
        for field_name in (
            "reviewed_payload_digest",
            "approved_payload_digest",
            "target_content_hash",
        ):
            value = getattr(self, field_name)
            if value is not None:
                _require_digest(value, field_name)
        if self.approval_occurred_at is not None:
            _require_utc(self.approval_occurred_at, "approval_occurred_at")


@dataclass(frozen=True)
class AuthorityCertificate:
    contract_version: str
    certificate_id: str
    issuer: AuthorityIssuer
    issued_at: datetime
    evidence: tuple[AuthorityEvidence, ...]
    binding: AuthorityBinding
    scope: AuthorityScope
    completeness_claim: AuthorityCompleteness
    supersedes_certificate_id: str | None
    certificate_digest: str
    signature: str

    def __post_init__(self) -> None:
        _require_text(self.contract_version, "contract_version")
        _require_text(self.certificate_id, "certificate_id")
        _require_utc(self.issued_at, "issued_at")
        if not isinstance(self.evidence, tuple) or not self.evidence:
            raise ValueError("evidence must be a non-empty tuple")
        if len({item.evidence_id for item in self.evidence}) != len(self.evidence):
            raise ValueError("evidence_id values must be unique within a certificate")
        if self.supersedes_certificate_id is not None:
            _require_text(self.supersedes_certificate_id, "supersedes_certificate_id")
        _require_enum(self.completeness_claim, AuthorityCompleteness, "completeness_claim")
        _require_digest(self.certificate_digest, "certificate_digest")
        _require_text(self.signature, "signature")


@dataclass(frozen=True)
class DetachedEvidenceFact:
    evidence_id: str
    canonical_payload: str
    digest_matches: bool

    def __post_init__(self) -> None:
        _require_text(self.evidence_id, "evidence_id")
        if not isinstance(self.canonical_payload, str):
            raise ValueError("canonical_payload must be an exact UTF-8 string")


@dataclass(frozen=True)
class SignatureVerificationFact:
    certificate_id: str
    certificate_digest: str
    is_valid: bool

    def __post_init__(self) -> None:
        _require_text(self.certificate_id, "certificate_id")
        _require_digest(self.certificate_digest, "certificate_digest")


@dataclass(frozen=True)
class IssuerTrustFact:
    issuer_id: str
    signing_key_id: str
    trust_policy_version: str
    is_trusted: bool

    def __post_init__(self) -> None:
        _require_text(self.issuer_id, "issuer_id")
        _require_text(self.signing_key_id, "signing_key_id")
        _require_text(self.trust_policy_version, "trust_policy_version")


@dataclass(frozen=True)
class RevocationEvidence:
    certificate_id: str
    certificate_digest: str
    status: RevocationStatus
    effective_at: datetime
    reason: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.certificate_id, "certificate_id")
        _require_digest(self.certificate_digest, "certificate_digest")
        _require_enum(self.status, RevocationStatus, "status")
        _require_utc(self.effective_at, "effective_at")


@dataclass(frozen=True)
class RevocationVerificationFact:
    evidence: RevocationEvidence
    signature_valid: bool
    issuer_trusted: bool


@dataclass(frozen=True)
class AuthorityConflictFact:
    certificate_ids: tuple[str, ...]
    is_conflicting: bool

    def __post_init__(self) -> None:
        if not isinstance(self.certificate_ids, tuple) or not self.certificate_ids:
            raise ValueError("certificate_ids must be a non-empty tuple")
        for certificate_id in self.certificate_ids:
            _require_text(certificate_id, "certificate_id")


@dataclass(frozen=True)
class TargetSnapshotFact:
    intent_id: str
    snapshot_id: str
    content_hash: str
    workspace_id: int
    portfolio_id: int
    authority_namespace: str
    environment_id: str | None = None

    def __post_init__(self) -> None:
        _require_text(self.intent_id, "intent_id")
        _require_text(self.snapshot_id, "snapshot_id")
        _require_digest(self.content_hash, "content_hash")
        if not isinstance(self.workspace_id, int) or not isinstance(self.portfolio_id, int):
            raise ValueError("workspace_id and portfolio_id must be integers")
        _require_text(self.authority_namespace, "authority_namespace")
        if self.environment_id is not None:
            _require_text(self.environment_id, "environment_id")


@dataclass(frozen=True)
class VerificationPolicy:
    contract_version: str
    policy_version: str
    evaluated_at: datetime
    available: bool = True
    supported_authority_contract_versions: frozenset[str] = frozenset({AUTHORITY_CONTRACT_VERSION})
    supported_digest_algorithms: frozenset[DigestAlgorithm] = frozenset({DigestAlgorithm.SHA256})
    supported_signature_algorithms: frozenset[SignatureAlgorithm] = frozenset(SignatureAlgorithm)
    approved_transformations: frozenset[str] = frozenset()
    allow_unverifiable_proposals: bool = False

    def __post_init__(self) -> None:
        _require_text(self.contract_version, "contract_version")
        _require_text(self.policy_version, "policy_version")
        _require_utc(self.evaluated_at, "evaluated_at")
        if not isinstance(self.supported_authority_contract_versions, frozenset):
            raise ValueError("supported_authority_contract_versions must be a frozenset")
        if not isinstance(self.supported_digest_algorithms, frozenset):
            raise ValueError("supported_digest_algorithms must be a frozenset")
        if any(not isinstance(value, DigestAlgorithm) for value in self.supported_digest_algorithms):
            raise ValueError("supported_digest_algorithms contains an invalid value")
        if not isinstance(self.supported_signature_algorithms, frozenset):
            raise ValueError("supported_signature_algorithms must be a frozenset")
        if any(not isinstance(value, SignatureAlgorithm) for value in self.supported_signature_algorithms):
            raise ValueError("supported_signature_algorithms contains an invalid value")
        if not isinstance(self.approved_transformations, frozenset):
            raise ValueError("approved_transformations must be a frozenset")


@dataclass(frozen=True)
class AuthorityVerificationResult:
    verification_contract_version: str
    certificate_id: str | None
    certificate_digest: str | None
    authority_level: AuthorityLevel
    reason_codes: tuple[AuthorityReasonCode, ...]
    verified_evidence_ids: tuple[str, ...]
    rejected_evidence_ids: tuple[str, ...]
    verified_scope: AuthorityScope | None
    verified_historical_actor_id: str | None
    verified_approval_occurred_at: datetime | None
    verified_target_snapshot_id: str | None
    verified_target_content_hash: str | None
    revocation_status: RevocationStatus
    provenance_completeness: ProvenanceCompleteness | None
    may_build_exact_snapshot: bool
    may_build_proposal: bool
    requires_reconfirmation: bool
    may_recreate_historical_approval: bool

    def __post_init__(self) -> None:
        _require_enum(self.authority_level, AuthorityLevel, "authority_level")
        _require_text(self.verification_contract_version, "verification_contract_version")
        if self.certificate_id is not None:
            _require_text(self.certificate_id, "certificate_id")
        if self.certificate_digest is not None:
            _require_digest(self.certificate_digest, "certificate_digest")
        if any(not isinstance(reason, AuthorityReasonCode) for reason in self.reason_codes):
            raise ValueError("reason_codes contains an invalid value")
        object.__setattr__(self, "reason_codes", _ordered_reasons(self.reason_codes))
        object.__setattr__(self, "verified_evidence_ids", tuple(sorted(set(self.verified_evidence_ids))))
        object.__setattr__(self, "rejected_evidence_ids", tuple(sorted(set(self.rejected_evidence_ids))))
        if self.verified_approval_occurred_at is not None:
            _require_utc(self.verified_approval_occurred_at, "verified_approval_occurred_at")
        if self.verified_target_snapshot_id is not None:
            _require_text(self.verified_target_snapshot_id, "verified_target_snapshot_id")
        if self.verified_target_content_hash is not None:
            _require_digest(self.verified_target_content_hash, "verified_target_content_hash")
        _require_enum(self.revocation_status, RevocationStatus, "revocation_status")
        if self.provenance_completeness is not None:
            _require_enum(
                self.provenance_completeness,
                ProvenanceCompleteness,
                "provenance_completeness",
            )
        if self.authority_level == AuthorityLevel.CERTIFIED_EXACT:
            if not self.may_build_exact_snapshot or not self.may_recreate_historical_approval:
                raise ValueError("CERTIFIED_EXACT must expose both exact capabilities")
            if self.reason_codes:
                raise ValueError("CERTIFIED_EXACT must not contain refusal/downgrade reasons")
            if (
                self.verified_scope is None
                or not self.verified_historical_actor_id
                or self.verified_approval_occurred_at is None
                or not self.verified_target_snapshot_id
                or not self.verified_target_content_hash
                or self.revocation_status != RevocationStatus.NOT_REVOKED
                or self.provenance_completeness != ProvenanceCompleteness.EXACT_FROZEN
            ):
                raise ValueError("CERTIFIED_EXACT requires complete verified authority facts")
        elif self.may_build_exact_snapshot or self.may_recreate_historical_approval:
            raise ValueError("only CERTIFIED_EXACT may expose exact capabilities")
        elif not self.reason_codes:
            raise ValueError("every non-exact authority result requires a reason code")


def canonicalize_authority_evidence(evidence: AuthorityEvidence) -> str:
    """Return explicit-field canonical JSON for one evidence envelope."""

    return _canonical_json(_authority_evidence_dict(evidence))


def compute_authority_evidence_digest(
    canonical_payload: str,
    *,
    source_contract_version: str,
) -> str:
    """Digest exact canonical source bytes, not a locator or reconstructed row."""

    if not isinstance(canonical_payload, str):
        raise ValueError("canonical_payload must be an exact UTF-8 string")
    _require_text(source_contract_version, "source_contract_version")
    domain = f"M33.5:authority-evidence:{source_contract_version}\n"
    return _sha256(domain + canonical_payload)


def canonicalize_authority_certificate(certificate: AuthorityCertificate) -> str:
    """Canonical signed content, excluding certificate_digest and signature."""

    evidence = sorted(
        certificate.evidence,
        key=lambda item: (
            item.evidence_kind.value,
            item.source_local_id,
            item.source_digest,
        ),
    )
    payload = {
        "contract_version": certificate.contract_version,
        "certificate_id": certificate.certificate_id,
        "issuer": _authority_issuer_dict(certificate.issuer),
        "issued_at": _canon_datetime(certificate.issued_at),
        "evidence": [_authority_evidence_dict(item) for item in evidence],
        "binding": _authority_binding_dict(certificate.binding),
        "scope": _authority_scope_dict(certificate.scope),
        "completeness_claim": certificate.completeness_claim.value,
        "supersedes_certificate_id": certificate.supersedes_certificate_id,
    }
    return _canonical_json(payload)


def compute_authority_certificate_digest(certificate: AuthorityCertificate) -> str:
    domain = f"M33.5:authority-certificate:{certificate.contract_version}\n"
    return _sha256(domain + canonicalize_authority_certificate(certificate))


def verify_authority(
    certificate: AuthorityCertificate | None,
    *,
    verification_policy: VerificationPolicy,
    detached_evidence: tuple[DetachedEvidenceFact, ...] = (),
    signature_fact: SignatureVerificationFact | None = None,
    issuer_trust_fact: IssuerTrustFact | None = None,
    revocation_facts: tuple[RevocationVerificationFact, ...] = (),
    target_snapshot_fact: TargetSnapshotFact | None = None,
    related_certificates: tuple[AuthorityCertificate, ...] = (),
    conflict_facts: tuple[AuthorityConflictFact, ...] = (),
    uncertified_evidence: tuple[AuthorityEvidence, ...] = (),
    uncertified_scope: AuthorityScope | None = None,
    source_act: HistoricalSourceAct | None = None,
) -> AuthorityVerificationResult:
    """Pure fail-closed authority eligibility verification.

    Every external conclusion is caller-supplied.  The verifier performs only
    deterministic structural, canonical-digest, equality, and policy checks.
    """

    effective_act = certificate.binding.source_act if certificate is not None else source_act
    if effective_act in (HistoricalSourceAct.REJECTED, HistoricalSourceAct.EXPIRED):
        return _verification_result(
            certificate,
            AuthorityLevel.OUT_OF_SCOPE,
            (AuthorityReasonCode.OUT_OF_SCOPE_DECISION,),
            revocation_status=RevocationStatus.UNKNOWN,
        )

    if certificate is None:
        return _verify_without_certificate(
            evidence=uncertified_evidence,
            scope=uncertified_scope,
            source_act=effective_act,
            detached_evidence=detached_evidence,
            policy=verification_policy,
        )

    proposal_available = _has_candidate_payload(certificate.evidence, detached_evidence)

    if (
        verification_policy.contract_version != VERIFICATION_POLICY_VERSION
        or certificate.contract_version not in verification_policy.supported_authority_contract_versions
    ):
        return _unverifiable(
            certificate,
            (AuthorityReasonCode.UNSUPPORTED_CONTRACT_VERSION,),
            policy=verification_policy,
            proposal_available=proposal_available,
        )
    if any(
        item.source_digest_algorithm not in verification_policy.supported_digest_algorithms
        for item in certificate.evidence
    ):
        return _unverifiable(
            certificate,
            (AuthorityReasonCode.UNSUPPORTED_DIGEST_ALGORITHM,),
            policy=verification_policy,
            proposal_available=proposal_available,
        )
    if certificate.issuer.signature_algorithm not in verification_policy.supported_signature_algorithms:
        return _unverifiable(
            certificate,
            (AuthorityReasonCode.UNSUPPORTED_SIGNATURE_ALGORITHM,),
            policy=verification_policy,
            proposal_available=proposal_available,
        )

    conflict_reasons = _certificate_conflicts(certificate, related_certificates, conflict_facts)
    if conflict_reasons:
        return _verification_result(
            certificate,
            AuthorityLevel.CONFLICTING,
            conflict_reasons,
            revocation_status=RevocationStatus.CONFLICTING,
        )

    if compute_authority_certificate_digest(certificate) != certificate.certificate_digest:
        return _unverifiable(
            certificate,
            (AuthorityReasonCode.CERTIFICATE_DIGEST_MISMATCH,),
            policy=verification_policy,
            proposal_available=proposal_available,
        )

    verified_ids, rejected_ids, evidence_reasons = _verify_evidence(
        certificate.evidence,
        detached_evidence,
    )
    if evidence_reasons:
        return _unverifiable(
            certificate,
            evidence_reasons,
            policy=verification_policy,
            proposal_available=proposal_available,
            verified_ids=verified_ids,
            rejected_ids=rejected_ids,
        )

    if (
        signature_fact is None
        or signature_fact.certificate_id != certificate.certificate_id
        or signature_fact.certificate_digest != certificate.certificate_digest
        or not signature_fact.is_valid
    ):
        return _unverifiable(
            certificate,
            (AuthorityReasonCode.SIGNATURE_INVALID,),
            policy=verification_policy,
            proposal_available=proposal_available,
            verified_ids=verified_ids,
        )

    if not verification_policy.available:
        return _unverifiable(
            certificate,
            (AuthorityReasonCode.TRUST_POLICY_UNAVAILABLE,),
            policy=verification_policy,
            proposal_available=proposal_available,
            verified_ids=verified_ids,
        )
    if issuer_trust_fact is None:
        return _unverifiable(
            certificate,
            (AuthorityReasonCode.ISSUER_UNTRUSTED,),
            policy=verification_policy,
            proposal_available=proposal_available,
            verified_ids=verified_ids,
        )
    if (
        issuer_trust_fact.trust_policy_version != verification_policy.policy_version
        or certificate.issuer.trust_policy_version != verification_policy.policy_version
    ):
        return _unverifiable(
            certificate,
            (AuthorityReasonCode.TRUST_POLICY_MISMATCH,),
            policy=verification_policy,
            proposal_available=proposal_available,
            verified_ids=verified_ids,
        )
    if (
        issuer_trust_fact.issuer_id != certificate.issuer.issuer_id
        or issuer_trust_fact.signing_key_id != certificate.issuer.signing_key_id
        or not issuer_trust_fact.is_trusted
    ):
        return _unverifiable(
            certificate,
            (AuthorityReasonCode.ISSUER_UNTRUSTED,),
            policy=verification_policy,
            proposal_available=proposal_available,
            verified_ids=verified_ids,
        )

    revocation_status = _resolve_revocation(certificate, revocation_facts, verification_policy)
    if revocation_status == RevocationStatus.CONFLICTING:
        return _verification_result(
            certificate,
            AuthorityLevel.CONFLICTING,
            (AuthorityReasonCode.REVOCATION_STATUS_CONFLICT,),
            verified_ids=verified_ids,
            revocation_status=revocation_status,
        )
    if revocation_status == RevocationStatus.REVOKED:
        return _verification_result(
            certificate,
            AuthorityLevel.UNVERIFIABLE,
            (AuthorityReasonCode.CERTIFICATE_REVOKED,),
            verified_ids=verified_ids,
            revocation_status=revocation_status,
            provenance=ProvenanceCompleteness.INCOMPLETE,
        )
    if revocation_status == RevocationStatus.UNKNOWN:
        return _verification_result(
            certificate,
            AuthorityLevel.UNVERIFIABLE,
            (AuthorityReasonCode.REVOCATION_STATUS_UNKNOWN,),
            verified_ids=verified_ids,
            revocation_status=revocation_status,
            provenance=ProvenanceCompleteness.INCOMPLETE,
            may_build_proposal=verification_policy.allow_unverifiable_proposals and proposal_available,
            requires_reconfirmation=verification_policy.allow_unverifiable_proposals and proposal_available,
        )

    scope_reasons = _scope_reasons(certificate.scope, target_snapshot_fact)
    if scope_reasons:
        return _verification_result(
            certificate,
            AuthorityLevel.CONFLICTING,
            scope_reasons,
            verified_ids=verified_ids,
            revocation_status=revocation_status,
        )

    if certificate.binding.lineage_ambiguous:
        return _verification_result(
            certificate,
            AuthorityLevel.CONFLICTING,
            (AuthorityReasonCode.LINEAGE_AMBIGUOUS,),
            verified_ids=verified_ids,
            verified_scope=certificate.scope,
            revocation_status=revocation_status,
        )

    payload_conflict = _payload_conflict_reason(certificate.binding, verification_policy)
    if payload_conflict is not None:
        return _verification_result(
            certificate,
            AuthorityLevel.CONFLICTING,
            (payload_conflict,),
            verified_ids=verified_ids,
            verified_scope=certificate.scope,
            revocation_status=revocation_status,
        )

    downgrade_reasons = _exact_requirement_reasons(
        certificate,
        verified_ids=frozenset(verified_ids),
        target=target_snapshot_fact,
    )
    if downgrade_reasons:
        level = (
            AuthorityLevel.CERTIFIED_PROPOSAL_ONLY
            if proposal_available
            else AuthorityLevel.UNVERIFIABLE
        )
        can_propose = proposal_available
        return _verification_result(
            certificate,
            level,
            tuple(downgrade_reasons) + (AuthorityReasonCode.FRESH_RECONFIRMATION_REQUIRED,),
            verified_ids=verified_ids,
            verified_scope=certificate.scope,
            verified_actor=(
                certificate.binding.historical_actor_id
                if AuthorityReasonCode.HISTORICAL_ACTOR_MISSING not in downgrade_reasons
                and AuthorityReasonCode.HISTORICAL_ACTOR_AMBIGUOUS not in downgrade_reasons
                else None
            ),
            verified_time=(
                certificate.binding.approval_occurred_at
                if AuthorityReasonCode.APPROVAL_TIME_MISSING not in downgrade_reasons
                and AuthorityReasonCode.TIMEZONE_AMBIGUOUS not in downgrade_reasons
                else None
            ),
            revocation_status=revocation_status,
            provenance=(
                ProvenanceCompleteness.LEGACY_RECONSTRUCTED
                if can_propose
                else ProvenanceCompleteness.INCOMPLETE
            ),
            may_build_proposal=can_propose,
            requires_reconfirmation=can_propose,
        )

    return _verification_result(
        certificate,
        AuthorityLevel.CERTIFIED_EXACT,
        (),
        verified_ids=verified_ids,
        verified_scope=certificate.scope,
        verified_actor=certificate.binding.historical_actor_id,
        verified_time=certificate.binding.approval_occurred_at,
        verified_target_snapshot_id=certificate.binding.target_snapshot_id,
        verified_target_content_hash=certificate.binding.target_content_hash,
        revocation_status=revocation_status,
        provenance=ProvenanceCompleteness.EXACT_FROZEN,
        may_build_exact_snapshot=True,
        may_build_proposal=True,
        may_recreate_historical_approval=True,
    )


def _verify_without_certificate(
    *,
    evidence: tuple[AuthorityEvidence, ...],
    scope: AuthorityScope | None,
    source_act: HistoricalSourceAct | None,
    detached_evidence: tuple[DetachedEvidenceFact, ...],
    policy: VerificationPolicy,
) -> AuthorityVerificationResult:
    verified_ids, rejected_ids, evidence_reasons = _verify_evidence(evidence, detached_evidence)
    candidate_available = scope is not None and _has_candidate_payload(evidence, detached_evidence)
    reasons = [AuthorityReasonCode.CERTIFICATE_MISSING, *evidence_reasons]
    if source_act == HistoricalSourceAct.PARTIAL_EXECUTION:
        reasons.append(AuthorityReasonCode.PARTIAL_EXECUTION_NOT_INTENT_AUTHORITY)
    can_propose = (
        policy.available
        and policy.allow_unverifiable_proposals
        and candidate_available
        and not evidence_reasons
    )
    if can_propose:
        reasons.append(AuthorityReasonCode.FRESH_RECONFIRMATION_REQUIRED)
    return _verification_result(
        None,
        AuthorityLevel.UNVERIFIABLE,
        reasons,
        verified_ids=verified_ids,
        rejected_ids=rejected_ids,
        verified_scope=scope if not evidence_reasons else None,
        revocation_status=RevocationStatus.UNKNOWN,
        provenance=ProvenanceCompleteness.INCOMPLETE,
        may_build_proposal=can_propose,
        requires_reconfirmation=can_propose,
    )


def _verify_evidence(
    evidence: tuple[AuthorityEvidence, ...],
    detached_evidence: tuple[DetachedEvidenceFact, ...],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[AuthorityReasonCode, ...]]:
    detached: dict[str, DetachedEvidenceFact] = {}
    reasons: list[AuthorityReasonCode] = []
    rejected: list[str] = []
    for fact in detached_evidence:
        existing = detached.get(fact.evidence_id)
        if existing is not None and existing != fact:
            reasons.append(AuthorityReasonCode.EVIDENCE_DIGEST_MISMATCH)
        detached[fact.evidence_id] = fact

    verified: list[str] = []
    for item in evidence:
        prohibited = _prohibited_evidence_reason(item.evidence_kind)
        if prohibited is not None:
            reasons.append(prohibited)
            rejected.append(item.evidence_id)
            continue
        fact = detached.get(item.evidence_id)
        payload = item.canonical_payload if item.canonical_payload is not None else (fact.canonical_payload if fact else None)
        requires_payload = bool(
            item.evidence_roles
            & frozenset(
                {
                    AuthorityEvidenceRole.REVIEWED_PAYLOAD,
                    AuthorityEvidenceRole.APPROVED_PAYLOAD,
                }
            )
        )
        if requires_payload and payload is None:
            reasons.append(AuthorityReasonCode.EVIDENCE_PAYLOAD_MISSING)
            rejected.append(item.evidence_id)
            continue
        if fact is not None and not fact.digest_matches:
            reasons.append(AuthorityReasonCode.EVIDENCE_DIGEST_MISMATCH)
            rejected.append(item.evidence_id)
            continue
        if payload is not None:
            computed = compute_authority_evidence_digest(
                payload,
                source_contract_version=item.source_contract_version,
            )
            if computed != item.source_digest:
                reasons.append(AuthorityReasonCode.EVIDENCE_DIGEST_MISMATCH)
                rejected.append(item.evidence_id)
                continue
        verified.append(item.evidence_id)
    return tuple(sorted(set(verified))), tuple(sorted(set(rejected))), _ordered_reasons(reasons)


def _certificate_conflicts(
    certificate: AuthorityCertificate,
    related_certificates: tuple[AuthorityCertificate, ...],
    conflict_facts: tuple[AuthorityConflictFact, ...],
) -> tuple[AuthorityReasonCode, ...]:
    reasons: list[AuthorityReasonCode] = []
    for related in related_certificates:
        if related.certificate_id == certificate.certificate_id:
            if related.certificate_digest != certificate.certificate_digest:
                reasons.append(AuthorityReasonCode.CERTIFICATE_ID_REUSED)
            continue
        if (
            certificate.binding.approval_event_id
            and related.binding.approval_event_id == certificate.binding.approval_event_id
            and _authority_binding_dict(related.binding) != _authority_binding_dict(certificate.binding)
        ):
            reasons.append(AuthorityReasonCode.CONFLICTING_CERTIFICATES)
    for fact in conflict_facts:
        if fact.is_conflicting and certificate.certificate_id in fact.certificate_ids:
            reasons.append(AuthorityReasonCode.CONFLICTING_CERTIFICATES)
    return _ordered_reasons(reasons)


def _resolve_revocation(
    certificate: AuthorityCertificate,
    facts: tuple[RevocationVerificationFact, ...],
    policy: VerificationPolicy,
) -> RevocationStatus:
    statuses: set[RevocationStatus] = set()
    for fact in facts:
        evidence = fact.evidence
        if (
            not fact.signature_valid
            or not fact.issuer_trusted
            or evidence.certificate_id != certificate.certificate_id
            or evidence.certificate_digest != certificate.certificate_digest
            or evidence.effective_at > policy.evaluated_at
        ):
            continue
        statuses.add(evidence.status)
    if RevocationStatus.CONFLICTING in statuses:
        return RevocationStatus.CONFLICTING
    decisive = statuses & {RevocationStatus.REVOKED, RevocationStatus.NOT_REVOKED}
    if len(decisive) > 1:
        return RevocationStatus.CONFLICTING
    if RevocationStatus.REVOKED in decisive:
        return RevocationStatus.REVOKED
    if RevocationStatus.NOT_REVOKED in decisive:
        return RevocationStatus.NOT_REVOKED
    return RevocationStatus.UNKNOWN


def _scope_reasons(
    scope: AuthorityScope,
    target: TargetSnapshotFact | None,
) -> tuple[AuthorityReasonCode, ...]:
    if target is None:
        return ()
    reasons: list[AuthorityReasonCode] = []
    if scope.workspace_id != target.workspace_id:
        reasons.append(AuthorityReasonCode.WORKSPACE_SCOPE_MISMATCH)
    if scope.portfolio_id != target.portfolio_id:
        reasons.append(AuthorityReasonCode.PORTFOLIO_SCOPE_MISMATCH)
    if scope.authority_namespace != target.authority_namespace:
        reasons.append(AuthorityReasonCode.AUTHORITY_NAMESPACE_MISMATCH)
    if scope.environment_id != target.environment_id:
        reasons.append(AuthorityReasonCode.ENVIRONMENT_SCOPE_MISMATCH)
    return _ordered_reasons(reasons)


def _payload_conflict_reason(
    binding: AuthorityBinding,
    policy: VerificationPolicy,
) -> AuthorityReasonCode | None:
    reviewed = binding.reviewed_payload_digest
    approved = binding.approved_payload_digest
    if reviewed is None or approved is None:
        return None
    if binding.payload_relationship == PayloadRelationship.IDENTICAL:
        if reviewed != approved:
            return AuthorityReasonCode.REVIEWED_APPROVED_PAYLOAD_CONFLICT
        return None
    if binding.payload_relationship == PayloadRelationship.LOSSLESS_TRANSFORMATION:
        if (
            not binding.transformation_contract_version
            or binding.transformation_contract_version not in policy.approved_transformations
        ):
            return AuthorityReasonCode.LOSSLESS_MAPPING_UNPROVEN
        return None
    if reviewed != approved:
        return AuthorityReasonCode.REVIEWED_APPROVED_PAYLOAD_CONFLICT
    return None


def _exact_requirement_reasons(
    certificate: AuthorityCertificate,
    *,
    verified_ids: frozenset[str],
    target: TargetSnapshotFact | None,
) -> list[AuthorityReasonCode]:
    binding = certificate.binding
    reasons: list[AuthorityReasonCode] = []
    if binding.source_act == HistoricalSourceAct.PARTIAL_EXECUTION:
        reasons.append(AuthorityReasonCode.PARTIAL_EXECUTION_NOT_INTENT_AUTHORITY)
    if binding.recommendation_ref is None:
        reasons.append(AuthorityReasonCode.RECOMMENDATION_BINDING_MISSING)
    if binding.decision_ref is None:
        reasons.append(AuthorityReasonCode.DECISION_BINDING_MISSING)

    reviewed_ids = {
        item.evidence_id
        for item in certificate.evidence
        if AuthorityEvidenceRole.REVIEWED_PAYLOAD in item.evidence_roles
        and item.source_digest == binding.reviewed_payload_digest
    }
    approved_ids = {
        item.evidence_id
        for item in certificate.evidence
        if AuthorityEvidenceRole.APPROVED_PAYLOAD in item.evidence_roles
        and item.source_digest == binding.approved_payload_digest
    }
    if (
        not binding.reviewed_payload_schema_version
        or not binding.reviewed_payload_digest
        or not (reviewed_ids & verified_ids)
    ):
        reasons.append(AuthorityReasonCode.REVIEWED_PAYLOAD_MISSING)
    if (
        not binding.approved_payload_schema_version
        or not binding.approved_payload_digest
        or not (approved_ids & verified_ids)
    ):
        reasons.append(AuthorityReasonCode.APPROVED_PAYLOAD_MISSING)

    if not binding.historical_actor_id:
        reasons.append(AuthorityReasonCode.HISTORICAL_ACTOR_MISSING)
    if binding.historical_actor_ambiguous:
        reasons.append(AuthorityReasonCode.HISTORICAL_ACTOR_AMBIGUOUS)
    identity_ids = {
        item.evidence_id
        for item in certificate.evidence
        if AuthorityEvidenceRole.ACTOR_IDENTITY in item.evidence_roles
    }
    if not (identity_ids & verified_ids):
        reasons.append(AuthorityReasonCode.ACTOR_IDENTITY_UNPROVEN)
    if (
        not binding.historical_actor_authority_ref
        or binding.historical_actor_authority_ref not in verified_ids
        or not any(
            item.evidence_id == binding.historical_actor_authority_ref
            and AuthorityEvidenceRole.ACTOR_AUTHORITY in item.evidence_roles
            for item in certificate.evidence
        )
    ):
        reasons.append(AuthorityReasonCode.ACTOR_AUTHORITY_UNPROVEN)

    if binding.approval_occurred_at is None:
        reasons.append(AuthorityReasonCode.APPROVAL_TIME_MISSING)
    if (
        binding.approval_time_ambiguous
        or (binding.approval_time_was_converted and not binding.source_timezone_semantics)
    ):
        reasons.append(AuthorityReasonCode.TIMEZONE_AMBIGUOUS)

    if target is None:
        reasons.extend(
            (
                AuthorityReasonCode.TARGET_INTENT_BINDING_MISSING,
                AuthorityReasonCode.TARGET_SNAPSHOT_BINDING_MISSING,
                AuthorityReasonCode.TARGET_CONTENT_HASH_MISSING,
            )
        )
    else:
        if not binding.target_intent_id:
            reasons.append(AuthorityReasonCode.TARGET_INTENT_BINDING_MISSING)
        elif binding.target_intent_id != target.intent_id:
            reasons.append(AuthorityReasonCode.TARGET_INTENT_ID_MISMATCH)
        if not binding.target_snapshot_id:
            reasons.append(AuthorityReasonCode.TARGET_SNAPSHOT_BINDING_MISSING)
        elif binding.target_snapshot_id != target.snapshot_id:
            reasons.append(AuthorityReasonCode.TARGET_SNAPSHOT_ID_MISMATCH)
        if not binding.target_content_hash:
            reasons.append(AuthorityReasonCode.TARGET_CONTENT_HASH_MISSING)
        elif binding.target_content_hash != target.content_hash:
            reasons.append(AuthorityReasonCode.TARGET_CONTENT_HASH_MISMATCH)
    return list(_ordered_reasons(reasons))


def _unverifiable(
    certificate: AuthorityCertificate,
    reasons: tuple[AuthorityReasonCode, ...],
    *,
    policy: VerificationPolicy,
    proposal_available: bool,
    verified_ids: tuple[str, ...] = (),
    rejected_ids: tuple[str, ...] = (),
) -> AuthorityVerificationResult:
    can_propose = policy.allow_unverifiable_proposals and proposal_available
    return _verification_result(
        certificate,
        AuthorityLevel.UNVERIFIABLE,
        reasons,
        verified_ids=verified_ids,
        rejected_ids=rejected_ids,
        revocation_status=RevocationStatus.UNKNOWN,
        provenance=ProvenanceCompleteness.INCOMPLETE,
        may_build_proposal=can_propose,
        requires_reconfirmation=can_propose,
    )


def _verification_result(
    certificate: AuthorityCertificate | None,
    level: AuthorityLevel,
    reasons: tuple[AuthorityReasonCode, ...] | list[AuthorityReasonCode],
    *,
    verified_ids: tuple[str, ...] = (),
    rejected_ids: tuple[str, ...] = (),
    verified_scope: AuthorityScope | None = None,
    verified_actor: str | None = None,
    verified_time: datetime | None = None,
    verified_target_snapshot_id: str | None = None,
    verified_target_content_hash: str | None = None,
    revocation_status: RevocationStatus,
    provenance: ProvenanceCompleteness | None = None,
    may_build_exact_snapshot: bool = False,
    may_build_proposal: bool = False,
    requires_reconfirmation: bool = False,
    may_recreate_historical_approval: bool = False,
) -> AuthorityVerificationResult:
    return AuthorityVerificationResult(
        verification_contract_version=VERIFICATION_POLICY_VERSION,
        certificate_id=certificate.certificate_id if certificate else None,
        certificate_digest=certificate.certificate_digest if certificate else None,
        authority_level=level,
        reason_codes=_ordered_reasons(reasons),
        verified_evidence_ids=verified_ids,
        rejected_evidence_ids=rejected_ids,
        verified_scope=verified_scope,
        verified_historical_actor_id=verified_actor,
        verified_approval_occurred_at=verified_time,
        verified_target_snapshot_id=verified_target_snapshot_id,
        verified_target_content_hash=verified_target_content_hash,
        revocation_status=revocation_status,
        provenance_completeness=provenance,
        may_build_exact_snapshot=may_build_exact_snapshot,
        may_build_proposal=may_build_proposal,
        requires_reconfirmation=requires_reconfirmation,
        may_recreate_historical_approval=may_recreate_historical_approval,
    )


def _has_candidate_payload(
    evidence: tuple[AuthorityEvidence, ...],
    detached: tuple[DetachedEvidenceFact, ...],
) -> bool:
    detached_ids = {fact.evidence_id for fact in detached if fact.digest_matches}
    return any(
        item.evidence_roles
        & frozenset(
            {
                AuthorityEvidenceRole.REVIEWED_PAYLOAD,
                AuthorityEvidenceRole.APPROVED_PAYLOAD,
            }
        )
        and (item.canonical_payload is not None or item.evidence_id in detached_ids)
        and _prohibited_evidence_reason(item.evidence_kind) is None
        for item in evidence
    )


def _prohibited_evidence_reason(
    kind: AuthorityEvidenceKind,
) -> AuthorityReasonCode | None:
    if kind == AuthorityEvidenceKind.SHADOW_PORTFOLIO:
        return AuthorityReasonCode.SHADOW_EVIDENCE_PROHIBITED
    if kind in (AuthorityEvidenceKind.TRANSACTION_LINK, AuthorityEvidenceKind.TRANSACTION_ROW):
        return AuthorityReasonCode.TRANSACTION_EVIDENCE_PROHIBITED
    if kind == AuthorityEvidenceKind.CURRENT_PORTFOLIO_HOLDINGS:
        return AuthorityReasonCode.PORTFOLIO_HOLDINGS_EVIDENCE_PROHIBITED
    return None


def _authority_issuer_dict(issuer: AuthorityIssuer) -> dict:
    return {
        "issuer_id": issuer.issuer_id,
        "issuer_kind": issuer.issuer_kind.value,
        "authority_namespace": issuer.authority_namespace,
        "trust_policy_version": issuer.trust_policy_version,
        "signing_key_id": issuer.signing_key_id,
        "signature_algorithm": issuer.signature_algorithm.value,
    }


def _authority_source_ref_dict(reference: AuthoritySourceReference | None) -> dict | None:
    if reference is None:
        return None
    return {
        "source_local_id": reference.source_local_id,
        "source_digest": reference.source_digest,
    }


def _authority_evidence_dict(evidence: AuthorityEvidence) -> dict:
    return {
        "evidence_id": evidence.evidence_id,
        "evidence_kind": evidence.evidence_kind.value,
        "evidence_roles": sorted(role.value for role in evidence.evidence_roles),
        "source_local_id": evidence.source_local_id,
        "source_contract_version": evidence.source_contract_version,
        "canonical_payload": evidence.canonical_payload,
        "source_digest_algorithm": evidence.source_digest_algorithm.value,
        "source_digest": evidence.source_digest,
        "occurred_at": _canon_datetime(evidence.occurred_at) if evidence.occurred_at else None,
        "recorded_at": _canon_datetime(evidence.recorded_at),
        "source_timezone": evidence.source_timezone,
        "source_local_time_text": evidence.source_local_time_text,
        "locator": evidence.locator,
    }


def _authority_scope_dict(scope: AuthorityScope) -> dict:
    return {
        "workspace_id": scope.workspace_id,
        "portfolio_id": scope.portfolio_id,
        "authority_namespace": scope.authority_namespace,
        "environment_id": scope.environment_id,
    }


def _authority_binding_dict(binding: AuthorityBinding) -> dict:
    return {
        "source_act": binding.source_act.value,
        "reviewed_payload_schema_version": binding.reviewed_payload_schema_version,
        "reviewed_payload_digest": binding.reviewed_payload_digest,
        "approved_payload_schema_version": binding.approved_payload_schema_version,
        "approved_payload_digest": binding.approved_payload_digest,
        "payload_relationship": binding.payload_relationship.value if binding.payload_relationship else None,
        "transformation_contract_version": binding.transformation_contract_version,
        "historical_actor_id": binding.historical_actor_id,
        "historical_actor_authority_ref": binding.historical_actor_authority_ref,
        "recommendation_ref": _authority_source_ref_dict(binding.recommendation_ref),
        "decision_ref": _authority_source_ref_dict(binding.decision_ref),
        "approval_event_id": binding.approval_event_id,
        "approval_occurred_at": (
            _canon_datetime(binding.approval_occurred_at)
            if binding.approval_occurred_at
            else None
        ),
        "source_timezone_semantics": binding.source_timezone_semantics,
        "approval_time_was_converted": binding.approval_time_was_converted,
        "approval_time_ambiguous": binding.approval_time_ambiguous,
        "historical_actor_ambiguous": binding.historical_actor_ambiguous,
        "lineage_ambiguous": binding.lineage_ambiguous,
        "target_intent_id": binding.target_intent_id,
        "target_snapshot_id": binding.target_snapshot_id,
        "target_content_hash": binding.target_content_hash,
    }


def _canonical_json(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _sha256(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


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


def _ordered_reasons(
    reasons: tuple[AuthorityReasonCode, ...] | list[AuthorityReasonCode],
) -> tuple[AuthorityReasonCode, ...]:
    return tuple(sorted(set(reasons), key=lambda reason: reason.value))
