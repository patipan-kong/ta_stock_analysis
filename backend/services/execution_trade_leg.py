"""Immutable, non-authoritative execution trade legs (M32.2).

This module is a planning projection only.  It receives the Registry-backed
facts, pure eligibility result, and already-calculated ``FeeQuote`` from its
caller; it does not resolve identity, select or recalculate fees, access ORM,
or change a legacy plan.  M32.2 uses it only for post-plan shadow diagnostics.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Mapping, Sequence

from services.broker_fees import FeeQuote, FeeQuoteStatus, TradeSide, quote_fee_for_instrument
from services.execution_eligibility import ExecutionEligibility
from services.execution_instrument_facts import (
    ExecutionInstrumentFacts,
    ExecutionInstrumentForm,
    ExecutionResolutionOutcome,
    ExecutionRole,
)

__all__ = [
    "ExecutionFundingRole",
    "LotAdjustmentSummary",
    "FractionalAdjustmentSummary",
    "LegacyExecutionTradeRequest",
    "ExecutionTradeLeg",
    "ExecutionTradeLegBuilder",
    "ShadowTradeLegComparison",
    "ExecutionTradeLegShadowProjection",
    "build_execution_trade_leg",
    "project_execution_plan_trade_legs_shadow",
]


_TRADE_LEG_CONTRACT_VERSION = "1"


class ExecutionFundingRole(str, Enum):
    """The current legacy instruction's planning job, not M31 execution role."""

    DEPLOYMENT = "DEPLOYMENT"
    FUNDING_SOURCE = "FUNDING_SOURCE"


@dataclass(frozen=True)
class LotAdjustmentSummary:
    """Records the deliberate M32.2 absence of lot-size adjustment."""

    lot_size: int | None
    requested_quantity: Decimal
    executable_quantity: Decimal
    adjusted: bool = False


@dataclass(frozen=True)
class FractionalAdjustmentSummary:
    """Records the deliberate M32.2 absence of fractional adjustment."""

    fractional_support: bool | None
    requested_quantity: Decimal
    executable_quantity: Decimal
    adjusted: bool = False


@dataclass(frozen=True)
class LegacyExecutionTradeRequest:
    """The minimum existing-plan evidence needed to project one trade leg.

    A caller must supply quantity and price explicitly.  In particular, a
    gross-only BUY allocation is not converted into a fictional quantity.
    """

    recommendation_reference: str | None
    requested_symbol: str
    side: TradeSide
    requested_quantity: Decimal
    unit_price: Decimal
    price_timestamp: datetime | None
    funding_role: ExecutionFundingRole
    provenance: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExecutionTradeLeg:
    """Immutable shadow projection of one proposed executable trade.

    ``execution_instrument_facts``, ``execution_eligibility``, and
    ``fee_quote`` deliberately retain the input objects.  The derived summary
    fields make the projection convenient to inspect but do not duplicate
    their authority.
    """

    contract_version: str
    leg_id: str
    recommendation_reference: str | None
    requested_symbol: str
    asset_id: int | None
    canonical_symbol: str | None
    side: TradeSide
    requested_quantity: Decimal
    executable_quantity: Decimal
    unit_price: Decimal | None
    price_timestamp: datetime | None
    gross_amount: Decimal | None
    fee_quote: FeeQuote
    estimated_total_cost: Decimal | None
    estimated_net_cash_effect: Decimal | None
    funding_role: ExecutionFundingRole
    execution_instrument_facts: ExecutionInstrumentFacts
    execution_eligibility: ExecutionEligibility
    instrument_form: ExecutionInstrumentForm
    execution_role: ExecutionRole
    lot_adjustment: LotAdjustmentSummary
    fractional_adjustment: FractionalAdjustmentSummary
    warnings: tuple[str, ...]
    provenance: tuple[str, ...]
    complete: bool


@dataclass(frozen=True)
class ShadowTradeLegComparison:
    """Post-plan diagnostic comparing unchanged legacy gross to a leg quote."""

    requested_symbol: str
    legacy_action: str
    legacy_gross_amount: Decimal
    trade_leg_gross_amount: Decimal | None
    estimated_total_cost: Decimal | None
    estimated_net_cash_effect: Decimal | None

    def to_log_dict(self) -> dict[str, str | None]:
        return {
            "requested_symbol": self.requested_symbol,
            "legacy_action": self.legacy_action,
            "legacy_gross_amount": format(self.legacy_gross_amount, "f"),
            "trade_leg_gross_amount": _decimal_text(self.trade_leg_gross_amount),
            "estimated_total_cost": _decimal_text(self.estimated_total_cost),
            "estimated_net_cash_effect": _decimal_text(self.estimated_net_cash_effect),
        }


@dataclass(frozen=True)
class ExecutionTradeLegShadowProjection:
    """Internal-only post-plan diagnostic; it is never added to API output."""

    legs: tuple[ExecutionTradeLeg, ...]
    comparisons: tuple[ShadowTradeLegComparison, ...]
    unprojectable_symbols: tuple[str, ...]


class ExecutionTradeLegBuilder:
    """The sole constructor boundary for ``ExecutionTradeLeg`` values."""

    def build(
        self,
        request: LegacyExecutionTradeRequest,
        facts: ExecutionInstrumentFacts,
        eligibility: ExecutionEligibility,
        fee_quote: FeeQuote,
    ) -> ExecutionTradeLeg:
        """Project existing inputs without performing lookup or fee arithmetic."""

        if fee_quote.side != request.side:
            raise ValueError("FeeQuote side must match the legacy trade request")
        if fee_quote.status == FeeQuoteStatus.QUOTED:
            if fee_quote.quantity != request.requested_quantity:
                raise ValueError("FeeQuote quantity must match the legacy trade request")
            if fee_quote.unit_price != request.unit_price:
                raise ValueError("FeeQuote price must match the legacy trade request")
            unit_price = fee_quote.unit_price
            gross_amount = fee_quote.gross_amount
            estimated_total_cost = fee_quote.total_cost
            estimated_net_cash_effect = fee_quote.net_cash_effect
            complete = eligibility.eligible
        else:
            # An unavailable quote is deliberately not treated as a free quote
            # nor as price evidence.  Quantity remains the legacy request.
            unit_price = None
            gross_amount = None
            estimated_total_cost = None
            estimated_net_cash_effect = None
            complete = False

        executable_quantity = request.requested_quantity
        lot_adjustment = LotAdjustmentSummary(
            lot_size=facts.lot_size,
            requested_quantity=request.requested_quantity,
            executable_quantity=executable_quantity,
        )
        fractional_adjustment = FractionalAdjustmentSummary(
            fractional_support=facts.fractional_support,
            requested_quantity=request.requested_quantity,
            executable_quantity=executable_quantity,
        )
        return ExecutionTradeLeg(
            contract_version=_TRADE_LEG_CONTRACT_VERSION,
            leg_id=_leg_id(request, facts, fee_quote),
            recommendation_reference=request.recommendation_reference,
            requested_symbol=request.requested_symbol,
            asset_id=(int(facts.asset_id) if facts.asset_id is not None else None),
            canonical_symbol=facts.canonical_symbol,
            side=request.side,
            requested_quantity=request.requested_quantity,
            executable_quantity=executable_quantity,
            unit_price=unit_price,
            price_timestamp=request.price_timestamp,
            gross_amount=gross_amount,
            fee_quote=fee_quote,
            estimated_total_cost=estimated_total_cost,
            estimated_net_cash_effect=estimated_net_cash_effect,
            funding_role=request.funding_role,
            execution_instrument_facts=facts,
            execution_eligibility=eligibility,
            instrument_form=facts.instrument_form,
            execution_role=facts.execution_role,
            lot_adjustment=lot_adjustment,
            fractional_adjustment=fractional_adjustment,
            warnings=_warnings_from(facts, eligibility, fee_quote),
            provenance=request.provenance + fee_quote.provenance + _facts_provenance(facts),
            complete=complete,
        )


_BUILDER = ExecutionTradeLegBuilder()


def build_execution_trade_leg(
    request: LegacyExecutionTradeRequest,
    facts: ExecutionInstrumentFacts,
    eligibility: ExecutionEligibility,
    fee_quote: FeeQuote,
) -> ExecutionTradeLeg:
    """Use the one trade-leg builder; callers must not assemble legs directly."""

    return _BUILDER.build(request, facts, eligibility, fee_quote)


def project_execution_plan_trade_legs_shadow(
    funding_actions: Sequence[Any],
    facts_by_symbol: Mapping[str, ExecutionInstrumentFacts],
    eligibility_by_symbol: Mapping[str, ExecutionEligibility],
    *,
    quoted_at: datetime,
    effective_at: datetime,
    buy_actions: Sequence[Any] = (),
) -> ExecutionTradeLegShadowProjection:
    """Project only priceable active legacy funding actions after plan creation.

    Decision Workspace BUY actions provide a gross amount but no quantity or
    price.  They are therefore explicitly retained as unprojectable rather
    than reverse-engineering a fictional executable quantity.  This function
    is orchestration-only and makes no Registry lookup; fee selection consumes
    the supplied immutable facts.
    """

    legs: list[ExecutionTradeLeg] = []
    comparisons: list[ShadowTradeLegComparison] = []
    # A BUY action has only a gross allocation today.  Keep that limitation
    # visible in the diagnostic without manufacturing a price or quantity.
    unprojectable: list[str] = [str(action.symbol) for action in buy_actions]
    for action in funding_actions:
        symbol = str(action.symbol)
        facts = facts_by_symbol.get(symbol)
        eligibility = eligibility_by_symbol.get(symbol)
        if facts is None or eligibility is None:
            unprojectable.append(symbol)
            continue
        quantity = Decimal(str(action.current_shares)) * Decimal(str(action.release_pct))
        legacy_gross = Decimal(str(action.estimated_cash_release))
        if quantity <= 0 or legacy_gross <= 0:
            unprojectable.append(symbol)
            continue
        request = LegacyExecutionTradeRequest(
            recommendation_reference=f"execution-plan:{action.action}:{symbol}",
            requested_symbol=symbol,
            side=TradeSide.SELL,
            requested_quantity=quantity,
            unit_price=legacy_gross / quantity,
            price_timestamp=None,
            funding_role=ExecutionFundingRole.FUNDING_SOURCE,
            provenance=(
                "legacy ExecutionPlanResult active funding action",
                "legacy estimated_cash_release/current_shares/release_pct",
            ),
        )
        quote = quote_fee_for_instrument(
            facts,
            side=request.side,
            quantity=request.requested_quantity,
            unit_price=request.unit_price,
            quoted_at=quoted_at,
            effective_at=effective_at,
        )
        leg = build_execution_trade_leg(request, facts, eligibility, quote)
        legs.append(leg)
        comparisons.append(
            ShadowTradeLegComparison(
                requested_symbol=symbol,
                legacy_action=str(action.action),
                legacy_gross_amount=legacy_gross,
                trade_leg_gross_amount=leg.gross_amount,
                estimated_total_cost=leg.estimated_total_cost,
                estimated_net_cash_effect=leg.estimated_net_cash_effect,
            )
        )
    return ExecutionTradeLegShadowProjection(
        legs=tuple(legs),
        comparisons=tuple(comparisons),
        unprojectable_symbols=tuple(unprojectable),
    )


def _leg_id(
    request: LegacyExecutionTradeRequest,
    facts: ExecutionInstrumentFacts,
    fee_quote: FeeQuote,
) -> str:
    payload = "|".join(
        (
            _TRADE_LEG_CONTRACT_VERSION,
            request.recommendation_reference or "",
            request.requested_symbol,
            str(facts.asset_id or ""),
            facts.canonical_symbol or "",
            request.side.value,
            format(request.requested_quantity, "f"),
            format(request.unit_price, "f"),
            fee_quote.quote_ref,
        )
    ).encode("utf-8")
    return "leg_" + hashlib.sha256(payload).hexdigest()[:24]


def _warnings_from(
    facts: ExecutionInstrumentFacts,
    eligibility: ExecutionEligibility,
    fee_quote: FeeQuote,
) -> tuple[str, ...]:
    """Carry warnings only from the three established source contracts."""

    values = (
        *((facts.reason,) if facts.reason else ()),
        *((eligibility.reason,) if not eligibility.eligible and eligibility.reason else ()),
        *fee_quote.warnings,
    )
    return tuple(dict.fromkeys(values))


def _facts_provenance(facts: ExecutionInstrumentFacts) -> tuple[str, ...]:
    return tuple(
        f"{item.fact}:{item.source_field}={item.source_value}"
        for item in facts.provenance
    )


def _decimal_text(value: Decimal | None) -> str | None:
    return format(value, "f") if value is not None else None
