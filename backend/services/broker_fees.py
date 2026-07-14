"""Versioned broker fee schedules and pure fee quotation (M32.1).

The authoritative interface in this module selects a schedule from immutable
``ExecutionInstrumentFacts``.  It never classifies a raw symbol.  The legacy
symbol-shape behavior required by current transaction posting lives in
``services.broker_fees_compat`` and is deliberately named as compatibility.

All monetary arithmetic is performed with ``Decimal``.  The component
calculator below is the only implementation of the existing SET formula.
``calc_fees`` remains as a backward-compatible adapter for existing callers.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Mapping

from services.execution_instrument_facts import (
    ExecutionInstrumentFacts,
    ExecutionInstrumentForm,
    ExecutionResolutionOutcome,
    ExecutionRole,
)

_COMPONENT_QUANTUM = Decimal("0.0001")
_FEE_QUOTE_CONTRACT_VERSION = "1"
_SET_SCHEDULE_ID = "SET_STANDARD"
_DR_SCHEDULE_ID = "DR_STANDARD"
_FREE_SCHEDULE_ID = "FREE"


class TradeSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class FeeQuoteStatus(str, Enum):
    QUOTED = "QUOTED"
    UNAVAILABLE = "UNAVAILABLE"


class FeeQuoteUnavailableReason(str, Enum):
    IDENTITY_UNKNOWN = "IDENTITY_UNKNOWN"
    IDENTITY_AMBIGUOUS = "IDENTITY_AMBIGUOUS"
    NOT_TRADABLE = "NOT_TRADABLE"
    REGISTRY_FAILURE = "REGISTRY_FAILURE"
    MISSING_FEE_SCHEDULE = "MISSING_FEE_SCHEDULE"
    MISSING_ACCOUNT_CONTEXT = "MISSING_ACCOUNT_CONTEXT"


@dataclass(frozen=True)
class PercentageFeeRule:
    """A percentage of gross consideration; no minimum/cap is implied."""

    rate: Decimal
    basis: str = "GROSS_AMOUNT"


@dataclass(frozen=True)
class FeeRoundingRules:
    """The current component-level rounding contract."""

    component_quantum: Decimal = _COMPONENT_QUANTUM
    mode: str = "ROUND_HALF_UP"
    round_each_component: bool = True
    tax_uses_rounded_components: bool = True


@dataclass(frozen=True)
class FeeProfile:
    """Backward-compatible profile input plus version/provenance metadata."""

    name: str
    commission_rate: Decimal
    trading_fee_rate: Decimal
    clearing_fee_rate: Decimal
    vat_rate: Decimal
    schedule_version: str = "legacy-v1"
    effective_from: datetime | None = None
    currency: str | None = None
    provenance: tuple[str, ...] = ("runtime FeeProfile registration",)


@dataclass(frozen=True)
class FeeSchedule:
    """Immutable, versioned fee rules for one supported applicability set."""

    schedule_id: str
    schedule_version: str
    effective_from: datetime | None
    commission_rule: PercentageFeeRule
    trading_fee_rule: PercentageFeeRule
    clearing_fee_rule: PercentageFeeRule
    tax_rule: PercentageFeeRule
    rounding_rules: FeeRoundingRules
    currency: str | None
    applicability_metadata: tuple[tuple[str, str], ...]
    provenance: tuple[str, ...]


@dataclass(frozen=True)
class FeeBreakdown:
    """Legacy component view retained for transaction/API compatibility."""

    gross_amount: Decimal
    commission: Decimal
    trading_fee: Decimal
    clearing_fee: Decimal
    vat: Decimal

    @property
    def total_fees_excl_vat(self) -> Decimal:
        return self.commission + self.trading_fee + self.clearing_fee

    @property
    def total_fees_incl_vat(self) -> Decimal:
        return self.total_fees_excl_vat + self.vat

    def net_buy_amount(self) -> Decimal:
        return self.gross_amount + self.total_fees_incl_vat

    def net_sell_proceeds(self) -> Decimal:
        return self.gross_amount - self.total_fees_incl_vat

    def to_dict(self) -> dict:
        return {
            "gross_amount": float(self.gross_amount),
            "commission": float(self.commission),
            "trading_fee": float(self.trading_fee),
            "clearing_fee": float(self.clearing_fee),
            "vat": float(self.vat),
            "total_excl_vat": float(self.total_fees_excl_vat),
            "total_incl_vat": float(self.total_fees_incl_vat),
        }


@dataclass(frozen=True)
class FeeQuote:
    """Immutable quote result.  UNAVAILABLE quotes carry no money values."""

    contract_version: str
    quote_ref: str
    status: FeeQuoteStatus
    side: TradeSide
    quantity: Decimal | None
    unit_price: Decimal | None
    gross_amount: Decimal | None
    commission: Decimal | None
    trading_fee: Decimal | None
    clearing_fee: Decimal | None
    taxes: Decimal | None
    total_cost: Decimal | None
    net_cash_effect: Decimal | None
    currency: str | None
    schedule_id: str | None
    schedule_version: str | None
    quoted_at: datetime
    effective_at: datetime
    warnings: tuple[str, ...]
    provenance: tuple[str, ...]
    unavailable_reason: FeeQuoteUnavailableReason | None = None

    def to_fee_breakdown(self) -> FeeBreakdown:
        """Project a successful quote into the unchanged legacy shape."""

        if self.status != FeeQuoteStatus.QUOTED:
            raise ValueError("an unavailable FeeQuote has no fee breakdown")
        assert self.gross_amount is not None
        assert self.commission is not None
        assert self.trading_fee is not None
        assert self.clearing_fee is not None
        assert self.taxes is not None
        return FeeBreakdown(
            gross_amount=self.gross_amount,
            commission=self.commission,
            trading_fee=self.trading_fee,
            clearing_fee=self.clearing_fee,
            vat=self.taxes,
        )

    def to_dict(self) -> dict:
        """Serialize without converting exact monetary values to floats."""

        def decimal_text(value: Decimal | None) -> str | None:
            return format(value, "f") if value is not None else None

        return {
            "contract_version": self.contract_version,
            "quote_ref": self.quote_ref,
            "status": self.status.value,
            "side": self.side.value,
            "quantity": decimal_text(self.quantity),
            "unit_price": decimal_text(self.unit_price),
            "gross_amount": decimal_text(self.gross_amount),
            "commission": decimal_text(self.commission),
            "trading_fee": decimal_text(self.trading_fee),
            "clearing_fee": decimal_text(self.clearing_fee),
            "taxes": decimal_text(self.taxes),
            "total_cost": decimal_text(self.total_cost),
            "net_cash_effect": decimal_text(self.net_cash_effect),
            "currency": self.currency,
            "schedule_id": self.schedule_id,
            "schedule_version": self.schedule_version,
            "quoted_at": self.quoted_at.isoformat(),
            "effective_at": self.effective_at.isoformat(),
            "warnings": list(self.warnings),
            "provenance": list(self.provenance),
            "unavailable_reason": (
                self.unavailable_reason.value if self.unavailable_reason else None
            ),
        }


@dataclass(frozen=True)
class FeeScheduleSelection:
    """Pure selection result used before arithmetic."""

    schedule: FeeSchedule | None
    unavailable_reason: FeeQuoteUnavailableReason | None
    warnings: tuple[str, ...]
    provenance: tuple[str, ...]


SET_STANDARD = FeeProfile(
    name=_SET_SCHEDULE_ID,
    commission_rate=Decimal("0.0015"),
    trading_fee_rate=Decimal("0.00006"),
    clearing_fee_rate=Decimal("0.00001"),
    vat_rate=Decimal("0.07"),
    schedule_version="1",
    currency="THB",
    provenance=("services.broker_fees.SET_STANDARD legacy production rates",),
)

DR_STANDARD = FeeProfile(
    name=_DR_SCHEDULE_ID,
    commission_rate=Decimal("0.0015"),
    trading_fee_rate=Decimal("0.00006"),
    clearing_fee_rate=Decimal("0.00001"),
    vat_rate=Decimal("0.07"),
    schedule_version="1",
    currency="THB",
    provenance=("services.broker_fees.DR_STANDARD legacy production rates",),
)

FREE = FeeProfile(
    name=_FREE_SCHEDULE_ID,
    commission_rate=Decimal("0"),
    trading_fee_rate=Decimal("0"),
    clearing_fee_rate=Decimal("0"),
    vat_rate=Decimal("0"),
    schedule_version="1",
    currency=None,
    provenance=("services.broker_fees.FREE simulation/test profile",),
)


def fee_schedule_from_profile(profile: FeeProfile) -> FeeSchedule:
    """Create the immutable schedule projection for a legacy profile."""

    if profile.name == _DR_SCHEDULE_ID:
        applicability = (
            ("exchange", "SET"),
            ("instrument_form", ExecutionInstrumentForm.DEPOSITARY_RECEIPT.value),
        )
    elif profile.name == _SET_SCHEDULE_ID:
        applicability = (("exchange", "SET"), ("currency", "THB"))
    else:
        applicability = (("explicit_override", "required"),)
    return FeeSchedule(
        schedule_id=profile.name,
        schedule_version=profile.schedule_version,
        effective_from=profile.effective_from,
        commission_rule=PercentageFeeRule(profile.commission_rate),
        trading_fee_rule=PercentageFeeRule(profile.trading_fee_rate),
        clearing_fee_rule=PercentageFeeRule(profile.clearing_fee_rate),
        tax_rule=PercentageFeeRule(profile.vat_rate, basis="PRE_TAX_FEE_COMPONENTS"),
        rounding_rules=FeeRoundingRules(),
        currency=profile.currency,
        applicability_metadata=applicability,
        provenance=profile.provenance,
    )


_PROFILES: dict[str, FeeProfile] = {
    profile.name: profile for profile in (SET_STANDARD, DR_STANDARD, FREE)
}
_SCHEDULES: dict[str, FeeSchedule] = {
    name: fee_schedule_from_profile(profile) for name, profile in _PROFILES.items()
}


def get_profile(name: str) -> FeeProfile:
    """Return a registered compatibility profile by ID."""

    return _PROFILES[name]


def get_fee_schedule(schedule_id: str) -> FeeSchedule:
    """Return a registered immutable schedule by ID."""

    return _SCHEDULES[schedule_id]


def register_profile(profile: FeeProfile) -> None:
    """Add/replace a profile and its schedule atomically at process startup."""

    _PROFILES[profile.name] = profile
    _SCHEDULES[profile.name] = fee_schedule_from_profile(profile)


def register_fee_schedule(schedule: FeeSchedule) -> None:
    """Add/replace a schedule and keep the legacy profile registry coherent."""

    _SCHEDULES[schedule.schedule_id] = schedule
    _PROFILES[schedule.schedule_id] = FeeProfile(
        name=schedule.schedule_id,
        commission_rate=schedule.commission_rule.rate,
        trading_fee_rate=schedule.trading_fee_rule.rate,
        clearing_fee_rate=schedule.clearing_fee_rule.rate,
        vat_rate=schedule.tax_rule.rate,
        schedule_version=schedule.schedule_version,
        effective_from=schedule.effective_from,
        currency=schedule.currency,
        provenance=schedule.provenance,
    )


def resolve_fee_profile(symbol: str) -> FeeProfile:
    """Backward-compatible raw-symbol selector.

    New code must use ``select_fee_schedule`` or ``quote_fee_for_instrument``.
    The import is intentionally local so raw-symbol heuristics remain isolated
    in the explicitly named compatibility module.
    """

    from services.broker_fees_compat import resolve_legacy_fee_profile

    return resolve_legacy_fee_profile(symbol)


def _round_component(value: Decimal, rules: FeeRoundingRules) -> Decimal:
    if rules.mode != "ROUND_HALF_UP":
        raise ValueError(f"unsupported fee rounding mode: {rules.mode}")
    return value.quantize(rules.component_quantum, rounding=ROUND_HALF_UP)


def calculate_fee_components(
    gross_amount: Decimal,
    schedule: FeeSchedule,
) -> FeeBreakdown:
    """The one pure implementation of the existing fee equations."""

    rules = schedule.rounding_rules
    if not rules.round_each_component or not rules.tax_uses_rounded_components:
        raise ValueError("unsupported fee rounding contract")
    commission = _round_component(
        gross_amount * schedule.commission_rule.rate,
        rules,
    )
    trading_fee = _round_component(
        gross_amount * schedule.trading_fee_rule.rate,
        rules,
    )
    clearing_fee = _round_component(
        gross_amount * schedule.clearing_fee_rule.rate,
        rules,
    )
    pre_tax_cost = commission + trading_fee + clearing_fee
    taxes = _round_component(pre_tax_cost * schedule.tax_rule.rate, rules)
    return FeeBreakdown(
        gross_amount=gross_amount,
        commission=commission,
        trading_fee=trading_fee,
        clearing_fee=clearing_fee,
        vat=taxes,
    )


def _decimal_key(value: Decimal) -> str:
    if value == 0:
        return "0"
    return format(value.normalize(), "f")


def _quote_ref(*parts: str) -> str:
    payload = "|".join(parts).encode("utf-8")
    return "feeq_" + hashlib.sha256(payload).hexdigest()[:24]


def calculate_fee_quote(
    schedule: FeeSchedule,
    *,
    side: TradeSide,
    quantity: Decimal,
    unit_price: Decimal,
    currency: str,
    quoted_at: datetime,
    effective_at: datetime,
    warnings: tuple[str, ...] = (),
    provenance: tuple[str, ...] = (),
) -> FeeQuote:
    """Pure quote arithmetic; performs no selection, I/O, ORM, or clock read."""

    gross_amount = quantity * unit_price
    breakdown = calculate_fee_components(gross_amount, schedule)
    total_cost = breakdown.total_fees_incl_vat
    net_cash_effect = (
        -(gross_amount + total_cost)
        if side == TradeSide.BUY
        else gross_amount - total_cost
    )
    quote_ref = _quote_ref(
        _FEE_QUOTE_CONTRACT_VERSION,
        schedule.schedule_id,
        schedule.schedule_version,
        side.value,
        _decimal_key(quantity),
        _decimal_key(unit_price),
        currency,
        effective_at.isoformat(),
    )
    return FeeQuote(
        contract_version=_FEE_QUOTE_CONTRACT_VERSION,
        quote_ref=quote_ref,
        status=FeeQuoteStatus.QUOTED,
        side=side,
        quantity=quantity,
        unit_price=unit_price,
        gross_amount=gross_amount,
        commission=breakdown.commission,
        trading_fee=breakdown.trading_fee,
        clearing_fee=breakdown.clearing_fee,
        taxes=breakdown.vat,
        total_cost=total_cost,
        net_cash_effect=net_cash_effect,
        currency=currency,
        schedule_id=schedule.schedule_id,
        schedule_version=schedule.schedule_version,
        quoted_at=quoted_at,
        effective_at=effective_at,
        warnings=warnings,
        provenance=schedule.provenance + provenance,
    )


def unavailable_fee_quote(
    *,
    side: TradeSide,
    currency: str | None,
    quoted_at: datetime,
    effective_at: datetime,
    reason: FeeQuoteUnavailableReason,
    identity_key: str,
    warnings: tuple[str, ...] = (),
    provenance: tuple[str, ...] = (),
) -> FeeQuote:
    """Build an explicit refusal with no optimistic monetary placeholders."""

    return FeeQuote(
        contract_version=_FEE_QUOTE_CONTRACT_VERSION,
        quote_ref=_quote_ref(
            _FEE_QUOTE_CONTRACT_VERSION,
            "UNAVAILABLE",
            side.value,
            currency or "",
            effective_at.isoformat(),
            reason.value,
            identity_key,
        ),
        status=FeeQuoteStatus.UNAVAILABLE,
        side=side,
        quantity=None,
        unit_price=None,
        gross_amount=None,
        commission=None,
        trading_fee=None,
        clearing_fee=None,
        taxes=None,
        total_cost=None,
        net_cash_effect=None,
        currency=currency,
        schedule_id=None,
        schedule_version=None,
        quoted_at=quoted_at,
        effective_at=effective_at,
        warnings=warnings,
        provenance=provenance,
        unavailable_reason=reason,
    )


def select_fee_schedule(
    facts: ExecutionInstrumentFacts,
    *,
    side: TradeSide,
    effective_at: datetime,
    explicit_schedule: FeeSchedule | None = None,
    account_context: Mapping[str, str] | None = None,
) -> FeeScheduleSelection:
    """Select from authoritative Registry facts without inspecting a symbol."""

    del side, account_context  # accepted for the stable future selector boundary
    provenance = ("services.broker_fees.select_fee_schedule",)
    if facts.resolution_error:
        return FeeScheduleSelection(
            None,
            FeeQuoteUnavailableReason.REGISTRY_FAILURE,
            (facts.reason or "Registry facts resolution failed",),
            provenance,
        )
    if facts.resolution_status == ExecutionResolutionOutcome.AMBIGUOUS:
        return FeeScheduleSelection(
            None,
            FeeQuoteUnavailableReason.IDENTITY_AMBIGUOUS,
            (facts.reason or "Registry identity is ambiguous",),
            provenance,
        )
    if facts.resolution_status == ExecutionResolutionOutcome.UNKNOWN:
        return FeeScheduleSelection(
            None,
            FeeQuoteUnavailableReason.IDENTITY_UNKNOWN,
            (facts.reason or "Registry identity is unknown",),
            provenance,
        )
    if (
        facts.resolution_status == ExecutionResolutionOutcome.NOT_TRADABLE
        or facts.execution_role == ExecutionRole.REFERENCE
        or facts.tradable is False
    ):
        return FeeScheduleSelection(
            None,
            FeeQuoteUnavailableReason.NOT_TRADABLE,
            (facts.reason or "Registry instrument is not tradable",),
            provenance,
        )
    if (
        facts.resolution_status != ExecutionResolutionOutcome.RESOLVED
        or facts.execution_role != ExecutionRole.TRADABLE
        or facts.instrument_form == ExecutionInstrumentForm.UNKNOWN
    ):
        return FeeScheduleSelection(
            None,
            FeeQuoteUnavailableReason.IDENTITY_UNKNOWN,
            (facts.reason or "Registry facts do not establish a tradable instrument",),
            provenance,
        )

    if explicit_schedule is not None:
        schedule = explicit_schedule
        selection_provenance = provenance + ("explicit schedule override",)
    elif (
        facts.instrument_form == ExecutionInstrumentForm.DEPOSITARY_RECEIPT
        and facts.exchange == "SET"
        and facts.currency == "THB"
    ):
        schedule = get_fee_schedule(_DR_SCHEDULE_ID)
        selection_provenance = provenance + (
            "ExecutionInstrumentFacts.instrument_form=DEPOSITARY_RECEIPT,"
            "exchange=SET,currency=THB",
        )
    elif facts.exchange == "SET" and facts.currency == "THB":
        schedule = get_fee_schedule(_SET_SCHEDULE_ID)
        selection_provenance = provenance + (
            "ExecutionInstrumentFacts.exchange=SET,currency=THB",
        )
    else:
        return FeeScheduleSelection(
            None,
            FeeQuoteUnavailableReason.MISSING_FEE_SCHEDULE,
            (
                "No registered fee schedule matches the Registry-backed "
                f"listing ({facts.exchange or 'unknown exchange'}, "
                f"{facts.currency or 'unknown currency'})",
            ),
            provenance,
        )

    if schedule.effective_from is not None and effective_at < schedule.effective_from:
        return FeeScheduleSelection(
            None,
            FeeQuoteUnavailableReason.MISSING_FEE_SCHEDULE,
            ("Selected fee schedule is not effective at the requested time",),
            selection_provenance,
        )
    if schedule.currency is not None and facts.currency != schedule.currency:
        return FeeScheduleSelection(
            None,
            FeeQuoteUnavailableReason.MISSING_FEE_SCHEDULE,
            ("Selected fee schedule does not apply to the Registry currency",),
            selection_provenance,
        )
    return FeeScheduleSelection(schedule, None, (), selection_provenance)


def quote_fee_for_instrument(
    facts: ExecutionInstrumentFacts,
    *,
    side: TradeSide,
    quantity: Decimal,
    unit_price: Decimal,
    quoted_at: datetime,
    effective_at: datetime,
    explicit_schedule: FeeSchedule | None = None,
    account_context: Mapping[str, str] | None = None,
) -> FeeQuote:
    """Facts-backed planning-capable quote interface."""

    selection = select_fee_schedule(
        facts,
        side=side,
        effective_at=effective_at,
        explicit_schedule=explicit_schedule,
        account_context=account_context,
    )
    if selection.schedule is None:
        assert selection.unavailable_reason is not None
        return unavailable_fee_quote(
            side=side,
            currency=facts.currency,
            quoted_at=quoted_at,
            effective_at=effective_at,
            reason=selection.unavailable_reason,
            identity_key=facts.query,
            warnings=selection.warnings,
            provenance=selection.provenance,
        )
    return calculate_fee_quote(
        selection.schedule,
        side=side,
        quantity=quantity,
        unit_price=unit_price,
        currency=facts.currency or selection.schedule.currency or "",
        quoted_at=quoted_at,
        effective_at=effective_at,
        warnings=selection.warnings,
        provenance=selection.provenance,
    )


def calc_fees(
    gross_amount: Decimal,
    profile: FeeProfile | None = None,
) -> FeeBreakdown:
    """Backward-compatible adapter over the shared pure component calculator."""

    selected_profile = profile or get_profile(_SET_SCHEDULE_ID)
    return calculate_fee_components(
        gross_amount,
        fee_schedule_from_profile(selected_profile),
    )


__all__ = [
    "DR_STANDARD",
    "FREE",
    "SET_STANDARD",
    "FeeBreakdown",
    "FeeProfile",
    "FeeQuote",
    "FeeQuoteStatus",
    "FeeQuoteUnavailableReason",
    "FeeRoundingRules",
    "FeeSchedule",
    "FeeScheduleSelection",
    "PercentageFeeRule",
    "TradeSide",
    "calc_fees",
    "calculate_fee_components",
    "calculate_fee_quote",
    "fee_schedule_from_profile",
    "get_fee_schedule",
    "get_profile",
    "quote_fee_for_instrument",
    "register_fee_schedule",
    "register_profile",
    "resolve_fee_profile",
    "select_fee_schedule",
    "unavailable_fee_quote",
]
