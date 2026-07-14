"""capability_safety.py unit tests (M30.1).

Coverage
--------
  1. quantity valuation allowed / denied, across kinds with different
     Axis 1 (unit) and Axis 4 (valuation) declarations.
  2. dividend flow allowed / denied, across kinds with different Axis 5
     (flow) declarations.
  3. permits_fractional_quantity / requires_price, the two additional
     predicates the M30.1 brief names as examples.
  4. missing capability handling — every predicate returns None (never
     True, never False, never raises) when the view itself is unresolved.

Every CapabilityView used here is a real one, resolved from the actual
DefinitionRegistry (no fakes/mocks of CapabilityView) — a predicate change
that silently drifted from a real declaration's shape would be caught here,
the same discipline test_asset_definitions_binding_resolver.py already
uses.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services import capability_safety as safety
from services.asset_definitions import BindingResolver, DefinitionRegistry
from services.asset_domain import AssetType


def _view(asset_type: AssetType):
    resolver = BindingResolver(DefinitionRegistry.build())
    return resolver.resolve(asset_type.value)


# ── quantity valuation ──────────────────────────────────────────────────

def test_quantity_valuation_allowed_for_equity():
    # EQUITY: quantity_equals_value=False, valuation=CONTINUOUS_QUOTATION.
    assert safety.permits_quantity_valuation(_view(AssetType.EQUITY)) is True


def test_quantity_valuation_allowed_for_fund_despite_periodic_nav():
    # FUND: quantity_equals_value=False, valuation=PERIODIC_NAV (not IDENTITY).
    assert safety.permits_quantity_valuation(_view(AssetType.FUND)) is True


def test_quantity_valuation_denied_for_cash():
    # CASH: quantity_equals_value=True — shares x price is not the right
    # formula even though CASH's valuation question is IDENTITY too.
    assert safety.permits_quantity_valuation(_view(AssetType.CASH)) is False


# ── dividend flow ────────────────────────────────────────────────────────

def test_dividend_flow_allowed_for_equity():
    assert safety.grants_dividend_flow(_view(AssetType.EQUITY)) is True


def test_dividend_flow_allowed_for_etf():
    assert safety.grants_dividend_flow(_view(AssetType.ETF)) is True


def test_dividend_flow_denied_for_cash():
    # CASH grants only INTEREST.
    assert safety.grants_dividend_flow(_view(AssetType.CASH)) is False


def test_dividend_flow_denied_for_bond():
    # BOND grants COUPON, not DIVIDEND — a bond's fixed coupon must never
    # be silently accepted through a dividend-shaped check.
    assert safety.grants_dividend_flow(_view(AssetType.BOND)) is False


def test_dividend_flow_denied_for_property():
    # PROPERTY grants RENT, not DIVIDEND.
    assert safety.grants_dividend_flow(_view(AssetType.PROPERTY)) is False


# ── permits_fractional_quantity ─────────────────────────────────────────

def test_fractional_quantity_permitted_for_equity():
    assert safety.permits_fractional_quantity(_view(AssetType.EQUITY)) is True


def test_fractional_quantity_denied_for_cash():
    # CASH is continuous, not discrete — "fractional" is a discrete-unit
    # refinement that does not apply.
    assert safety.permits_fractional_quantity(_view(AssetType.CASH)) is False


def test_fractional_quantity_denied_for_property():
    # PROPERTY is discrete but explicitly indivisible.
    assert safety.permits_fractional_quantity(_view(AssetType.PROPERTY)) is False


# ── requires_price ───────────────────────────────────────────────────────

def test_requires_price_true_for_equity_and_bond():
    assert safety.requires_price(_view(AssetType.EQUITY)) is True
    assert safety.requires_price(_view(AssetType.BOND)) is True


def test_requires_price_false_for_fund_periodic_nav():
    # FUND is valued by periodic NAV, not a continuously observed price.
    assert safety.requires_price(_view(AssetType.FUND)) is False


def test_requires_price_false_for_property_appraisal():
    assert safety.requires_price(_view(AssetType.PROPERTY)) is False


def test_requires_price_false_for_cash_identity():
    assert safety.requires_price(_view(AssetType.CASH)) is False


# ── missing capability handling ─────────────────────────────────────────

def test_every_predicate_returns_none_for_unresolved_view():
    assert safety.permits_quantity_valuation(None) is None
    assert safety.grants_dividend_flow(None) is None
    assert safety.permits_fractional_quantity(None) is None
    assert safety.requires_price(None) is None
