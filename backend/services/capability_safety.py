"""capability_safety.py — pure capability-safety predicates (M30.1).

Design: docs/implementation/M30_capability_safety_foundation_design.md §3.1.

Every function here answers one yes/no/unknown question about a
CapabilityView, using only the seven axes CapabilityView already exposes
(services/asset_definitions/capability_view.py) — no new capability is
invented, no vocabulary word is added. Pure: no ORM, no DB session, no
network access, no logging, no global state — this is what makes the
module safe for portfolio_metrics.py to import directly (its own contract
is identical; see ARCHITECTURE.md "Portfolio Metrics Engine").

`view` is `CapabilityView | None` throughout: `None` stands for "no
CapabilityView could be resolved for this symbol" (an unknown/undefined
asset_type, an unresolvable binding, or a registry that failed to boot —
see capability_lookup_service.py). Per D7 ("absence is a declaration,
refuse loudly, never default"), an unresolved view must never silently
read as "safe" or "unsafe" — every predicate below returns `None` for that
case rather than guessing True or False.
"""
from __future__ import annotations

from typing import Optional

from services.asset_definitions.capability_view import CapabilityView
from services.asset_definitions.vocabulary import FlowType, ValuationQuestion

__all__ = [
    "permits_quantity_valuation",
    "grants_dividend_flow",
    "permits_fractional_quantity",
    "requires_price",
]


def permits_quantity_valuation(view: Optional[CapabilityView]) -> Optional[bool]:
    """True when `quantity x price` is a valid valuation formula for this
    kind, False when it is not, None when unresolvable.

    Not simply `not unit_quantity_equals_value()` — Cash's own declaration
    proves why: quantity_equals_value=True means "one unit is worth one
    unit," which already makes shares x price correct in the degenerate
    case (price=1, always). The real disqualifier is Axis 4: a kind with
    valuation_question()==IDENTITY has no market price to multiply by at
    all (Cash's Capability Projection — "identity valuation, worth its
    face amount"). Both facts must be asked.
    """
    if view is None:
        return None
    return not view.unit_quantity_equals_value() and view.valuation_question() != ValuationQuestion.IDENTITY


def grants_dividend_flow(view: Optional[CapabilityView]) -> Optional[bool]:
    """True when the kind's declaration grants a DIVIDEND flow, False when
    it does not, None when unresolvable."""
    if view is None:
        return None
    return view.grants_flow(FlowType.DIVIDEND)


def permits_fractional_quantity(view: Optional[CapabilityView]) -> Optional[bool]:
    """True when the kind's unit declaration permits fractional-quantity
    refinement (Axis 1), False when it does not, None when unresolvable."""
    if view is None:
        return None
    return view.unit_permits_fractional_refinement()


def requires_price(view: Optional[CapabilityView]) -> Optional[bool]:
    """True when valuing an instance of this kind requires a continuously
    observed market quotation (Axis 4 == CONTINUOUS_QUOTATION), False when
    it does not (IDENTITY, PERIODIC_NAV, or APPRAISAL_ON_EVENT all value an
    instance some other way), None when unresolvable.

    Deliberately narrower than "valuation_question() != IDENTITY": a fund's
    PERIODIC_NAV and a property's APPRAISAL_ON_EVENT are both non-identity
    valuations that do not require a market *price* in the sense this
    predicate's callers mean (e.g. deciding whether a `price_lookup` entry
    is expected) — conflating the three would misname what is being asked.
    """
    if view is None:
        return None
    return view.valuation_question() == ValuationQuestion.CONTINUOUS_QUOTATION
