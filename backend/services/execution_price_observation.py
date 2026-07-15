"""Immutable price evidence and pure freshness assessment (M32.3C).

This module records what a caller or provider supplied.  It does not fetch
market data, resolve Registry identity, select a price for execution, quote a
fee, or read a clock.  In particular, provider receipt time and cache-write
time never become an exchange observation time.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, Mapping, Sequence


_OBSERVATION_CONTRACT_VERSION = "1"
_FRESHNESS_CONTRACT_VERSION = "1"


class PriceKind(str, Enum):
    MARKET_LAST = "MARKET_LAST"
    MARKET_CLOSE = "MARKET_CLOSE"
    MARKET_OPEN = "MARKET_OPEN"
    MARKET_HIGH = "MARKET_HIGH"
    MARKET_LOW = "MARKET_LOW"
    USER_EXECUTION_TERM = "USER_EXECUTION_TERM"
    AVG_COST_REFERENCE = "AVG_COST_REFERENCE"
    ESTIMATED = "ESTIMATED"
    UNKNOWN = "UNKNOWN"
    # Transitional M32.3B name. It is an alias, not another canonical value.
    MARKET_REFERENCE = "MARKET_LAST"


class PriceSource(str, Enum):
    YAHOO_CHART = "YAHOO_CHART"
    YAHOO_FINANCE = "YAHOO_FINANCE"
    YAHOO_HISTORY = "YAHOO_HISTORY"
    USER_ENTERED = "USER_ENTERED"
    PORTFOLIO_AVG_COST = "PORTFOLIO_AVG_COST"
    CALLER_SUPPLIED = "CALLER_SUPPLIED"
    UNKNOWN = "UNKNOWN"


class MarketSession(str, Enum):
    REGULAR = "REGULAR"
    PRE_MARKET = "PRE_MARKET"
    AFTER_HOURS = "AFTER_HOURS"
    CLOSED = "CLOSED"
    UNKNOWN = "UNKNOWN"


class PriceTimestampQuality(str, Enum):
    EXCHANGE_OBSERVED = "EXCHANGE_OBSERVED"
    PROVIDER_BAR = "PROVIDER_BAR"
    RECEIPT_ONLY = "RECEIPT_ONLY"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"


class PriceObservationQuality(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    REFERENCE_ONLY = "REFERENCE_ONLY"
    UNKNOWN = "UNKNOWN"


class PriceFreshnessStatus(str, Enum):
    UNKNOWN = "UNKNOWN"
    CURRENT = "CURRENT"
    STALE = "STALE"
    EXPIRED = "EXPIRED"
    SESSION_CLOSED = "SESSION_CLOSED"
    PRICE_TIMESTAMP_MISSING = "PRICE_TIMESTAMP_MISSING"
    SESSION_UNKNOWN = "SESSION_UNKNOWN"
    CURRENCY_UNKNOWN = "CURRENCY_UNKNOWN"


_MARKET_PRICE_KINDS = frozenset(
    {
        PriceKind.MARKET_LAST,
        PriceKind.MARKET_CLOSE,
        PriceKind.MARKET_OPEN,
        PriceKind.MARKET_HIGH,
        PriceKind.MARKET_LOW,
        # Compatibility only for already-built M32.3B request fixtures.
        PriceKind.MARKET_REFERENCE,
    }
)


@dataclass(frozen=True)
class ExecutionPriceObservation:
    """One immutable record of supplied price evidence, not a price decision."""

    contract_version: str
    observation_ref: str
    requested_symbol: str
    asset_id: int | None
    canonical_symbol: str | None
    currency: str | None
    observed_price: Decimal | None
    price_type: PriceKind
    source: PriceSource
    provider: str | None
    provider_version: str | None
    observed_at: datetime | None
    received_at: datetime | None
    cached_at: datetime | None
    market_session: MarketSession
    exchange_timezone: str | None
    delay: timedelta | None
    timestamp_quality: PriceTimestampQuality
    quality: PriceObservationQuality
    warnings: tuple[str, ...]
    provenance: tuple[str, ...]

    @property
    def is_market_observation(self) -> bool:
        return self.price_type in _MARKET_PRICE_KINDS

    @property
    def satisfies_execution_price_evidence(self) -> bool:
        """Structural evidence only; no execution pricing policy is applied."""

        return bool(
            self.is_market_observation
            and isinstance(self.observed_price, Decimal)
            and self.observed_price > 0
            and self.observed_at is not None
            and self.received_at is not None
            and self.currency
            and self.market_session != MarketSession.UNKNOWN
        )


@dataclass(frozen=True)
class PriceFreshnessPolicy:
    """Versioned age/session prerequisites supplied to the pure assessor."""

    policy_version: str
    current_for: timedelta
    stale_for: timedelta
    require_currency: bool = True
    require_known_session: bool = True
    closed_session_is_current: bool = False


@dataclass(frozen=True)
class PriceFreshnessAssessment:
    """A time-specific assessment; freshness is never stored on observation."""

    contract_version: str
    assessment_ref: str
    observation_ref: str
    policy_version: str
    assessed_at: datetime
    status: PriceFreshnessStatus
    age: timedelta | None
    reason: str
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class ShadowPriceComparison:
    requested_symbol: str
    legacy_price: Decimal | None
    observation: ExecutionPriceObservation
    freshness: PriceFreshnessAssessment

    def to_log_dict(self) -> dict[str, object]:
        return {
            "requested_symbol": self.requested_symbol,
            "legacy_price": _decimal_text(self.legacy_price),
            "observed_price": _decimal_text(self.observation.observed_price),
            "price_kind": self.observation.price_type.value,
            "timestamp_quality": self.observation.timestamp_quality.value,
            "freshness_status": self.freshness.status.value,
            "provider": self.observation.provider,
        }


@dataclass(frozen=True)
class PriceObservationShadowProjection:
    comparisons: tuple[ShadowPriceComparison, ...]

    @property
    def evidence_by_symbol(
        self,
    ) -> dict[str, tuple[ExecutionPriceObservation, PriceFreshnessAssessment]]:
        return {
            comparison.requested_symbol: (
                comparison.observation,
                comparison.freshness,
            )
            for comparison in self.comparisons
        }


DEFAULT_SHADOW_FRESHNESS_POLICY = PriceFreshnessPolicy(
    policy_version="m32.3c-shadow-v1",
    current_for=timedelta(minutes=5),
    stale_for=timedelta(minutes=15),
)


def build_price_observation(
    *,
    requested_symbol: str,
    asset_id: int | None,
    canonical_symbol: str | None,
    observed_price: Decimal | None,
    price_type: PriceKind,
    source: PriceSource,
    currency: str | None = None,
    provider: str | None = None,
    provider_version: str | None = None,
    observed_at: datetime | None = None,
    received_at: datetime | None = None,
    cached_at: datetime | None = None,
    market_session: MarketSession = MarketSession.UNKNOWN,
    exchange_timezone: str | None = None,
    delay: timedelta | None = None,
    timestamp_quality: PriceTimestampQuality | None = None,
    quality: PriceObservationQuality | None = None,
    warnings: Sequence[str] = (),
    provenance: Sequence[str] = (),
) -> ExecutionPriceObservation:
    """Build deterministic evidence from supplied fields without enrichment."""

    timestamp_quality = timestamp_quality or _timestamp_quality(observed_at, received_at)
    quality = quality or _observation_quality(
        observed_price,
        price_type,
        currency,
        observed_at,
        received_at,
        market_session,
    )
    normalized_warnings = _unique(warnings)
    normalized_provenance = _unique(provenance)
    parts = (
        _OBSERVATION_CONTRACT_VERSION,
        requested_symbol,
        str(asset_id or ""),
        canonical_symbol or "",
        currency or "",
        _decimal_text(observed_price),
        price_type.value,
        source.value,
        provider or "",
        provider_version or "",
        _datetime_text(observed_at),
        _datetime_text(received_at),
        _datetime_text(cached_at),
        market_session.value,
        exchange_timezone or "",
        _timedelta_text(delay),
        timestamp_quality.value,
        quality.value,
        *normalized_warnings,
        *normalized_provenance,
    )
    return ExecutionPriceObservation(
        contract_version=_OBSERVATION_CONTRACT_VERSION,
        observation_ref=_ref("pxo", parts),
        requested_symbol=requested_symbol,
        asset_id=asset_id,
        canonical_symbol=canonical_symbol,
        currency=_clean_text(currency),
        observed_price=observed_price,
        price_type=price_type,
        source=source,
        provider=_clean_text(provider),
        provider_version=_clean_text(provider_version),
        observed_at=observed_at,
        received_at=received_at,
        cached_at=cached_at,
        market_session=market_session,
        exchange_timezone=_clean_text(exchange_timezone),
        delay=delay,
        timestamp_quality=timestamp_quality,
        quality=quality,
        warnings=normalized_warnings,
        provenance=normalized_provenance,
    )


def assess_price_freshness(
    observation: ExecutionPriceObservation,
    *,
    assessed_at: datetime,
    policy: PriceFreshnessPolicy,
) -> PriceFreshnessAssessment:
    """Assess supplied timestamps only.  This function never reads a clock."""

    age: timedelta | None = None
    warnings: tuple[str, ...] = ()
    if not observation.is_market_observation:
        status = PriceFreshnessStatus.UNKNOWN
        reason = f"{observation.price_type.value} is not market-price evidence"
    elif observation.observed_price is None or observation.observed_price <= 0:
        status = PriceFreshnessStatus.UNKNOWN
        reason = "observed market price is absent or non-positive"
    elif policy.require_currency and not observation.currency:
        status = PriceFreshnessStatus.CURRENCY_UNKNOWN
        reason = "price currency is absent"
    elif observation.observed_at is None:
        status = PriceFreshnessStatus.PRICE_TIMESTAMP_MISSING
        reason = "provider observation time is absent"
    elif policy.require_known_session and observation.market_session == MarketSession.UNKNOWN:
        status = PriceFreshnessStatus.SESSION_UNKNOWN
        reason = "market session is unknown"
    elif observation.market_session == MarketSession.CLOSED and not policy.closed_session_is_current:
        status = PriceFreshnessStatus.SESSION_CLOSED
        reason = "market session is closed"
    else:
        try:
            age = assessed_at - observation.observed_at
        except (TypeError, ValueError):
            status = PriceFreshnessStatus.UNKNOWN
            reason = "assessment and observation timestamps are not comparable"
        else:
            if age < timedelta(0):
                status = PriceFreshnessStatus.UNKNOWN
                reason = "observation time is after assessment time"
                warnings = ("negative price age",)
            elif age <= policy.current_for:
                status = PriceFreshnessStatus.CURRENT
                reason = "price age is within the current threshold"
            elif age <= policy.stale_for:
                status = PriceFreshnessStatus.STALE
                reason = "price age exceeds current threshold"
            else:
                status = PriceFreshnessStatus.EXPIRED
                reason = "price age exceeds stale threshold"

    parts = (
        _FRESHNESS_CONTRACT_VERSION,
        observation.observation_ref,
        policy.policy_version,
        assessed_at.isoformat(),
        status.value,
        _timedelta_text(age),
        reason,
        *warnings,
    )
    return PriceFreshnessAssessment(
        contract_version=_FRESHNESS_CONTRACT_VERSION,
        assessment_ref=_ref("pxf", parts),
        observation_ref=observation.observation_ref,
        policy_version=policy.policy_version,
        assessed_at=assessed_at,
        status=status,
        age=age,
        reason=reason,
        warnings=warnings,
    )


def adapt_yahoo_chart_quote(
    payload: Mapping[str, Any],
    *,
    requested_symbol: str,
    asset_id: int | None = None,
    canonical_symbol: str | None = None,
    cached_at: datetime | None = None,
    provider_version: str | None = None,
) -> ExecutionPriceObservation:
    return _adapt_current_quote(
        payload,
        requested_symbol=requested_symbol,
        asset_id=asset_id,
        canonical_symbol=canonical_symbol,
        cached_at=cached_at,
        source=PriceSource.YAHOO_CHART,
        provider="yahoo_chart",
        provider_version=provider_version,
        price_type=PriceKind.MARKET_LAST,
    )


def adapt_yahoo_finance_quote(
    payload: Mapping[str, Any],
    *,
    requested_symbol: str,
    asset_id: int | None = None,
    canonical_symbol: str | None = None,
    cached_at: datetime | None = None,
    provider_version: str | None = None,
) -> ExecutionPriceObservation:
    return _adapt_current_quote(
        payload,
        requested_symbol=requested_symbol,
        asset_id=asset_id,
        canonical_symbol=canonical_symbol,
        cached_at=cached_at,
        source=PriceSource.YAHOO_FINANCE,
        provider="yahoo_finance",
        provider_version=provider_version,
        # YahooProvider.get_quote reads the most recent history Close.
        price_type=PriceKind.MARKET_CLOSE,
    )


def adapt_yahoo_history_bar(
    *,
    requested_symbol: str,
    price: Decimal | None,
    price_type: PriceKind,
    observed_at: datetime | None,
    received_at: datetime | None,
    asset_id: int | None = None,
    canonical_symbol: str | None = None,
    currency: str | None = None,
    cached_at: datetime | None = None,
    provider_version: str | None = None,
    market_session: MarketSession = MarketSession.UNKNOWN,
    exchange_timezone: str | None = None,
    provenance: Sequence[str] = (),
) -> ExecutionPriceObservation:
    """Translate one already-selected provider bar; do not select a bar."""

    return build_price_observation(
        requested_symbol=requested_symbol,
        asset_id=asset_id,
        canonical_symbol=canonical_symbol,
        observed_price=price,
        price_type=price_type,
        source=PriceSource.YAHOO_HISTORY,
        currency=currency,
        provider="yahoo_history_dataframe",
        provider_version=provider_version,
        observed_at=observed_at,
        received_at=received_at,
        cached_at=cached_at,
        market_session=market_session,
        exchange_timezone=exchange_timezone,
        timestamp_quality=(
            PriceTimestampQuality.PROVIDER_BAR
            if observed_at is not None
            else PriceTimestampQuality.MISSING
        ),
        provenance=("provider DataFrame bar supplied by caller", *provenance),
    )


def adapt_avg_cost_reference(
    *,
    requested_symbol: str,
    avg_cost: Decimal | None,
    asset_id: int | None = None,
    canonical_symbol: str | None = None,
    currency: str | None = None,
    provenance: Sequence[str] = (),
) -> ExecutionPriceObservation:
    """Record accounting cost basis as reference-only, never market evidence."""

    return build_price_observation(
        requested_symbol=requested_symbol,
        asset_id=asset_id,
        canonical_symbol=canonical_symbol,
        observed_price=avg_cost,
        price_type=PriceKind.AVG_COST_REFERENCE,
        source=PriceSource.PORTFOLIO_AVG_COST,
        currency=currency,
        quality=PriceObservationQuality.REFERENCE_ONLY,
        timestamp_quality=PriceTimestampQuality.MISSING,
        warnings=("average cost is accounting evidence, not a market observation",),
        provenance=("Portfolio Runtime average cost reference", *provenance),
    )


def adapt_user_execution_term(
    *,
    requested_symbol: str,
    entered_price: Decimal | None,
    currency: str | None,
    asset_id: int | None = None,
    canonical_symbol: str | None = None,
    provenance: Sequence[str] = (),
) -> ExecutionPriceObservation:
    return build_price_observation(
        requested_symbol=requested_symbol,
        asset_id=asset_id,
        canonical_symbol=canonical_symbol,
        observed_price=entered_price,
        price_type=PriceKind.USER_EXECUTION_TERM,
        source=PriceSource.USER_ENTERED,
        currency=currency,
        quality=PriceObservationQuality.REFERENCE_ONLY,
        timestamp_quality=PriceTimestampQuality.MISSING,
        warnings=("user execution term is not a market observation or fill",),
        provenance=("caller-supplied execution term", *provenance),
    )


def project_execution_plan_price_observations_shadow(
    buy_actions: Sequence[Any],
    funding_actions: Sequence[Any],
    facts_by_symbol: Mapping[str, Any],
    *,
    assessed_at: datetime,
    policy: PriceFreshnessPolicy = DEFAULT_SHADOW_FRESHNESS_POLICY,
) -> PriceObservationShadowProjection:
    """Describe legacy plan price evidence after the plan already exists."""

    comparisons: list[ShadowPriceComparison] = []
    for action in buy_actions:
        symbol = str(action.symbol)
        facts = facts_by_symbol.get(symbol)
        observation = build_price_observation(
            requested_symbol=symbol,
            asset_id=getattr(facts, "asset_id", None),
            canonical_symbol=getattr(facts, "canonical_symbol", None),
            observed_price=None,
            price_type=PriceKind.UNKNOWN,
            source=PriceSource.UNKNOWN,
            currency=None,
            warnings=("legacy BuyAction has amount but no unit price",),
            provenance=("legacy ExecutionPlanResult BuyAction",),
        )
        comparisons.append(
            ShadowPriceComparison(
                symbol,
                None,
                observation,
                assess_price_freshness(observation, assessed_at=assessed_at, policy=policy),
            )
        )
    for action in funding_actions:
        symbol = str(action.symbol)
        facts = facts_by_symbol.get(symbol)
        quantity = Decimal(str(action.current_shares)) * Decimal(str(action.release_pct))
        legacy_price = (
            Decimal(str(action.estimated_cash_release)) / quantity
            if quantity > 0
            else None
        )
        observation = adapt_avg_cost_reference(
            requested_symbol=symbol,
            avg_cost=legacy_price,
            asset_id=getattr(facts, "asset_id", None),
            canonical_symbol=getattr(facts, "canonical_symbol", None),
            currency=getattr(facts, "currency", None),
            provenance=("legacy plan implied price from average-cost funding arithmetic",),
        )
        comparisons.append(
            ShadowPriceComparison(
                symbol,
                legacy_price,
                observation,
                assess_price_freshness(observation, assessed_at=assessed_at, policy=policy),
            )
        )
    return PriceObservationShadowProjection(tuple(comparisons))


def _adapt_current_quote(
    payload: Mapping[str, Any],
    *,
    requested_symbol: str,
    asset_id: int | None,
    canonical_symbol: str | None,
    cached_at: datetime | None,
    source: PriceSource,
    provider: str,
    provider_version: str | None,
    price_type: PriceKind,
) -> ExecutionPriceObservation:
    observed_at = _parse_datetime(
        payload.get("observed_at")
        or payload.get("regular_market_time")
        or payload.get("regularMarketTime")
    )
    explicit_received = payload.get("received_at")
    received_at = _parse_datetime(
        explicit_received if explicit_received is not None else payload.get("last_updated")
    )
    warnings: list[str] = []
    if explicit_received is None and payload.get("last_updated") is not None:
        warnings.append("provider last_updated is fetch/receipt time, not observation time")
    if observed_at is None:
        warnings.append("provider quote DTO has no exchange observation timestamp")
    session = _market_session(payload.get("market_session") or payload.get("market_state"))
    delay_seconds = _decimal(payload.get("delay_seconds"))
    return build_price_observation(
        requested_symbol=requested_symbol,
        asset_id=asset_id,
        canonical_symbol=canonical_symbol,
        observed_price=_decimal(payload.get("current_price")),
        price_type=price_type,
        source=source,
        currency=_clean_text(payload.get("currency")),
        provider=provider,
        provider_version=provider_version,
        observed_at=observed_at,
        received_at=received_at,
        cached_at=cached_at,
        market_session=session,
        exchange_timezone=_clean_text(payload.get("exchange_timezone")),
        delay=(timedelta(seconds=float(delay_seconds)) if delay_seconds is not None else None),
        timestamp_quality=(
            PriceTimestampQuality.EXCHANGE_OBSERVED
            if observed_at is not None
            else PriceTimestampQuality.RECEIPT_ONLY
            if received_at is not None
            else PriceTimestampQuality.MISSING
        ),
        warnings=warnings,
        provenance=(f"services.market_data {provider} quote DTO",),
    )


def _timestamp_quality(
    observed_at: datetime | None,
    received_at: datetime | None,
) -> PriceTimestampQuality:
    if observed_at is not None:
        return PriceTimestampQuality.EXCHANGE_OBSERVED
    if received_at is not None:
        return PriceTimestampQuality.RECEIPT_ONLY
    return PriceTimestampQuality.MISSING


def _observation_quality(
    price: Decimal | None,
    price_type: PriceKind,
    currency: str | None,
    observed_at: datetime | None,
    received_at: datetime | None,
    session: MarketSession,
) -> PriceObservationQuality:
    if price_type in {PriceKind.AVG_COST_REFERENCE, PriceKind.USER_EXECUTION_TERM, PriceKind.ESTIMATED}:
        return PriceObservationQuality.REFERENCE_ONLY
    if price_type == PriceKind.UNKNOWN or price is None:
        return PriceObservationQuality.UNKNOWN
    if currency and observed_at is not None and received_at is not None and session != MarketSession.UNKNOWN:
        return PriceObservationQuality.COMPLETE
    return PriceObservationQuality.PARTIAL


def _market_session(value: Any) -> MarketSession:
    text = _clean_text(value)
    if text is None:
        return MarketSession.UNKNOWN
    mapping = {
        "REGULAR": MarketSession.REGULAR,
        "REGULAR_MARKET": MarketSession.REGULAR,
        "PRE": MarketSession.PRE_MARKET,
        "PRE_MARKET": MarketSession.PRE_MARKET,
        "PREPRE": MarketSession.PRE_MARKET,
        "POST": MarketSession.AFTER_HOURS,
        "AFTER_HOURS": MarketSession.AFTER_HOURS,
        "POSTPOST": MarketSession.AFTER_HOURS,
        "CLOSED": MarketSession.CLOSED,
    }
    return mapping.get(text.upper(), MarketSession.UNKNOWN)


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    text = _clean_text(value)
    if text is None:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


def _decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _unique(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values if str(value)))


def _ref(prefix: str, parts: Sequence[object]) -> str:
    payload = "|".join("" if part is None else str(part) for part in parts)
    return f"{prefix}_" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _decimal_text(value: Decimal | None) -> str | None:
    return format(value, "f") if isinstance(value, Decimal) else None


def _datetime_text(value: datetime | None) -> str:
    return value.isoformat() if value is not None else ""


def _timedelta_text(value: timedelta | None) -> str:
    return format(Decimal(str(value.total_seconds())), "f") if value is not None else ""


__all__ = [
    "DEFAULT_SHADOW_FRESHNESS_POLICY",
    "ExecutionPriceObservation",
    "MarketSession",
    "PriceFreshnessAssessment",
    "PriceFreshnessPolicy",
    "PriceFreshnessStatus",
    "PriceKind",
    "PriceObservationQuality",
    "PriceObservationShadowProjection",
    "PriceSource",
    "PriceTimestampQuality",
    "ShadowPriceComparison",
    "adapt_avg_cost_reference",
    "adapt_user_execution_term",
    "adapt_yahoo_chart_quote",
    "adapt_yahoo_finance_quote",
    "adapt_yahoo_history_bar",
    "assess_price_freshness",
    "build_price_observation",
    "project_execution_plan_price_observations_shadow",
]
