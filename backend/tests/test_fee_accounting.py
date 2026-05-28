"""Tests for broker-grade fee accounting correctness.

Validates:
  1. Fee formula:  Commission + Trading + Clearing + VAT components
  2. Fee-inclusive cost basis on BUY (avg_cost embeds all fees)
  3. Realized P/L on SELL reflects true economic gain
  4. Fee profile resolution: SET vs DR symbols
  5. period_fees_paid in snapshots includes both fees + taxes columns
  6. Partial sell preserves avg_cost
  7. Round-trip cash reconciliation: cash_in - cash_out = net P/L

All tests use an in-memory SQLite database; no network calls.
"""
import sys
import os
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models.database import Base, Portfolio, PortfolioItem, PortfolioSnapshot, Transaction, Workspace
from services.broker_fees import (
    FeeProfile, FeeBreakdown,
    SET_STANDARD, DR_STANDARD, FREE,
    calc_fees, resolve_fee_profile, get_profile, register_profile,
)
from services.portfolio_transactions import execute_buy, execute_sell, execute_deposit


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _seed(db, cash=0.0):
    ws = Workspace(name="Test")
    db.add(ws)
    db.flush()
    p = Portfolio(workspace_id=ws.id, name="Test", cash_balance=cash)
    db.add(p)
    db.commit()
    return ws, p


def _prev_snapshot(db, portfolio_id, workspace_id, date_str, total_value):
    snap = PortfolioSnapshot(
        workspace_id=workspace_id,
        portfolio_id=portfolio_id,
        snapshot_date=date_str,
        total_value=total_value,
        cash_balance=total_value,
        total_invested=0.0,
    )
    db.add(snap)
    db.commit()
    return snap


def _today():
    return datetime.utcnow().strftime("%Y-%m-%d")


def _prev_date():
    return (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")


def run_snapshot(db, portfolio_id, workspace_id, today_str, price_map):
    import asyncio
    from services.portfolio_snapshots import generate_daily_snapshot

    async def _go():
        with patch(
            "services.portfolio_snapshots.fetch_price_info",
            side_effect=lambda sym: {"current_price": price_map.get(sym, 0.0)},
        ):
            return await generate_daily_snapshot(db, portfolio_id, workspace_id, today_str)

    return asyncio.get_event_loop().run_until_complete(_go())


# ── 1. Fee formula correctness ────────────────────────────────────────────────

class TestFeeFormula:
    """Verify individual component values match the exact SET breakdown."""

    def test_set_standard_components(self):
        gross = Decimal("10000")
        bd = calc_fees(gross, SET_STANDARD)

        assert bd.commission   == pytest.approx(Decimal("15.0000"), abs=Decimal("0.0001"))
        assert bd.trading_fee  == pytest.approx(Decimal("0.6000"),  abs=Decimal("0.0001"))
        assert bd.clearing_fee == pytest.approx(Decimal("0.1000"),  abs=Decimal("0.0001"))
        # VAT on (15.00 + 0.60 + 0.10) = 15.70 × 0.07 = 1.0990
        assert bd.vat          == pytest.approx(Decimal("1.0990"),  abs=Decimal("0.0001"))

    def test_total_equals_legacy_formula(self):
        """Total fee must equal the old single-rate formula: gross × 0.00157 × 1.07."""
        gross = Decimal("10000")
        bd = calc_fees(gross, SET_STANDARD)
        legacy = gross * Decimal("0.00157") * Decimal("1.07")
        assert bd.total_fees_incl_vat == pytest.approx(legacy, abs=Decimal("0.0005"))

    def test_free_profile_zero_fees(self):
        gross = Decimal("50000")
        bd = calc_fees(gross, FREE)
        assert bd.total_fees_incl_vat == Decimal("0")
        assert bd.net_buy_amount() == gross
        assert bd.net_sell_proceeds() == gross

    def test_net_buy_is_gross_plus_all_fees(self):
        gross = Decimal("20000")
        bd = calc_fees(gross)
        assert bd.net_buy_amount() == gross + bd.total_fees_incl_vat

    def test_net_sell_is_gross_minus_all_fees(self):
        gross = Decimal("20000")
        bd = calc_fees(gross)
        assert bd.net_sell_proceeds() == gross - bd.total_fees_incl_vat

    def test_to_dict_keys(self):
        bd = calc_fees(Decimal("5000"))
        d = bd.to_dict()
        for key in ("gross_amount", "commission", "trading_fee", "clearing_fee",
                    "vat", "total_excl_vat", "total_incl_vat"):
            assert key in d


# ── 2. Fee profile resolution ─────────────────────────────────────────────────

class TestFeeProfileResolution:
    """resolve_fee_profile must pick the right profile per symbol type."""

    def test_set_stock(self):
        assert resolve_fee_profile("SCB.BK").name  == "SET_STANDARD"
        assert resolve_fee_profile("KBANK.BK").name == "SET_STANDARD"
        assert resolve_fee_profile("PTT.BK").name   == "SET_STANDARD"

    def test_dr_symbol(self):
        assert resolve_fee_profile("NVDA01.BK").name  == "DR_STANDARD"
        assert resolve_fee_profile("MSFT01.BK").name  == "DR_STANDARD"
        assert resolve_fee_profile("AAPL08.BK").name  == "DR_STANDARD"

    def test_us_stock_falls_back_to_set(self):
        # US stocks currently default to SET_STANDARD (placeholder)
        assert resolve_fee_profile("AAPL").name  == "SET_STANDARD"
        assert resolve_fee_profile("TSLA").name  == "SET_STANDARD"

    def test_register_custom_profile(self):
        custom = FeeProfile(
            name="CUSTOM_ZERO_COMM",
            commission_rate=Decimal("0"),
            trading_fee_rate=Decimal("0.00006"),
            clearing_fee_rate=Decimal("0.00001"),
            vat_rate=Decimal("0.07"),
        )
        register_profile(custom)
        assert get_profile("CUSTOM_ZERO_COMM") is custom

    def test_get_profile_unknown_raises(self):
        with pytest.raises(KeyError):
            get_profile("DOES_NOT_EXIST_PROFILE")


# ── 3. Fee-inclusive cost basis ───────────────────────────────────────────────

class TestFeeInclusiveCostBasis:
    """BUY avg_cost must embed all fees so realized P/L on SELL is economically correct."""

    def test_new_position_avg_cost_includes_fees(self):
        db = make_session()
        ws, p = _seed(db, cash=100_000.0)

        result = execute_buy(db, ws.id, p.id, "SCB.BK", shares=100, price_per_share=190.0)

        gross  = 100 * 190
        bd     = calc_fees(Decimal(str(gross)), SET_STANDARD)
        expected_avg = float(bd.net_buy_amount() / Decimal("100"))

        assert result["holding"]["avg_cost"] == pytest.approx(expected_avg, abs=0.001)

    def test_avg_cost_strictly_above_price(self):
        """avg_cost must always exceed the raw buy price when fees > 0."""
        db = make_session()
        ws, p = _seed(db, cash=200_000.0)
        execute_buy(db, ws.id, p.id, "PTT.BK", shares=500, price_per_share=30.0)

        item = db.query(PortfolioItem).filter_by(portfolio_id=p.id, symbol="PTT.BK").first()
        assert item.avg_cost > 30.0

    def test_partial_add_weighted_average(self):
        """Adding to an existing position must produce a correct fee-inclusive weighted avg."""
        db = make_session()
        ws, p = _seed(db, cash=500_000.0)

        r1 = execute_buy(db, ws.id, p.id, "KBANK.BK", shares=100, price_per_share=150.0)
        avg1 = r1["holding"]["avg_cost"]

        r2 = execute_buy(db, ws.id, p.id, "KBANK.BK", shares=200, price_per_share=160.0)
        avg2 = r2["holding"]["avg_cost"]

        # Manual computation
        bd1 = calc_fees(Decimal("15000"), SET_STANDARD)
        bd2 = calc_fees(Decimal("32000"), SET_STANDARD)
        expected_avg = float(
            (bd1.net_buy_amount() + bd2.net_buy_amount()) / Decimal("300")
        )
        assert avg2 == pytest.approx(expected_avg, abs=0.001)

    def test_fees_taxes_columns_split(self):
        """Transaction must store fees = excl_vat and taxes = vat (not the old lump sum)."""
        db = make_session()
        ws, p = _seed(db, cash=100_000.0)
        result = execute_buy(db, ws.id, p.id, "CPALL.BK", shares=100, price_per_share=500.0)

        tx = db.query(Transaction).filter_by(id=result["transaction_id"]).first()
        gross = Decimal("50000")
        bd    = calc_fees(gross, SET_STANDARD)

        assert tx.fees  == pytest.approx(float(bd.total_fees_excl_vat), abs=0.001)
        assert tx.taxes == pytest.approx(float(bd.vat),                 abs=0.001)
        # Old code stored fees = total, taxes = 0.  With new code both are non-zero.
        assert tx.taxes > 0


# ── 4. SELL realized P/L ─────────────────────────────────────────────────────

class TestSellRealizedPnl:
    """SELL realized P/L must equal true economic gain: cash_out - cost_in."""

    def test_round_trip_pnl_matches_cash_flow(self):
        """net_sell_proceeds - total_buy_cost = realized_pnl.

        The P/L stored in the SELL notes must equal the true round-trip gain,
        which is (net sell cash) - (net buy cash including buy fees).
        """
        db = make_session()
        ws, p = _seed(db, cash=50_000.0)

        buy_result  = execute_buy(db,  ws.id, p.id, "SCB.BK", shares=100, price_per_share=190.0)
        cash_after_buy = buy_result["cash_balance"]

        sell_result = execute_sell(db, ws.id, p.id, "SCB.BK", shares=100, price_per_share=200.0)

        gross_buy  = Decimal("19000")
        bd_buy     = calc_fees(gross_buy, SET_STANDARD)
        gross_sell = Decimal("20000")
        bd_sell    = calc_fees(gross_sell, SET_STANDARD)

        expected_pnl = float(
            bd_sell.net_sell_proceeds() - bd_buy.net_buy_amount()
        )
        assert sell_result["realized_pnl"] == pytest.approx(expected_pnl, abs=0.01)

    def test_partial_sell_avg_cost_preserved(self):
        """Avg_cost must not change after a partial sell."""
        db = make_session()
        ws, p = _seed(db, cash=200_000.0)
        buy_result = execute_buy(db, ws.id, p.id, "KBANK.BK", shares=200, price_per_share=150.0)
        avg_before = buy_result["holding"]["avg_cost"]

        sell_result = execute_sell(db, ws.id, p.id, "KBANK.BK", shares=100, price_per_share=160.0)
        avg_after = sell_result["holding"]["avg_cost"]

        assert avg_after == pytest.approx(avg_before, abs=0.0001)
        assert sell_result["holding"]["shares"] == pytest.approx(100.0, abs=0.001)

    def test_sell_pnl_note_matches_returned_value(self):
        """The P&L embedded in transaction notes must match the returned realized_pnl."""
        import re
        db = make_session()
        ws, p = _seed(db, cash=100_000.0)
        execute_buy(db, ws.id, p.id, "PTT.BK", shares=500, price_per_share=30.0)
        result = execute_sell(db, ws.id, p.id, "PTT.BK", shares=500, price_per_share=35.0)

        tx = db.query(Transaction).filter_by(id=result["transaction_id"]).first()
        m = re.search(r"Realized P&L:\s*([-+]?\d+\.?\d*)", tx.notes)
        assert m is not None
        assert float(m.group(1)) == pytest.approx(result["realized_pnl"], abs=0.001)

    def test_loss_scenario(self):
        """Selling below avg_cost (which includes buy fees) yields a negative P/L."""
        db = make_session()
        ws, p = _seed(db, cash=100_000.0)
        execute_buy(db, ws.id, p.id, "XYZ.BK", shares=100, price_per_share=200.0)
        result = execute_sell(db, ws.id, p.id, "XYZ.BK", shares=100, price_per_share=195.0)
        assert result["realized_pnl"] < 0

    def test_sell_fees_taxes_split(self):
        db = make_session()
        ws, p = _seed(db, cash=100_000.0)
        execute_buy(db, ws.id, p.id, "SCB.BK", shares=100, price_per_share=200.0)
        result = execute_sell(db, ws.id, p.id, "SCB.BK", shares=100, price_per_share=210.0)

        tx = db.query(Transaction).filter_by(id=result["transaction_id"]).first()
        gross = Decimal("21000")
        bd    = calc_fees(gross, SET_STANDARD)

        assert tx.fees  == pytest.approx(float(bd.total_fees_excl_vat), abs=0.001)
        assert tx.taxes == pytest.approx(float(bd.vat),                 abs=0.001)
        assert tx.taxes > 0


# ── 5. Cash balance integrity ─────────────────────────────────────────────────

class TestCashIntegrity:
    """Cash balance must reconcile with transaction ledger at all times."""

    def test_buy_reduces_cash_by_gross_plus_all_fees(self):
        db = make_session()
        ws, p = _seed(db, cash=50_000.0)
        result = execute_buy(db, ws.id, p.id, "SCB.BK", shares=100, price_per_share=190.0)

        gross = Decimal("19000")
        bd    = calc_fees(gross, SET_STANDARD)
        expected_cash = 50_000.0 - float(bd.net_buy_amount())
        assert result["cash_balance"] == pytest.approx(expected_cash, abs=0.01)

    def test_sell_increases_cash_by_net_proceeds(self):
        db = make_session()
        ws, p = _seed(db, cash=50_000.0)
        buy_result  = execute_buy(db, ws.id, p.id, "SCB.BK", shares=100, price_per_share=190.0)
        cash_after_buy = buy_result["cash_balance"]

        result = execute_sell(db, ws.id, p.id, "SCB.BK", shares=100, price_per_share=200.0)
        gross_sell = Decimal("20000")
        bd_sell    = calc_fees(gross_sell, SET_STANDARD)
        expected_cash = cash_after_buy + float(bd_sell.net_sell_proceeds())
        assert result["cash_balance"] == pytest.approx(expected_cash, abs=0.01)

    def test_nav_invariant_after_buy_at_purchase_price(self):
        """At the exact moment of purchase, NAV = cash + equity must hold.

        BUY moves cash_out → equity_in at gross (not including fees).
        The fee drag is immediate: NAV decreases by exactly total_fees.
        """
        db = make_session()
        ws, p = _seed(db, cash=100_000.0)
        result = execute_buy(db, ws.id, p.id, "AAPL", shares=100, price_per_share=150.0)

        cash  = result["cash_balance"]
        gross = Decimal("15000")
        bd    = calc_fees(gross, SET_STANDARD)
        # equity at purchase price (not avg_cost)
        equity_at_px = 100 * 150.0
        nav   = cash + equity_at_px
        # NAV should be 100k - fees
        expected_nav = 100_000.0 - float(bd.total_fees_incl_vat)
        assert nav == pytest.approx(expected_nav, abs=0.10)


# ── 6. Snapshot period_fees_paid includes taxes ───────────────────────────────

class TestSnapshotFeesIncludeVAT:
    """period_fees_paid must sum both fees (excl_vat) and taxes (vat) columns."""

    def test_period_fees_paid_is_total_incl_vat(self):
        """After one BUY, period_fees_paid must equal total_fees_incl_vat."""
        db = make_session()
        ws, p = _seed(db, cash=100_000.0)
        _prev_snapshot(db, p.id, ws.id, _prev_date(), 100_000.0)

        buy_result = execute_buy(db, ws.id, p.id, "SCB.BK", shares=100, price_per_share=190.0)

        result = run_snapshot(db, p.id, ws.id, _today(), {"SCB.BK": 190.0})

        gross = Decimal("19000")
        bd    = calc_fees(gross, SET_STANDARD)
        expected_fees = float(bd.total_fees_incl_vat)

        assert result["period_fees_paid"] == pytest.approx(expected_fees, abs=0.01)

    def test_period_fees_buy_and_sell_combined(self):
        """period_fees_paid accumulates fees from both BUY and SELL in the period."""
        db = make_session()
        ws, p = _seed(db, cash=200_000.0)
        _prev_snapshot(db, p.id, ws.id, _prev_date(), 200_000.0)

        execute_buy(db, ws.id, p.id, "KBANK.BK", shares=200, price_per_share=150.0)
        execute_sell(db, ws.id, p.id, "KBANK.BK", shares=200, price_per_share=155.0)

        result = run_snapshot(db, p.id, ws.id, _today(), {})

        bd_buy  = calc_fees(Decimal("30000"), SET_STANDARD)
        bd_sell = calc_fees(Decimal("31000"), SET_STANDARD)
        expected = float(bd_buy.total_fees_incl_vat + bd_sell.total_fees_incl_vat)

        assert result["period_fees_paid"] == pytest.approx(expected, abs=0.05)


# ── 7. DR compatibility ───────────────────────────────────────────────────────

class TestDRCompatibility:
    """DR instruments must use DR_STANDARD profile automatically."""

    def test_dr_buy_uses_dr_profile(self):
        db = make_session()
        ws, p = _seed(db, cash=100_000.0)
        result = execute_buy(db, ws.id, p.id, "NVDA01.BK", shares=10, price_per_share=4_000.0)
        assert result["fee_profile"] == "DR_STANDARD"

    def test_dr_and_set_same_rates_currently(self):
        """DR_STANDARD currently has identical rates to SET_STANDARD."""
        gross = Decimal("100000")
        bd_set = calc_fees(gross, SET_STANDARD)
        bd_dr  = calc_fees(gross, DR_STANDARD)
        assert bd_set.total_fees_incl_vat == bd_dr.total_fees_incl_vat

    def test_dr_profile_can_be_overridden_independently(self):
        """After patching DR_STANDARD rates, DR symbol gets different fees than SET."""
        from services.broker_fees import FeeProfile, register_profile, calc_fees
        custom_dr = FeeProfile(
            name="DR_STANDARD",
            commission_rate=Decimal("0.001"),   # lower commission
            trading_fee_rate=Decimal("0.00006"),
            clearing_fee_rate=Decimal("0.00001"),
            vat_rate=Decimal("0.07"),
        )
        register_profile(custom_dr)

        gross = Decimal("100000")
        bd_set = calc_fees(gross, SET_STANDARD)
        bd_dr  = calc_fees(gross, custom_dr)
        assert bd_dr.total_fees_incl_vat < bd_set.total_fees_incl_vat

        # Restore
        register_profile(DR_STANDARD)
