"""Focused pure M33.2 Execution Intent contract/hashing tests."""
from __future__ import annotations

from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from services.execution_intent_contracts import (
    Actor,
    ActorType,
    ExecutionIntentAllocationTerm,
    IntentKind,
    ProvenanceCompleteness,
    SourceKind,
    SourceProvenance,
    TermSide,
    build_execution_intent_snapshot,
    build_execution_intent_terms,
    compute_snapshot_content_hash,
)


_EFFECTIVE = datetime(2026, 7, 16, 3, 0, tzinfo=timezone.utc)
_RECORDED = _EFFECTIVE + timedelta(seconds=1)
_HUMAN = Actor(ActorType.HUMAN, "user:42")


def _provenance(**overrides) -> SourceProvenance:
    values = dict(
        source_kind=SourceKind.LEGACY_RECOMMENDATION_SNAPSHOT,
        source_local_id="rec-1",
        source_contract_version="1",
        source_created_at=_EFFECTIVE - timedelta(hours=1),
        source_digest="digest-abc",
        completeness=ProvenanceCompleteness.EXACT_FROZEN,
    )
    values.update(overrides)
    return SourceProvenance(**values)


def _terms(**overrides):
    allocations = overrides.pop(
        "allocations",
        (
            ExecutionIntentAllocationTerm("KBANK.BK", TermSide.BUY, target_weight=Decimal("0.10")),
            ExecutionIntentAllocationTerm("PTT.BK", TermSide.SELL, target_value=Decimal("5000")),
        ),
    )
    return build_execution_intent_terms("1", allocations, **overrides)


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
        effective_at=_EFFECTIVE,
        recorded_at=_RECORDED,
        expires_at=None,
    )
    values.update(overrides)
    return build_execution_intent_snapshot(**values)


class TestImmutability:
    def test_snapshot_is_frozen(self):
        snapshot = _snapshot()
        with pytest.raises(FrozenInstanceError):
            snapshot.revision = 2  # type: ignore[misc]

    def test_terms_are_frozen(self):
        terms = _terms()
        with pytest.raises(FrozenInstanceError):
            terms.notes = "changed"  # type: ignore[misc]

    def test_allocation_term_is_frozen(self):
        allocation = ExecutionIntentAllocationTerm("KBANK.BK", TermSide.BUY, target_weight=Decimal("0.1"))
        with pytest.raises(FrozenInstanceError):
            allocation.symbol = "PTT.BK"  # type: ignore[misc]


class TestTermsValidation:
    def test_requires_at_least_one_allocation(self):
        with pytest.raises(ValueError):
            build_execution_intent_terms("1", ())

    def test_rejects_duplicate_symbol_side(self):
        allocations = (
            ExecutionIntentAllocationTerm("KBANK.BK", TermSide.BUY, target_weight=Decimal("0.1")),
            ExecutionIntentAllocationTerm("KBANK.BK", TermSide.BUY, target_weight=Decimal("0.2")),
        )
        with pytest.raises(ValueError):
            build_execution_intent_terms("1", allocations)

    def test_requires_exactly_one_of_weight_or_value(self):
        with pytest.raises(ValueError):
            build_execution_intent_terms(
                "1",
                (ExecutionIntentAllocationTerm("KBANK.BK", TermSide.BUY),),
            )
        with pytest.raises(ValueError):
            build_execution_intent_terms(
                "1",
                (
                    ExecutionIntentAllocationTerm(
                        "KBANK.BK",
                        TermSide.BUY,
                        target_weight=Decimal("0.1"),
                        target_value=Decimal("100"),
                    ),
                ),
            )

    def test_rejects_non_positive_terms(self):
        with pytest.raises(ValueError):
            build_execution_intent_terms(
                "1",
                (ExecutionIntentAllocationTerm("KBANK.BK", TermSide.BUY, target_weight=Decimal("0")),),
            )


class TestSnapshotConstruction:
    def test_reserved_future_canonical_plan_source_is_refused(self):
        with pytest.raises(ValueError):
            _snapshot(
                source_provenance=(
                    _provenance(source_kind=SourceKind.FUTURE_CANONICAL_EXECUTION_PLAN),
                ),
            )

    def test_revision_must_be_positive(self):
        with pytest.raises(ValueError):
            _snapshot(revision=0)

    def test_revision_one_forbids_predecessor(self):
        with pytest.raises(ValueError):
            _snapshot(revision=1, supersedes_snapshot_id="snap-0")

    def test_revision_above_one_requires_predecessor(self):
        with pytest.raises(ValueError):
            _snapshot(revision=2, supersedes_snapshot_id=None)

    def test_requires_at_least_one_source_provenance(self):
        with pytest.raises(ValueError):
            _snapshot(source_provenance=())

    def test_naive_datetime_rejected(self):
        with pytest.raises(ValueError):
            _snapshot(effective_at=datetime(2026, 7, 16, 3, 0))

    def test_naive_recorded_at_rejected(self):
        with pytest.raises(ValueError):
            _snapshot(recorded_at=datetime(2026, 7, 16, 3, 0))


class TestCanonicalHashing:
    def test_deterministic_across_runs(self):
        snapshot_a = _snapshot()
        snapshot_b = _snapshot()
        assert snapshot_a.content_hash == snapshot_b.content_hash

    def test_hash_insensitive_to_identity_and_lineage_fields(self):
        base = _snapshot()
        other_identity = _snapshot(snapshot_id="snap-999", intent_id="intent-999")
        assert base.content_hash == other_identity.content_hash

        as_revision_two = _snapshot(revision=2, supersedes_snapshot_id="snap-0")
        assert base.content_hash == as_revision_two.content_hash

    def test_hash_insensitive_to_actor_and_recorded_at(self):
        base = _snapshot()
        other = _snapshot(
            created_by_actor=Actor(ActorType.SYSTEM, "system:recommendation-writer"),
            recorded_at=_RECORDED + timedelta(days=1),
        )
        assert base.content_hash == other.content_hash

    def test_hash_sensitive_to_terms(self):
        base = _snapshot()
        changed = _snapshot(
            terms=_terms(
                allocations=(
                    ExecutionIntentAllocationTerm("KBANK.BK", TermSide.BUY, target_weight=Decimal("0.20")),
                    ExecutionIntentAllocationTerm("PTT.BK", TermSide.SELL, target_value=Decimal("5000")),
                )
            )
        )
        assert base.content_hash != changed.content_hash

    def test_hash_sensitive_to_allocation_order_independence(self):
        """Reordered-but-identical allocations must hash the same (order-independent)."""

        forward = _terms(
            allocations=(
                ExecutionIntentAllocationTerm("KBANK.BK", TermSide.BUY, target_weight=Decimal("0.1")),
                ExecutionIntentAllocationTerm("PTT.BK", TermSide.SELL, target_value=Decimal("5000")),
            )
        )
        backward = _terms(
            allocations=(
                ExecutionIntentAllocationTerm("PTT.BK", TermSide.SELL, target_value=Decimal("5000")),
                ExecutionIntentAllocationTerm("KBANK.BK", TermSide.BUY, target_weight=Decimal("0.1")),
            )
        )
        assert _snapshot(terms=forward).content_hash == _snapshot(terms=backward).content_hash

    def test_hash_sensitive_to_workspace_and_portfolio(self):
        base = _snapshot()
        other_workspace = _snapshot(workspace_id=2)
        other_portfolio = _snapshot(portfolio_id=8)
        assert base.content_hash != other_workspace.content_hash
        assert base.content_hash != other_portfolio.content_hash

    def test_hash_sensitive_to_effective_and_expiry(self):
        base = _snapshot()
        other_effective = _snapshot(effective_at=_EFFECTIVE + timedelta(days=1))
        other_expiry = _snapshot(expires_at=_EFFECTIVE + timedelta(days=14))
        assert base.content_hash != other_effective.content_hash
        assert base.content_hash != other_expiry.content_hash

    def test_hash_sensitive_to_source_provenance(self):
        base = _snapshot()
        other = _snapshot(source_provenance=(_provenance(source_digest="digest-different"),))
        assert base.content_hash != other.content_hash

    def test_hash_sensitive_to_intent_kind(self):
        base = _snapshot()
        other = _snapshot(intent_kind=IntentKind.MANUAL_OVERRIDE)
        assert base.content_hash != other.content_hash

    def test_hash_rejects_naive_datetime(self):
        with pytest.raises(ValueError):
            compute_snapshot_content_hash(
                terms_schema_version="1",
                intent_kind=IntentKind.FOLLOW_RECOMMENDATION,
                terms=_terms(),
                workspace_id=1,
                portfolio_id=7,
                effective_at=datetime(2026, 7, 16, 3, 0),
                expires_at=None,
                source_provenance=(_provenance(),),
            )

    def test_hash_rejects_non_finite_decimal(self):
        non_finite_terms = build_execution_intent_terms(
            "1",
            (
                ExecutionIntentAllocationTerm(
                    "KBANK.BK",
                    TermSide.BUY,
                    target_weight=Decimal("Infinity"),
                ),
            ),
        )
        with pytest.raises(ValueError):
            compute_snapshot_content_hash(
                terms_schema_version="1",
                intent_kind=IntentKind.FOLLOW_RECOMMENDATION,
                terms=non_finite_terms,
                workspace_id=1,
                portfolio_id=7,
                effective_at=_EFFECTIVE,
                expires_at=None,
                source_provenance=(_provenance(),),
            )
