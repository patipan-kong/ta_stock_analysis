"""Pure M31.3 execution-eligibility shadow evaluation and telemetry.

The predicate in this module describes what Registry-backed execution facts
say about eligibility.  It never admits or rejects a trade, resolves Registry
identity, accesses a database, mutates optimizer output, or persists telemetry.
Boundary callers may log the returned shadow record only after their legacy
result has already been constructed.
"""
from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Mapping, Sequence, Tuple

from services.execution_cutover_config import (
    get_execution_eligibility_cutover_mode,
)
from services.execution_eligibility_observability import (
    EligibilityObservation,
    record_execution_eligibility_observation,
)
from services.execution_instrument_facts import (
    ExecutionFactProvenance,
    ExecutionInstrumentFacts,
    ExecutionInstrumentForm,
    ExecutionResolutionOutcome,
    ExecutionRole,
)

__all__ = [
    "ExecutionEligibilityOutcome",
    "ExecutionEligibility",
    "ShadowExecutionAction",
    "ExecutionEligibilityTelemetry",
    "evaluate_execution_eligibility",
    "consult_execution_eligibility_shadow",
]


class ExecutionEligibilityOutcome(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    UNKNOWN_IDENTITY = "UNKNOWN_IDENTITY"
    AMBIGUOUS_IDENTITY = "AMBIGUOUS_IDENTITY"
    NOT_TRADABLE = "NOT_TRADABLE"
    REFERENCE_ONLY = "REFERENCE_ONLY"
    REGISTRY_FAILURE = "REGISTRY_FAILURE"


@dataclass(frozen=True)
class ExecutionEligibility:
    outcome: ExecutionEligibilityOutcome
    eligible: bool
    reason: str
    registry_failure: bool = False


@dataclass(frozen=True)
class ShadowExecutionAction:
    requested_symbol: str
    legacy_action: str
    classification_agreement: bool | None = None


@dataclass(frozen=True)
class ExecutionEligibilityTelemetry:
    requested_symbol: str
    canonical_symbol: str | None
    registry_asset_id: int | None
    resolution_status: ExecutionResolutionOutcome
    execution_role: ExecutionRole
    instrument_form: ExecutionInstrumentForm
    legacy_action: str
    legacy_path: str
    shadow_eligibility: ExecutionEligibilityOutcome
    legacy_permitted: bool
    disagreement: bool
    registry_failure: bool
    cutover_mode: str
    classification_agreement: bool | None
    registry_error: str | None
    reason: str
    provenance: Tuple[ExecutionFactProvenance, ...]

    def to_log_dict(self) -> dict:
        payload = asdict(self)
        payload["resolution_status"] = self.resolution_status.value
        payload["execution_role"] = self.execution_role.value
        payload["instrument_form"] = self.instrument_form.value
        payload["shadow_eligibility"] = self.shadow_eligibility.value
        payload["provenance"] = [asdict(item) for item in self.provenance]
        return payload


def evaluate_execution_eligibility(
    facts: ExecutionInstrumentFacts,
) -> ExecutionEligibility:
    """Evaluate authoritative facts without consulting symbols or a database."""

    if facts.resolution_error:
        return ExecutionEligibility(
            outcome=ExecutionEligibilityOutcome.REGISTRY_FAILURE,
            eligible=False,
            reason=facts.reason or "Registry facts resolution failed",
            registry_failure=True,
        )
    if facts.execution_role == ExecutionRole.REFERENCE:
        return ExecutionEligibility(
            outcome=ExecutionEligibilityOutcome.REFERENCE_ONLY,
            eligible=False,
            reason=facts.reason or "Registry asset is a reference, not an executable instrument",
        )
    if facts.resolution_status == ExecutionResolutionOutcome.AMBIGUOUS:
        return ExecutionEligibility(
            outcome=ExecutionEligibilityOutcome.AMBIGUOUS_IDENTITY,
            eligible=False,
            reason=facts.reason or "Registry identity is ambiguous",
        )
    if facts.resolution_status == ExecutionResolutionOutcome.UNKNOWN:
        return ExecutionEligibility(
            outcome=ExecutionEligibilityOutcome.UNKNOWN_IDENTITY,
            eligible=False,
            reason=facts.reason or "Registry identity is unknown",
        )
    if (
        facts.resolution_status == ExecutionResolutionOutcome.NOT_TRADABLE
        or facts.tradable is False
    ):
        return ExecutionEligibility(
            outcome=ExecutionEligibilityOutcome.NOT_TRADABLE,
            eligible=False,
            reason=facts.reason or "Registry marks the instrument as non-tradable",
            registry_failure=bool(facts.resolution_error),
        )
    if (
        facts.resolution_status == ExecutionResolutionOutcome.RESOLVED
        and facts.execution_role == ExecutionRole.TRADABLE
        and facts.instrument_form != ExecutionInstrumentForm.UNKNOWN
    ):
        return ExecutionEligibility(
            outcome=ExecutionEligibilityOutcome.ELIGIBLE,
            eligible=True,
            reason="Registry identity is resolved and tradable",
        )
    return ExecutionEligibility(
        outcome=ExecutionEligibilityOutcome.UNKNOWN_IDENTITY,
        eligible=False,
        reason=facts.reason or "Registry facts do not establish execution eligibility",
    )


def consult_execution_eligibility_shadow(
    actions: Sequence[ShadowExecutionAction],
    facts_by_symbol: Mapping[str, ExecutionInstrumentFacts],
    *,
    legacy_path: str,
    logger: logging.Logger,
) -> Tuple[ExecutionEligibilityTelemetry, ...]:
    """Log shadow findings without mutating or rejecting the legacy actions.

    The function is deliberately exception-contained.  A malformed action or
    logging failure cannot escape into an optimizer, plan, or transaction path.
    Returned telemetry exists for focused verification and in-process callers;
    production boundaries ignore it.
    """

    records: list[ExecutionEligibilityTelemetry] = []
    cutover_mode = get_execution_eligibility_cutover_mode()
    for action in actions:
        try:
            facts = facts_by_symbol.get(action.requested_symbol)
            if facts is None:
                facts = ExecutionInstrumentFacts(
                    query=action.requested_symbol,
                    resolution_status=ExecutionResolutionOutcome.UNKNOWN,
                    instrument_form=ExecutionInstrumentForm.UNKNOWN,
                    execution_role=ExecutionRole.UNKNOWN,
                    reason="No ExecutionInstrumentFacts supplied at shadow boundary",
                )
            eligibility = evaluate_execution_eligibility(facts)
            telemetry = ExecutionEligibilityTelemetry(
                requested_symbol=action.requested_symbol,
                canonical_symbol=facts.canonical_symbol,
                registry_asset_id=(int(facts.asset_id) if facts.asset_id is not None else None),
                resolution_status=facts.resolution_status,
                execution_role=facts.execution_role,
                instrument_form=facts.instrument_form,
                legacy_action=action.legacy_action,
                legacy_path=legacy_path,
                shadow_eligibility=eligibility.outcome,
                legacy_permitted=True,
                disagreement=not eligibility.eligible,
                registry_failure=eligibility.registry_failure,
                cutover_mode=cutover_mode.value,
                classification_agreement=action.classification_agreement,
                registry_error=facts.resolution_error,
                reason=eligibility.reason,
                provenance=facts.provenance,
            )
            records.append(telemetry)
            agreement_label = (
                "UNKNOWN"
                if action.classification_agreement is None
                else ("AGREE" if action.classification_agreement else "DISAGREE")
            )
            metric = record_execution_eligibility_observation(
                EligibilityObservation(
                    boundary=legacy_path,
                    eligibility_outcome=eligibility.outcome.value,
                    resolution_status=facts.resolution_status.value,
                    instrument_form=facts.instrument_form.value,
                    execution_role=facts.execution_role.value,
                    cutover_mode=cutover_mode.value,
                    registry_failure=eligibility.registry_failure,
                    classification_agreement=agreement_label,
                )
            )
            logger.debug(
                "execution eligibility metric path=%s outcome=%s mode=%s count=%d",
                legacy_path,
                eligibility.outcome.value,
                cutover_mode.value,
                metric.count,
                extra={"execution_eligibility_metric": metric.to_log_dict()},
            )
            if metric.emit_diagnostic_sample:
                log_method = logger.warning if telemetry.disagreement else logger.debug
                log_method(
                    "execution eligibility shadow path=%s symbol=%r action=%s outcome=%s",
                    legacy_path,
                    action.requested_symbol,
                    action.legacy_action,
                    eligibility.outcome.value,
                    extra={"execution_eligibility": telemetry.to_log_dict()},
                )
        except Exception:
            try:
                logger.exception(
                    "execution eligibility shadow consultation failed path=%s symbol=%r",
                    legacy_path,
                    getattr(action, "requested_symbol", None),
                )
            except Exception:
                pass
    return tuple(records)
