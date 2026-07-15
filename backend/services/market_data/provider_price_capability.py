"""Read-only provider market-price capability contracts (M32.3E3F2).

Capability is evidence about one provider/market path.  It is deliberately not
a provider router or an execution-price suitability decision.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Sequence

from services.market_price_evidence import (
    DeclaredProviderDelayEvidence,
    DelayApprovalState,
)

__all__ = [
    "CapabilityApprovalState",
    "CapabilityConfidence",
    "CapabilitySupport",
    "ProviderMarketPriceCapability",
    "ProviderMarketPriceCapabilityAudit",
    "ProviderMarketPriceReadiness",
    "audit_provider_market_price_capability",
    "build_provider_market_price_capability",
    "current_yahoo_chart_set_capability",
]


_CONTRACT_VERSION = "1"


class CapabilitySupport(str, Enum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    UNAVAILABLE = "UNAVAILABLE"
    UNMEASURED = "UNMEASURED"


class CapabilityConfidence(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"


class CapabilityApprovalState(str, Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    QUARANTINED = "QUARANTINED"


class ProviderMarketPriceReadiness(str, Enum):
    READY_FOR_EVIDENCE_REVIEW = "READY_FOR_EVIDENCE_REVIEW"
    LAST_PRICE_ONLY = "LAST_PRICE_ONLY"
    TOP_OF_BOOK_INCOMPLETE = "TOP_OF_BOOK_INCOMPLETE"
    DELAYED_UNSUITABLE = "DELAYED_UNSUITABLE"
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    UNMEASURED = "UNMEASURED"
    UNSUPPORTED = "UNSUPPORTED"
    QUARANTINED = "QUARANTINED"


@dataclass(frozen=True)
class ProviderMarketPriceCapability:
    contract_version: str
    capability_ref: str
    provider_id: str
    provider_version: str | None
    market_scope_ref: str
    regular_last: CapabilitySupport
    explicit_last_trade: CapabilitySupport
    bid: CapabilitySupport
    ask: CapabilitySupport
    bid_ask_sizes: CapabilitySupport
    quote_timestamp: CapabilitySupport
    payload_delay: CapabilitySupport
    session_evidence: CapabilitySupport
    currency: CapabilitySupport
    batch_behavior: CapabilitySupport
    declared_delay_evidence: DeclaredProviderDelayEvidence | None
    source_authority: str | None
    source_version: str | None
    effective_from: datetime | None
    effective_to: datetime | None
    confidence: CapabilityConfidence
    approval_state: CapabilityApprovalState
    warnings: tuple[str, ...]
    provenance: tuple[str, ...]


@dataclass(frozen=True)
class ProviderMarketPriceCapabilityAudit:
    contract_version: str
    audit_ref: str
    capability: ProviderMarketPriceCapability
    measured_samples: int
    regular_last_coverage: int
    bid_coverage: int
    ask_coverage: int
    size_coverage: int
    quote_timestamp_coverage: int
    payload_delay_coverage: int
    currency_coverage: int
    session_coverage: int
    batch_behavior: CapabilitySupport
    authentication_status: str
    operational_status: str
    readiness: ProviderMarketPriceReadiness
    warnings: tuple[str, ...]
    provenance: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "audit_ref": self.audit_ref,
            "provider_id": self.capability.provider_id,
            "provider_version": self.capability.provider_version,
            "market_scope_ref": self.capability.market_scope_ref,
            "declared_support": {
                name: getattr(self.capability, name).value
                for name in ("regular_last", "explicit_last_trade", "bid", "ask", "bid_ask_sizes", "quote_timestamp", "payload_delay", "session_evidence", "currency", "batch_behavior")
            },
            "measured_coverage": {
                "samples": self.measured_samples, "regular_last": self.regular_last_coverage,
                "bid": self.bid_coverage, "ask": self.ask_coverage, "sizes": self.size_coverage,
                "quote_timestamp": self.quote_timestamp_coverage, "payload_delay": self.payload_delay_coverage,
                "currency": self.currency_coverage, "session": self.session_coverage,
            },
            "batch_behavior": self.batch_behavior.value,
            "authentication_status": self.authentication_status,
            "operational_status": self.operational_status,
            "readiness": self.readiness.value,
            "warnings": list(self.warnings),
            "provenance": list(self.provenance),
        }


def build_provider_market_price_capability(
    *,
    provider_id: str,
    provider_version: str | None,
    market_scope_ref: str,
    regular_last: CapabilitySupport,
    explicit_last_trade: CapabilitySupport,
    bid: CapabilitySupport,
    ask: CapabilitySupport,
    bid_ask_sizes: CapabilitySupport,
    quote_timestamp: CapabilitySupport,
    payload_delay: CapabilitySupport,
    session_evidence: CapabilitySupport,
    currency: CapabilitySupport,
    batch_behavior: CapabilitySupport,
    declared_delay_evidence: DeclaredProviderDelayEvidence | None = None,
    source_authority: str | None = None,
    source_version: str | None = None,
    effective_from: datetime | None = None,
    effective_to: datetime | None = None,
    confidence: CapabilityConfidence = CapabilityConfidence.UNKNOWN,
    approval_state: CapabilityApprovalState = CapabilityApprovalState.DRAFT,
    warnings: Sequence[str] = (),
    provenance: Sequence[str] = (),
) -> ProviderMarketPriceCapability:
    _aware("effective_from", effective_from)
    _aware("effective_to", effective_to)
    warnings, provenance = _unique(warnings), _unique(provenance)
    fields = (regular_last, explicit_last_trade, bid, ask, bid_ask_sizes, quote_timestamp,
              payload_delay, session_evidence, currency, batch_behavior)
    ref = _ref("pmpc", (_CONTRACT_VERSION, provider_id, provider_version or "", market_scope_ref,
        *(field.value for field in fields), getattr(declared_delay_evidence, "evidence_ref", ""), source_authority or "",
        source_version or "", _datetime(effective_from), _datetime(effective_to), confidence.value,
        approval_state.value, *warnings, *provenance))
    return ProviderMarketPriceCapability(_CONTRACT_VERSION, ref, provider_id, _text(provider_version), market_scope_ref,
        *fields, declared_delay_evidence, _text(source_authority), _text(source_version), effective_from,
        effective_to, confidence, approval_state, warnings, provenance)


def current_yahoo_chart_set_capability(
    *,
    declared_delay_evidence: DeclaredProviderDelayEvidence | None = None,
) -> ProviderMarketPriceCapability:
    """The measured application path, without using a ticker/exchange heuristic."""

    approved_delay = (
        declared_delay_evidence
        if declared_delay_evidence is not None and declared_delay_evidence.approval_state == DelayApprovalState.APPROVED
        else None
    )
    warnings = ["Yahoo Chart current path supplies provider regular-last evidence, not timestamped top-of-book"]
    if declared_delay_evidence is not None and approved_delay is None:
        warnings.append("unapproved provider-delay evidence is not attached to the Yahoo Chart capability mapping")
    return build_provider_market_price_capability(
        provider_id="yahoo_chart", provider_version=None, market_scope_ref="provider-market:yahoo_chart:set",
        regular_last=CapabilitySupport.SUPPORTED, explicit_last_trade=CapabilitySupport.UNAVAILABLE,
        bid=CapabilitySupport.UNSUPPORTED, ask=CapabilitySupport.UNSUPPORTED,
        bid_ask_sizes=CapabilitySupport.UNSUPPORTED, quote_timestamp=CapabilitySupport.UNSUPPORTED,
        payload_delay=CapabilitySupport.UNAVAILABLE, session_evidence=CapabilitySupport.SUPPORTED,
        currency=CapabilitySupport.SUPPORTED, batch_behavior=CapabilitySupport.SUPPORTED,
        declared_delay_evidence=approved_delay, confidence=CapabilityConfidence.PARTIAL,
        approval_state=CapabilityApprovalState.DRAFT,
        warnings=tuple(warnings),
        provenance=("M32.3E3F1 controlled Chart capability measurement",),
    )


def audit_provider_market_price_capability(
    capability: ProviderMarketPriceCapability,
    *,
    samples: Sequence[dict[str, object]] = (),
    authentication_status: str = "NOT_REQUIRED_FOR_STATIC_AUDIT",
    operational_status: str = "STATIC_DECLARATION_ONLY",
    provenance: Sequence[str] = (),
) -> ProviderMarketPriceCapabilityAudit:
    """Assess only supplied sanitized samples; never accesses a provider/network."""

    count = len(samples)
    coverage = {key: sum(1 for item in samples if bool(item.get(key))) for key in (
        "regular_last", "bid", "ask", "sizes", "quote_timestamp", "payload_delay", "currency", "session"
    )}
    readiness = _readiness(capability, count, coverage, authentication_status)
    warnings = list(capability.warnings)
    if not count:
        warnings.append("no runtime sample supplied; declared capability remains unmeasured")
    ref = _ref("pmpa", (_CONTRACT_VERSION, capability.capability_ref, count, *(coverage[key] for key in sorted(coverage)),
        capability.batch_behavior.value, authentication_status, operational_status, readiness.value, *_unique(warnings), *_unique(provenance)))
    return ProviderMarketPriceCapabilityAudit(_CONTRACT_VERSION, ref, capability, count, coverage["regular_last"],
        coverage["bid"], coverage["ask"], coverage["sizes"], coverage["quote_timestamp"], coverage["payload_delay"],
        coverage["currency"], coverage["session"], capability.batch_behavior, authentication_status,
        operational_status, readiness, _unique(warnings), _unique(provenance))


def _readiness(capability, count, coverage, auth):
    if auth == "AUTHENTICATION_REQUIRED":
        return ProviderMarketPriceReadiness.AUTHENTICATION_REQUIRED
    if capability.approval_state == CapabilityApprovalState.QUARANTINED:
        return ProviderMarketPriceReadiness.QUARANTINED
    if not count:
        return ProviderMarketPriceReadiness.UNMEASURED
    if capability.bid == CapabilitySupport.UNSUPPORTED or capability.ask == CapabilitySupport.UNSUPPORTED:
        return ProviderMarketPriceReadiness.LAST_PRICE_ONLY
    if not coverage["bid"] or not coverage["ask"] or not coverage["quote_timestamp"]:
        return ProviderMarketPriceReadiness.TOP_OF_BOOK_INCOMPLETE
    if capability.declared_delay_evidence is not None and capability.declared_delay_evidence.delay:
        return ProviderMarketPriceReadiness.DELAYED_UNSUITABLE
    return ProviderMarketPriceReadiness.READY_FOR_EVIDENCE_REVIEW


def _aware(name, value):
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError(f"{name} must be timezone-aware")


def _unique(values):
    return tuple(dict.fromkeys(str(value) for value in values if str(value)))


def _text(value):
    value = str(value).strip() if value is not None else ""
    return value or None


def _datetime(value):
    return value.isoformat() if value else ""


def _ref(prefix, values):
    return f"{prefix}_" + hashlib.sha256("|".join(str(value) for value in values).encode()).hexdigest()[:24]
