"""M33.8 pure stable-identity and scoped-authority contract tests."""
from __future__ import annotations

import re
from dataclasses import FrozenInstanceError, fields, replace
from datetime import datetime, timedelta, timezone

import pytest

from services.execution_intent_contracts import ActorType
from services.execution_intent_identity import (
    IDENTITY_CONTRACT_VERSION,
    IDENTITY_VALIDATION_POLICY_VERSION,
    ActorAuthorityFact,
    ActorLifecycleStatus,
    ActorRef,
    ActorStatusFact,
    AuthenticationAssuranceClass,
    AuthenticationEventRef,
    AuthenticationSubjectMode,
    AuthorityDecision,
    AuthorizationScope,
    CredentialBinding,
    CredentialStatus,
    GrantKind,
    GrantSourceRef,
    GrantStatus,
    IdentityRefusalCode,
    IdentityValidationInput,
    IdentityValidationOutcome,
    IdentityValidationPolicy,
    Permission,
    ResourceStatus,
    SessionStatus,
    canonicalize_actor_authority_fact,
    canonicalize_actor_ref,
    canonicalize_authentication_event_ref,
    canonicalize_identity_validation_binding,
    compute_actor_authority_fact_hash,
    compute_actor_ref_hash,
    compute_authentication_event_ref_hash,
    compute_identity_validation_binding_hash,
    validate_human_authority,
)


_T0 = datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc)
_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


def _actor(**overrides) -> ActorRef:
    values = dict(
        contract_version=IDENTITY_CONTRACT_VERSION,
        actor_type=ActorType.HUMAN,
        actor_id="actor:person-42",
        authority_namespace="deployment:test",
        identity_provider_ref="provider:workforce-v1",
    )
    values.update(overrides)
    return ActorRef(**values)


def _auth(actor: ActorRef | None = None, **overrides) -> AuthenticationEventRef:
    values = dict(
        contract_version=IDENTITY_CONTRACT_VERSION,
        authentication_event_id="auth-event:100",
        actor_ref=actor or _actor(),
        provider_ref="provider:workforce-v1",
        authenticated_at=_T0 - timedelta(minutes=20),
        valid_until=_T0 + timedelta(minutes=20),
        assurance_class=AuthenticationAssuranceClass.MULTI_FACTOR,
        credential_status_version="credential-state:7",
        credential_binding=CredentialBinding.INDIVIDUAL,
        subject_mode=AuthenticationSubjectMode.DIRECT,
    )
    values.update(overrides)
    return AuthenticationEventRef(**values)


def _status(
    actor: ActorRef | None = None,
    authentication_event_id: str = "auth-event:100",
    **overrides,
) -> ActorStatusFact:
    values = dict(
        contract_version=IDENTITY_CONTRACT_VERSION,
        status_fact_id="actor-status:100",
        actor_ref=actor or _actor(),
        authentication_event_id=authentication_event_id,
        actor_status=ActorLifecycleStatus.ACTIVE,
        credential_status=CredentialStatus.ACTIVE,
        credential_status_version="credential-state:7",
        session_status=SessionStatus.ACTIVE,
        checked_at=_T0 - timedelta(minutes=1),
        valid_until=_T0 + timedelta(minutes=10),
    )
    values.update(overrides)
    return ActorStatusFact(**values)


def _scope(**overrides) -> AuthorizationScope:
    values = dict(
        contract_version=IDENTITY_CONTRACT_VERSION,
        authority_namespace="deployment:test",
        workspace_id=1,
        portfolio_id=7,
    )
    values.update(overrides)
    return AuthorizationScope(**values)


def _grant(**overrides) -> GrantSourceRef:
    values = dict(
        contract_version=IDENTITY_CONTRACT_VERSION,
        grant_source_id="grant:portfolio-reviewer",
        grant_kind=GrantKind.DIRECT_PORTFOLIO,
        authority_namespace="deployment:test",
    )
    values.update(overrides)
    return GrantSourceRef(**values)


def _authority(actor: ActorRef | None = None, **overrides) -> ActorAuthorityFact:
    values = dict(
        contract_version=IDENTITY_CONTRACT_VERSION,
        authority_fact_id="authority-fact:100",
        actor_ref=actor or _actor(),
        authentication_event_id="auth-event:100",
        scope=_scope(),
        permission=Permission.EXECUTION_INTENT_REVIEW,
        authorization_policy_version="workspace-rbac:1",
        grant_source=_grant(),
        checked_at=_T0 - timedelta(seconds=30),
        valid_until=_T0 + timedelta(minutes=5),
        decision=AuthorityDecision.ALLOW,
        grant_status=GrantStatus.ACTIVE,
        workspace_status=ResourceStatus.ACTIVE,
        portfolio_status=ResourceStatus.ACTIVE,
    )
    values.update(overrides)
    return ActorAuthorityFact(**values)


def _policy(**overrides) -> IdentityValidationPolicy:
    values = dict(
        contract_version=IDENTITY_CONTRACT_VERSION,
        policy_version=IDENTITY_VALIDATION_POLICY_VERSION,
        supported_identity_contract_versions=frozenset({IDENTITY_CONTRACT_VERSION}),
        supported_authorization_policy_versions=frozenset({"workspace-rbac:1"}),
        allowed_assurance_classes=frozenset({AuthenticationAssuranceClass.MULTI_FACTOR}),
        max_authentication_age=timedelta(hours=1),
        max_actor_status_age=timedelta(minutes=5),
        max_authority_check_age=timedelta(minutes=2),
        allow_workspace_inherited_portfolio_grants=False,
    )
    values.update(overrides)
    return IdentityValidationPolicy(**values)


def _bundle(**overrides) -> dict:
    actor = overrides.pop("actor_ref", _actor())
    auth = overrides.pop("authentication_event", _auth(actor))
    auth_id = auth.authentication_event_id if auth is not None else "auth-event:100"
    values = dict(
        actor_ref=actor,
        authentication_event=auth,
        actor_status_fact=_status(actor, auth_id),
        authority_fact=_authority(actor, authentication_event_id=auth_id),
        required_scope=_scope(),
        required_permission=Permission.EXECUTION_INTENT_REVIEW,
        validation_time=_T0,
        policy=_policy(),
    )
    values.update(overrides)
    return values


def _validate(**overrides):
    return validate_human_authority(**_bundle(**overrides))


class TestContractsAndSuccess:
    def test_valid_direct_human_authority(self):
        values = _bundle()
        result = validate_human_authority(**values)

        assert result.outcome == IdentityValidationOutcome.ACCEPTED
        assert result.accepted is True
        assert result.refusal_code is None
        assert result.validated_actor == values["actor_ref"]
        assert result.validated_authentication_event == values["authentication_event"]
        assert result.validated_actor_status_fact == values["actor_status_fact"]
        assert result.validated_authority_fact == values["authority_fact"]
        assert result.validated_scope == values["required_scope"]
        assert result.validated_permission == Permission.EXECUTION_INTENT_REVIEW
        assert result.valid_from == values["authority_fact"].checked_at
        assert result.valid_until == (
            values["authority_fact"].checked_at + values["policy"].max_authority_check_age
        )
        for digest in (
            result.actor_ref_hash,
            result.authentication_event_hash,
            result.authority_fact_hash,
            result.validation_binding_hash,
        ):
            assert digest is not None and _HASH_RE.fullmatch(digest)

    def test_direct_portfolio_grant_succeeds(self):
        assert _validate().accepted is True

    def test_explicit_workspace_inheritance_succeeds(self):
        fact = _authority(
            grant_source=_grant(grant_kind=GrantKind.WORKSPACE_INHERITED),
        )
        result = _validate(
            authority_fact=fact,
            policy=_policy(allow_workspace_inherited_portfolio_grants=True),
        )
        assert result.accepted is True

    def test_stable_actor_is_independent_of_mutable_display_attributes(self):
        actor = _actor()
        first_display = {"username": "old-name", "email": "old@example.test", "display_name": "Old"}
        second_display = {"username": "new-name", "email": "new@example.test", "display_name": "New"}
        assert first_display != second_display
        assert compute_actor_ref_hash(actor) == compute_actor_ref_hash(actor)
        assert set(item.name for item in fields(ActorRef)).isdisjoint(first_display)

    @pytest.mark.parametrize(
        "value",
        [
            _actor(),
            _auth(),
            _status(),
            _scope(),
            _grant(),
            _authority(),
            _policy(),
            IdentityValidationInput(**_bundle()),
            _validate(),
        ],
    )
    def test_contracts_are_frozen(self, value):
        with pytest.raises(FrozenInstanceError):
            value.contract_version = "changed"  # type: ignore[misc]

    def test_identical_inputs_produce_byte_equivalent_result(self):
        assert _validate() == _validate()

    def test_validator_has_zero_side_effects(self):
        values = _bundle()
        before = dict(values)
        first = validate_human_authority(**values)
        second = validate_human_authority(**values)
        assert values == before
        assert first == second


class TestRefusalMatrix:
    @pytest.mark.parametrize(
        "overrides, expected",
        [
            ({"policy": _policy(contract_version="2")}, IdentityRefusalCode.UNSUPPORTED_CONTRACT_VERSION),
            ({"policy": _policy(policy_version="2")}, IdentityRefusalCode.UNSUPPORTED_POLICY_VERSION),
            (
                {"authority_fact": _authority(authorization_policy_version="rbac:unknown")},
                IdentityRefusalCode.UNSUPPORTED_AUTHORIZATION_POLICY,
            ),
            (
                {"required_scope": _scope(authority_namespace="deployment:other")},
                IdentityRefusalCode.AUTHORITY_NAMESPACE_MISMATCH,
            ),
            (
                {"actor_ref": _actor(actor_type=ActorType.SYSTEM)},
                IdentityRefusalCode.SYSTEM_ACTOR_CANNOT_REVIEW,
            ),
            ({"authentication_event": None}, IdentityRefusalCode.AUTHENTICATION_EVENT_MISSING),
            (
                {"authentication_event": _auth(credential_binding=CredentialBinding.SHARED)},
                IdentityRefusalCode.SHARED_CREDENTIAL_PROHIBITED,
            ),
            (
                {"authentication_event": _auth(subject_mode=AuthenticationSubjectMode.DELEGATED)},
                IdentityRefusalCode.DELEGATION_UNSUPPORTED,
            ),
            (
                {"authentication_event": _auth(subject_mode=AuthenticationSubjectMode.IMPERSONATED)},
                IdentityRefusalCode.IMPERSONATION_UNSUPPORTED,
            ),
            (
                {"authentication_event": _auth(_actor(actor_id="actor:other"))},
                IdentityRefusalCode.AUTHENTICATION_ACTOR_MISMATCH,
            ),
            (
                {"authentication_event": _auth(provider_ref="provider:other")},
                IdentityRefusalCode.AUTHENTICATION_PROVIDER_MISMATCH,
            ),
            ({"actor_status_fact": None}, IdentityRefusalCode.ACTOR_STATUS_FACT_MISSING),
            (
                {"actor_status_fact": _status(_actor(actor_id="actor:other"))},
                IdentityRefusalCode.ACTOR_STATUS_MISMATCH,
            ),
            ({"authority_fact": None}, IdentityRefusalCode.AUTHORITY_FACT_MISSING),
            (
                {"authority_fact": _authority(_actor(actor_id="actor:other"))},
                IdentityRefusalCode.AUTHORITY_ACTOR_MISMATCH,
            ),
            (
                {"authority_fact": _authority(authentication_event_id="auth-event:other")},
                IdentityRefusalCode.AUTHORITY_AUTHENTICATION_EVENT_MISMATCH,
            ),
            (
                {"actor_status_fact": _status(actor_status=ActorLifecycleStatus.DISABLED)},
                IdentityRefusalCode.ACTOR_DISABLED,
            ),
            (
                {"actor_status_fact": _status(actor_status=ActorLifecycleStatus.DELETED)},
                IdentityRefusalCode.ACTOR_DELETED,
            ),
            (
                {"actor_status_fact": _status(actor_status=ActorLifecycleStatus.UNKNOWN)},
                IdentityRefusalCode.ACTOR_STATUS_UNKNOWN,
            ),
            (
                {"actor_status_fact": _status(credential_status=CredentialStatus.REVOKED)},
                IdentityRefusalCode.CREDENTIAL_REVOKED,
            ),
            (
                {"actor_status_fact": _status(credential_status=CredentialStatus.UNKNOWN)},
                IdentityRefusalCode.CREDENTIAL_STATUS_UNKNOWN,
            ),
            (
                {"actor_status_fact": _status(credential_status_version="credential-state:old")},
                IdentityRefusalCode.CREDENTIAL_STATUS_VERSION_MISMATCH,
            ),
            (
                {"actor_status_fact": _status(session_status=SessionStatus.REVOKED)},
                IdentityRefusalCode.SESSION_REVOKED,
            ),
            (
                {"actor_status_fact": _status(session_status=SessionStatus.UNKNOWN)},
                IdentityRefusalCode.SESSION_STATUS_UNKNOWN,
            ),
            (
                {
                    "authentication_event": _auth(
                        authenticated_at=_T0 + timedelta(minutes=1),
                        valid_until=_T0 + timedelta(minutes=20),
                    )
                },
                IdentityRefusalCode.AUTHENTICATION_NOT_YET_VALID,
            ),
            (
                {
                    "authentication_event": _auth(
                        authenticated_at=_T0 - timedelta(hours=1),
                        valid_until=_T0,
                    )
                },
                IdentityRefusalCode.AUTHENTICATION_EXPIRED,
            ),
            (
                {
                    "authentication_event": _auth(
                        authenticated_at=_T0 - timedelta(minutes=30),
                        valid_until=_T0 + timedelta(hours=1),
                    ),
                    "policy": _policy(max_authentication_age=timedelta(minutes=10)),
                },
                IdentityRefusalCode.AUTHENTICATION_STALE,
            ),
            (
                {"actor_status_fact": _status(checked_at=_T0 + timedelta(seconds=1), valid_until=_T0 + timedelta(minutes=5))},
                IdentityRefusalCode.ACTOR_STATUS_NOT_YET_VALID,
            ),
            (
                {"actor_status_fact": _status(checked_at=_T0 - timedelta(minutes=2), valid_until=_T0)},
                IdentityRefusalCode.ACTOR_STATUS_EXPIRED,
            ),
            (
                {
                    "actor_status_fact": _status(checked_at=_T0 - timedelta(minutes=10), valid_until=_T0 + timedelta(minutes=1)),
                    "policy": _policy(max_actor_status_age=timedelta(minutes=5)),
                },
                IdentityRefusalCode.ACTOR_STATUS_STALE,
            ),
            (
                {"authentication_event": _auth(assurance_class=AuthenticationAssuranceClass.PASSWORD)},
                IdentityRefusalCode.ASSURANCE_POLICY_UNSUPPORTED,
            ),
            (
                {"authority_fact": _authority(scope=_scope(workspace_id=2))},
                IdentityRefusalCode.WORKSPACE_SCOPE_MISMATCH,
            ),
            (
                {"authority_fact": _authority(scope=_scope(portfolio_id=8))},
                IdentityRefusalCode.PORTFOLIO_SCOPE_MISMATCH,
            ),
            (
                {"authority_fact": _authority(workspace_status=ResourceStatus.DELETED)},
                IdentityRefusalCode.WORKSPACE_DELETED,
            ),
            (
                {"authority_fact": _authority(workspace_status=ResourceStatus.UNKNOWN)},
                IdentityRefusalCode.WORKSPACE_STATUS_UNKNOWN,
            ),
            (
                {"authority_fact": _authority(portfolio_status=ResourceStatus.DELETED)},
                IdentityRefusalCode.PORTFOLIO_DELETED,
            ),
            (
                {"authority_fact": _authority(portfolio_status=ResourceStatus.UNKNOWN)},
                IdentityRefusalCode.PORTFOLIO_STATUS_UNKNOWN,
            ),
            (
                {"authority_fact": _authority(permission=Permission.EXECUTION_INTENT_PREPARE)},
                IdentityRefusalCode.PERMISSION_MISMATCH,
            ),
            (
                {"authority_fact": _authority(decision=AuthorityDecision.DENY)},
                IdentityRefusalCode.AUTHORITY_DENIED,
            ),
            (
                {"authority_fact": _authority(grant_status=GrantStatus.REVOKED)},
                IdentityRefusalCode.GRANT_REVOKED,
            ),
            (
                {"authority_fact": _authority(grant_status=GrantStatus.EXPIRED)},
                IdentityRefusalCode.GRANT_EXPIRED,
            ),
            (
                {"authority_fact": _authority(grant_status=GrantStatus.UNKNOWN)},
                IdentityRefusalCode.GRANT_STATUS_UNKNOWN,
            ),
            (
                {"authority_fact": _authority(checked_at=_T0 + timedelta(seconds=1), valid_until=_T0 + timedelta(minutes=5))},
                IdentityRefusalCode.AUTHORITY_CHECK_NOT_YET_VALID,
            ),
            (
                {"authority_fact": _authority(checked_at=_T0 - timedelta(minutes=2), valid_until=_T0)},
                IdentityRefusalCode.AUTHORITY_CHECK_EXPIRED,
            ),
            (
                {
                    "authority_fact": _authority(checked_at=_T0 - timedelta(minutes=10), valid_until=_T0 + timedelta(minutes=1)),
                    "policy": _policy(max_authority_check_age=timedelta(minutes=5)),
                },
                IdentityRefusalCode.AUTHORITY_CHECK_STALE,
            ),
            (
                {"authority_fact": _authority(grant_source=_grant(grant_kind=GrantKind.WORKSPACE_INHERITED))},
                IdentityRefusalCode.WORKSPACE_INHERITANCE_PROHIBITED,
            ),
        ],
    )
    def test_fail_closed_business_refusals(self, overrides, expected):
        result = _validate(**overrides)
        assert result.outcome == IdentityValidationOutcome.REFUSED
        assert result.refusal_code == expected
        assert result.refusal_detail
        assert result.validated_actor is None
        assert result.validation_binding_hash is None

    def test_system_actor_with_human_auth_cannot_review(self):
        human = _actor()
        system = _actor(actor_type=ActorType.SYSTEM, actor_id="actor:service")
        result = validate_human_authority(
            system,
            _auth(human),
            _status(human),
            _authority(human),
            _scope(),
            Permission.EXECUTION_INTENT_REVIEW,
            _T0,
            _policy(),
        )
        assert result.refusal_code == IdentityRefusalCode.SYSTEM_ACTOR_CANNOT_REVIEW

    def test_auth_event_and_authority_fact_mismatch_is_not_inferred(self):
        result = _validate(
            authority_fact=_authority(authentication_event_id="auth-event:another")
        )
        assert result.refusal_code == IdentityRefusalCode.AUTHORITY_AUTHENTICATION_EVENT_MISMATCH

    def test_refusal_precedence_is_deterministic(self):
        result = _validate(
            policy=_policy(policy_version="unsupported"),
            authentication_event=_auth(credential_binding=CredentialBinding.SHARED),
            authority_fact=_authority(decision=AuthorityDecision.DENY),
        )
        assert result.refusal_code == IdentityRefusalCode.UNSUPPORTED_POLICY_VERSION


class TestCanonicalBinding:
    def test_canonical_output_and_hash_are_deterministic(self):
        actor = _actor()
        auth = _auth(actor)
        authority = _authority(actor)
        values = IdentityValidationInput(**_bundle())
        first = canonicalize_identity_validation_binding(
            values,
            valid_from=authority.checked_at,
            valid_until=authority.valid_until,
        )
        second = canonicalize_identity_validation_binding(
            values,
            valid_from=authority.checked_at,
            valid_until=authority.valid_until,
        )
        assert first == second
        assert compute_actor_ref_hash(actor) == compute_actor_ref_hash(actor)
        assert compute_authentication_event_ref_hash(auth) == compute_authentication_event_ref_hash(auth)
        assert compute_actor_authority_fact_hash(authority) == compute_actor_authority_fact_hash(authority)
        assert compute_identity_validation_binding_hash(
            values, valid_from=authority.checked_at, valid_until=authority.valid_until
        ) == compute_identity_validation_binding_hash(
            values, valid_from=authority.checked_at, valid_until=authority.valid_until
        )

    def test_policy_set_order_is_canonical(self):
        values = _bundle()
        policy_a = _policy(
            supported_identity_contract_versions=frozenset({"1", "2"}),
            allowed_assurance_classes=frozenset(
                {AuthenticationAssuranceClass.MULTI_FACTOR, AuthenticationAssuranceClass.HARDWARE_BOUND}
            ),
        )
        policy_b = _policy(
            supported_identity_contract_versions=frozenset({"2", "1"}),
            allowed_assurance_classes=frozenset(
                {AuthenticationAssuranceClass.HARDWARE_BOUND, AuthenticationAssuranceClass.MULTI_FACTOR}
            ),
        )
        a = IdentityValidationInput(**{**values, "policy": policy_a})
        b = IdentityValidationInput(**{**values, "policy": policy_b})
        fact = values["authority_fact"]
        assert compute_identity_validation_binding_hash(
            a, valid_from=fact.checked_at, valid_until=fact.valid_until
        ) == compute_identity_validation_binding_hash(
            b, valid_from=fact.checked_at, valid_until=fact.valid_until
        )

    @pytest.mark.parametrize(
        "mutator",
        [
            lambda value: replace(value, contract_version="2"),
            lambda value: replace(value, actor_type=ActorType.SYSTEM),
            lambda value: replace(value, actor_id="actor:other"),
            lambda value: replace(value, authority_namespace="deployment:other"),
            lambda value: replace(value, identity_provider_ref="provider:other"),
        ],
    )
    def test_actor_hash_sensitive_to_every_included_field(self, mutator):
        actor = _actor()
        assert compute_actor_ref_hash(actor) != compute_actor_ref_hash(mutator(actor))

    @pytest.mark.parametrize(
        "mutator",
        [
            lambda value: replace(value, contract_version="2"),
            lambda value: replace(value, authentication_event_id="auth-event:other"),
            lambda value: replace(value, actor_ref=_actor(actor_id="actor:other")),
            lambda value: replace(value, provider_ref="provider:other"),
            lambda value: replace(value, authenticated_at=value.authenticated_at + timedelta(seconds=1)),
            lambda value: replace(value, valid_until=value.valid_until + timedelta(seconds=1)),
            lambda value: replace(value, assurance_class=AuthenticationAssuranceClass.HARDWARE_BOUND),
            lambda value: replace(value, credential_status_version="credential-state:8"),
            lambda value: replace(value, credential_binding=CredentialBinding.SHARED),
            lambda value: replace(value, subject_mode=AuthenticationSubjectMode.DELEGATED),
        ],
    )
    def test_authentication_hash_sensitive_to_every_included_field(self, mutator):
        auth = _auth()
        assert compute_authentication_event_ref_hash(auth) != compute_authentication_event_ref_hash(mutator(auth))

    @pytest.mark.parametrize(
        "mutator",
        [
            lambda value: replace(value, contract_version="2"),
            lambda value: replace(value, authority_fact_id="authority-fact:other"),
            lambda value: replace(value, actor_ref=_actor(actor_id="actor:other")),
            lambda value: replace(value, authentication_event_id="auth-event:other"),
            lambda value: replace(value, scope=_scope(portfolio_id=8)),
            lambda value: replace(value, permission=Permission.EXECUTION_INTENT_PREPARE),
            lambda value: replace(value, authorization_policy_version="workspace-rbac:2"),
            lambda value: replace(value, grant_source=_grant(grant_source_id="grant:other")),
            lambda value: replace(value, checked_at=value.checked_at + timedelta(seconds=1)),
            lambda value: replace(value, valid_until=value.valid_until + timedelta(seconds=1)),
            lambda value: replace(value, decision=AuthorityDecision.DENY),
            lambda value: replace(value, grant_status=GrantStatus.REVOKED),
            lambda value: replace(value, workspace_status=ResourceStatus.DELETED),
            lambda value: replace(value, portfolio_status=ResourceStatus.DELETED),
        ],
    )
    def test_authority_hash_sensitive_to_every_included_field(self, mutator):
        authority = _authority()
        assert compute_actor_authority_fact_hash(authority) != compute_actor_authority_fact_hash(
            mutator(authority)
        )

    def test_successful_binding_hash_includes_status_and_policy(self):
        values = _bundle()
        base = IdentityValidationInput(**values)
        fact = values["authority_fact"]
        changed_status = IdentityValidationInput(
            **{
                **values,
                "actor_status_fact": replace(values["actor_status_fact"], status_fact_id="status:other"),
            }
        )
        changed_policy = IdentityValidationInput(
            **{
                **values,
                "policy": _policy(max_authority_check_age=timedelta(minutes=3)),
            }
        )
        base_hash = compute_identity_validation_binding_hash(
            base, valid_from=fact.checked_at, valid_until=fact.valid_until
        )
        assert base_hash != compute_identity_validation_binding_hash(
            changed_status, valid_from=fact.checked_at, valid_until=fact.valid_until
        )
        assert base_hash != compute_identity_validation_binding_hash(
            changed_policy, valid_from=fact.checked_at, valid_until=fact.valid_until
        )

    def test_no_secret_or_display_name_is_in_contract_or_hash_payload(self):
        forbidden = {"password", "password_hash", "jwt", "token", "cookie", "email", "username", "display_name"}
        contract_fields = {
            item.name
            for contract in (ActorRef, AuthenticationEventRef, ActorAuthorityFact)
            for item in fields(contract)
        }
        canonical = "".join(
            (
                canonicalize_actor_ref(_actor()),
                canonicalize_authentication_event_ref(_auth()),
                canonicalize_actor_authority_fact(_authority()),
            )
        ).lower()
        assert contract_fields.isdisjoint(forbidden)
        assert all(item not in canonical for item in forbidden)


class TestMalformedConstruction:
    @pytest.mark.parametrize(
        "factory",
        [
            lambda: _auth(authenticated_at=datetime(2026, 7, 17, 11, 0)),
            lambda: _status(checked_at=datetime(2026, 7, 17, 11, 0)),
            lambda: _authority(checked_at=datetime(2026, 7, 17, 11, 0)),
            lambda: IdentityValidationInput(**{**_bundle(), "validation_time": datetime(2026, 7, 17, 12, 0)}),
            lambda: _auth(authenticated_at=_T0, valid_until=_T0),
            lambda: _scope(workspace_id=0),
            lambda: _actor(actor_id=""),
            lambda: _policy(max_authentication_age=timedelta(microseconds=500_000)),
        ],
    )
    def test_malformed_primitives_raise_value_error(self, factory):
        with pytest.raises(ValueError):
            factory()

    def test_non_utc_aware_offset_is_rejected(self):
        plus_seven = timezone(timedelta(hours=7))
        with pytest.raises(ValueError):
            _auth(
                authenticated_at=datetime(2026, 7, 17, 18, 0, tzinfo=plus_seven),
                valid_until=datetime(2026, 7, 17, 19, 0, tzinfo=plus_seven),
            )
