"""M32.3E2 private, non-authoritative live-evidence execution-plan shadow.

The module has two deliberately separate halves: pure adapters/evaluation
helpers, and a small bounded provider orchestration function.  It never
resolves Registry facts, mutates a plan, reads a database, or chooses a market
provider.  ``execution_plan`` supplies already loaded facts, holdings, actions,
and the selected provider after its legacy result is final.
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping, Sequence

from services.broker_fees import TradeSide, quote_fee_for_instrument
from services.execution_eligibility import ExecutionEligibility
from services.execution_instrument_facts import ExecutionInstrumentFacts
from services.execution_policy import (
    ExecutionFreshnessPolicy,
    ExecutionPolicyBundle,
    ExecutionPolicyOutcome,
    PolicyEvaluation,
    ExecutionPricingPolicy,
    ExecutionQuantityPolicy,
    ExecutionQuoteLifecycle,
    ExecutionResidualPolicy,
    ExecutionSizingPolicy,
    PlanningCurrencyContext,
    accept_freshness_and_session,
    constrain_executable_quantity,
    derive_requested_quantity,
    normalize_policy_trade_input,
    select_execution_price,
)
from services.execution_price_observation import (
    ExecutionPriceObservation,
    MarketSession,
    PriceFreshnessAssessment,
    PriceFreshnessPolicy,
    PriceKind,
    PriceSource,
    assess_price_freshness,
    build_price_observation,
)
from services.execution_trade_leg import (
    ExecutionFundingRole,
    ExecutionTradeLeg,
    build_execution_trade_leg_from_policy_input,
)
from services.market_data.execution_quote import (
    ExecutionQuoteEnvelope,
    ExecutionQuoteEvidence,
    adapt_yahoo_finance_execution_quote,
)
from services.normalized_trade_input import (
    HoldingQuantitySnapshot,
    QuantityIntentSource,
)

__all__ = [
    "DEFAULT_LIVE_EVIDENCE_POLICY_BUNDLE",
    "DEFAULT_LIVE_EVIDENCE_FRESHNESS_POLICY",
    "ExecutionPlanShadowIntent",
    "RegistryCapabilityReadiness",
    "ShadowCanonicalPlanDiagnostic",
    "ShadowDiagnosticOutcome",
    "ShadowSymbolDiagnostic",
    "adapt_execution_quote_envelope_to_observation",
    "adapt_execution_plan_buy_intent",
    "adapt_execution_plan_funding_intent",
    "adapt_holding_quantity_snapshot",
    "assess_registry_capability_readiness",
    "collect_live_execution_quote_evidence",
    "project_live_execution_plan_shadow",
]


_MAX_PROVIDER_CALLS = 25
_MAX_PROVIDER_WORKERS = 5


DEFAULT_LIVE_EVIDENCE_FRESHNESS_POLICY = PriceFreshnessPolicy(
    policy_version="m32.3e2-shadow-v1",
    current_for=timedelta(minutes=5),
    stale_for=timedelta(minutes=15),
)
DEFAULT_LIVE_EVIDENCE_POLICY_BUNDLE = ExecutionPolicyBundle.create(
    pricing=ExecutionPricingPolicy(policy_version="m32.3e1-shadow-pricing-v1"),
    freshness=ExecutionFreshnessPolicy(
        policy_version="m32.3e1-shadow-freshness-v1",
        current_for=timedelta(minutes=5),
        assessment_policy_version=DEFAULT_LIVE_EVIDENCE_FRESHNESS_POLICY.policy_version,
    ),
    sizing=ExecutionSizingPolicy(policy_version="m32.3e1-shadow-sizing-v1"),
    quantity=ExecutionQuantityPolicy(policy_version="m32.3e1-shadow-quantity-v1"),
    residual=ExecutionResidualPolicy(policy_version="m32.3e1-shadow-residual-v1"),
    quote_lifecycle=ExecutionQuoteLifecycle(policy_version="m32.3e1-shadow-quote-v1"),
)


class ShadowDiagnosticOutcome(str, Enum):
    COMPLETE = "COMPLETE"
    DEFERRED = "DEFERRED"
    INCOMPLETE = "INCOMPLETE"
    EXCLUDED = "EXCLUDED"
    ERROR = "ERROR"


@dataclass(frozen=True)
class ExecutionPlanShadowIntent:
    recommendation_reference: str
    requested_symbol: str
    side: TradeSide
    quantity_source: QuantityIntentSource
    requested_value: Decimal | None
    holding_fraction: Decimal | None
    funding_role: ExecutionFundingRole
    provenance: tuple[str, ...]


@dataclass(frozen=True)
class RegistryCapabilityReadiness:
    facts_ready: bool
    lot_ready: bool
    fractional_ready: bool
    currency_ready: bool
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class ShadowSymbolDiagnostic:
    requested_symbol: str
    outcome: ShadowDiagnosticOutcome
    evidence_status: str
    envelope_ref: str | None
    observation_ref: str | None
    freshness_ref: str | None
    facts_status: str | None
    eligibility_outcome: str | None
    capability: RegistryCapabilityReadiness | None
    policy_outcome: str | None
    policy_reason: str | None
    fee_quote_ref: str | None
    fee_quote_status: str | None
    normalization_ref: str | None
    normalization_status: str | None
    trade_leg_ref: str | None
    residual_quantity: Decimal | None
    residual_value: Decimal | None
    warnings: tuple[str, ...]
    provenance: tuple[str, ...]


@dataclass(frozen=True)
class ShadowCanonicalPlanDiagnostic:
    contract_version: str
    plan_reference: str
    assessed_at: datetime
    policy_bundle_ref: str
    symbols: tuple[ShadowSymbolDiagnostic, ...]
    counts: tuple[tuple[str, int], ...]

    def low_cardinality_labels(self) -> dict[str, int]:
        """Aggregate-only operational labels: never include symbol or asset ID."""

        return dict(self.counts)


def adapt_execution_plan_buy_intent(action: Any, *, plan_reference: str) -> ExecutionPlanShadowIntent:
    """Preserve the legacy amount-only BUY request without deriving units."""

    return ExecutionPlanShadowIntent(
        recommendation_reference=f"{plan_reference}:BUY:{action.symbol}",
        requested_symbol=str(action.symbol),
        side=TradeSide.BUY,
        quantity_source=QuantityIntentSource.ALLOCATION_VALUE_AT_PRICE,
        requested_value=_decimal(getattr(action, "estimated_amount", None)),
        holding_fraction=None,
        funding_role=ExecutionFundingRole.DEPLOYMENT,
        provenance=("legacy ExecutionPlanResult BuyAction.estimated_amount",),
    )


def adapt_execution_plan_funding_intent(action: Any, *, plan_reference: str) -> ExecutionPlanShadowIntent:
    """Preserve the declared funding fraction; never reconstruct a new policy."""

    fraction = _decimal(getattr(action, "release_pct", None))
    source = (
        QuantityIntentSource.FULL_HOLDING_QUANTITY
        if fraction == Decimal("1")
        else QuantityIntentSource.HOLDING_FRACTION
    )
    return ExecutionPlanShadowIntent(
        recommendation_reference=f"{plan_reference}:{action.action}:{action.symbol}",
        requested_symbol=str(action.symbol),
        side=TradeSide.SELL,
        quantity_source=source,
        requested_value=None,
        holding_fraction=fraction if source == QuantityIntentSource.HOLDING_FRACTION else None,
        funding_role=ExecutionFundingRole.FUNDING_SOURCE,
        provenance=(
            "legacy ExecutionPlanResult active funding action",
            "legacy FundingAction.current_shares/release_pct retained for comparison",
        ),
    )


def adapt_holding_quantity_snapshot(
    item: Any,
    *,
    captured_at: datetime,
    source: str = "PortfolioItem loaded by execution_plan",
) -> HoldingQuantitySnapshot:
    """Make a frozen holding snapshot from an already-loaded PortfolioItem."""

    return HoldingQuantitySnapshot(
        quantity=_decimal(getattr(item, "shares", None)) or Decimal("0"),
        observed_at=captured_at,
        source=source,
        provenance=(f"PortfolioItem.symbol={getattr(item, 'symbol', '')}",),
    )


def assess_registry_capability_readiness(
    facts: ExecutionInstrumentFacts | None,
    eligibility: ExecutionEligibility | None,
    *,
    planning_currency: str = "THB",
) -> RegistryCapabilityReadiness:
    """Read-only readiness report; absent capabilities are never defaulted."""

    if facts is None or eligibility is None:
        return RegistryCapabilityReadiness(False, False, False, False, ("Registry facts or eligibility are absent",))
    warnings: list[str] = []
    facts_ready = eligibility.eligible and not facts.resolution_error
    if not facts_ready:
        warnings.append(facts.reason or "Registry facts are not eligible")
    lot_ready = isinstance(facts.lot_size, int) and not isinstance(facts.lot_size, bool) and facts.lot_size > 0
    if not lot_ready:
        warnings.append("Registry lot_size must be a positive integer")
    fractional_ready = facts.fractional_support is False
    if not fractional_ready:
        warnings.append("Registry fractional_support must be explicitly False for v1 shadow policy")
    currency_ready = facts.currency == planning_currency
    if not currency_ready:
        warnings.append("Registry listing currency does not match transitional planning currency")
    return RegistryCapabilityReadiness(facts_ready, lot_ready, fractional_ready, currency_ready, tuple(warnings))


def adapt_execution_quote_envelope_to_observation(
    envelope: ExecutionQuoteEnvelope | None,
    *,
    requested_symbol: str,
    facts: ExecutionInstrumentFacts | None,
    error: str | None = None,
) -> ExecutionPriceObservation:
    """Purely attach pre-resolved Registry identity to provider evidence."""

    if envelope is None:
        return build_price_observation(
            requested_symbol=requested_symbol,
            asset_id=(int(facts.asset_id) if facts and facts.asset_id is not None else None),
            canonical_symbol=facts.canonical_symbol if facts else None,
            observed_price=None,
            price_type=PriceKind.UNKNOWN,
            source=PriceSource.UNKNOWN,
            currency=None,
            warnings=((error or "live provider/cache quote evidence is unavailable"),),
            provenance=("M32.3E2 missing live quote evidence",),
        )
    source = {
        "yahoo_chart": PriceSource.YAHOO_CHART,
        "yahoo_finance": PriceSource.YAHOO_FINANCE,
    }.get(envelope.provider_id, PriceSource.UNKNOWN)
    return build_price_observation(
        requested_symbol=requested_symbol,
        asset_id=(int(facts.asset_id) if facts and facts.asset_id is not None else None),
        canonical_symbol=facts.canonical_symbol if facts else None,
        observed_price=envelope.price,
        price_type=envelope.price_kind,
        source=source,
        currency=envelope.currency,
        provider=envelope.provider_id,
        provider_version=envelope.provider_version,
        observed_at=envelope.observed_at,
        received_at=envelope.received_at,
        cached_at=envelope.cached_at,
        market_session=envelope.market_session,
        exchange_timezone=envelope.exchange_timezone,
        delay=envelope.delay,
        warnings=envelope.warnings,
        provenance=envelope.provenance + (f"ExecutionQuoteEnvelope={envelope.envelope_ref}",),
    )


def collect_live_execution_quote_evidence(
    symbols: Sequence[str],
    *,
    provider: Any,
    received_at: datetime,
    max_symbols: int = _MAX_PROVIDER_CALLS,
    cache_evidence_by_symbol: Mapping[str, ExecutionQuoteEvidence] | None = None,
) -> dict[str, ExecutionQuoteEvidence]:
    """Bounded provider orchestration with per-symbol failure containment.

    A provider with the additive batch method is invoked exactly once.  Older
    providers are called through a fixed-size executor; each unique symbol has
    at most one attempt and no result is retried or substituted.
    """

    unique = tuple(dict.fromkeys(str(symbol) for symbol in symbols))
    cache_evidence_by_symbol = cache_evidence_by_symbol or {}
    results: dict[str, ExecutionQuoteEvidence] = {
        symbol: cache_evidence_by_symbol[symbol]
        for symbol in unique
        if symbol in cache_evidence_by_symbol
    }
    uncached = tuple(symbol for symbol in unique if symbol not in results)
    selected = uncached[:max_symbols]
    for symbol in uncached[max_symbols:]:
        results[symbol] = ExecutionQuoteEvidence(symbol, None, "provider call bound exceeded", "BOUND")
    if not selected:
        return results
    try:
        batch = getattr(provider, "get_execution_quote_envelopes", None)
        if callable(batch):
            raw = batch(list(selected))
            for symbol in selected:
                envelope = raw.get(symbol) if raw else None
                results[symbol] = ExecutionQuoteEvidence(
                    symbol, envelope,
                    None if envelope is not None else "provider returned no execution quote evidence",
                )
            return results
    except Exception as exc:
        return {
            **results,
            **{symbol: ExecutionQuoteEvidence(symbol, None, f"provider batch failure: {type(exc).__name__}") for symbol in selected},
        }

    def one(symbol: str) -> ExecutionQuoteEvidence:
        try:
            envelope_method = getattr(provider, "get_execution_quote_envelope", None)
            if callable(envelope_method):
                envelope = envelope_method(symbol)
            else:
                payload = provider.get_quote(symbol)
                envelope = adapt_yahoo_finance_execution_quote(
                    payload,
                    requested_symbol=symbol,
                    provider_symbol=symbol,
                    received_at=received_at,
                )
            return ExecutionQuoteEvidence(symbol, envelope, None if envelope else "provider returned no execution quote evidence")
        except Exception as exc:
            return ExecutionQuoteEvidence(symbol, None, f"provider failure: {type(exc).__name__}")

    with ThreadPoolExecutor(max_workers=min(_MAX_PROVIDER_WORKERS, len(selected))) as executor:
        futures = {executor.submit(one, symbol): symbol for symbol in selected}
        for future in as_completed(futures):
            symbol = futures[future]
            try:
                results[symbol] = future.result()
            except Exception as exc:  # executor-level defensive isolation
                results[symbol] = ExecutionQuoteEvidence(symbol, None, f"provider worker failure: {type(exc).__name__}")
    return results


def project_live_execution_plan_shadow(
    *,
    plan_reference: str,
    buy_actions: Sequence[Any],
    funding_actions: Sequence[Any],
    holdings_by_symbol: Mapping[str, Any],
    facts_by_symbol: Mapping[str, ExecutionInstrumentFacts],
    eligibility_by_symbol: Mapping[str, ExecutionEligibility],
    provider: Any,
    assessed_at: datetime,
    policy_bundle: ExecutionPolicyBundle = DEFAULT_LIVE_EVIDENCE_POLICY_BUNDLE,
    freshness_policy: PriceFreshnessPolicy = DEFAULT_LIVE_EVIDENCE_FRESHNESS_POLICY,
    cache_evidence_by_symbol: Mapping[str, ExecutionQuoteEvidence] | None = None,
) -> ShadowCanonicalPlanDiagnostic:
    """Run the E2 private shadow after an immutable legacy plan is complete."""

    intents = tuple(
        [adapt_execution_plan_buy_intent(action, plan_reference=plan_reference) for action in buy_actions]
        + [adapt_execution_plan_funding_intent(action, plan_reference=plan_reference) for action in funding_actions]
    )
    evidence = collect_live_execution_quote_evidence(
        [intent.requested_symbol for intent in intents], provider=provider, received_at=assessed_at,
        cache_evidence_by_symbol=cache_evidence_by_symbol,
    )
    planning_currency = PlanningCurrencyContext.thb_transitional(
        source="M32.3E2 private execution-plan shadow",
    )
    diagnostics: list[ShadowSymbolDiagnostic] = []
    for intent in intents:
        facts = facts_by_symbol.get(intent.requested_symbol)
        eligibility = eligibility_by_symbol.get(intent.requested_symbol)
        quote_evidence = evidence.get(intent.requested_symbol)
        envelope = quote_evidence.envelope if quote_evidence else None
        observation = adapt_execution_quote_envelope_to_observation(
            envelope,
            requested_symbol=intent.requested_symbol,
            facts=facts,
            error=quote_evidence.error if quote_evidence else "quote evidence is absent",
        )
        assessment = assess_price_freshness(
            observation, assessed_at=assessed_at, policy=freshness_policy,
        )
        capability = assess_registry_capability_readiness(facts, eligibility)
        holding = None
        if intent.side == TradeSide.SELL:
            item = holdings_by_symbol.get(intent.requested_symbol)
            if item is not None:
                holding = adapt_holding_quantity_snapshot(item, captured_at=assessed_at)
        try:
            diagnostic = _evaluate_intent(
                intent=intent,
                facts=facts,
                eligibility=eligibility,
                observation=observation,
                assessment=assessment,
                capability=capability,
                holding=holding,
                planning_currency=planning_currency,
                policy_bundle=policy_bundle,
                assessed_at=assessed_at,
                evidence_status=("AVAILABLE" if envelope is not None else "MISSING"),
                envelope_ref=envelope.envelope_ref if envelope else None,
            )
        except Exception as exc:  # one malformed evidence record must never abort the plan
            diagnostic = ShadowSymbolDiagnostic(
                requested_symbol=intent.requested_symbol,
                outcome=ShadowDiagnosticOutcome.ERROR,
                evidence_status="ERROR",
                envelope_ref=envelope.envelope_ref if envelope else None,
                observation_ref=observation.observation_ref,
                freshness_ref=assessment.assessment_ref,
                facts_status=facts.resolution_status.value if facts else None,
                eligibility_outcome=eligibility.outcome.value if eligibility else None,
                capability=capability,
                policy_outcome=None,
                policy_reason=type(exc).__name__,
                fee_quote_ref=None,
                fee_quote_status=None,
                normalization_ref=None,
                normalization_status=None,
                trade_leg_ref=None,
                residual_quantity=None,
                residual_value=None,
                warnings=(f"M32.3E2 shadow evaluation failure: {type(exc).__name__}",),
                provenance=("M32.3E2 exception-contained per-symbol shadow",),
            )
        diagnostics.append(diagnostic)
    counts: dict[str, int] = {}
    for item in diagnostics:
        counts[item.outcome.value] = counts.get(item.outcome.value, 0) + 1
    return ShadowCanonicalPlanDiagnostic(
        contract_version="1",
        plan_reference=plan_reference,
        assessed_at=assessed_at,
        policy_bundle_ref=policy_bundle.bundle_ref,
        symbols=tuple(diagnostics),
        counts=tuple(sorted(counts.items())),
    )


def _evaluate_intent(
    *,
    intent: ExecutionPlanShadowIntent,
    facts: ExecutionInstrumentFacts | None,
    eligibility: ExecutionEligibility | None,
    observation: ExecutionPriceObservation,
    assessment: PriceFreshnessAssessment,
    capability: RegistryCapabilityReadiness,
    holding: HoldingQuantitySnapshot | None,
    planning_currency: PlanningCurrencyContext,
    policy_bundle: ExecutionPolicyBundle,
    assessed_at: datetime,
    evidence_status: str,
    envelope_ref: str | None,
) -> ShadowSymbolDiagnostic:
    if facts is None or eligibility is None:
        return _incomplete_diagnostic(intent, observation, assessment, capability, evidence_status, envelope_ref,
            "Registry facts/eligibility are unavailable", facts, eligibility)
    if facts.resolution_error:
        return _incomplete_diagnostic(intent, observation, assessment, capability, evidence_status, envelope_ref,
            "Registry facts resolution failed", facts, eligibility)
    if not capability.lot_ready or not capability.fractional_ready or not capability.currency_ready:
        return _incomplete_diagnostic(intent, observation, assessment, capability, evidence_status, envelope_ref,
            "Registry capability readiness is incomplete", facts, eligibility)
    price = select_execution_price((observation,), facts=facts, planning_currency=planning_currency,
        policy=policy_bundle.pricing)
    if not price.evaluation.ready or price.observation is None:
        return _policy_diagnostic(intent, observation, assessment, capability, evidence_status, envelope_ref,
            price.evaluation, None, None, None, facts, eligibility)
    freshness = accept_freshness_and_session(price.observation, assessment, policy=policy_bundle.freshness)
    if not freshness.ready:
        return _policy_diagnostic(intent, observation, assessment, capability, evidence_status, envelope_ref,
            freshness, None, None, None, facts, eligibility)
    if not eligibility.eligible:
        return _policy_diagnostic(intent, observation, assessment, capability, evidence_status, envelope_ref,
            PolicyEvaluation(ExecutionPolicyOutcome.EXCLUDED, None, eligibility.reason, "m32.3e2-eligibility"),
            None, None, None, facts, eligibility)
    derivation = derive_requested_quantity(
        side=intent.side,
        quantity_source=intent.quantity_source,
        requested_value=intent.requested_value,
        selected_price=price.observation.observed_price,
        holding_snapshot=holding,
        holding_fraction=intent.holding_fraction,
        policy=policy_bundle.sizing,
    )
    if not derivation.evaluation.ready:
        return _policy_diagnostic(intent, observation, assessment, capability, evidence_status, envelope_ref,
            derivation.evaluation, None, None, None, facts, eligibility)
    constraint = constrain_executable_quantity(
        requested_quantity=derivation.requested_quantity,
        quantity_source=intent.quantity_source,
        facts=facts,
        holding_snapshot=holding,
        policy=policy_bundle.quantity,
    )
    if not constraint.evaluation.ready:
        return _policy_diagnostic(intent, observation, assessment, capability, evidence_status, envelope_ref,
            constraint.evaluation, None, constraint, None, facts, eligibility)
    assert constraint.executable_quantity is not None and price.observation.observed_price is not None
    quote = quote_fee_for_instrument(
        facts,
        side=intent.side,
        quantity=constraint.executable_quantity,
        unit_price=price.observation.observed_price,
        quoted_at=assessed_at,
        effective_at=assessed_at,
    )
    produced = normalize_policy_trade_input(
        recommendation_reference=intent.recommendation_reference,
        requested_symbol=intent.requested_symbol,
        side=intent.side,
        quantity_source=intent.quantity_source,
        facts=facts,
        eligibility=eligibility,
        observations=(observation,),
        freshness_assessment=assessment,
        planning_currency=planning_currency,
        policy_bundle=policy_bundle,
        fee_quote=quote,
        requested_value=intent.requested_value,
        holding_snapshot=holding,
        holding_fraction=intent.holding_fraction,
        provenance=intent.provenance,
    )
    normalized = produced.normalized_input
    leg: ExecutionTradeLeg | None = None
    if normalized is not None and normalized.complete:
        leg = build_execution_trade_leg_from_policy_input(normalized, funding_role=intent.funding_role)
    return ShadowSymbolDiagnostic(
        requested_symbol=intent.requested_symbol,
        outcome=ShadowDiagnosticOutcome.COMPLETE if leg is not None else _outcome_from_policy(produced.evaluation.outcome),
        evidence_status=evidence_status,
        envelope_ref=envelope_ref,
        observation_ref=observation.observation_ref,
        freshness_ref=assessment.assessment_ref,
        facts_status=facts.resolution_status.value,
        eligibility_outcome=eligibility.outcome.value,
        capability=capability,
        policy_outcome=produced.evaluation.outcome.value,
        policy_reason=produced.evaluation.reason.value if produced.evaluation.reason else None,
        fee_quote_ref=quote.quote_ref,
        fee_quote_status=quote.status.value,
        normalization_ref=normalized.normalization_ref if normalized else None,
        normalization_status=normalized.status.value if normalized else None,
        trade_leg_ref=leg.leg_id if leg else None,
        residual_quantity=produced.residual.quantity_residual if produced.residual else None,
        residual_value=produced.residual.gross_value_residual if produced.residual else None,
        warnings=capability.warnings + observation.warnings + quote.warnings,
        provenance=intent.provenance + observation.provenance,
    )


def _incomplete_diagnostic(intent, observation, assessment, capability, evidence_status, envelope_ref, reason, facts, eligibility):
    return ShadowSymbolDiagnostic(intent.requested_symbol, ShadowDiagnosticOutcome.INCOMPLETE, evidence_status,
        envelope_ref, observation.observation_ref, assessment.assessment_ref,
        facts.resolution_status.value if facts else None, eligibility.outcome.value if eligibility else None, capability, "INCOMPLETE",
        reason, None, None, None, None, None, None, None, capability.warnings + (reason,), intent.provenance + observation.provenance)


def _policy_diagnostic(intent, observation, assessment, capability, evidence_status, envelope_ref, evaluation, quote, constraint, normalized, facts, eligibility):
    return ShadowSymbolDiagnostic(intent.requested_symbol, _outcome_from_policy(evaluation.outcome), evidence_status,
        envelope_ref, observation.observation_ref, assessment.assessment_ref,
        facts.resolution_status.value if facts else None, eligibility.outcome.value if eligibility else None, capability,
        evaluation.outcome.value, evaluation.reason.value if evaluation.reason else None,
        quote.quote_ref if quote else None, quote.status.value if quote else None,
        normalized.normalization_ref if normalized else None, normalized.status.value if normalized else None,
        None, constraint.requested_quantity - constraint.executable_quantity if constraint and constraint.requested_quantity is not None and constraint.executable_quantity is not None else None,
        None, capability.warnings + (evaluation.detail,), intent.provenance + observation.provenance)


def _outcome_from_policy(outcome: ExecutionPolicyOutcome) -> ShadowDiagnosticOutcome:
    return {
        ExecutionPolicyOutcome.READY: ShadowDiagnosticOutcome.INCOMPLETE,
        ExecutionPolicyOutcome.DEFERRED: ShadowDiagnosticOutcome.DEFERRED,
        ExecutionPolicyOutcome.DEFERRED_BELOW_EXECUTABLE_LOT: ShadowDiagnosticOutcome.DEFERRED,
        ExecutionPolicyOutcome.EXCLUDED: ShadowDiagnosticOutcome.EXCLUDED,
        ExecutionPolicyOutcome.ERROR: ShadowDiagnosticOutcome.ERROR,
    }.get(outcome, ShadowDiagnosticOutcome.INCOMPLETE)


def _decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None
