"""Immutable market-price evidence contracts for the M32.3E3F2 shadow.

This module deliberately records evidence without deciding whether a price can
be used for an order.  In particular it does not resolve Registry identity,
fetch a provider, read a cache, read a clock, select BID/ASK, quote a fee, or
derive a quantity.  All timestamps and absences are retained as supplied.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Mapping, Sequence

from services.execution_price_observation import PriceFreshnessStatus

if TYPE_CHECKING:
    from services.execution_instrument_facts import ExecutionInstrumentFacts
    from services.market_data.execution_quote import ExecutionQuoteEnvelope
    from services.market_data.session_evidence import MarketSessionEvidence


__all__ = [
    "DeclaredProviderDelayEvidence",
    "DelayApprovalState",
    "DelayConfidence",
    "EvidenceAgeAssessment",
    "EvidenceAgeKind",
    "EvidenceAgePolicy",
    "EvidenceQuality",
    "LastPriceEvidence",
    "LastPriceSemanticKind",
    "MarketPriceEvidenceSet",
    "TopOfBookEvidence",
    "TopOfBookPairQuality",
    "adapt_execution_quote_envelope_to_last_price_evidence",
    "adapt_quote_fixture_to_top_of_book_evidence",
    "assess_cache_age",
    "assess_last_price_age",
    "assess_provider_receipt_age",
    "assess_top_of_book_age",
    "build_declared_provider_delay_evidence",
    "build_last_price_evidence",
    "build_market_price_evidence_set",
    "build_top_of_book_evidence",
    "declared_delay_status",
]


_CONTRACT_VERSION = "1"


class LastPriceSemanticKind(str, Enum):
    PROVIDER_REGULAR_LAST = "PROVIDER_REGULAR_LAST"
    LAST_TRADE = "LAST_TRADE"
    INDEX_VALUE = "INDEX_VALUE"
    UNKNOWN = "UNKNOWN"


class TopOfBookPairQuality(str, Enum):
    TWO_SIDED = "TWO_SIDED"
    BID_ONLY = "BID_ONLY"
    ASK_ONLY = "ASK_ONLY"
    LOCKED = "LOCKED"
    CROSSED = "CROSSED"
    EMPTY = "EMPTY"
    UNKNOWN = "UNKNOWN"


class EvidenceQuality(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    REFERENCE_ONLY = "REFERENCE_ONLY"
    UNKNOWN = "UNKNOWN"


class EvidenceAgeKind(str, Enum):
    LAST_PRICE_EVENT = "LAST_PRICE_EVENT"
    TOP_OF_BOOK_QUOTE = "TOP_OF_BOOK_QUOTE"
    PROVIDER_RECEIPT = "PROVIDER_RECEIPT"
    CACHE_INGESTION = "CACHE_INGESTION"


class DelayConfidence(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"


class DelayApprovalState(str, Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    QUARANTINED = "QUARANTINED"


@dataclass(frozen=True)
class DeclaredProviderDelayEvidence:
    """Governed provider/market delay claim, never a timestamp correction."""

    contract_version: str
    evidence_ref: str
    provider_id: str
    provider_version: str | None
    market_scope_ref: str
    delay: timedelta | None
    source_authority: str | None
    source_locator: str | None
    source_version: str | None
    source_published_at: datetime | None
    source_retrieved_at: datetime | None
    effective_from: datetime | None
    effective_to: datetime | None
    confidence: DelayConfidence
    approval_state: DelayApprovalState
    warnings: tuple[str, ...]
    provenance: tuple[str, ...]


@dataclass(frozen=True)
class LastPriceEvidence:
    """One supplied provider last-price event; it is not a price decision."""

    contract_version: str
    evidence_ref: str
    asset_id: int | None
    requested_symbol: str
    canonical_symbol: str | None
    provider_symbol: str | None
    provider_id: str
    provider_version: str | None
    semantic_kind: LastPriceSemanticKind
    price: Decimal | None
    currency: str | None
    observed_at: datetime | None
    provider_received_at: datetime | None
    cached_at: datetime | None
    event_id: str | None
    session_evidence: "MarketSessionEvidence | None"
    declared_delay_evidence: DeclaredProviderDelayEvidence | None
    quality: EvidenceQuality
    warnings: tuple[str, ...]
    provenance: tuple[str, ...]


@dataclass(frozen=True)
class TopOfBookEvidence:
    """Independent bid/ask evidence; missing quote time stays incomplete."""

    contract_version: str
    evidence_ref: str
    asset_id: int | None
    requested_symbol: str
    canonical_symbol: str | None
    provider_symbol: str | None
    provider_id: str
    provider_version: str | None
    currency: str | None
    bid: Decimal | None
    bid_size: Decimal | None
    ask: Decimal | None
    ask_size: Decimal | None
    quote_observed_at: datetime | None
    provider_received_at: datetime | None
    cached_at: datetime | None
    event_id: str | None
    pair_quality: TopOfBookPairQuality
    session_evidence: "MarketSessionEvidence | None"
    declared_delay_evidence: DeclaredProviderDelayEvidence | None
    quality: EvidenceQuality
    warnings: tuple[str, ...]
    provenance: tuple[str, ...]

    @property
    def midpoint(self) -> Decimal | None:
        """A pure reference convenience, never a selected execution price."""

        if self.pair_quality != TopOfBookPairQuality.TWO_SIDED or self.quote_observed_at is None:
            return None
        if self.bid is None or self.ask is None:
            return None
        return (self.bid + self.ask) / Decimal("2")


@dataclass(frozen=True)
class MarketPriceEvidenceSet:
    """Identity-preserving aggregation of independently timed evidence."""

    contract_version: str
    evidence_set_ref: str
    facts: "ExecutionInstrumentFacts | None"
    provider_id: str
    provider_version: str | None
    currency: str | None
    last_price_evidence: LastPriceEvidence | None
    top_of_book_evidence: TopOfBookEvidence | None
    declared_delay_evidence: DeclaredProviderDelayEvidence | None
    session_evidence: "MarketSessionEvidence | None"
    provider_received_at: datetime | None
    cached_at: datetime | None
    quality: EvidenceQuality
    warnings: tuple[str, ...]
    provenance: tuple[str, ...]


@dataclass(frozen=True)
class EvidenceAgePolicy:
    """Diagnostic-only thresholds.  It never approves an execution price."""

    policy_version: str
    current_for: timedelta
    stale_for: timedelta


@dataclass(frozen=True)
class EvidenceAgeAssessment:
    """One component-specific age; receipt/cache age is never observation age."""

    contract_version: str
    assessment_ref: str
    evidence_ref: str
    age_kind: EvidenceAgeKind
    policy_version: str
    assessed_at: datetime
    status: PriceFreshnessStatus
    age: timedelta | None
    reason: str
    warnings: tuple[str, ...]


def build_declared_provider_delay_evidence(
    *,
    provider_id: str,
    provider_version: str | None,
    market_scope_ref: str,
    delay: timedelta | None,
    source_authority: str | None,
    source_locator: str | None,
    source_version: str | None,
    source_published_at: datetime | None,
    source_retrieved_at: datetime | None,
    effective_from: datetime | None,
    effective_to: datetime | None = None,
    confidence: DelayConfidence = DelayConfidence.UNKNOWN,
    approval_state: DelayApprovalState = DelayApprovalState.DRAFT,
    warnings: Sequence[str] = (),
    provenance: Sequence[str] = (),
) -> DeclaredProviderDelayEvidence:
    _require_aware("source_published_at", source_published_at)
    _require_aware("source_retrieved_at", source_retrieved_at)
    _require_aware("effective_from", effective_from)
    _require_aware("effective_to", effective_to)
    values = _normalized(warnings), _normalized(provenance)
    return DeclaredProviderDelayEvidence(
        _CONTRACT_VERSION,
        _ref("pde", (_CONTRACT_VERSION, provider_id, provider_version or "", market_scope_ref,
                     _duration_text(delay), source_authority or "", source_locator or "", source_version or "",
                     _datetime_text(source_published_at), _datetime_text(source_retrieved_at),
                     _datetime_text(effective_from), _datetime_text(effective_to), confidence.value,
                     approval_state.value, *values[0], *values[1])),
        provider_id, _text(provider_version), market_scope_ref, delay, _text(source_authority),
        _text(source_locator), _text(source_version), source_published_at, source_retrieved_at,
        effective_from, effective_to, confidence, approval_state, values[0], values[1],
    )


def build_last_price_evidence(
    *,
    asset_id: int | None,
    requested_symbol: str,
    canonical_symbol: str | None,
    provider_symbol: str | None,
    provider_id: str,
    provider_version: str | None,
    semantic_kind: LastPriceSemanticKind,
    price: Decimal | None,
    currency: str | None,
    observed_at: datetime | None,
    provider_received_at: datetime | None,
    cached_at: datetime | None = None,
    event_id: str | None = None,
    session_evidence: "MarketSessionEvidence | None" = None,
    declared_delay_evidence: DeclaredProviderDelayEvidence | None = None,
    quality: EvidenceQuality | None = None,
    warnings: Sequence[str] = (),
    provenance: Sequence[str] = (),
) -> LastPriceEvidence:
    _require_aware("observed_at", observed_at)
    _require_aware("provider_received_at", provider_received_at)
    _require_aware("cached_at", cached_at)
    normalized_warnings, normalized_provenance = _normalized(warnings), _normalized(provenance)
    if observed_at is None:
        normalized_warnings = _normalized((*normalized_warnings, "last-price observation time is absent"))
    quality = quality or _last_quality(price, currency, observed_at, provider_received_at)
    return LastPriceEvidence(
        _CONTRACT_VERSION,
        _ref("lpe", (_CONTRACT_VERSION, str(asset_id or ""), requested_symbol, canonical_symbol or "",
                     provider_symbol or "", provider_id, provider_version or "", semantic_kind.value,
                     _decimal_text(price), currency or "", _datetime_text(observed_at),
                     _datetime_text(provider_received_at), _datetime_text(cached_at), event_id or "",
                     _session_ref(session_evidence), _delay_ref(declared_delay_evidence), quality.value,
                     *normalized_warnings, *normalized_provenance)),
        asset_id, requested_symbol, _text(canonical_symbol), _text(provider_symbol), provider_id,
        _text(provider_version), semantic_kind, price, _text(currency), observed_at, provider_received_at,
        cached_at, _text(event_id), session_evidence, declared_delay_evidence, quality,
        normalized_warnings, normalized_provenance,
    )


def build_top_of_book_evidence(
    *,
    asset_id: int | None,
    requested_symbol: str,
    canonical_symbol: str | None,
    provider_symbol: str | None,
    provider_id: str,
    provider_version: str | None,
    currency: str | None,
    bid: Decimal | None,
    bid_size: Decimal | None,
    ask: Decimal | None,
    ask_size: Decimal | None,
    quote_observed_at: datetime | None,
    provider_received_at: datetime | None,
    cached_at: datetime | None = None,
    event_id: str | None = None,
    session_evidence: "MarketSessionEvidence | None" = None,
    declared_delay_evidence: DeclaredProviderDelayEvidence | None = None,
    pair_quality: TopOfBookPairQuality | None = None,
    quality: EvidenceQuality | None = None,
    warnings: Sequence[str] = (),
    provenance: Sequence[str] = (),
) -> TopOfBookEvidence:
    _require_aware("quote_observed_at", quote_observed_at)
    _require_aware("provider_received_at", provider_received_at)
    _require_aware("cached_at", cached_at)
    normalized_warnings, normalized_provenance = _normalized(warnings), _normalized(provenance)
    pair_quality = pair_quality or _book_quality(bid, ask)
    if quote_observed_at is None:
        normalized_warnings = _normalized((*normalized_warnings, "top-of-book quote observation time is absent"))
    quality = quality or _book_evidence_quality(pair_quality, quote_observed_at, currency)
    return TopOfBookEvidence(
        _CONTRACT_VERSION,
        _ref("tob", (_CONTRACT_VERSION, str(asset_id or ""), requested_symbol, canonical_symbol or "",
                     provider_symbol or "", provider_id, provider_version or "", currency or "", _decimal_text(bid),
                     _decimal_text(bid_size), _decimal_text(ask), _decimal_text(ask_size),
                     _datetime_text(quote_observed_at), _datetime_text(provider_received_at), _datetime_text(cached_at),
                     event_id or "", pair_quality.value, _session_ref(session_evidence), _delay_ref(declared_delay_evidence),
                     quality.value, *normalized_warnings, *normalized_provenance)),
        asset_id, requested_symbol, _text(canonical_symbol), _text(provider_symbol), provider_id,
        _text(provider_version), _text(currency), bid, bid_size, ask, ask_size, quote_observed_at,
        provider_received_at, cached_at, _text(event_id), pair_quality, session_evidence,
        declared_delay_evidence, quality, normalized_warnings, normalized_provenance,
    )


def adapt_execution_quote_envelope_to_last_price_evidence(
    envelope: "ExecutionQuoteEnvelope",
    *,
    facts: "ExecutionInstrumentFacts | None" = None,
    declared_delay_evidence: DeclaredProviderDelayEvidence | None = None,
    semantic_kind: LastPriceSemanticKind | None = None,
) -> LastPriceEvidence:
    """Purely map an existing envelope; Yahoo Chart stays provider-regular-last."""

    kind = semantic_kind or (
        LastPriceSemanticKind.PROVIDER_REGULAR_LAST
        if envelope.provider_id == "yahoo_chart" else LastPriceSemanticKind.UNKNOWN
    )
    # M31 represents an index as OTHER + REFERENCE; INDEX is intentionally not
    # an instrument-form enum value.
    if facts is not None and getattr(getattr(facts, "execution_role", None), "value", None) == "REFERENCE":
        kind = LastPriceSemanticKind.INDEX_VALUE
    return build_last_price_evidence(
        asset_id=(int(facts.asset_id) if facts and facts.asset_id is not None else None),
        requested_symbol=envelope.requested_symbol,
        canonical_symbol=facts.canonical_symbol if facts else None,
        provider_symbol=envelope.provider_symbol,
        provider_id=envelope.provider_id,
        provider_version=envelope.provider_version,
        semantic_kind=kind,
        price=envelope.price,
        currency=envelope.currency,
        observed_at=envelope.observed_at,
        provider_received_at=envelope.received_at,
        cached_at=envelope.cached_at,
        session_evidence=envelope.session_evidence,
        declared_delay_evidence=declared_delay_evidence,
        warnings=envelope.warnings,
        provenance=(*envelope.provenance, f"ExecutionQuoteEnvelope={envelope.envelope_ref}"),
    )


def adapt_quote_fixture_to_top_of_book_evidence(
    payload: Mapping[str, object],
    *,
    asset_id: int | None,
    requested_symbol: str,
    canonical_symbol: str | None,
    provider_id: str,
    provider_version: str | None,
    provider_symbol: str | None = None,
    session_evidence: "MarketSessionEvidence | None" = None,
    declared_delay_evidence: DeclaredProviderDelayEvidence | None = None,
) -> TopOfBookEvidence:
    """Adapt caller-supplied quote-like data only; it performs no retrieval."""

    return build_top_of_book_evidence(
        asset_id=asset_id, requested_symbol=requested_symbol, canonical_symbol=canonical_symbol,
        provider_symbol=provider_symbol, provider_id=provider_id, provider_version=provider_version,
        currency=_text(payload.get("currency")), bid=_decimal(payload.get("bid")),
        bid_size=_decimal(payload.get("bid_size")), ask=_decimal(payload.get("ask")),
        ask_size=_decimal(payload.get("ask_size")), quote_observed_at=_datetime(payload.get("quote_observed_at")),
        provider_received_at=_datetime(payload.get("provider_received_at")), cached_at=_datetime(payload.get("cached_at")),
        event_id=_text(payload.get("event_id")), session_evidence=session_evidence,
        declared_delay_evidence=declared_delay_evidence, provenance=("supplied quote-like fixture",),
    )


def build_market_price_evidence_set(
    *,
    facts: "ExecutionInstrumentFacts | None",
    provider_id: str,
    provider_version: str | None,
    currency: str | None,
    last_price_evidence: LastPriceEvidence | None,
    top_of_book_evidence: TopOfBookEvidence | None,
    declared_delay_evidence: DeclaredProviderDelayEvidence | None,
    session_evidence: "MarketSessionEvidence | None",
    provider_received_at: datetime | None,
    cached_at: datetime | None,
    quality: EvidenceQuality | None = None,
    warnings: Sequence[str] = (),
    provenance: Sequence[str] = (),
) -> MarketPriceEvidenceSet:
    _require_aware("provider_received_at", provider_received_at)
    _require_aware("cached_at", cached_at)
    normalized_warnings, normalized_provenance = _normalized(warnings), _normalized(provenance)
    quality = quality or _set_quality(last_price_evidence, top_of_book_evidence)
    return MarketPriceEvidenceSet(
        _CONTRACT_VERSION,
        _ref("mpe", (_CONTRACT_VERSION, str(getattr(facts, "asset_id", "") or ""), provider_id,
                     provider_version or "", currency or "", _last_ref(last_price_evidence), _book_ref(top_of_book_evidence),
                     _delay_ref(declared_delay_evidence), _session_ref(session_evidence), _datetime_text(provider_received_at),
                     _datetime_text(cached_at), quality.value, *normalized_warnings, *normalized_provenance)),
        facts, provider_id, _text(provider_version), _text(currency), last_price_evidence,
        top_of_book_evidence, declared_delay_evidence, session_evidence, provider_received_at,
        cached_at, quality, normalized_warnings, normalized_provenance,
    )


def assess_last_price_age(evidence: LastPriceEvidence, *, assessed_at: datetime, policy: EvidenceAgePolicy) -> EvidenceAgeAssessment:
    return _assess(evidence.evidence_ref, EvidenceAgeKind.LAST_PRICE_EVENT, evidence.observed_at, assessed_at, policy)


def assess_top_of_book_age(evidence: TopOfBookEvidence, *, assessed_at: datetime, policy: EvidenceAgePolicy) -> EvidenceAgeAssessment:
    return _assess(evidence.evidence_ref, EvidenceAgeKind.TOP_OF_BOOK_QUOTE, evidence.quote_observed_at, assessed_at, policy)


def assess_provider_receipt_age(evidence: LastPriceEvidence | TopOfBookEvidence, *, assessed_at: datetime, policy: EvidenceAgePolicy) -> EvidenceAgeAssessment:
    return _assess(evidence.evidence_ref, EvidenceAgeKind.PROVIDER_RECEIPT, evidence.provider_received_at, assessed_at, policy)


def assess_cache_age(evidence: LastPriceEvidence | TopOfBookEvidence, *, assessed_at: datetime, policy: EvidenceAgePolicy) -> EvidenceAgeAssessment:
    return _assess(evidence.evidence_ref, EvidenceAgeKind.CACHE_INGESTION, evidence.cached_at, assessed_at, policy)


def declared_delay_status(evidence: DeclaredProviderDelayEvidence | None) -> str:
    """Return an evidence-state label; it does not interpret or apply delay."""

    if evidence is None or evidence.delay is None:
        return "MISSING"
    if evidence.approval_state != DelayApprovalState.APPROVED:
        return "UNAPPROVED"
    return "PRESENT"


def _assess(evidence_ref: str, kind: EvidenceAgeKind, observed_at: datetime | None, assessed_at: datetime, policy: EvidenceAgePolicy) -> EvidenceAgeAssessment:
    _require_aware("assessed_at", assessed_at)
    if observed_at is None:
        status, age, reason, warnings = PriceFreshnessStatus.PRICE_TIMESTAMP_MISSING, None, f"{kind.value} timestamp is absent", ()
    else:
        try:
            age = assessed_at - observed_at
        except TypeError:
            status, age, reason, warnings = PriceFreshnessStatus.UNKNOWN, None, "assessment and evidence timestamps are not comparable", ()
        else:
            if age < timedelta(0):
                status, reason, warnings = PriceFreshnessStatus.UNKNOWN, "evidence time is after assessment time", ("negative evidence age",)
            elif age <= policy.current_for:
                status, reason, warnings = PriceFreshnessStatus.CURRENT, "evidence age is within the diagnostic current threshold", ()
            elif age <= policy.stale_for:
                status, reason, warnings = PriceFreshnessStatus.STALE, "evidence age exceeds the diagnostic current threshold", ()
            else:
                status, reason, warnings = PriceFreshnessStatus.EXPIRED, "evidence age exceeds the diagnostic stale threshold", ()
    return EvidenceAgeAssessment(_CONTRACT_VERSION, _ref("mpa", (_CONTRACT_VERSION, evidence_ref, kind.value, policy.policy_version,
        _datetime_text(assessed_at), status.value, _duration_text(age), reason, *warnings)), evidence_ref, kind,
        policy.policy_version, assessed_at, status, age, reason, warnings)


def _book_quality(bid: Decimal | None, ask: Decimal | None) -> TopOfBookPairQuality:
    if bid is None and ask is None:
        return TopOfBookPairQuality.EMPTY
    if bid is None:
        return TopOfBookPairQuality.ASK_ONLY
    if ask is None:
        return TopOfBookPairQuality.BID_ONLY
    if bid <= 0 or ask <= 0:
        return TopOfBookPairQuality.UNKNOWN
    if bid == ask:
        return TopOfBookPairQuality.LOCKED
    if bid > ask:
        return TopOfBookPairQuality.CROSSED
    return TopOfBookPairQuality.TWO_SIDED


def _last_quality(price, currency, observed_at, received_at) -> EvidenceQuality:
    if price is not None and price > 0 and currency and observed_at and received_at:
        return EvidenceQuality.COMPLETE
    if price is not None:
        return EvidenceQuality.PARTIAL
    return EvidenceQuality.UNKNOWN


def _book_evidence_quality(pair_quality, observed_at, currency) -> EvidenceQuality:
    if pair_quality == TopOfBookPairQuality.TWO_SIDED and observed_at and currency:
        return EvidenceQuality.COMPLETE
    if pair_quality in (TopOfBookPairQuality.LOCKED, TopOfBookPairQuality.CROSSED):
        return EvidenceQuality.REFERENCE_ONLY
    return EvidenceQuality.PARTIAL if pair_quality != TopOfBookPairQuality.EMPTY else EvidenceQuality.UNKNOWN


def _set_quality(last, book) -> EvidenceQuality:
    if book and book.quality == EvidenceQuality.COMPLETE:
        return EvidenceQuality.COMPLETE
    if last and last.quality != EvidenceQuality.UNKNOWN:
        return EvidenceQuality.PARTIAL
    return EvidenceQuality.UNKNOWN


def _require_aware(name: str, value: datetime | None) -> None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError(f"{name} must be timezone-aware")


def _text(value: object | None) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _decimal(value: object | None) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _datetime(value: object | None) -> datetime | None:
    return value if isinstance(value, datetime) else None


def _normalized(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(value) for value in values if str(value)))


def _ref(prefix: str, values: Sequence[object]) -> str:
    return f"{prefix}_" + hashlib.sha256("|".join(str(value) for value in values).encode()).hexdigest()[:24]


def _datetime_text(value: datetime | None) -> str:
    return value.isoformat() if value is not None else ""


def _duration_text(value: timedelta | None) -> str:
    return format(Decimal(str(value.total_seconds())), "f") if value is not None else ""


def _decimal_text(value: Decimal | None) -> str:
    return format(value, "f") if value is not None else ""


def _session_ref(value: object | None) -> str:
    return str(getattr(value, "session_evidence_ref", "") or "")


def _delay_ref(value: object | None) -> str:
    return str(getattr(value, "evidence_ref", "") or "")


def _last_ref(value: LastPriceEvidence | None) -> str:
    return value.evidence_ref if value else ""


def _book_ref(value: TopOfBookEvidence | None) -> str:
    return value.evidence_ref if value else ""
