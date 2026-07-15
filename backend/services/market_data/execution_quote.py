"""Additive live-quote evidence contracts for the M32.3E2 shadow path.

This module is owned by Market Data.  It translates an already loaded provider
payload (or cache provenance) into an immutable envelope; it does not resolve
Registry identity, evaluate execution policy, access a cache/database, fetch
the network, or read a clock.  The legacy ``get_quote`` dictionary contract is
intentionally not represented or changed here.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping, Sequence

from services.execution_price_observation import MarketSession, PriceKind

__all__ = [
    "ExecutionQuoteEnvelope",
    "ExecutionQuoteEvidence",
    "adapt_cached_execution_quote",
    "adapt_yahoo_chart_execution_quote",
    "adapt_yahoo_finance_execution_quote",
    "build_execution_quote_envelope",
]


_CONTRACT_VERSION = "1"


@dataclass(frozen=True)
class ExecutionQuoteEnvelope:
    """Provider/cache evidence, before Registry identity is attached.

    ``received_at`` and ``cached_at`` are deliberately separate from
    ``observed_at``.  Callers must pass a receipt instant captured at their I/O
    boundary; the pure builders below never create one.
    """

    contract_version: str
    envelope_ref: str
    requested_symbol: str
    provider_symbol: str | None
    provider_id: str
    provider_version: str | None
    price: Decimal | None
    price_kind: PriceKind
    currency: str | None
    observed_at: datetime | None
    received_at: datetime | None
    cached_at: datetime | None
    market_session: MarketSession
    exchange_timezone: str | None
    delay: timedelta | None
    warnings: tuple[str, ...]
    provenance: tuple[str, ...]


@dataclass(frozen=True)
class ExecutionQuoteEvidence:
    """One bounded provider/cache attempt, including an isolated failure."""

    requested_symbol: str
    envelope: ExecutionQuoteEnvelope | None
    error: str | None = None
    source: str = "PROVIDER"


def build_execution_quote_envelope(
    *,
    requested_symbol: str,
    provider_symbol: str | None,
    provider_id: str,
    provider_version: str | None,
    price: Decimal | None,
    price_kind: PriceKind,
    currency: str | None,
    observed_at: datetime | None,
    received_at: datetime | None,
    cached_at: datetime | None = None,
    market_session: MarketSession = MarketSession.UNKNOWN,
    exchange_timezone: str | None = None,
    delay: timedelta | None = None,
    warnings: Sequence[str] = (),
    provenance: Sequence[str] = (),
) -> ExecutionQuoteEnvelope:
    """Build deterministic evidence only from explicit caller-supplied values."""

    normalized_warnings = _unique(warnings)
    normalized_provenance = _unique(provenance)
    parts = (
        _CONTRACT_VERSION,
        requested_symbol,
        provider_symbol or "",
        provider_id,
        provider_version or "",
        _decimal_text(price),
        price_kind.value,
        currency or "",
        _datetime_text(observed_at),
        _datetime_text(received_at),
        _datetime_text(cached_at),
        market_session.value,
        exchange_timezone or "",
        _timedelta_text(delay),
        *normalized_warnings,
        *normalized_provenance,
    )
    return ExecutionQuoteEnvelope(
        contract_version=_CONTRACT_VERSION,
        envelope_ref=_ref("eqe", parts),
        requested_symbol=requested_symbol,
        provider_symbol=_clean_text(provider_symbol),
        provider_id=provider_id,
        provider_version=_clean_text(provider_version),
        price=price,
        price_kind=price_kind,
        currency=_clean_text(currency),
        observed_at=observed_at,
        received_at=received_at,
        cached_at=cached_at,
        market_session=market_session,
        exchange_timezone=_clean_text(exchange_timezone),
        delay=delay,
        warnings=normalized_warnings,
        provenance=normalized_provenance,
    )


def adapt_yahoo_chart_execution_quote(
    result: Mapping[str, Any] | None,
    *,
    requested_symbol: str,
    received_at: datetime | None,
    provider_symbol: str | None = None,
    provider_version: str | None = None,
) -> ExecutionQuoteEnvelope:
    """Adapt one already-loaded Yahoo Chart ``chart.result[0]`` payload."""

    meta = (result or {}).get("meta") or {}
    observed_at = _parse_datetime(meta.get("regularMarketTime"))
    session = _market_session(meta.get("marketState"))
    delay_seconds = _decimal(meta.get("exchangeDataDelayedBy"))
    warnings: list[str] = []
    if observed_at is None:
        warnings.append("Yahoo Chart payload has no regularMarketTime")
    if session == MarketSession.UNKNOWN:
        warnings.append("Yahoo Chart payload has no recognized market session")
    if not _clean_text(meta.get("currency")):
        warnings.append("Yahoo Chart payload has no provider currency")
    return build_execution_quote_envelope(
        requested_symbol=requested_symbol,
        provider_symbol=provider_symbol or meta.get("symbol"),
        provider_id="yahoo_chart",
        provider_version=provider_version,
        price=_decimal(meta.get("regularMarketPrice")),
        price_kind=PriceKind.MARKET_LAST,
        currency=_clean_text(meta.get("currency")),
        observed_at=observed_at,
        received_at=received_at,
        market_session=session,
        exchange_timezone=_clean_text(meta.get("exchangeTimezoneName")),
        delay=(timedelta(seconds=float(delay_seconds)) if delay_seconds is not None else None),
        warnings=warnings,
        provenance=("Yahoo Chart chart.result[0].meta",),
    )


def adapt_yahoo_finance_execution_quote(
    payload: Mapping[str, Any] | None,
    *,
    requested_symbol: str,
    received_at: datetime | None,
    provider_symbol: str | None = None,
    provider_version: str | None = None,
) -> ExecutionQuoteEnvelope:
    """Adapt the legacy yfinance quote without relabelling its Close as last."""

    payload = payload or {}
    return build_execution_quote_envelope(
        requested_symbol=requested_symbol,
        provider_symbol=provider_symbol or requested_symbol,
        provider_id="yahoo_finance",
        provider_version=provider_version,
        price=_decimal(payload.get("current_price")),
        price_kind=PriceKind.MARKET_CLOSE,
        currency=_clean_text(payload.get("currency")),
        observed_at=None,
        received_at=received_at,
        market_session=MarketSession.UNKNOWN,
        warnings=(
            "legacy yfinance quote is latest history Close, not MARKET_LAST",
            "legacy yfinance quote has no exchange observation timestamp",
        ),
        provenance=("YahooProvider.get_quote legacy DTO",),
    )


def adapt_cached_execution_quote(
    envelope: ExecutionQuoteEnvelope,
    *,
    fetched_at: datetime | None,
    provenance: Sequence[str] = (),
) -> ExecutionQuoteEnvelope:
    """Attach cache-write provenance without reclassifying time evidence."""

    # Rebuild instead of mutating so the reference captures cache provenance.
    return build_execution_quote_envelope(
        requested_symbol=envelope.requested_symbol,
        provider_symbol=envelope.provider_symbol,
        provider_id=envelope.provider_id,
        provider_version=envelope.provider_version,
        price=envelope.price,
        price_kind=envelope.price_kind,
        currency=envelope.currency,
        observed_at=envelope.observed_at,
        received_at=envelope.received_at,
        cached_at=fetched_at,
        market_session=envelope.market_session,
        exchange_timezone=envelope.exchange_timezone,
        delay=envelope.delay,
        warnings=envelope.warnings,
        provenance=envelope.provenance + ("MarketDataCache.fetched_at is cache provenance",) + tuple(provenance),
    )


def _parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    if value is None:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def _market_session(value: Any) -> MarketSession:
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
    return f"{prefix}_" + hashlib.sha256("|".join(str(part) for part in parts).encode("utf-8")).hexdigest()[:24]


def _decimal_text(value: Decimal | None) -> str:
    return format(value, "f") if value is not None else ""


def _datetime_text(value: datetime | None) -> str:
    return value.isoformat() if value is not None else ""


def _timedelta_text(value: timedelta | None) -> str:
    return format(Decimal(str(value.total_seconds())), "f") if value is not None else ""
