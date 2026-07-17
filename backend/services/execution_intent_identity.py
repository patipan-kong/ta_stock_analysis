"""Pure identity and scoped-authority contracts for M33 approval (M33.8).

The Authentication/Authorization domain owns accounts, credentials, login,
sessions, actor status, memberships, roles, grants, delegation, and
impersonation.  This module owns none of those systems.  It receives immutable
references and point-in-time facts from a caller and validates whether one
stable human has current authority to review one exact workspace/portfolio
scope.

There are deliberately no ORM, framework, environment, token, database, or
clock imports.  Expected business failures are typed result data.  Only
construction-time malformed primitives raise ``ValueError``.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

from services.execution_intent_contracts import ActorType

__all__ = [
    "IDENTITY_CONTRACT_VERSION",
    "IDENTITY_VALIDATION_POLICY_VERSION",
    "ActorType",
    "ActorLifecycleStatus",
    "CredentialBinding",
    "CredentialStatus",
    "SessionStatus",
    "AuthenticationSubjectMode",
    "AuthenticationAssuranceClass",
    "Permission",
    "GrantKind",
    "GrantStatus",
    "ResourceStatus",
    "AuthorityDecision",
    "IdentityValidationOutcome",
    "IdentityRefusalCode",
    "ActorRef",
    "AuthenticationEventRef",
    "ActorStatusFact",
    "AuthorizationScope",
    "GrantSourceRef",
    "ActorAuthorityFact",
    "IdentityValidationPolicy",
    "IdentityValidationInput",
    "IdentityValidationResult",
    "canonicalize_actor_ref",
    "compute_actor_ref_hash",
    "canonicalize_authentication_event_ref",
    "compute_authentication_event_ref_hash",
    "canonicalize_actor_authority_fact",
    "compute_actor_authority_fact_hash",
    "canonicalize_identity_validation_binding",
    "compute_identity_validation_binding_hash",
    "validate_human_authority",
]


IDENTITY_CONTRACT_VERSION = "1"
IDENTITY_VALIDATION_POLICY_VERSION = "1"
_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class ActorLifecycleStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    DELETED = "DELETED"
    UNKNOWN = "UNKNOWN"


class CredentialBinding(str, Enum):
    INDIVIDUAL = "INDIVIDUAL"
    SHARED = "SHARED"


class CredentialStatus(str, Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    UNKNOWN = "UNKNOWN"


class SessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    UNKNOWN = "UNKNOWN"


class AuthenticationSubjectMode(str, Enum):
    DIRECT = "DIRECT"
    DELEGATED = "DELEGATED"
    IMPERSONATED = "IMPERSONATED"


class AuthenticationAssuranceClass(str, Enum):
    PASSWORD = "PASSWORD"
    MULTI_FACTOR = "MULTI_FACTOR"
    FEDERATED_HIGH = "FEDERATED_HIGH"
    HARDWARE_BOUND = "HARDWARE_BOUND"


class Permission(str, Enum):
    EXECUTION_INTENT_REVIEW = "EXECUTION_INTENT_REVIEW"
    # Typed non-approval permission used to make permission mismatch explicit.
    EXECUTION_INTENT_PREPARE = "EXECUTION_INTENT_PREPARE"


class GrantKind(str, Enum):
    DIRECT_PORTFOLIO = "DIRECT_PORTFOLIO"
    WORKSPACE_INHERITED = "WORKSPACE_INHERITED"


class GrantStatus(str, Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"
    UNKNOWN = "UNKNOWN"


class ResourceStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DELETED = "DELETED"
    UNKNOWN = "UNKNOWN"


class AuthorityDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"


class IdentityValidationOutcome(str, Enum):
    ACCEPTED = "ACCEPTED"
    REFUSED = "REFUSED"


class IdentityRefusalCode(str, Enum):
    UNSUPPORTED_CONTRACT_VERSION = "UNSUPPORTED_CONTRACT_VERSION"
    UNSUPPORTED_POLICY_VERSION = "UNSUPPORTED_POLICY_VERSION"
    UNSUPPORTED_AUTHORIZATION_POLICY = "UNSUPPORTED_AUTHORIZATION_POLICY"
    AUTHORITY_NAMESPACE_MISMATCH = "AUTHORITY_NAMESPACE_MISMATCH"
    SYSTEM_ACTOR_CANNOT_REVIEW = "SYSTEM_ACTOR_CANNOT_REVIEW"
    SHARED_CREDENTIAL_PROHIBITED = "SHARED_CREDENTIAL_PROHIBITED"
    DELEGATION_UNSUPPORTED = "DELEGATION_UNSUPPORTED"
    IMPERSONATION_UNSUPPORTED = "IMPERSONATION_UNSUPPORTED"
    AUTHENTICATION_EVENT_MISSING = "AUTHENTICATION_EVENT_MISSING"
    AUTHENTICATION_ACTOR_MISMATCH = "AUTHENTICATION_ACTOR_MISMATCH"
    AUTHENTICATION_PROVIDER_MISMATCH = "AUTHENTICATION_PROVIDER_MISMATCH"
    ACTOR_STATUS_FACT_MISSING = "ACTOR_STATUS_FACT_MISSING"
    ACTOR_STATUS_MISMATCH = "ACTOR_STATUS_MISMATCH"
    AUTHORITY_FACT_MISSING = "AUTHORITY_FACT_MISSING"
    AUTHORITY_ACTOR_MISMATCH = "AUTHORITY_ACTOR_MISMATCH"
    AUTHORITY_AUTHENTICATION_EVENT_MISMATCH = "AUTHORITY_AUTHENTICATION_EVENT_MISMATCH"
    ACTOR_DISABLED = "ACTOR_DISABLED"
    ACTOR_DELETED = "ACTOR_DELETED"
    ACTOR_STATUS_UNKNOWN = "ACTOR_STATUS_UNKNOWN"
    CREDENTIAL_REVOKED = "CREDENTIAL_REVOKED"
    CREDENTIAL_STATUS_UNKNOWN = "CREDENTIAL_STATUS_UNKNOWN"
    CREDENTIAL_STATUS_VERSION_MISMATCH = "CREDENTIAL_STATUS_VERSION_MISMATCH"
    SESSION_REVOKED = "SESSION_REVOKED"
    SESSION_STATUS_UNKNOWN = "SESSION_STATUS_UNKNOWN"
    AUTHENTICATION_NOT_YET_VALID = "AUTHENTICATION_NOT_YET_VALID"
    AUTHENTICATION_EXPIRED = "AUTHENTICATION_EXPIRED"
    AUTHENTICATION_STALE = "AUTHENTICATION_STALE"
    ACTOR_STATUS_NOT_YET_VALID = "ACTOR_STATUS_NOT_YET_VALID"
    ACTOR_STATUS_EXPIRED = "ACTOR_STATUS_EXPIRED"
    ACTOR_STATUS_STALE = "ACTOR_STATUS_STALE"
    ASSURANCE_POLICY_UNSUPPORTED = "ASSURANCE_POLICY_UNSUPPORTED"
    WORKSPACE_SCOPE_MISMATCH = "WORKSPACE_SCOPE_MISMATCH"
    PORTFOLIO_SCOPE_MISMATCH = "PORTFOLIO_SCOPE_MISMATCH"
    WORKSPACE_DELETED = "WORKSPACE_DELETED"
    WORKSPACE_STATUS_UNKNOWN = "WORKSPACE_STATUS_UNKNOWN"
    PORTFOLIO_DELETED = "PORTFOLIO_DELETED"
    PORTFOLIO_STATUS_UNKNOWN = "PORTFOLIO_STATUS_UNKNOWN"
    PERMISSION_MISMATCH = "PERMISSION_MISMATCH"
    AUTHORITY_DENIED = "AUTHORITY_DENIED"
    GRANT_REVOKED = "GRANT_REVOKED"
    GRANT_EXPIRED = "GRANT_EXPIRED"
    GRANT_STATUS_UNKNOWN = "GRANT_STATUS_UNKNOWN"
    AUTHORITY_CHECK_NOT_YET_VALID = "AUTHORITY_CHECK_NOT_YET_VALID"
    AUTHORITY_CHECK_EXPIRED = "AUTHORITY_CHECK_EXPIRED"
    AUTHORITY_CHECK_STALE = "AUTHORITY_CHECK_STALE"
    WORKSPACE_INHERITANCE_PROHIBITED = "WORKSPACE_INHERITANCE_PROHIBITED"


@dataclass(frozen=True)
class ActorRef:
    contract_version: str
    actor_type: ActorType
    actor_id: str
    authority_namespace: str
    identity_provider_ref: str

    def __post_init__(self) -> None:
        _require_text(self.contract_version, "contract_version")
        _require_enum(self.actor_type, ActorType, "actor_type")
        _require_text(self.actor_id, "actor_id")
        _require_text(self.authority_namespace, "authority_namespace")
        _require_text(self.identity_provider_ref, "identity_provider_ref")


@dataclass(frozen=True)
class AuthenticationEventRef:
    contract_version: str
    authentication_event_id: str
    actor_ref: ActorRef
    provider_ref: str
    authenticated_at: datetime
    valid_until: datetime
    assurance_class: AuthenticationAssuranceClass
    credential_status_version: str
    credential_binding: CredentialBinding
    subject_mode: AuthenticationSubjectMode

    def __post_init__(self) -> None:
        _require_text(self.contract_version, "contract_version")
        _require_text(self.authentication_event_id, "authentication_event_id")
        if not isinstance(self.actor_ref, ActorRef):
            raise ValueError("actor_ref must be an ActorRef")
        _require_text(self.provider_ref, "provider_ref")
        _require_utc(self.authenticated_at, "authenticated_at")
        _require_utc(self.valid_until, "valid_until")
        if self.valid_until <= self.authenticated_at:
            raise ValueError("valid_until must be after authenticated_at")
        _require_enum(self.assurance_class, AuthenticationAssuranceClass, "assurance_class")
        _require_text(self.credential_status_version, "credential_status_version")
        _require_enum(self.credential_binding, CredentialBinding, "credential_binding")
        _require_enum(self.subject_mode, AuthenticationSubjectMode, "subject_mode")


@dataclass(frozen=True)
class ActorStatusFact:
    contract_version: str
    status_fact_id: str
    actor_ref: ActorRef
    authentication_event_id: str
    actor_status: ActorLifecycleStatus
    credential_status: CredentialStatus
    credential_status_version: str
    session_status: SessionStatus
    checked_at: datetime
    valid_until: datetime

    def __post_init__(self) -> None:
        _require_text(self.contract_version, "contract_version")
        _require_text(self.status_fact_id, "status_fact_id")
        if not isinstance(self.actor_ref, ActorRef):
            raise ValueError("actor_ref must be an ActorRef")
        _require_text(self.authentication_event_id, "authentication_event_id")
        _require_enum(self.actor_status, ActorLifecycleStatus, "actor_status")
        _require_enum(self.credential_status, CredentialStatus, "credential_status")
        _require_text(self.credential_status_version, "credential_status_version")
        _require_enum(self.session_status, SessionStatus, "session_status")
        _require_utc(self.checked_at, "checked_at")
        _require_utc(self.valid_until, "valid_until")
        if self.valid_until <= self.checked_at:
            raise ValueError("valid_until must be after checked_at")


@dataclass(frozen=True)
class AuthorizationScope:
    contract_version: str
    authority_namespace: str
    workspace_id: int
    portfolio_id: int

    def __post_init__(self) -> None:
        _require_text(self.contract_version, "contract_version")
        _require_text(self.authority_namespace, "authority_namespace")
        _require_positive_int(self.workspace_id, "workspace_id")
        _require_positive_int(self.portfolio_id, "portfolio_id")


@dataclass(frozen=True)
class GrantSourceRef:
    contract_version: str
    grant_source_id: str
    grant_kind: GrantKind
    authority_namespace: str

    def __post_init__(self) -> None:
        _require_text(self.contract_version, "contract_version")
        _require_text(self.grant_source_id, "grant_source_id")
        _require_enum(self.grant_kind, GrantKind, "grant_kind")
        _require_text(self.authority_namespace, "authority_namespace")


@dataclass(frozen=True)
class ActorAuthorityFact:
    contract_version: str
    authority_fact_id: str
    actor_ref: ActorRef
    authentication_event_id: str
    scope: AuthorizationScope
    permission: Permission
    authorization_policy_version: str
    grant_source: GrantSourceRef
    checked_at: datetime
    valid_until: datetime
    decision: AuthorityDecision
    grant_status: GrantStatus
    workspace_status: ResourceStatus
    portfolio_status: ResourceStatus

    def __post_init__(self) -> None:
        _require_text(self.contract_version, "contract_version")
        _require_text(self.authority_fact_id, "authority_fact_id")
        if not isinstance(self.actor_ref, ActorRef):
            raise ValueError("actor_ref must be an ActorRef")
        _require_text(self.authentication_event_id, "authentication_event_id")
        if not isinstance(self.scope, AuthorizationScope):
            raise ValueError("scope must be an AuthorizationScope")
        _require_enum(self.permission, Permission, "permission")
        _require_text(self.authorization_policy_version, "authorization_policy_version")
        if not isinstance(self.grant_source, GrantSourceRef):
            raise ValueError("grant_source must be a GrantSourceRef")
        _require_utc(self.checked_at, "checked_at")
        _require_utc(self.valid_until, "valid_until")
        if self.valid_until <= self.checked_at:
            raise ValueError("valid_until must be after checked_at")
        _require_enum(self.decision, AuthorityDecision, "decision")
        _require_enum(self.grant_status, GrantStatus, "grant_status")
        _require_enum(self.workspace_status, ResourceStatus, "workspace_status")
        _require_enum(self.portfolio_status, ResourceStatus, "portfolio_status")


@dataclass(frozen=True)
class IdentityValidationPolicy:
    contract_version: str
    policy_version: str
    supported_identity_contract_versions: frozenset[str]
    supported_authorization_policy_versions: frozenset[str]
    allowed_assurance_classes: frozenset[AuthenticationAssuranceClass]
    max_authentication_age: timedelta
    max_actor_status_age: timedelta
    max_authority_check_age: timedelta
    allow_workspace_inherited_portfolio_grants: bool = False

    def __post_init__(self) -> None:
        _require_text(self.contract_version, "contract_version")
        _require_text(self.policy_version, "policy_version")
        _require_text_frozenset(
            self.supported_identity_contract_versions,
            "supported_identity_contract_versions",
        )
        _require_text_frozenset(
            self.supported_authorization_policy_versions,
            "supported_authorization_policy_versions",
        )
        if not isinstance(self.allowed_assurance_classes, frozenset) or not self.allowed_assurance_classes:
            raise ValueError("allowed_assurance_classes must be a non-empty frozenset")
        if any(not isinstance(item, AuthenticationAssuranceClass) for item in self.allowed_assurance_classes):
            raise ValueError("allowed_assurance_classes contains an invalid value")
        for field_name in (
            "max_authentication_age",
            "max_actor_status_age",
            "max_authority_check_age",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, timedelta) or value <= timedelta(0):
                raise ValueError(f"{field_name} must be a positive timedelta")
            if not value.total_seconds().is_integer():
                raise ValueError(f"{field_name} must use whole seconds")


@dataclass(frozen=True)
class IdentityValidationInput:
    actor_ref: ActorRef
    authentication_event: AuthenticationEventRef | None
    actor_status_fact: ActorStatusFact | None
    authority_fact: ActorAuthorityFact | None
    required_scope: AuthorizationScope
    required_permission: Permission
    validation_time: datetime
    policy: IdentityValidationPolicy

    def __post_init__(self) -> None:
        if not isinstance(self.actor_ref, ActorRef):
            raise ValueError("actor_ref must be an ActorRef")
        if self.authentication_event is not None and not isinstance(
            self.authentication_event, AuthenticationEventRef
        ):
            raise ValueError("authentication_event must be an AuthenticationEventRef or None")
        if self.actor_status_fact is not None and not isinstance(self.actor_status_fact, ActorStatusFact):
            raise ValueError("actor_status_fact must be an ActorStatusFact or None")
        if self.authority_fact is not None and not isinstance(self.authority_fact, ActorAuthorityFact):
            raise ValueError("authority_fact must be an ActorAuthorityFact or None")
        if not isinstance(self.required_scope, AuthorizationScope):
            raise ValueError("required_scope must be an AuthorizationScope")
        _require_enum(self.required_permission, Permission, "required_permission")
        _require_utc(self.validation_time, "validation_time")
        if not isinstance(self.policy, IdentityValidationPolicy):
            raise ValueError("policy must be an IdentityValidationPolicy")


@dataclass(frozen=True)
class IdentityValidationResult:
    outcome: IdentityValidationOutcome
    refusal_code: IdentityRefusalCode | None
    refusal_detail: str | None
    validated_actor: ActorRef | None
    validated_authentication_event: AuthenticationEventRef | None
    validated_actor_status_fact: ActorStatusFact | None
    validated_authority_fact: ActorAuthorityFact | None
    validated_scope: AuthorizationScope | None
    validated_permission: Permission | None
    validation_time: datetime
    valid_from: datetime | None
    valid_until: datetime | None
    validation_policy_contract_version: str
    validation_policy_version: str
    actor_ref_hash: str | None
    authentication_event_hash: str | None
    authority_fact_hash: str | None
    validation_binding_hash: str | None

    def __post_init__(self) -> None:
        _require_enum(self.outcome, IdentityValidationOutcome, "outcome")
        _require_utc(self.validation_time, "validation_time")
        _require_text(
            self.validation_policy_contract_version,
            "validation_policy_contract_version",
        )
        _require_text(self.validation_policy_version, "validation_policy_version")
        validated_values = (
            self.validated_actor,
            self.validated_authentication_event,
            self.validated_actor_status_fact,
            self.validated_authority_fact,
            self.validated_scope,
            self.validated_permission,
            self.valid_from,
            self.valid_until,
            self.actor_ref_hash,
            self.authentication_event_hash,
            self.authority_fact_hash,
            self.validation_binding_hash,
        )
        if self.outcome == IdentityValidationOutcome.REFUSED:
            if not isinstance(self.refusal_code, IdentityRefusalCode) or not self.refusal_detail:
                raise ValueError("a refused result requires one refusal code and detail")
            if any(value is not None for value in validated_values):
                raise ValueError("a refused result cannot expose a validated binding")
            return
        if self.refusal_code is not None or self.refusal_detail is not None:
            raise ValueError("an accepted result cannot carry a refusal")
        if any(value is None for value in validated_values):
            raise ValueError("an accepted result requires a complete validated binding")
        _require_utc(self.valid_from, "valid_from")  # type: ignore[arg-type]
        _require_utc(self.valid_until, "valid_until")  # type: ignore[arg-type]
        if self.valid_until <= self.valid_from:  # type: ignore[operator]
            raise ValueError("accepted result valid_until must be after valid_from")
        for field_name in (
            "actor_ref_hash",
            "authentication_event_hash",
            "authority_fact_hash",
            "validation_binding_hash",
        ):
            _require_hash(getattr(self, field_name), field_name)

    @property
    def accepted(self) -> bool:
        return self.outcome == IdentityValidationOutcome.ACCEPTED


def canonicalize_actor_ref(actor_ref: ActorRef) -> str:
    return _canonical_json(_actor_ref_dict(actor_ref))


def compute_actor_ref_hash(actor_ref: ActorRef) -> str:
    return _domain_hash("actor-ref", actor_ref.contract_version, canonicalize_actor_ref(actor_ref))


def canonicalize_authentication_event_ref(authentication_event: AuthenticationEventRef) -> str:
    return _canonical_json(_authentication_event_dict(authentication_event))


def compute_authentication_event_ref_hash(authentication_event: AuthenticationEventRef) -> str:
    return _domain_hash(
        "authentication-event",
        authentication_event.contract_version,
        canonicalize_authentication_event_ref(authentication_event),
    )


def canonicalize_actor_authority_fact(authority_fact: ActorAuthorityFact) -> str:
    return _canonical_json(_authority_fact_dict(authority_fact))


def compute_actor_authority_fact_hash(authority_fact: ActorAuthorityFact) -> str:
    return _domain_hash(
        "actor-authority-fact",
        authority_fact.contract_version,
        canonicalize_actor_authority_fact(authority_fact),
    )


def canonicalize_identity_validation_binding(
    validation_input: IdentityValidationInput,
    *,
    valid_from: datetime,
    valid_until: datetime,
) -> str:
    """Serialize the exact facts supporting one successful validation.

    The function is intentionally a serializer, not a second validator.  The
    public validator calls it only after every fail-closed check succeeds.
    """

    _require_utc(valid_from, "valid_from")
    _require_utc(valid_until, "valid_until")
    if valid_until <= valid_from:
        raise ValueError("valid_until must be after valid_from")
    if (
        validation_input.authentication_event is None
        or validation_input.actor_status_fact is None
        or validation_input.authority_fact is None
    ):
        raise ValueError("successful binding requires authentication, status, and authority facts")
    payload = {
        "binding_contract_version": IDENTITY_CONTRACT_VERSION,
        "actor_ref": _actor_ref_dict(validation_input.actor_ref),
        "authentication_event": _authentication_event_dict(validation_input.authentication_event),
        "actor_status_fact": _actor_status_fact_dict(validation_input.actor_status_fact),
        "authority_fact": _authority_fact_dict(validation_input.authority_fact),
        "required_scope": _scope_dict(validation_input.required_scope),
        "required_permission": validation_input.required_permission.value,
        "validation_time": _canon_datetime(validation_input.validation_time),
        "valid_from": _canon_datetime(valid_from),
        "valid_until": _canon_datetime(valid_until),
        "validation_policy": _policy_dict(validation_input.policy),
    }
    return _canonical_json(payload)


def compute_identity_validation_binding_hash(
    validation_input: IdentityValidationInput,
    *,
    valid_from: datetime,
    valid_until: datetime,
) -> str:
    canonical = canonicalize_identity_validation_binding(
        validation_input,
        valid_from=valid_from,
        valid_until=valid_until,
    )
    return _domain_hash("validation-binding", IDENTITY_CONTRACT_VERSION, canonical)


def validate_human_authority(
    actor_ref: ActorRef,
    authentication_event: AuthenticationEventRef | None,
    actor_status_fact: ActorStatusFact | None,
    authority_fact: ActorAuthorityFact | None,
    required_scope: AuthorizationScope,
    required_permission: Permission,
    validation_time: datetime,
    policy: IdentityValidationPolicy,
) -> IdentityValidationResult:
    """Validate one caller-supplied, point-in-time human authority bundle."""

    validation_input = IdentityValidationInput(
        actor_ref=actor_ref,
        authentication_event=authentication_event,
        actor_status_fact=actor_status_fact,
        authority_fact=authority_fact,
        required_scope=required_scope,
        required_permission=required_permission,
        validation_time=validation_time,
        policy=policy,
    )

    # 1. Contract and policy versions fail before semantic interpretation.
    if policy.contract_version != IDENTITY_CONTRACT_VERSION:
        return _refuse(validation_input, IdentityRefusalCode.UNSUPPORTED_CONTRACT_VERSION, "unsupported validation-policy contract version")
    if policy.policy_version != IDENTITY_VALIDATION_POLICY_VERSION:
        return _refuse(validation_input, IdentityRefusalCode.UNSUPPORTED_POLICY_VERSION, "unsupported identity validation policy version")
    versioned = [actor_ref.contract_version, required_scope.contract_version]
    if authentication_event is not None:
        versioned.extend((authentication_event.contract_version, authentication_event.actor_ref.contract_version))
    if actor_status_fact is not None:
        versioned.extend((actor_status_fact.contract_version, actor_status_fact.actor_ref.contract_version))
    if authority_fact is not None:
        versioned.extend(
            (
                authority_fact.contract_version,
                authority_fact.actor_ref.contract_version,
                authority_fact.scope.contract_version,
                authority_fact.grant_source.contract_version,
            )
        )
    if any(version not in policy.supported_identity_contract_versions for version in versioned):
        return _refuse(validation_input, IdentityRefusalCode.UNSUPPORTED_CONTRACT_VERSION, "one or more identity facts use an unsupported contract version")
    if (
        authority_fact is not None
        and authority_fact.authorization_policy_version
        not in policy.supported_authorization_policy_versions
    ):
        return _refuse(validation_input, IdentityRefusalCode.UNSUPPORTED_AUTHORIZATION_POLICY, "authority fact uses an unsupported authorization policy")

    # 2. Namespace comparison is exact; default/current-owner inference is forbidden.
    namespaces = [actor_ref.authority_namespace, required_scope.authority_namespace]
    if authentication_event is not None:
        namespaces.append(authentication_event.actor_ref.authority_namespace)
    if actor_status_fact is not None:
        namespaces.append(actor_status_fact.actor_ref.authority_namespace)
    if authority_fact is not None:
        namespaces.extend(
            (
                authority_fact.actor_ref.authority_namespace,
                authority_fact.scope.authority_namespace,
                authority_fact.grant_source.authority_namespace,
            )
        )
    if any(namespace != actor_ref.authority_namespace for namespace in namespaces):
        return _refuse(validation_input, IdentityRefusalCode.AUTHORITY_NAMESPACE_MISMATCH, "authority namespaces do not match exactly")

    # 3. This entry point is intentionally human-only.
    if actor_ref.actor_type != ActorType.HUMAN:
        return _refuse(validation_input, IdentityRefusalCode.SYSTEM_ACTOR_CANNOT_REVIEW, "only a HUMAN actor may review an execution intent")

    # 4-5. Authentication must be direct and individually bound.
    if authentication_event is None:
        return _refuse(validation_input, IdentityRefusalCode.AUTHENTICATION_EVENT_MISSING, "authentication event is required")
    if authentication_event.credential_binding == CredentialBinding.SHARED:
        return _refuse(validation_input, IdentityRefusalCode.SHARED_CREDENTIAL_PROHIBITED, "shared credentials cannot establish human authority")
    if authentication_event.subject_mode == AuthenticationSubjectMode.DELEGATED:
        return _refuse(validation_input, IdentityRefusalCode.DELEGATION_UNSUPPORTED, "delegation is unsupported in the MVP")
    if authentication_event.subject_mode == AuthenticationSubjectMode.IMPERSONATED:
        return _refuse(validation_input, IdentityRefusalCode.IMPERSONATION_UNSUPPORTED, "impersonation is unsupported in the MVP")
    if authentication_event.actor_ref != actor_ref:
        return _refuse(validation_input, IdentityRefusalCode.AUTHENTICATION_ACTOR_MISMATCH, "authentication event actor does not match")
    if authentication_event.provider_ref != actor_ref.identity_provider_ref:
        return _refuse(validation_input, IdentityRefusalCode.AUTHENTICATION_PROVIDER_MISMATCH, "authentication provider does not match actor identity provider")
    if actor_status_fact is None:
        return _refuse(validation_input, IdentityRefusalCode.ACTOR_STATUS_FACT_MISSING, "current actor/session status fact is required")
    if actor_status_fact.actor_ref != actor_ref or actor_status_fact.authentication_event_id != authentication_event.authentication_event_id:
        return _refuse(validation_input, IdentityRefusalCode.ACTOR_STATUS_MISMATCH, "actor status fact does not match actor/authentication event")
    if authority_fact is None:
        return _refuse(validation_input, IdentityRefusalCode.AUTHORITY_FACT_MISSING, "scoped authority fact is required")
    if authority_fact.actor_ref != actor_ref:
        return _refuse(validation_input, IdentityRefusalCode.AUTHORITY_ACTOR_MISMATCH, "authority fact actor does not match")
    if authority_fact.authentication_event_id != authentication_event.authentication_event_id:
        return _refuse(validation_input, IdentityRefusalCode.AUTHORITY_AUTHENTICATION_EVENT_MISMATCH, "authority fact authentication event does not match")

    # 6. Current actor, credential, and session state fail closed.
    if actor_status_fact.actor_status == ActorLifecycleStatus.DISABLED:
        return _refuse(validation_input, IdentityRefusalCode.ACTOR_DISABLED, "actor is disabled")
    if actor_status_fact.actor_status == ActorLifecycleStatus.DELETED:
        return _refuse(validation_input, IdentityRefusalCode.ACTOR_DELETED, "actor is deleted; its stable id remains audit-only")
    if actor_status_fact.actor_status == ActorLifecycleStatus.UNKNOWN:
        return _refuse(validation_input, IdentityRefusalCode.ACTOR_STATUS_UNKNOWN, "actor status is unknown")
    if actor_status_fact.credential_status == CredentialStatus.REVOKED:
        return _refuse(validation_input, IdentityRefusalCode.CREDENTIAL_REVOKED, "credential is revoked")
    if actor_status_fact.credential_status == CredentialStatus.UNKNOWN:
        return _refuse(validation_input, IdentityRefusalCode.CREDENTIAL_STATUS_UNKNOWN, "credential status is unknown")
    if actor_status_fact.credential_status_version != authentication_event.credential_status_version:
        return _refuse(validation_input, IdentityRefusalCode.CREDENTIAL_STATUS_VERSION_MISMATCH, "credential status version does not match authentication event")
    if actor_status_fact.session_status == SessionStatus.REVOKED:
        return _refuse(validation_input, IdentityRefusalCode.SESSION_REVOKED, "authentication session is revoked")
    if actor_status_fact.session_status == SessionStatus.UNKNOWN:
        return _refuse(validation_input, IdentityRefusalCode.SESSION_STATUS_UNKNOWN, "authentication session status is unknown")

    # 7. Event and current-status validity use only the caller's UTC validation time.
    if authentication_event.authenticated_at > validation_time:
        return _refuse(validation_input, IdentityRefusalCode.AUTHENTICATION_NOT_YET_VALID, "authentication event occurs after validation time")
    if validation_time >= authentication_event.valid_until:
        return _refuse(validation_input, IdentityRefusalCode.AUTHENTICATION_EXPIRED, "authentication event is expired")
    if validation_time - authentication_event.authenticated_at > policy.max_authentication_age:
        return _refuse(validation_input, IdentityRefusalCode.AUTHENTICATION_STALE, "authentication event exceeds maximum age")
    if actor_status_fact.checked_at > validation_time:
        return _refuse(validation_input, IdentityRefusalCode.ACTOR_STATUS_NOT_YET_VALID, "actor status was checked after validation time")
    if validation_time >= actor_status_fact.valid_until:
        return _refuse(validation_input, IdentityRefusalCode.ACTOR_STATUS_EXPIRED, "actor status fact is expired")
    if validation_time - actor_status_fact.checked_at > policy.max_actor_status_age:
        return _refuse(validation_input, IdentityRefusalCode.ACTOR_STATUS_STALE, "actor status fact exceeds maximum age")
    if authentication_event.assurance_class not in policy.allowed_assurance_classes:
        return _refuse(validation_input, IdentityRefusalCode.ASSURANCE_POLICY_UNSUPPORTED, "authentication assurance is not permitted by policy")

    # 8. Scope equality and resource existence are exact.
    if authority_fact.scope.workspace_id != required_scope.workspace_id:
        return _refuse(validation_input, IdentityRefusalCode.WORKSPACE_SCOPE_MISMATCH, "workspace scope does not match")
    if authority_fact.scope.portfolio_id != required_scope.portfolio_id:
        return _refuse(validation_input, IdentityRefusalCode.PORTFOLIO_SCOPE_MISMATCH, "portfolio scope does not match")
    if authority_fact.workspace_status == ResourceStatus.DELETED:
        return _refuse(validation_input, IdentityRefusalCode.WORKSPACE_DELETED, "workspace is deleted")
    if authority_fact.workspace_status == ResourceStatus.UNKNOWN:
        return _refuse(validation_input, IdentityRefusalCode.WORKSPACE_STATUS_UNKNOWN, "workspace status is unknown")
    if authority_fact.portfolio_status == ResourceStatus.DELETED:
        return _refuse(validation_input, IdentityRefusalCode.PORTFOLIO_DELETED, "portfolio is deleted")
    if authority_fact.portfolio_status == ResourceStatus.UNKNOWN:
        return _refuse(validation_input, IdentityRefusalCode.PORTFOLIO_STATUS_UNKNOWN, "portfolio status is unknown")

    # 9-11. Permission, grant disposition, freshness, and inheritance policy.
    if authority_fact.permission != required_permission:
        return _refuse(validation_input, IdentityRefusalCode.PERMISSION_MISMATCH, "authority permission does not match")
    if authority_fact.decision == AuthorityDecision.DENY:
        return _refuse(validation_input, IdentityRefusalCode.AUTHORITY_DENIED, "authorization decision is DENY")
    if authority_fact.grant_status == GrantStatus.REVOKED:
        return _refuse(validation_input, IdentityRefusalCode.GRANT_REVOKED, "grant is revoked")
    if authority_fact.grant_status == GrantStatus.EXPIRED:
        return _refuse(validation_input, IdentityRefusalCode.GRANT_EXPIRED, "grant is expired")
    if authority_fact.grant_status == GrantStatus.UNKNOWN:
        return _refuse(validation_input, IdentityRefusalCode.GRANT_STATUS_UNKNOWN, "grant status is unknown")
    if authority_fact.checked_at > validation_time:
        return _refuse(validation_input, IdentityRefusalCode.AUTHORITY_CHECK_NOT_YET_VALID, "authority check occurs after validation time")
    if validation_time >= authority_fact.valid_until:
        return _refuse(validation_input, IdentityRefusalCode.AUTHORITY_CHECK_EXPIRED, "authority fact is expired")
    if validation_time - authority_fact.checked_at > policy.max_authority_check_age:
        return _refuse(validation_input, IdentityRefusalCode.AUTHORITY_CHECK_STALE, "authority check exceeds maximum age")
    if (
        authority_fact.grant_source.grant_kind == GrantKind.WORKSPACE_INHERITED
        and not policy.allow_workspace_inherited_portfolio_grants
    ):
        return _refuse(validation_input, IdentityRefusalCode.WORKSPACE_INHERITANCE_PROHIBITED, "workspace inheritance is not explicitly permitted")

    valid_from = max(
        authentication_event.authenticated_at,
        actor_status_fact.checked_at,
        authority_fact.checked_at,
    )
    valid_until = min(
        authentication_event.valid_until,
        actor_status_fact.valid_until,
        authority_fact.valid_until,
        authentication_event.authenticated_at + policy.max_authentication_age,
        actor_status_fact.checked_at + policy.max_actor_status_age,
        authority_fact.checked_at + policy.max_authority_check_age,
    )
    binding_hash = compute_identity_validation_binding_hash(
        validation_input,
        valid_from=valid_from,
        valid_until=valid_until,
    )
    return IdentityValidationResult(
        outcome=IdentityValidationOutcome.ACCEPTED,
        refusal_code=None,
        refusal_detail=None,
        validated_actor=actor_ref,
        validated_authentication_event=authentication_event,
        validated_actor_status_fact=actor_status_fact,
        validated_authority_fact=authority_fact,
        validated_scope=required_scope,
        validated_permission=required_permission,
        validation_time=validation_time,
        valid_from=valid_from,
        valid_until=valid_until,
        validation_policy_contract_version=policy.contract_version,
        validation_policy_version=policy.policy_version,
        actor_ref_hash=compute_actor_ref_hash(actor_ref),
        authentication_event_hash=compute_authentication_event_ref_hash(authentication_event),
        authority_fact_hash=compute_actor_authority_fact_hash(authority_fact),
        validation_binding_hash=binding_hash,
    )


def _refuse(
    validation_input: IdentityValidationInput,
    code: IdentityRefusalCode,
    detail: str,
) -> IdentityValidationResult:
    return IdentityValidationResult(
        outcome=IdentityValidationOutcome.REFUSED,
        refusal_code=code,
        refusal_detail=detail,
        validated_actor=None,
        validated_authentication_event=None,
        validated_actor_status_fact=None,
        validated_authority_fact=None,
        validated_scope=None,
        validated_permission=None,
        validation_time=validation_input.validation_time,
        valid_from=None,
        valid_until=None,
        validation_policy_contract_version=validation_input.policy.contract_version,
        validation_policy_version=validation_input.policy.policy_version,
        actor_ref_hash=None,
        authentication_event_hash=None,
        authority_fact_hash=None,
        validation_binding_hash=None,
    )


def _actor_ref_dict(actor_ref: ActorRef) -> dict:
    return {
        "contract_version": actor_ref.contract_version,
        "actor_type": actor_ref.actor_type.value,
        "actor_id": actor_ref.actor_id,
        "authority_namespace": actor_ref.authority_namespace,
        "identity_provider_ref": actor_ref.identity_provider_ref,
    }


def _authentication_event_dict(authentication_event: AuthenticationEventRef) -> dict:
    return {
        "contract_version": authentication_event.contract_version,
        "authentication_event_id": authentication_event.authentication_event_id,
        "actor_ref": _actor_ref_dict(authentication_event.actor_ref),
        "provider_ref": authentication_event.provider_ref,
        "authenticated_at": _canon_datetime(authentication_event.authenticated_at),
        "valid_until": _canon_datetime(authentication_event.valid_until),
        "assurance_class": authentication_event.assurance_class.value,
        "credential_status_version": authentication_event.credential_status_version,
        "credential_binding": authentication_event.credential_binding.value,
        "subject_mode": authentication_event.subject_mode.value,
    }


def _actor_status_fact_dict(status_fact: ActorStatusFact) -> dict:
    return {
        "contract_version": status_fact.contract_version,
        "status_fact_id": status_fact.status_fact_id,
        "actor_ref": _actor_ref_dict(status_fact.actor_ref),
        "authentication_event_id": status_fact.authentication_event_id,
        "actor_status": status_fact.actor_status.value,
        "credential_status": status_fact.credential_status.value,
        "credential_status_version": status_fact.credential_status_version,
        "session_status": status_fact.session_status.value,
        "checked_at": _canon_datetime(status_fact.checked_at),
        "valid_until": _canon_datetime(status_fact.valid_until),
    }


def _scope_dict(scope: AuthorizationScope) -> dict:
    return {
        "contract_version": scope.contract_version,
        "authority_namespace": scope.authority_namespace,
        "workspace_id": scope.workspace_id,
        "portfolio_id": scope.portfolio_id,
    }


def _grant_source_dict(grant_source: GrantSourceRef) -> dict:
    return {
        "contract_version": grant_source.contract_version,
        "grant_source_id": grant_source.grant_source_id,
        "grant_kind": grant_source.grant_kind.value,
        "authority_namespace": grant_source.authority_namespace,
    }


def _authority_fact_dict(authority_fact: ActorAuthorityFact) -> dict:
    return {
        "contract_version": authority_fact.contract_version,
        "authority_fact_id": authority_fact.authority_fact_id,
        "actor_ref": _actor_ref_dict(authority_fact.actor_ref),
        "authentication_event_id": authority_fact.authentication_event_id,
        "scope": _scope_dict(authority_fact.scope),
        "permission": authority_fact.permission.value,
        "authorization_policy_version": authority_fact.authorization_policy_version,
        "grant_source": _grant_source_dict(authority_fact.grant_source),
        "checked_at": _canon_datetime(authority_fact.checked_at),
        "valid_until": _canon_datetime(authority_fact.valid_until),
        "decision": authority_fact.decision.value,
        "grant_status": authority_fact.grant_status.value,
        "workspace_status": authority_fact.workspace_status.value,
        "portfolio_status": authority_fact.portfolio_status.value,
    }


def _policy_dict(policy: IdentityValidationPolicy) -> dict:
    return {
        "contract_version": policy.contract_version,
        "policy_version": policy.policy_version,
        "supported_identity_contract_versions": sorted(policy.supported_identity_contract_versions),
        "supported_authorization_policy_versions": sorted(
            policy.supported_authorization_policy_versions
        ),
        "allowed_assurance_classes": sorted(item.value for item in policy.allowed_assurance_classes),
        "max_authentication_age_seconds": _timedelta_seconds(policy.max_authentication_age),
        "max_actor_status_age_seconds": _timedelta_seconds(policy.max_actor_status_age),
        "max_authority_check_age_seconds": _timedelta_seconds(policy.max_authority_check_age),
        "allow_workspace_inherited_portfolio_grants": policy.allow_workspace_inherited_portfolio_grants,
    }


def _canonical_json(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _domain_hash(kind: str, version: str, canonical: str) -> str:
    raw = f"M33.8:{kind}:{version}\n{canonical}".encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _canon_datetime(value: datetime) -> str:
    _require_utc(value, "datetime")
    return value.astimezone(timezone.utc).isoformat()


def _timedelta_seconds(value: timedelta) -> str:
    total = value.total_seconds()
    if not total.is_integer():
        raise ValueError("policy durations must use whole seconds")
    return str(int(total))


def _require_utc(value: datetime, field_name: str) -> None:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
        or value.utcoffset() != timedelta(0)
    ):
        raise ValueError(f"{field_name} must be a timezone-aware UTC datetime")


def _require_text(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")


def _require_positive_int(value: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{field_name} must be a positive integer")


def _require_hash(value: str | None, field_name: str) -> None:
    if not isinstance(value, str) or _HASH_RE.fullmatch(value) is None:
        raise ValueError(f"{field_name} must use lowercase sha256:<64-hex> syntax")


def _require_enum(value: Enum, enum_type: type[Enum], field_name: str) -> None:
    if not isinstance(value, enum_type):
        raise ValueError(f"{field_name} must be a {enum_type.__name__} value")


def _require_text_frozenset(value: frozenset[str], field_name: str) -> None:
    if not isinstance(value, frozenset) or not value:
        raise ValueError(f"{field_name} must be a non-empty frozenset")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{field_name} must contain non-empty strings")
