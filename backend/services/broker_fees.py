"""Configurable broker fee profiles for the transaction accounting engine.

Thai SET standard fee breakdown (used as the default):
    Commission   = Gross × 0.15%   (0.0015)
    Trading Fee  = Gross × 0.006%  (0.00006)
    Clearing Fee = Gross × 0.001%  (0.00001)
    Sub-total    = Gross × 0.157%  (0.00157)
    VAT          = Sub-total × 7%
    Total        = Sub-total × 1.07 ≈ Gross × 0.0016799

The fee components are tracked individually so:
  • Transaction.fees  stores the pre-VAT sub-total (commission + trading + clearing)
  • Transaction.taxes stores the VAT amount
  • Their sum equals the total cost of transacting

Profiles are held in a runtime registry so new structures (e.g. US equities,
offshore DRs) can be registered without touching this module.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

_CENT = Decimal("0.0001")


@dataclass(frozen=True)
class FeeProfile:
    """Rate definitions for one broker/exchange combination."""
    name: str
    commission_rate: Decimal      # broker commission fraction (e.g. 0.0015)
    trading_fee_rate: Decimal     # exchange trading fee fraction
    clearing_fee_rate: Decimal    # clearing/settlement fee fraction
    vat_rate: Decimal             # VAT applied to (commission + trading + clearing)


@dataclass
class FeeBreakdown:
    """Computed fee components for one trade leg."""
    gross_amount: Decimal
    commission: Decimal
    trading_fee: Decimal
    clearing_fee: Decimal
    vat: Decimal

    @property
    def total_fees_excl_vat(self) -> Decimal:
        """Pre-VAT subtotal → stored in Transaction.fees."""
        return self.commission + self.trading_fee + self.clearing_fee

    @property
    def total_fees_incl_vat(self) -> Decimal:
        """Full fee burden → total_fees_excl_vat + vat."""
        return self.total_fees_excl_vat + self.vat

    def net_buy_amount(self) -> Decimal:
        """Total cash outflow for a BUY: Gross + all fees + VAT."""
        return self.gross_amount + self.total_fees_incl_vat

    def net_sell_proceeds(self) -> Decimal:
        """Total cash inflow for a SELL: Gross − all fees − VAT."""
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


# ── Built-in profiles ─────────────────────────────────────────────────────────

SET_STANDARD = FeeProfile(
    name="SET_STANDARD",
    commission_rate=Decimal("0.0015"),
    trading_fee_rate=Decimal("0.00006"),
    clearing_fee_rate=Decimal("0.00001"),
    vat_rate=Decimal("0.07"),
)

# Depository Receipts trade on SET at identical rates.
# Defined separately so a future amendment can be applied narrowly
# without touching the base SET_STANDARD profile.
DR_STANDARD = FeeProfile(
    name="DR_STANDARD",
    commission_rate=Decimal("0.0015"),
    trading_fee_rate=Decimal("0.00006"),
    clearing_fee_rate=Decimal("0.00001"),
    vat_rate=Decimal("0.07"),
)

# Zero-fee profile: test fixtures, simulation, or commission-free accounts
FREE = FeeProfile(
    name="FREE",
    commission_rate=Decimal("0"),
    trading_fee_rate=Decimal("0"),
    clearing_fee_rate=Decimal("0"),
    vat_rate=Decimal("0"),
)

_PROFILES: dict[str, FeeProfile] = {
    p.name: p for p in (SET_STANDARD, DR_STANDARD, FREE)
}

# DR pattern: one-or-more letters + exactly two digits + .BK
_DR_RE = re.compile(r"^[A-Z]+\d{2}\.BK$", re.IGNORECASE)


def get_profile(name: str) -> FeeProfile:
    """Return a registered profile by name. Raises KeyError for unknown names."""
    return _PROFILES[name]


def register_profile(profile: FeeProfile) -> None:
    """Add or replace a profile in the runtime registry (thread-unsafe; call at startup)."""
    _PROFILES[profile.name] = profile


def resolve_fee_profile(symbol: str) -> FeeProfile:
    """Auto-select the correct fee profile for a symbol.

    Resolution order (first match wins):
      1. DR symbols (e.g. NVDA01.BK, MSFT01.BK) → DR_STANDARD
      2. Thai SET .BK symbols                     → SET_STANDARD
      3. All other symbols                        → SET_STANDARD (placeholder;
                                                     update when US trading is added)
    """
    if _DR_RE.match(symbol):
        return DR_STANDARD
    return SET_STANDARD


def calc_fees(gross_amount: Decimal, profile: FeeProfile | None = None) -> FeeBreakdown:
    """Compute all broker fee components for one trade leg.

    Args:
        gross_amount: Share_Unit × Unit_Price as Decimal.
        profile:      FeeProfile to apply. Defaults to SET_STANDARD.

    Returns:
        FeeBreakdown with each component rounded to 4 decimal places.

    Formula:
        commission   = gross × commission_rate
        trading_fee  = gross × trading_fee_rate
        clearing_fee = gross × clearing_fee_rate
        vat          = (commission + trading_fee + clearing_fee) × vat_rate

    Numeric example (gross = 10,000):
        commission   = 10,000 × 0.0015   = 15.0000
        trading_fee  = 10,000 × 0.00006  =  0.6000
        clearing_fee = 10,000 × 0.00001  =  0.1000
        vat          = 15.71 × 0.07      =  1.0997
        total        = 16.7997
    """
    p = profile or SET_STANDARD
    commission   = (gross_amount * p.commission_rate).quantize(_CENT, rounding=ROUND_HALF_UP)
    trading_fee  = (gross_amount * p.trading_fee_rate).quantize(_CENT, rounding=ROUND_HALF_UP)
    clearing_fee = (gross_amount * p.clearing_fee_rate).quantize(_CENT, rounding=ROUND_HALF_UP)
    vat = (
        (commission + trading_fee + clearing_fee) * p.vat_rate
    ).quantize(_CENT, rounding=ROUND_HALF_UP)
    return FeeBreakdown(
        gross_amount=gross_amount,
        commission=commission,
        trading_fee=trading_fee,
        clearing_fee=clearing_fee,
        vat=vat,
    )
