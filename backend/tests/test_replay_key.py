"""Tests for services/replay_key.py.

Pure-function tests, no database or network. Covers the three-tier
deterministic fallback (asset_id → canonical_symbol → raw_symbol) that
services/replay_key.py implements for M5 Track B / M6 Native Integration
Stage 0 (docs/implementation/M5_TRACK_B_NATIVE_INTEGRATION_TDD.md §2.1),
satisfying ADR-005 (docs/decisions/ADR-005_REPLAY_CORRECTNESS_BASELINE.md).

Coverage
--------
  1. asset_id present → returned, even when canonical_symbol/raw_symbol also present
  2. asset_id absent, canonical_symbol present → canonical_symbol returned
  3. asset_id absent, canonical_symbol absent, raw_symbol present → raw_symbol returned
  4. Cash-only transaction (raw_symbol=None, canonical_symbol=None) → None
  5. KBANK / KBANK.BK regression case: same ReplayKey once canonical_symbol agrees
  6. Pure/deterministic: same input always produces the same output
"""
from __future__ import annotations

import sys
import os
from datetime import date
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.transaction_canonicalizer import CanonicalTransaction
from services.replay_key import replay_key


def _ctx(
    raw_symbol: str | None = "AOT.BK",
    canonical_symbol: str | None = "AOT.BK",
    asset_id: int | None = None,
) -> CanonicalTransaction:
    ctx = CanonicalTransaction(
        id                   = 1,
        transaction_type     = "BUY",
        raw_symbol           = raw_symbol,
        canonical_symbol     = canonical_symbol,
        shares               = Decimal("100"),
        price_per_share      = Decimal("75"),
        total_amount         = Decimal("7500"),
        fees                 = Decimal("0"),
        taxes                = Decimal("0"),
        transaction_date     = date(2026, 1, 15),
        created_at           = None,
        sector               = None,
        notes                = None,
        qty_correction_delta = None,
        realized_pnl         = None,
    )
    if asset_id is not None:
        # CanonicalTransaction does not carry asset_id until M5 Track B (§4.3);
        # simulate a future post-Track-B instance via object.__setattr__ since
        # the dataclass is frozen. replay_key() reads it via getattr, so this
        # is enough to exercise the first tier without touching production code.
        object.__setattr__(ctx, "asset_id", asset_id)
    return ctx


def test_asset_id_present_takes_precedence():
    ctx = _ctx(raw_symbol="KBANK", canonical_symbol="KBANK.BK", asset_id=41)
    assert replay_key(ctx) == 41


def test_canonical_symbol_used_when_asset_id_absent():
    ctx = _ctx(raw_symbol="KBANK", canonical_symbol="KBANK.BK")
    assert replay_key(ctx) == "KBANK.BK"


def test_raw_symbol_used_when_canonical_symbol_absent():
    ctx = _ctx(raw_symbol="WEIRD", canonical_symbol=None)
    assert replay_key(ctx) == "WEIRD"


def test_cash_only_transaction_returns_none():
    ctx = _ctx(raw_symbol=None, canonical_symbol=None)
    assert replay_key(ctx) is None


def test_kbank_and_kbank_bk_produce_same_replay_key():
    # The ADR-005 regression case: two raw spellings, same canonical form,
    # no asset_id yet (Stage 0) — must merge under one ReplayKey.
    ctx_a = _ctx(raw_symbol="KBANK",    canonical_symbol="KBANK.BK")
    ctx_b = _ctx(raw_symbol="KBANK.BK", canonical_symbol="KBANK.BK")
    assert replay_key(ctx_a) == replay_key(ctx_b) == "KBANK.BK"


def test_deterministic_across_repeated_calls():
    ctx = _ctx(raw_symbol="PTT.BK", canonical_symbol="PTT.BK")
    assert replay_key(ctx) == replay_key(ctx) == replay_key(ctx)


def test_no_database_or_registry_access():
    """Pure function: calling it must never require a db session argument or
    perform any attribute access beyond the CanonicalTransaction fields."""
    import inspect
    sig = inspect.signature(replay_key)
    assert list(sig.parameters) == ["ctx"]
