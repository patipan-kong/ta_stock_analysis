"""Immutable provider market-session evidence for the M32.3E3S2 shadow.

This Market Data-owned module records distinct provider claims without deciding
whether a price is acceptable for execution.  In particular, a price's labelled
observation session is not the provider response/venue state, and neither is a
canonical exchange-calendar assessment.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Mapping, Sequence

from services.execution_price_observation import MarketSession

__all__ = [
    "MarketSessionConfidence",
    "MarketSessionEvidence",
    "MarketTradingPeriod",
    "ObservationSessionBasis",
    "TradingPeriodInterval",
    "adapt_yahoo_chart_market_session_evidence",
    "build_market_session_evidence",
    "normalize_provider_reported_state",
]


_CONTRACT_VERSION = "1"
_MAX_RAW_STATE_LENGTH = 64


class ObservationSessionBasis(str, Enum):
    PROVIDER_REGULAR_MARKET_FIELDS = "PROVIDER_REGULAR_MARKET_FIELDS"
    PROVIDER_EXPLICIT_OBSERVATION_SESSION = "PROVIDER_EXPLICIT_OBSERVATION_SESSION"
    PROVIDER_STATE_ONLY = "PROVIDER_STATE_ONLY"
    NONE = "NONE"


class MarketSessionConfidence(str, Enum):
    EXPLICIT_PROVIDER_FIELD = "EXPLICIT_PROVIDER_FIELD"
    PROVIDER_SEMANTIC_PAIR = "PROVIDER_SEMANTIC_PAIR"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class TradingPeriodInterval:
    """One provider-supplied schedule interval, retained without calendar use."""

    start: datetime | None
    end: datetime | None

    def __post_init__(self) -> None:
        _require_aware("trading period start", self.start)
        _require_aware("trading period end", self.end)


@dataclass(frozen=True)
class MarketTradingPeriod:
    """Exact normalized provider schedule metadata, not a canonical calendar."""

    pre: TradingPeriodInterval | None
    regular: TradingPeriodInterval | None
    post: TradingPeriodInterval | None


@dataclass(frozen=True)
class MarketSessionEvidence:
    """Immutable provider session evidence attached to one quote envelope.

    ``observation_session_claim`` concerns the selected provider price at
    ``observation_at``.  ``provider_reported_state_normalized`` instead
    concerns an optional response-level provider state and never supplies the
    observation claim by implication.
    """

    contract_version: str
    session_evidence_ref: str
    envelope_ref: str | None
    requested_symbol: str
    provider_symbol: str | None
    provider_id: str
    provider_version: str | None
    observation_session_claim: MarketSession
    observation_session_basis: ObservationSessionBasis
    observation_at: datetime | None
    provider_reported_state_raw: str | None
    provider_reported_state_normalized: MarketSession
    provider_state_received_at: datetime | None
    provider_state_at: datetime | None
    current_trading_period: MarketTradingPeriod | None
    exchange_timezone: str | None
    gmt_offset: timedelta | None
    provider_delay: timedelta | None
    confidence: MarketSessionConfidence
    warnings: tuple[str, ...]
    provenance: tuple[str, ...]

    def __post_init__(self) -> None:
        if not _clean_text(self.envelope_ref):
            raise ValueError("envelope_ref is required")
        _require_aware("observation_at", self.observation_at)
        _require_aware("provider_state_received_at", self.provider_state_received_at)
        _require_aware("provider_state_at", self.provider_state_at)
        _validate_period(self.current_trading_period)


def build_market_session_evidence(
    *,
    envelope_ref: str,
    requested_symbol: str,
    provider_symbol: str | None,
    provider_id: str,
    provider_version: str | None,
    observation_session_claim: MarketSession = MarketSession.UNKNOWN,
    observation_session_basis: ObservationSessionBasis = ObservationSessionBasis.NONE,
    observation_at: datetime | None = None,
    provider_reported_state_raw: str | None = None,
    provider_reported_state_normalized: MarketSession = MarketSession.UNKNOWN,
    provider_state_received_at: datetime | None = None,
    provider_state_at: datetime | None = None,
    current_trading_period: MarketTradingPeriod | None = None,
    exchange_timezone: str | None = None,
    gmt_offset: timedelta | None = None,
    provider_delay: timedelta | None = None,
    confidence: MarketSessionConfidence = MarketSessionConfidence.UNKNOWN,
    warnings: Sequence[str] = (),
    provenance: Sequence[str] = (),
) -> MarketSessionEvidence:
    """Build deterministic evidence from explicit, timezone-aware inputs only."""

    if not _clean_text(envelope_ref):
        raise ValueError("envelope_ref is required")
    _require_aware("observation_at", observation_at)
    _require_aware("provider_state_received_at", provider_state_received_at)
    _require_aware("provider_state_at", provider_state_at)
    _validate_period(current_trading_period)
    raw_state = _bounded_raw_state(provider_reported_state_raw)
    normalized_warnings = _unique(warnings)
    if provider_reported_state_raw is not None and raw_state is None:
        normalized_warnings = _unique(
            normalized_warnings + ("provider response state exceeds bounded evidence length",)
        )
    normalized_provenance = _unique(provenance)
    parts = (
        _CONTRACT_VERSION,
        envelope_ref or "",
        requested_symbol,
        provider_symbol or "",
        provider_id,
        provider_version or "",
        observation_session_claim.value,
        observation_session_basis.value,
        _datetime_text(observation_at),
        raw_state or "",
        provider_reported_state_normalized.value,
        _datetime_text(provider_state_received_at),
        _datetime_text(provider_state_at),
        _period_text(current_trading_period),
        exchange_timezone or "",
        _timedelta_text(gmt_offset),
        _timedelta_text(provider_delay),
        confidence.value,
        *normalized_warnings,
        *normalized_provenance,
    )
    return MarketSessionEvidence(
        contract_version=_CONTRACT_VERSION,
        session_evidence_ref=_ref("mse", parts),
        envelope_ref=_clean_text(envelope_ref),
        requested_symbol=requested_symbol,
        provider_symbol=_clean_text(provider_symbol),
        provider_id=provider_id,
        provider_version=_clean_text(provider_version),
        observation_session_claim=observation_session_claim,
        observation_session_basis=observation_session_basis,
        observation_at=observation_at,
        provider_reported_state_raw=raw_state,
        provider_reported_state_normalized=provider_reported_state_normalized,
        provider_state_received_at=provider_state_received_at,
        provider_state_at=provider_state_at,
        current_trading_period=current_trading_period,
        exchange_timezone=_clean_text(exchange_timezone),
        gmt_offset=gmt_offset,
        provider_delay=provider_delay,
        confidence=confidence,
        warnings=normalized_warnings,
        provenance=normalized_provenance,
    )


def adapt_yahoo_chart_market_session_evidence(
    result: Mapping[str, Any] | None,
    *,
    envelope_ref: str,
    requested_symbol: str,
    provider_symbol: str | None,
    provider_version: str | None,
    received_at: datetime | None,
) -> MarketSessionEvidence:
    """Purely translate already-loaded Yahoo Chart metadata into evidence."""

    meta = (result or {}).get("meta") or {}
    observed_at = _parse_datetime(meta.get("regularMarketTime"))
    price_present = _valid_price(meta.get("regularMarketPrice"))
    raw_state = _clean_text(meta.get("marketState"))
    response_state = normalize_provider_reported_state(raw_state)
    pair = price_present and observed_at is not None
    warnings: list[str] = []
    if not pair:
        warnings.append("Yahoo Chart payload has no complete regularMarketPrice/regularMarketTime pair")
    if raw_state is None:
        warnings.append("Yahoo Chart payload has no provider response state")
    elif response_state == MarketSession.UNKNOWN:
        warnings.append("Yahoo Chart payload has unrecognized provider response state")
    if meta.get("exchangeDataDelayedBy") is None:
        warnings.append("Yahoo Chart payload has no provider delay evidence")
    return build_market_session_evidence(
        envelope_ref=envelope_ref,
        requested_symbol=requested_symbol,
        provider_symbol=provider_symbol or _clean_text(meta.get("symbol")),
        provider_id="yahoo_chart",
        provider_version=provider_version,
        observation_session_claim=(MarketSession.REGULAR if pair else MarketSession.UNKNOWN),
        observation_session_basis=(
            ObservationSessionBasis.PROVIDER_REGULAR_MARKET_FIELDS
            if pair else ObservationSessionBasis.NONE
        ),
        observation_at=observed_at,
        provider_reported_state_raw=raw_state,
        provider_reported_state_normalized=response_state,
        provider_state_received_at=received_at if raw_state is not None else None,
        provider_state_at=None,
        current_trading_period=_adapt_trading_period(meta.get("currentTradingPeriod")),
        exchange_timezone=_clean_text(meta.get("exchangeTimezoneName")),
        gmt_offset=_seconds_to_delta(meta.get("gmtoffset")),
        provider_delay=_seconds_to_delta(meta.get("exchangeDataDelayedBy")),
        confidence=(
            MarketSessionConfidence.PROVIDER_SEMANTIC_PAIR
            if pair else (MarketSessionConfidence.PARTIAL if raw_state is not None else MarketSessionConfidence.UNKNOWN)
        ),
        warnings=warnings,
        provenance=("Yahoo Chart chart.result[0].meta",),
    )


def normalize_provider_reported_state(value: Any) -> MarketSession:
    """Normalize explicit provider response state without inferring an observation."""

    key = _clean_text(value)
    if key is None:
        return MarketSession.UNKNOWN
    return {
        "REGULAR": MarketSession.REGULAR,
        "REGULAR_MARKET": MarketSession.REGULAR,
        "PRE": MarketSession.PRE_MARKET,
        "PREPRE": MarketSession.PRE_MARKET,
        "PRE_MARKET": MarketSession.PRE_MARKET,
        "POST": MarketSession.AFTER_HOURS,
        "POSTPOST": MarketSession.AFTER_HOURS,
        "AFTER_HOURS": MarketSession.AFTER_HOURS,
        "CLOSED": MarketSession.CLOSED,
    }.get(key.upper(), MarketSession.UNKNOWN)


def _adapt_trading_period(value: Any) -> MarketTradingPeriod | None:
    if not isinstance(value, Mapping):
        return None
    return MarketTradingPeriod(
        pre=_adapt_interval(value.get("pre")),
        regular=_adapt_interval(value.get("regular")),
        post=_adapt_interval(value.get("post")),
    )


def _adapt_interval(value: Any) -> TradingPeriodInterval | None:
    if not isinstance(value, Mapping):
        return None
    return TradingPeriodInterval(
        start=_parse_datetime(value.get("start")),
        end=_parse_datetime(value.get("end")),
    )


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if _is_aware(value) else None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if value is None:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if _is_aware(parsed) else None


def _seconds_to_delta(value: Any) -> timedelta | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return timedelta(seconds=float(value))
    except (TypeError, ValueError, OverflowError):
        return None


def _valid_price(value: Any) -> bool:
    if value is None or isinstance(value, bool):
        return False
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False


def _validate_period(period: MarketTradingPeriod | None) -> None:
    if period is None:
        return
    for name, interval in (("pre", period.pre), ("regular", period.regular), ("post", period.post)):
        if interval is None:
            continue
        _require_aware(f"current_trading_period.{name}.start", interval.start)
        _require_aware(f"current_trading_period.{name}.end", interval.end)


def _require_aware(name: str, value: datetime | None) -> None:
    if value is not None and not _is_aware(value):
        raise ValueError(f"{name} must be timezone-aware")


def _is_aware(value: datetime) -> bool:
    return value.tzinfo is not None and value.utcoffset() is not None


def _bounded_raw_state(value: str | None) -> str | None:
    cleaned = _clean_text(value)
    return cleaned if cleaned and len(cleaned) <= _MAX_RAW_STATE_LENGTH else None


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _unique(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values if str(value)))


def _ref(prefix: str, parts: Sequence[object]) -> str:
    return f"{prefix}_" + hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:24]


def _datetime_text(value: datetime | None) -> str:
    return value.isoformat() if value is not None else ""


def _timedelta_text(value: timedelta | None) -> str:
    return str(value.total_seconds()) if value is not None else ""


def _period_text(period: MarketTradingPeriod | None) -> str:
    if period is None:
        return ""
    return "|".join(
        f"{name}:{_datetime_text(interval.start) if interval else ''}:{_datetime_text(interval.end) if interval else ''}"
        for name, interval in (("pre", period.pre), ("regular", period.regular), ("post", period.post))
    )
