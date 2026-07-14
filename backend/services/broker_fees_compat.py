"""Explicit legacy fee-schedule compatibility for M32.1.

Current transaction posting must preserve the pre-M32 raw-symbol behavior
while Registry coverage remains incomplete.  This module is the only owner of
that heuristic.  Facts-backed fee selection in ``services.broker_fees`` never
imports or consults it.
"""
from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal

from services.broker_fees import (
    FeeProfile,
    FeeQuote,
    TradeSide,
    calculate_fee_quote,
    fee_schedule_from_profile,
    get_fee_schedule,
    get_profile,
)

_DR_STANDARD_SCHEDULE_ID = "DR_STANDARD"
_SET_STANDARD_SCHEDULE_ID = "SET_STANDARD"

# Preserved verbatim from the pre-M32 resolver.  It is compatibility evidence,
# never an authoritative instrument classification.
_LEGACY_DR_SYMBOL_RE = re.compile(r"^[A-Z]+\d{2}\.BK$", re.IGNORECASE)


def resolve_legacy_fee_profile(symbol: str) -> FeeProfile:
    """Return the currently registered profile selected by the legacy rule."""

    profile_id = (
        _DR_STANDARD_SCHEDULE_ID
        if _LEGACY_DR_SYMBOL_RE.match(symbol)
        else _SET_STANDARD_SCHEDULE_ID
    )
    return get_profile(profile_id)


def resolve_legacy_fee_schedule(symbol: str):
    """Return the registered schedule selected by the legacy rule."""

    schedule_id = (
        _DR_STANDARD_SCHEDULE_ID
        if _LEGACY_DR_SYMBOL_RE.match(symbol)
        else _SET_STANDARD_SCHEDULE_ID
    )
    return get_fee_schedule(schedule_id)


def quote_transaction_fee_compat(
    symbol: str,
    *,
    side: TradeSide,
    quantity: Decimal,
    unit_price: Decimal,
    currency: str,
    quoted_at: datetime,
    effective_at: datetime,
    profile_override: FeeProfile | None = None,
) -> FeeQuote:
    """Quote current writes through the isolated parity path."""

    if profile_override is None:
        schedule = resolve_legacy_fee_schedule(symbol)
        warnings = (
            "Legacy raw-symbol fee schedule compatibility was used; "
            "this is not Registry-backed instrument classification.",
        )
        provenance = ("services.broker_fees_compat.resolve_legacy_fee_schedule",)
    else:
        schedule = fee_schedule_from_profile(profile_override)
        warnings = ()
        provenance = ("explicit FeeProfile override",)
    return calculate_fee_quote(
        schedule,
        side=side,
        quantity=quantity,
        unit_price=unit_price,
        currency=currency,
        quoted_at=quoted_at,
        effective_at=effective_at,
        warnings=warnings,
        provenance=provenance,
    )


__all__ = [
    "quote_transaction_fee_compat",
    "resolve_legacy_fee_profile",
    "resolve_legacy_fee_schedule",
]
