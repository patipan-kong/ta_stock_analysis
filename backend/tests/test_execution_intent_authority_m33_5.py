"""Pure M33.5 historical-authority verification and hashing tests."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone

import pytest

from services.execution_intent_authority import (
    AUTHORITY_CONTRACT_VERSION,
    AuthorityBinding,
    AuthorityCertificate,
    AuthorityCompleteness,
    AuthorityConflictFact,
    AuthorityEvidence,
    AuthorityEvidenceKind,
    AuthorityEvidenceRole,
    AuthorityIssuer,
    AuthorityIssuerKind,
    AuthorityLevel,
    AuthorityReasonCode,
    AuthorityScope,
    AuthoritySourceReference,
    DetachedEvidenceFact,
    DigestAlgorithm,
    HistoricalSourceAct,
    IssuerTrustFact,
    PayloadRelationship,
    RevocationEvidence,
    RevocationStatus,
    RevocationVerificationFact,
    SignatureAlgorithm,
    SignatureVerificationFact,
    TargetSnapshotFact,
    VerificationPolicy,
    canonicalize_authority_certificate,
    canonicalize_authority_evidence,
    compute_authority_certificate_digest,
    compute_authority_evidence_digest,
    verify_authority,
)
from services.execution_intent_contracts import ProvenanceCompleteness


_T0 = datetime(2026, 7, 17, 3, 0, tzinfo=timezone.utc)
_PAYLOAD = '{"allocations":[{"side":"BUY","symbol":"KBANK.BK","target_weight":"0.10"}]}'
_OTHER_PAYLOAD = '{"allocations":[{"side":"BUY","symbol":"KBANK.BK","target_weight":"0.20"}]}'
_ZERO_DIGEST = "sha256:" + ("0" * 64)
_TARGET_HASH = "sha256:" + ("a" * 64)
_REF_DIGEST = "sha256:" + ("b" * 64)


def _source_digest(payload: str = _PAYLOAD, version: str = "1") -> str:
    return compute_authority_evidence_digest(payload, source_contract_version=version)


def _evidence(
    evidence_id: str,
    roles: frozenset[AuthorityEvidenceRole],
    *,
    kind: AuthorityEvidenceKind = AuthorityEvidenceKind.AUDIT_LOG,
    payload: str | None = _PAYLOAD,
    source_digest: str | None = None,
    **overrides,
) -> AuthorityEvidence:
    values = dict(
        evidence_id=evidence_id,
        evidence_kind=kind,
        evidence_roles=roles,
        source_local_id=f"source:{evidence_id}",
        source_contract_version="1",
        canonical_payload=payload,
        source_digest_algorithm=DigestAlgorithm.SHA256,
        source_digest=source_digest or _source_digest(payload or ""),
        occurred_at=_T0,
        recorded_at=_T0 + timedelta(seconds=1),
        source_timezone=None,
        source_local_time_text=None,
        locator=None,
    )
    values.update(overrides)
    return AuthorityEvidence(**values)


def _scope(**overrides) -> AuthorityScope:
    values = dict(
        workspace_id=1,
        portfolio_id=7,
        authority_namespace="deployment:test",
        environment_id="env:test",
    )
    values.update(overrides)
    return AuthorityScope(**values)


def _target(**overrides) -> TargetSnapshotFact:
    values = dict(
        intent_id="intent:new",
        snapshot_id="snapshot:new",
        content_hash=_TARGET_HASH,
        workspace_id=1,
        portfolio_id=7,
        authority_namespace="deployment:test",
        environment_id="env:test",
    )
    values.update(overrides)
    return TargetSnapshotFact(**values)


def _issuer(**overrides) -> AuthorityIssuer:
    values = dict(
        issuer_id="issuer:audit",
        issuer_kind=AuthorityIssuerKind.TRUSTED_AUDIT_SYSTEM,
        authority_namespace="deployment:test",
        trust_policy_version="1",
        signing_key_id="key:1",
        signature_algorithm=SignatureAlgorithm.ED25519,
    )
    values.update(overrides)
    return AuthorityIssuer(**values)


def _binding(**overrides) -> AuthorityBinding:
    digest = _source_digest()
    values = dict(
        source_act=HistoricalSourceAct.APPROVED,
        reviewed_payload_schema_version="1",
        reviewed_payload_digest=digest,
        approved_payload_schema_version="1",
        approved_payload_digest=digest,
        payload_relationship=PayloadRelationship.IDENTICAL,
        transformation_contract_version=None,
        historical_actor_id="user:42",
        historical_actor_authority_ref="authority",
        recommendation_ref=AuthoritySourceReference("recommendation:1", _REF_DIGEST),
        decision_ref=AuthoritySourceReference("decision:1", _REF_DIGEST),
        approval_event_id="approval:1",
        approval_occurred_at=_T0,
        source_timezone_semantics=None,
        approval_time_was_converted=False,
        approval_time_ambiguous=False,
        historical_actor_ambiguous=False,
        lineage_ambiguous=False,
        target_intent_id="intent:new",
        target_snapshot_id="snapshot:new",
        target_content_hash=_TARGET_HASH,
    )
    values.update(overrides)
    return AuthorityBinding(**values)


def _evidence_set() -> tuple[AuthorityEvidence, ...]:
    return (
        _evidence("reviewed", frozenset({AuthorityEvidenceRole.REVIEWED_PAYLOAD})),
        _evidence("approved", frozenset({AuthorityEvidenceRole.APPROVED_PAYLOAD})),
        _evidence("actor", frozenset({AuthorityEvidenceRole.ACTOR_IDENTITY}), payload='{"actor":"user:42"}'),
        _evidence(
            "authority",
            frozenset({AuthorityEvidenceRole.ACTOR_AUTHORITY}),
            payload='{"portfolio_id":7,"workspace_id":1}',
        ),
    )


def _certificate(**overrides) -> AuthorityCertificate:
    values = dict(
        contract_version=AUTHORITY_CONTRACT_VERSION,
        certificate_id="certificate:1",
        issuer=_issuer(),
        issued_at=_T0 + timedelta(minutes=1),
        evidence=_evidence_set(),
        binding=_binding(),
        scope=_scope(),
        completeness_claim=AuthorityCompleteness.EXACT,
        supersedes_certificate_id=None,
        certificate_digest=_ZERO_DIGEST,
        signature="signature:one",
    )
    values.update(overrides)
    certificate = AuthorityCertificate(**values)
    if "certificate_digest" not in overrides:
        certificate = replace(
            certificate,
            certificate_digest=compute_authority_certificate_digest(certificate),
        )
    return certificate


def _policy(**overrides) -> VerificationPolicy:
    values = dict(
        contract_version="1",
        policy_version="1",
        evaluated_at=_T0 + timedelta(days=1),
        available=True,
        allow_unverifiable_proposals=False,
    )
    values.update(overrides)
    return VerificationPolicy(**values)


def _revocation_fact(
    certificate: AuthorityCertificate,
    status: RevocationStatus = RevocationStatus.NOT_REVOKED,
) -> RevocationVerificationFact:
    return RevocationVerificationFact(
        RevocationEvidence(
            certificate.certificate_id,
            certificate.certificate_digest,
            status,
            _T0 + timedelta(hours=1),
        ),
        signature_valid=True,
        issuer_trusted=True,
    )


def _verify(certificate: AuthorityCertificate, **overrides):
    values = dict(
        verification_policy=_policy(),
        signature_fact=SignatureVerificationFact(
            certificate.certificate_id,
            certificate.certificate_digest,
            True,
        ),
        issuer_trust_fact=IssuerTrustFact("issuer:audit", "key:1", "1", True),
        revocation_facts=(_revocation_fact(certificate),),
        target_snapshot_fact=_target(),
    )
    values.update(overrides)
    return verify_authority(certificate, **values)


class TestAuthorityContracts:
    def test_contracts_are_frozen(self):
        certificate = _certificate()
        with pytest.raises(FrozenInstanceError):
            certificate.signature = "changed"  # type: ignore[misc]

    @pytest.mark.parametrize(
        "factory",
        [
            lambda: _certificate(issued_at=datetime(2026, 7, 17, 3, 0)),
            lambda: _evidence(
                "bad-time",
                frozenset({AuthorityEvidenceRole.REVIEWED_PAYLOAD}),
                recorded_at=datetime(2026, 7, 17, 3, 0),
            ),
            lambda: _binding(approval_occurred_at=datetime(2026, 7, 17, 3, 0)),
            lambda: _policy(evaluated_at=datetime(2026, 7, 17, 3, 0)),
        ],
    )
    def test_naive_datetime_rejected(self, factory):
        with pytest.raises(ValueError):
            factory()

    @pytest.mark.parametrize("bad_digest", ["", "abc", "sha256:ABC", "sha256:" + ("a" * 63)])
    def test_digest_syntax_rejected(self, bad_digest):
        with pytest.raises(ValueError):
            _target(content_hash=bad_digest)


class TestCanonicalization:
    def test_evidence_order_independent_certificate_digest(self):
        certificate = _certificate()
        reversed_certificate = _certificate(evidence=tuple(reversed(certificate.evidence)))
        assert compute_authority_certificate_digest(certificate) == compute_authority_certificate_digest(
            reversed_certificate
        )

    def test_role_order_independent(self):
        roles_a = frozenset(
            {AuthorityEvidenceRole.REVIEWED_PAYLOAD, AuthorityEvidenceRole.APPROVED_PAYLOAD}
        )
        roles_b = frozenset(reversed(tuple(roles_a)))
        assert canonicalize_authority_evidence(_evidence("both", roles_a)) == canonicalize_authority_evidence(
            _evidence("both", roles_b)
        )

    @pytest.mark.parametrize(
        "mutator",
        [
            lambda cert: replace(cert, certificate_id="certificate:2"),
            lambda cert: replace(cert, issued_at=cert.issued_at + timedelta(seconds=1)),
            lambda cert: replace(cert, issuer=replace(cert.issuer, signing_key_id="key:2")),
            lambda cert: replace(cert, scope=_scope(portfolio_id=8)),
            lambda cert: replace(cert, binding=_binding(target_snapshot_id="snapshot:other")),
            lambda cert: replace(cert, completeness_claim=AuthorityCompleteness.PROPOSAL_ONLY),
            lambda cert: replace(cert, supersedes_certificate_id="certificate:0"),
            lambda cert: replace(
                cert,
                evidence=cert.evidence
                + (_evidence("extra", frozenset({AuthorityEvidenceRole.EVENT_TIME}), payload='{"time":"x"}'),),
            ),
        ],
    )
    def test_certificate_digest_sensitive_to_every_top_level_inclusion(self, mutator):
        certificate = _certificate()
        assert compute_authority_certificate_digest(certificate) != compute_authority_certificate_digest(
            mutator(certificate)
        )

    def test_certificate_digest_excludes_signature_and_stored_digest(self):
        certificate = _certificate()
        changed = replace(
            certificate,
            signature="different-signature",
            certificate_digest="sha256:" + ("f" * 64),
        )
        assert compute_authority_certificate_digest(certificate) == compute_authority_certificate_digest(changed)

    def test_evidence_payload_digest_sensitive_to_payload(self):
        assert _source_digest(_PAYLOAD) != _source_digest(_OTHER_PAYLOAD)

    def test_certificate_canonicalization_only_copies_opaque_target_hash(self):
        certificate = _certificate()
        canonical = canonicalize_authority_certificate(certificate)
        assert _TARGET_HASH in canonical
        assert "source_provenance" not in canonical


class TestAuthorityVerification:
    def test_fully_certified_exact(self):
        result = _verify(_certificate())
        assert result.authority_level == AuthorityLevel.CERTIFIED_EXACT
        assert result.reason_codes == ()
        assert result.may_build_exact_snapshot is True
        assert result.may_recreate_historical_approval is True
        assert result.may_build_proposal is True
        assert result.requires_reconfirmation is False
        assert result.provenance_completeness == ProvenanceCompleteness.EXACT_FROZEN

    def test_missing_actor_is_proposal_only(self):
        certificate = _certificate(binding=_binding(historical_actor_id=None))
        result = _verify(certificate)
        assert result.authority_level == AuthorityLevel.CERTIFIED_PROPOSAL_ONLY
        assert AuthorityReasonCode.HISTORICAL_ACTOR_MISSING in result.reason_codes
        assert result.requires_reconfirmation is True
        assert result.may_recreate_historical_approval is False

    @pytest.mark.parametrize(
        "binding,reason",
        [
            (_binding(reviewed_payload_digest=None), AuthorityReasonCode.REVIEWED_PAYLOAD_MISSING),
            (_binding(approved_payload_digest=None), AuthorityReasonCode.APPROVED_PAYLOAD_MISSING),
        ],
    )
    def test_missing_payload_binding_is_proposal_only(self, binding, reason):
        result = _verify(_certificate(binding=binding))
        assert result.authority_level == AuthorityLevel.CERTIFIED_PROPOSAL_ONLY
        assert reason in result.reason_codes

    def test_same_certificate_id_same_bytes_replays_same_result(self):
        certificate = _certificate()
        base = _verify(certificate)
        replay = _verify(certificate, related_certificates=(certificate,))
        assert replay == base

    def test_same_certificate_id_different_bytes_conflicts(self):
        certificate = _certificate()
        conflicting = _certificate(completeness_claim=AuthorityCompleteness.PROPOSAL_ONLY)
        result = _verify(certificate, related_certificates=(conflicting,))
        assert result.authority_level == AuthorityLevel.CONFLICTING
        assert AuthorityReasonCode.CERTIFICATE_ID_REUSED in result.reason_codes

    def test_conflicting_certificates_refused(self):
        certificate = _certificate()
        other = _certificate(
            certificate_id="certificate:2",
            binding=_binding(target_snapshot_id="snapshot:other"),
        )
        result = _verify(certificate, related_certificates=(other,))
        assert result.authority_level == AuthorityLevel.CONFLICTING
        assert AuthorityReasonCode.CONFLICTING_CERTIFICATES in result.reason_codes

    def test_caller_supplied_conflict_fact_refused(self):
        certificate = _certificate()
        result = _verify(
            certificate,
            conflict_facts=(AuthorityConflictFact((certificate.certificate_id, "certificate:2"), True),),
        )
        assert result.authority_level == AuthorityLevel.CONFLICTING

    def test_legacy_only_without_certificate_can_be_explicitly_proposal_eligible(self):
        evidence = (_evidence("legacy", frozenset({AuthorityEvidenceRole.APPROVED_PAYLOAD})),)
        result = verify_authority(
            None,
            verification_policy=_policy(allow_unverifiable_proposals=True),
            uncertified_evidence=evidence,
            uncertified_scope=_scope(),
            source_act=HistoricalSourceAct.APPROVED,
        )
        assert result.authority_level == AuthorityLevel.UNVERIFIABLE
        assert AuthorityReasonCode.CERTIFICATE_MISSING in result.reason_codes
        assert result.may_build_proposal is True
        assert result.may_build_exact_snapshot is False

    def test_proposal_only_certificate(self):
        certificate = _certificate(binding=_binding(target_snapshot_id=None, target_content_hash=None))
        result = _verify(certificate)
        assert result.authority_level == AuthorityLevel.CERTIFIED_PROPOSAL_ONLY
        assert result.may_build_proposal is True
        assert result.requires_reconfirmation is True

    def test_certificate_digest_mismatch(self):
        certificate = _certificate(certificate_digest="sha256:" + ("c" * 64))
        result = _verify(certificate)
        assert result.authority_level == AuthorityLevel.UNVERIFIABLE
        assert AuthorityReasonCode.CERTIFICATE_DIGEST_MISMATCH in result.reason_codes

    def test_detached_evidence_digest_mismatch(self):
        reviewed = _evidence(
            "reviewed",
            frozenset({AuthorityEvidenceRole.REVIEWED_PAYLOAD}),
            payload=None,
            source_digest=_source_digest(),
        )
        certificate = _certificate(evidence=(reviewed,) + _evidence_set()[1:])
        result = _verify(
            certificate,
            detached_evidence=(DetachedEvidenceFact("reviewed", _PAYLOAD, False),),
        )
        assert result.authority_level == AuthorityLevel.UNVERIFIABLE
        assert AuthorityReasonCode.EVIDENCE_DIGEST_MISMATCH in result.reason_codes

    def test_invalid_signature(self):
        certificate = _certificate()
        result = _verify(
            certificate,
            signature_fact=SignatureVerificationFact(
                certificate.certificate_id,
                certificate.certificate_digest,
                False,
            ),
        )
        assert result.authority_level == AuthorityLevel.UNVERIFIABLE
        assert AuthorityReasonCode.SIGNATURE_INVALID in result.reason_codes

    def test_untrusted_issuer(self):
        result = _verify(
            _certificate(),
            issuer_trust_fact=IssuerTrustFact("issuer:audit", "key:1", "1", False),
        )
        assert AuthorityReasonCode.ISSUER_UNTRUSTED in result.reason_codes

    def test_unavailable_trust_policy(self):
        result = _verify(_certificate(), verification_policy=_policy(available=False))
        assert AuthorityReasonCode.TRUST_POLICY_UNAVAILABLE in result.reason_codes

    def test_effective_revocation(self):
        certificate = _certificate()
        result = _verify(certificate, revocation_facts=(_revocation_fact(certificate, RevocationStatus.REVOKED),))
        assert result.authority_level == AuthorityLevel.UNVERIFIABLE
        assert result.revocation_status == RevocationStatus.REVOKED
        assert result.may_build_proposal is False

    def test_unknown_revocation(self):
        result = _verify(_certificate(), revocation_facts=())
        assert result.authority_level == AuthorityLevel.UNVERIFIABLE
        assert result.revocation_status == RevocationStatus.UNKNOWN
        assert AuthorityReasonCode.REVOCATION_STATUS_UNKNOWN in result.reason_codes

    def test_conflicting_revocation(self):
        certificate = _certificate()
        result = _verify(
            certificate,
            revocation_facts=(
                _revocation_fact(certificate, RevocationStatus.REVOKED),
                _revocation_fact(certificate, RevocationStatus.NOT_REVOKED),
            ),
        )
        assert result.authority_level == AuthorityLevel.CONFLICTING
        assert result.revocation_status == RevocationStatus.CONFLICTING

    @pytest.mark.parametrize(
        "target,reason",
        [
            (_target(workspace_id=2), AuthorityReasonCode.WORKSPACE_SCOPE_MISMATCH),
            (_target(portfolio_id=8), AuthorityReasonCode.PORTFOLIO_SCOPE_MISMATCH),
            (_target(authority_namespace="other"), AuthorityReasonCode.AUTHORITY_NAMESPACE_MISMATCH),
            (_target(environment_id="other"), AuthorityReasonCode.ENVIRONMENT_SCOPE_MISMATCH),
        ],
    )
    def test_scope_mismatch_conflicts(self, target, reason):
        result = _verify(_certificate(), target_snapshot_fact=target)
        assert result.authority_level == AuthorityLevel.CONFLICTING
        assert reason in result.reason_codes

    def test_timezone_ambiguity_is_proposal_only(self):
        certificate = _certificate(binding=_binding(approval_time_ambiguous=True))
        result = _verify(certificate)
        assert result.authority_level == AuthorityLevel.CERTIFIED_PROPOSAL_ONLY
        assert AuthorityReasonCode.TIMEZONE_AMBIGUOUS in result.reason_codes

    @pytest.mark.parametrize(
        "binding,reason",
        [
            (_binding(historical_actor_ambiguous=True), AuthorityReasonCode.HISTORICAL_ACTOR_AMBIGUOUS),
            (_binding(historical_actor_authority_ref=None), AuthorityReasonCode.ACTOR_AUTHORITY_UNPROVEN),
            (_binding(recommendation_ref=None), AuthorityReasonCode.RECOMMENDATION_BINDING_MISSING),
            (_binding(decision_ref=None), AuthorityReasonCode.DECISION_BINDING_MISSING),
            (_binding(target_intent_id="intent:other"), AuthorityReasonCode.TARGET_INTENT_ID_MISMATCH),
        ],
    )
    def test_missing_exact_authority_facts_downgrade_to_proposal(self, binding, reason):
        result = _verify(_certificate(binding=binding))
        assert result.authority_level == AuthorityLevel.CERTIFIED_PROPOSAL_ONLY
        assert reason in result.reason_codes

    def test_ambiguous_lineage_conflicts(self):
        result = _verify(_certificate(binding=_binding(lineage_ambiguous=True)))
        assert result.authority_level == AuthorityLevel.CONFLICTING
        assert AuthorityReasonCode.LINEAGE_AMBIGUOUS in result.reason_codes

    def test_unapproved_transformation_conflicts(self):
        result = _verify(
            _certificate(
                binding=_binding(
                    payload_relationship=PayloadRelationship.LOSSLESS_TRANSFORMATION,
                    transformation_contract_version="legacy-map:1",
                )
            )
        )
        assert result.authority_level == AuthorityLevel.CONFLICTING
        assert AuthorityReasonCode.LOSSLESS_MAPPING_UNPROVEN in result.reason_codes

    def test_reviewed_approved_digest_conflict_refused(self):
        result = _verify(
            _certificate(
                binding=_binding(approved_payload_digest=_source_digest(_OTHER_PAYLOAD))
            )
        )
        assert result.authority_level == AuthorityLevel.CONFLICTING
        assert AuthorityReasonCode.REVIEWED_APPROVED_PAYLOAD_CONFLICT in result.reason_codes

    def test_partial_execution_label_never_supplies_exact_authority(self):
        result = _verify(_certificate(binding=_binding(source_act=HistoricalSourceAct.PARTIAL_EXECUTION)))
        assert result.authority_level == AuthorityLevel.CERTIFIED_PROPOSAL_ONLY
        assert AuthorityReasonCode.PARTIAL_EXECUTION_NOT_INTENT_AUTHORITY in result.reason_codes

    @pytest.mark.parametrize(
        "binding,reason",
        [
            (_binding(target_snapshot_id="snapshot:other"), AuthorityReasonCode.TARGET_SNAPSHOT_ID_MISMATCH),
            (
                _binding(target_content_hash="sha256:" + ("d" * 64)),
                AuthorityReasonCode.TARGET_CONTENT_HASH_MISMATCH,
            ),
        ],
    )
    def test_target_mismatch_never_exact(self, binding, reason):
        result = _verify(_certificate(binding=binding))
        assert result.authority_level == AuthorityLevel.CERTIFIED_PROPOSAL_ONLY
        assert reason in result.reason_codes
        assert result.may_recreate_historical_approval is False

    @pytest.mark.parametrize("source_act", [HistoricalSourceAct.REJECTED, HistoricalSourceAct.EXPIRED])
    def test_rejected_and_expired_are_out_of_scope(self, source_act):
        certificate = _certificate(binding=_binding(source_act=source_act))
        result = _verify(certificate)
        assert result.authority_level == AuthorityLevel.OUT_OF_SCOPE
        assert result.may_build_proposal is False

    @pytest.mark.parametrize(
        "kind,reason",
        [
            (AuthorityEvidenceKind.SHADOW_PORTFOLIO, AuthorityReasonCode.SHADOW_EVIDENCE_PROHIBITED),
            (AuthorityEvidenceKind.TRANSACTION_LINK, AuthorityReasonCode.TRANSACTION_EVIDENCE_PROHIBITED),
        ],
    )
    def test_prohibited_evidence_refused(self, kind, reason):
        certificate = _certificate(
            evidence=_evidence_set()
            + (_evidence("prohibited", frozenset({AuthorityEvidenceRole.EVENT_TIME}), kind=kind),)
        )
        result = _verify(certificate)
        assert result.authority_level == AuthorityLevel.UNVERIFIABLE
        assert reason in result.reason_codes

    def test_unknown_contract_version_fails_closed(self):
        certificate = _certificate(contract_version="99")
        result = _verify(certificate)
        assert result.authority_level == AuthorityLevel.UNVERIFIABLE
        assert result.reason_codes == (AuthorityReasonCode.UNSUPPORTED_CONTRACT_VERSION,)

    def test_reason_codes_are_canonically_ordered(self):
        certificate = _certificate(
            binding=_binding(
                historical_actor_id=None,
                reviewed_payload_digest=None,
                target_snapshot_id=None,
            )
        )
        result = _verify(certificate)
        assert result.reason_codes == tuple(sorted(result.reason_codes, key=lambda reason: reason.value))

    def test_identical_inputs_produce_byte_equivalent_result(self):
        certificate = _certificate()
        assert _verify(certificate) == _verify(certificate)
