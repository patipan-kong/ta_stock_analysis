"""Tests for services/ledger_validator.py.

All tests are read-only and run without a live database.
Mock transaction/snapshot/portfolio objects use SimpleNamespace.

Coverage
--------
  Structural checks
    1.  DUP_INITIAL_POSITION   — same symbol + date, multiple INITIAL_POSITION
    2.  SYMBOL_ALIAS           — multiple raw forms → same canonical ticker
    3.  NULL_SYMBOL            — equity tx with no symbol
    4.  ZERO_SHARES            — equity tx with shares=0 or None
    5.  ZERO_PRICE             — BUY/INITIAL_POSITION with price=0 or None
    6.  PRE_PORTFOLIO_TX       — transaction_date before portfolio.created_at
    7.  LARGE_DATE_SKEW        — created_at vs transaction_date gap
    8.  DUP_TX_FINGERPRINT     — identical (type, symbol, shares, price, date)
  Replay checks
    9.  SELL_WITHOUT_HOLDING   — SELL before any BUY for that symbol
   10.  NEG_SHARE_BALANCE      — SELL produces negative shares
   11.  NEG_CASH_BALANCE       — BUY drives cash below zero
   12.  QCORR_WITHOUT_HOLDING  — QUANTITY_CORRECTION on absent symbol
   13.  Clean buy-sell sequence → no findings
  DB consistency checks
   14.  CASH_MISMATCH          — replayed cash ≠ Portfolio.cash_balance
   15.  HOLDINGS_MISMATCH      — missing, extra, or differing share counts
   16.  SNAPSHOT_CASH_MISMATCH — replayed cash at snapshot date ≠ stored value
  Report properties
   17.  overall_severity derivation
   18.  Severity sort order in report.findings
"""
from __future__ import annotations

import sys
import os
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.ledger_validator import (
    FindingSeverity,
    LedgerFinding,
    LedgerValidationReport,
    _ReplayState,
    _check_cash_consistency,
    _check_date_skew,
    _check_duplicate_fingerprints,
    _check_duplicate_initial_positions,
    _check_holdings_consistency,
    _check_null_symbols,
    _check_pre_portfolio_transactions,
    _check_snapshot_cash_consistency,
    _check_symbol_aliases,
    _check_zero_prices,
    _check_zero_shares,
    _replay_and_check,
)


# ══════════════════════════════════════════════════════════════════════════════
# Helpers — lightweight mock objects (no DB required)
# ══════════════════════════════════════════════════════════════════════════════

def _tx(
    tx_id: int,
    tx_type: str,
    symbol: str | None = None,
    shares: float | None = None,
    price: float | None = None,
    amount: float = 0.0,
    date_str: str = "2026-01-01",
    created_str: str | None = None,
    notes: str | None = None,
) -> SimpleNamespace:
    tx_date    = datetime.strptime(date_str, "%Y-%m-%d")
    created_at = (
        datetime.strptime(created_str, "%Y-%m-%d")
        if created_str
        else tx_date
    )
    return SimpleNamespace(
        id               = tx_id,
        transaction_type = tx_type,
        symbol           = symbol,
        shares           = shares,
        price_per_share  = price,
        total_amount     = amount,
        transaction_date = tx_date,
        created_at       = created_at,
        notes            = notes,
    )


def _portfolio(
    port_id: int = 1,
    name: str = "Test",
    cash: float = 100_000.0,
    created_str: str = "2025-01-01",
) -> SimpleNamespace:
    return SimpleNamespace(
        id           = port_id,
        name         = name,
        cash_balance = cash,
        created_at   = datetime.strptime(created_str, "%Y-%m-%d"),
    )


def _item(
    symbol: str,
    shares: float,
    avg_cost: float = 50.0,
    portfolio_id: int = 1,
) -> SimpleNamespace:
    return SimpleNamespace(
        portfolio_id = portfolio_id,
        symbol       = symbol,
        shares       = shares,
        avg_cost     = avg_cost,
    )


def _snap(
    snap_id: int,
    date_str: str,
    cash: float,
    portfolio_id: int = 1,
) -> SimpleNamespace:
    return SimpleNamespace(
        id            = snap_id,
        portfolio_id  = portfolio_id,
        snapshot_date = date_str,
        cash_balance  = cash,
    )


def _replay_state(holdings: dict[str, float] = None, cash: float = 0.0) -> _ReplayState:
    return _ReplayState(
        holdings = {k: Decimal(str(v)) for k, v in (holdings or {}).items()},
        cash     = Decimal(str(cash)),
    )


def _only_findings(findings: list[LedgerFinding], check_id: str) -> list[LedgerFinding]:
    return [f for f in findings if f.check_id == check_id]


# ══════════════════════════════════════════════════════════════════════════════
# CHECK 1 — DUP_INITIAL_POSITION
# ══════════════════════════════════════════════════════════════════════════════

class TestDuplicateInitialPosition:
    def test_two_records_same_symbol_same_date_is_critical(self):
        txs = [
            _tx(21, "INITIAL_POSITION", "GULF.BK", shares=1500, price=124.59, date_str="2024-01-15"),
            _tx(24, "INITIAL_POSITION", "GULF.BK", shares=1500, price=56.25, date_str="2024-01-15"),
        ]
        findings = _check_duplicate_initial_positions(4, txs)
        assert len(findings) == 1
        f = findings[0]
        assert f.check_id == "DUP_INITIAL_POSITION"
        assert f.severity == FindingSeverity.CRITICAL
        assert f.portfolio_id == 4
        assert set(f.transaction_ids) == {21, 24}
        assert f.normalized_symbol == "GULF.BK"
        assert f.details["count"] == 2

    def test_two_records_different_dates_is_pass(self):
        txs = [
            _tx(1, "INITIAL_POSITION", "AOT.BK", shares=100, price=60.0, date_str="2024-01-01"),
            _tx(2, "INITIAL_POSITION", "AOT.BK", shares=50,  price=65.0, date_str="2024-06-01"),
        ]
        findings = _check_duplicate_initial_positions(1, txs)
        assert findings == []

    def test_single_initial_position_is_pass(self):
        txs = [_tx(1, "INITIAL_POSITION", "PTT.BK", shares=200, price=35.0, date_str="2024-01-01")]
        assert _check_duplicate_initial_positions(1, txs) == []

    def test_symbol_alias_detected_as_duplicate(self):
        # KBANK stored with and without .BK on same date → same canonical KBANK.BK
        txs = [
            _tx(10, "INITIAL_POSITION", "KBANK",    shares=500, price=140.0, date_str="2024-03-01"),
            _tx(11, "INITIAL_POSITION", "KBANK.BK", shares=500, price=140.0, date_str="2024-03-01"),
        ]
        findings = _check_duplicate_initial_positions(1, txs)
        assert len(findings) == 1
        assert findings[0].check_id == "DUP_INITIAL_POSITION"
        assert "KBANK.BK" in findings[0].normalized_symbol

    def test_three_duplicates_all_captured(self):
        txs = [
            _tx(1, "INITIAL_POSITION", "BH.BK", shares=100, price=200.0, date_str="2024-01-01"),
            _tx(2, "INITIAL_POSITION", "BH.BK", shares=100, price=210.0, date_str="2024-01-01"),
            _tx(3, "INITIAL_POSITION", "BH.BK", shares=100, price=220.0, date_str="2024-01-01"),
        ]
        findings = _check_duplicate_initial_positions(1, txs)
        assert len(findings) == 1
        assert findings[0].details["count"] == 3
        assert set(findings[0].transaction_ids) == {1, 2, 3}

    def test_non_initial_position_types_ignored(self):
        txs = [
            _tx(1, "BUY",  "AOT.BK", shares=100, price=60.0, date_str="2024-01-01"),
            _tx(2, "BUY",  "AOT.BK", shares=100, price=60.0, date_str="2024-01-01"),
            _tx(3, "SELL", "AOT.BK", shares=50,  price=65.0, date_str="2024-06-01"),
        ]
        assert _check_duplicate_initial_positions(1, txs) == []


# ══════════════════════════════════════════════════════════════════════════════
# CHECK 2 — SYMBOL_ALIAS
# ══════════════════════════════════════════════════════════════════════════════

class TestSymbolAliases:
    def test_kbank_with_and_without_bk_is_warning(self):
        txs = [
            _tx(1, "INITIAL_POSITION", "KBANK",    shares=100, date_str="2024-01-01"),
            _tx(2, "BUY",              "KBANK.BK", shares=50,  date_str="2024-06-01"),
        ]
        findings = _check_symbol_aliases(1, txs)
        assert len(findings) == 1
        f = findings[0]
        assert f.check_id == "SYMBOL_ALIAS"
        assert f.severity == FindingSeverity.WARNING
        assert "KBANK" in f.details["raw_symbols"]
        assert "KBANK.BK" in f.details["raw_symbols"]

    def test_dr_with_and_without_bk_is_warning(self):
        # NVDA01 and NVDA01.BK both resolve to NVDA
        txs = [
            _tx(1, "INITIAL_POSITION", "NVDA01",    shares=10, date_str="2024-01-01"),
            _tx(2, "BUY",              "NVDA01.BK", shares=5,  date_str="2024-06-01"),
        ]
        findings = _check_symbol_aliases(1, txs)
        assert len(findings) == 1
        assert findings[0].normalized_symbol == "NVDA"

    def test_clean_ledger_no_alias_findings(self):
        txs = [
            _tx(1, "BUY",  "AOT.BK",  shares=100, date_str="2024-01-01"),
            _tx(2, "BUY",  "PTT.BK",  shares=200, date_str="2024-01-01"),
            _tx(3, "SELL", "AOT.BK",  shares=50,  date_str="2024-06-01"),
        ]
        assert _check_symbol_aliases(1, txs) == []

    def test_same_raw_symbol_used_multiple_times_no_alias(self):
        txs = [
            _tx(1, "BUY",  "GULF.BK", shares=100, date_str="2024-01-01"),
            _tx(2, "BUY",  "GULF.BK", shares=50,  date_str="2024-03-01"),
            _tx(3, "SELL", "GULF.BK", shares=80,  date_str="2024-06-01"),
        ]
        assert _check_symbol_aliases(1, txs) == []

    def test_cash_transactions_without_symbol_ignored(self):
        txs = [
            _tx(1, "DEPOSIT",  amount=50000, date_str="2024-01-01"),
            _tx(2, "WITHDRAW", amount=10000, date_str="2024-06-01"),
        ]
        assert _check_symbol_aliases(1, txs) == []


# ══════════════════════════════════════════════════════════════════════════════
# CHECK 3 — NULL_SYMBOL
# ══════════════════════════════════════════════════════════════════════════════

class TestNullSymbols:
    def test_buy_with_null_symbol_is_error(self):
        txs = [_tx(1, "BUY", symbol=None, shares=100, price=50.0, amount=5000)]
        findings = _check_null_symbols(1, txs)
        assert len(findings) == 1
        assert findings[0].check_id == "NULL_SYMBOL"
        assert findings[0].severity == FindingSeverity.ERROR

    def test_sell_with_empty_symbol_is_error(self):
        txs = [_tx(1, "SELL", symbol="  ", shares=50, price=60.0, amount=3000)]
        findings = _check_null_symbols(1, txs)
        assert len(findings) == 1
        assert findings[0].check_id == "NULL_SYMBOL"

    def test_initial_position_null_symbol_is_error(self):
        txs = [_tx(1, "INITIAL_POSITION", symbol=None, shares=100, price=40.0)]
        assert len(_check_null_symbols(1, txs)) == 1

    def test_cash_transactions_without_symbol_are_pass(self):
        txs = [
            _tx(1, "DEPOSIT",     symbol=None, amount=50000),
            _tx(2, "WITHDRAW",    symbol=None, amount=10000),
            _tx(3, "INITIAL_CASH", symbol=None, amount=20000),
        ]
        assert _check_null_symbols(1, txs) == []

    def test_valid_symbol_is_pass(self):
        txs = [_tx(1, "BUY", "AOT.BK", shares=100, price=60.0, amount=6000)]
        assert _check_null_symbols(1, txs) == []


# ══════════════════════════════════════════════════════════════════════════════
# CHECK 4 — ZERO_SHARES
# ══════════════════════════════════════════════════════════════════════════════

class TestZeroShares:
    def test_buy_with_zero_shares_is_error(self):
        txs = [_tx(1, "BUY", "AOT.BK", shares=0, price=60.0, amount=0)]
        findings = _check_zero_shares(1, txs)
        assert len(findings) == 1
        assert findings[0].check_id == "ZERO_SHARES"
        assert findings[0].severity == FindingSeverity.ERROR

    def test_buy_with_null_shares_is_error(self):
        txs = [_tx(1, "BUY", "AOT.BK", shares=None, price=60.0, amount=6000)]
        assert len(_check_zero_shares(1, txs)) == 1

    def test_sell_with_zero_shares_is_error(self):
        txs = [_tx(1, "SELL", "AOT.BK", shares=0, price=65.0, amount=0)]
        assert len(_check_zero_shares(1, txs)) == 1

    def test_positive_shares_is_pass(self):
        txs = [_tx(1, "BUY", "AOT.BK", shares=100, price=60.0, amount=6000)]
        assert _check_zero_shares(1, txs) == []

    def test_deposit_without_shares_is_pass(self):
        txs = [_tx(1, "DEPOSIT", shares=None, amount=50000)]
        assert _check_zero_shares(1, txs) == []


# ══════════════════════════════════════════════════════════════════════════════
# CHECK 5 — ZERO_PRICE
# ══════════════════════════════════════════════════════════════════════════════

class TestZeroPrices:
    def test_buy_with_zero_price_is_warning(self):
        txs = [_tx(1, "BUY", "AOT.BK", shares=100, price=0.0, amount=0)]
        findings = _check_zero_prices(1, txs)
        assert len(findings) == 1
        assert findings[0].check_id == "ZERO_PRICE"
        assert findings[0].severity == FindingSeverity.WARNING

    def test_buy_with_null_price_is_warning(self):
        txs = [_tx(1, "BUY", "AOT.BK", shares=100, price=None, amount=6000)]
        assert len(_check_zero_prices(1, txs)) == 1

    def test_initial_position_with_zero_price_is_warning(self):
        txs = [_tx(1, "INITIAL_POSITION", "AOT.BK", shares=100, price=0.0)]
        assert len(_check_zero_prices(1, txs)) == 1

    def test_sell_with_zero_price_is_pass(self):
        # SELL price is not used for avg_cost — not flagged
        txs = [_tx(1, "SELL", "AOT.BK", shares=50, price=0.0, amount=0)]
        assert _check_zero_prices(1, txs) == []

    def test_positive_price_is_pass(self):
        txs = [_tx(1, "BUY", "AOT.BK", shares=100, price=60.5, amount=6050)]
        assert _check_zero_prices(1, txs) == []


# ══════════════════════════════════════════════════════════════════════════════
# CHECK 6 — PRE_PORTFOLIO_TX
# ══════════════════════════════════════════════════════════════════════════════

class TestPrePortfolioTransactions:
    def test_transaction_before_portfolio_created_is_error(self):
        txs = [_tx(1, "INITIAL_POSITION", "PTT.BK", shares=100, price=30.0, date_str="2020-01-01")]
        findings = _check_pre_portfolio_transactions(1, datetime(2024, 1, 1), txs)
        assert len(findings) == 1
        assert findings[0].check_id == "PRE_PORTFOLIO_TX"
        assert findings[0].severity == FindingSeverity.ERROR

    def test_transaction_on_same_day_as_portfolio_creation_is_pass(self):
        txs = [_tx(1, "INITIAL_CASH", amount=50000, date_str="2024-01-01")]
        findings = _check_pre_portfolio_transactions(1, datetime(2024, 1, 1), txs)
        assert findings == []

    def test_transaction_after_portfolio_creation_is_pass(self):
        txs = [_tx(1, "BUY", "AOT.BK", shares=100, price=60.0, amount=6000, date_str="2024-06-01")]
        findings = _check_pre_portfolio_transactions(1, datetime(2024, 1, 1), txs)
        assert findings == []

    def test_no_portfolio_created_at_is_pass(self):
        txs = [_tx(1, "BUY", "AOT.BK", shares=100, price=60.0, amount=6000, date_str="2024-06-01")]
        findings = _check_pre_portfolio_transactions(1, None, txs)
        assert findings == []

    def test_multiple_pre_portfolio_transactions(self):
        txs = [
            _tx(1, "INITIAL_POSITION", "PTT.BK", shares=100, price=30.0, date_str="2020-01-01"),
            _tx(2, "INITIAL_CASH", amount=50000, date_str="2021-06-01"),
        ]
        findings = _check_pre_portfolio_transactions(1, datetime(2024, 1, 1), txs)
        assert len(findings) == 2


# ══════════════════════════════════════════════════════════════════════════════
# CHECK 7 — LARGE_DATE_SKEW
# ══════════════════════════════════════════════════════════════════════════════

class TestDateSkew:
    def test_small_skew_is_pass(self):
        txs = [_tx(1, "BUY", "AOT.BK", shares=100, price=60.0,
                   date_str="2026-01-01", created_str="2026-01-02")]
        assert _check_date_skew(1, txs, warning_days=90, error_days=365) == []

    def test_skew_above_warning_threshold_is_warning(self):
        # 120 days skew — above 90-day warning, below 365-day error
        txs = [_tx(1, "BUY", "AOT.BK", shares=100, price=60.0,
                   date_str="2025-09-01", created_str="2025-12-30")]
        findings = _check_date_skew(1, txs, warning_days=90, error_days=365)
        assert len(findings) == 1
        assert findings[0].check_id == "LARGE_DATE_SKEW"
        assert findings[0].severity == FindingSeverity.WARNING
        assert findings[0].details["skew_days"] >= 90

    def test_skew_above_error_threshold_is_error(self):
        # 400 days skew — above 365-day error threshold
        txs = [_tx(1, "INITIAL_POSITION", "GULF.BK", shares=1500, price=56.0,
                   date_str="2023-01-01", created_str="2024-02-05")]
        findings = _check_date_skew(1, txs, warning_days=90, error_days=365)
        assert len(findings) == 1
        assert findings[0].severity == FindingSeverity.ERROR
        assert findings[0].details["skew_days"] >= 365

    def test_missing_created_at_is_pass(self):
        tx = SimpleNamespace(
            id=1, transaction_type="BUY", symbol="AOT.BK",
            shares=100, price_per_share=60.0, total_amount=6000,
            transaction_date=datetime(2026, 1, 1),
            created_at=None,  # missing
            notes=None,
        )
        assert _check_date_skew(1, [tx]) == []


# ══════════════════════════════════════════════════════════════════════════════
# CHECK 8 — DUP_TX_FINGERPRINT
# ══════════════════════════════════════════════════════════════════════════════

class TestDuplicateFingerprints:
    def test_identical_transactions_is_error(self):
        txs = [
            _tx(1, "BUY", "GULF.BK", shares=500, price=56.0, amount=28000, date_str="2024-01-15"),
            _tx(2, "BUY", "GULF.BK", shares=500, price=56.0, amount=28000, date_str="2024-01-15"),
        ]
        findings = _check_duplicate_fingerprints(1, txs)
        assert len(findings) == 1
        f = findings[0]
        assert f.check_id == "DUP_TX_FINGERPRINT"
        assert f.severity == FindingSeverity.ERROR
        assert set(f.transaction_ids) == {1, 2}

    def test_same_symbol_different_price_is_pass(self):
        txs = [
            _tx(1, "BUY", "GULF.BK", shares=500, price=56.0, amount=28000, date_str="2024-01-15"),
            _tx(2, "BUY", "GULF.BK", shares=500, price=57.0, amount=28500, date_str="2024-01-15"),
        ]
        assert _check_duplicate_fingerprints(1, txs) == []

    def test_same_symbol_different_date_is_pass(self):
        txs = [
            _tx(1, "BUY", "GULF.BK", shares=500, price=56.0, amount=28000, date_str="2024-01-15"),
            _tx(2, "BUY", "GULF.BK", shares=500, price=56.0, amount=28000, date_str="2024-01-16"),
        ]
        assert _check_duplicate_fingerprints(1, txs) == []

    def test_same_symbol_different_shares_is_pass(self):
        txs = [
            _tx(1, "BUY", "GULF.BK", shares=500, price=56.0, amount=28000, date_str="2024-01-15"),
            _tx(2, "BUY", "GULF.BK", shares=600, price=56.0, amount=33600, date_str="2024-01-15"),
        ]
        assert _check_duplicate_fingerprints(1, txs) == []

    def test_three_identical_transactions(self):
        txs = [
            _tx(i, "INITIAL_POSITION", "PTT.BK", shares=100, price=30.0, amount=3000, date_str="2024-01-01")
            for i in range(1, 4)
        ]
        findings = _check_duplicate_fingerprints(1, txs)
        assert len(findings) == 1
        assert findings[0].details["count"] == 3


# ══════════════════════════════════════════════════════════════════════════════
# Replay checks
# ══════════════════════════════════════════════════════════════════════════════

class TestReplayChecks:
    def _clean_buy_sell_sequence(self):
        return [
            _tx(1, "INITIAL_CASH",     amount=200_000, date_str="2026-01-01"),
            _tx(2, "BUY",  "AOT.BK",  shares=100, price=60.0, amount=6000,  date_str="2026-01-02"),
            _tx(3, "BUY",  "PTT.BK",  shares=200, price=35.0, amount=7000,  date_str="2026-01-03"),
            _tx(4, "SELL", "AOT.BK",  shares=50,  price=70.0, amount=3500,  date_str="2026-06-01"),
        ]

    def test_clean_sequence_no_findings(self):
        state, findings, _ = _replay_and_check(1, self._clean_buy_sell_sequence())
        assert findings == []
        assert float(state.holdings["AOT.BK"]) == pytest.approx(50.0)
        assert float(state.holdings["PTT.BK"]) == pytest.approx(200.0)

    def test_sell_without_holding_is_critical(self):
        txs = [
            _tx(1, "INITIAL_CASH", amount=100_000, date_str="2026-01-01"),
            _tx(2, "SELL", "AOT.BK", shares=100, price=70.0, amount=7000, date_str="2026-06-01"),
        ]
        _, findings, _ = _replay_and_check(1, txs)
        sell_findings = _only_findings(findings, "SELL_WITHOUT_HOLDING")
        assert len(sell_findings) == 1
        assert sell_findings[0].severity == FindingSeverity.CRITICAL
        assert sell_findings[0].transaction_ids == [2]

    def test_negative_share_balance_is_critical(self):
        txs = [
            _tx(1, "INITIAL_CASH",   amount=100_000, date_str="2026-01-01"),
            _tx(2, "BUY", "BH.BK",  shares=50, price=200.0, amount=10_000, date_str="2026-01-02"),
            _tx(3, "SELL", "BH.BK", shares=100, price=210.0, amount=21_000, date_str="2026-06-01"),
        ]
        _, findings, _ = _replay_and_check(1, txs)
        neg_findings = _only_findings(findings, "NEG_SHARE_BALANCE")
        assert len(neg_findings) == 1
        assert neg_findings[0].severity == FindingSeverity.CRITICAL
        assert neg_findings[0].details["shares_after"] < 0

    def test_negative_cash_balance_is_warning(self):
        txs = [
            # No deposit — cash starts at 0, BUY will push it negative
            _tx(1, "BUY", "AOT.BK", shares=100, price=60.0, amount=6000, date_str="2026-01-01"),
        ]
        _, findings, _ = _replay_and_check(1, txs)
        neg_cash = _only_findings(findings, "NEG_CASH_BALANCE")
        assert len(neg_cash) == 1
        assert neg_cash[0].severity == FindingSeverity.WARNING

    def test_qcorr_without_holding_is_error(self):
        txs = [
            _tx(1, "INITIAL_CASH", amount=100_000, date_str="2026-01-01"),
            _tx(2, "QUANTITY_CORRECTION", "GULF.BK", shares=50, price=56.0,
                date_str="2026-06-01",
                notes="Quantity correction: +50.0 shares"),
        ]
        _, findings, _ = _replay_and_check(1, txs)
        qcorr = _only_findings(findings, "QCORR_WITHOUT_HOLDING")
        assert len(qcorr) == 1
        assert qcorr[0].severity == FindingSeverity.ERROR

    def test_qcorr_on_existing_holding_is_pass(self):
        txs = [
            _tx(1, "INITIAL_CASH",  amount=100_000, date_str="2026-01-01"),
            _tx(2, "BUY", "BH.BK", shares=100, price=200.0, amount=20_000, date_str="2026-01-02"),
            _tx(3, "QUANTITY_CORRECTION", "BH.BK", shares=5, price=200.0,
                date_str="2026-03-01",
                notes="Quantity correction: +5.0 shares"),
        ]
        _, findings, _ = _replay_and_check(1, txs)
        qcorr = _only_findings(findings, "QCORR_WITHOUT_HOLDING")
        assert qcorr == []

    def test_snapshot_state_captured_at_correct_dates(self):
        txs = [
            _tx(1, "INITIAL_CASH",  amount=100_000, date_str="2026-01-01"),
            _tx(2, "BUY", "AOT.BK", shares=100, price=60.0, amount=6000, date_str="2026-01-02"),
            _tx(3, "BUY", "PTT.BK", shares=200, price=35.0, amount=7000, date_str="2026-03-01"),
        ]
        snap_dates = ["2026-01-01", "2026-01-31", "2026-06-01"]
        _, _, state_by_date = _replay_and_check(1, txs, snapshot_dates=snap_dates)

        # 2026-01-01: INITIAL_CASH applied — cash should be 100_000
        s1 = state_by_date["2026-01-01"]
        assert float(s1.cash) == pytest.approx(100_000)
        assert "AOT.BK" not in s1.holdings  # BUY on 01-02 not yet applied

        # 2026-01-31: BUY AOT.BK on 01-02 applied — cash = 94_000
        s2 = state_by_date["2026-01-31"]
        assert float(s2.cash) == pytest.approx(94_000)
        assert float(s2.holdings.get("AOT.BK", 0)) == pytest.approx(100.0)

        # 2026-06-01: all txs applied
        s3 = state_by_date["2026-06-01"]
        assert float(s3.cash) == pytest.approx(87_000)
        assert float(s3.holdings.get("PTT.BK", 0)) == pytest.approx(200.0)

    def test_full_sell_removes_holding(self):
        txs = [
            _tx(1, "INITIAL_CASH", amount=100_000, date_str="2026-01-01"),
            _tx(2, "BUY",  "AOT.BK", shares=100, price=60.0, amount=6000, date_str="2026-01-02"),
            _tx(3, "SELL", "AOT.BK", shares=100, price=70.0, amount=7000, date_str="2026-06-01"),
        ]
        state, findings, _ = _replay_and_check(1, txs)
        assert findings == []
        assert "AOT.BK" not in state.holdings

    def test_initial_position_does_not_affect_cash(self):
        txs = [
            _tx(1, "INITIAL_CASH",     amount=50_000, date_str="2026-01-01"),
            _tx(2, "INITIAL_POSITION", "BH.BK", shares=100, price=200.0, date_str="2026-01-01"),
        ]
        state, _, _ = _replay_and_check(1, txs)
        assert float(state.cash) == pytest.approx(50_000)
        assert float(state.holdings["BH.BK"]) == pytest.approx(100.0)


# ══════════════════════════════════════════════════════════════════════════════
# DB consistency checks
# ══════════════════════════════════════════════════════════════════════════════

class TestCashConsistency:
    def test_exact_match_is_pass(self):
        findings = _check_cash_consistency(1, 94_000.0, Decimal("94000"), tolerance=1.0)
        assert findings == []

    def test_within_tolerance_is_pass(self):
        findings = _check_cash_consistency(1, 94_000.0, Decimal("94000.50"), tolerance=1.0)
        assert findings == []

    def test_mismatch_beyond_tolerance_is_error(self):
        findings = _check_cash_consistency(1, 94_000.0, Decimal("90000"), tolerance=1.0)
        assert len(findings) == 1
        f = findings[0]
        assert f.check_id == "CASH_MISMATCH"
        assert f.severity == FindingSeverity.ERROR
        assert f.details["difference"] == pytest.approx(-4000.0)

    def test_replayed_higher_than_stored_is_error(self):
        findings = _check_cash_consistency(1, 90_000.0, Decimal("94000"), tolerance=1.0)
        assert len(findings) == 1
        assert findings[0].details["difference"] == pytest.approx(4000.0)


class TestHoldingsConsistency:
    def test_exact_match_is_pass(self):
        items = [_item("AOT.BK", 100.0), _item("PTT.BK", 200.0)]
        state = _replay_state({"AOT.BK": 100.0, "PTT.BK": 200.0})
        assert _check_holdings_consistency(1, items, state) == []

    def test_within_tolerance_is_pass(self):
        items = [_item("AOT.BK", 100.0)]
        state = _replay_state({"AOT.BK": 100.0005})
        assert _check_holdings_consistency(1, items, state, shares_tol=0.001) == []

    def test_symbol_in_db_not_in_replay_is_error(self):
        items = [_item("AOT.BK", 100.0), _item("GHOST.BK", 50.0)]
        state = _replay_state({"AOT.BK": 100.0})
        findings = _check_holdings_consistency(1, items, state)
        mismatch = _only_findings(findings, "HOLDINGS_MISMATCH")
        assert any("GHOST.BK" in f.title for f in mismatch)
        assert all(f.severity == FindingSeverity.ERROR for f in mismatch)

    def test_symbol_in_replay_not_in_db_is_error(self):
        items = [_item("AOT.BK", 100.0)]
        state = _replay_state({"AOT.BK": 100.0, "NEW.BK": 50.0})
        findings = _check_holdings_consistency(1, items, state)
        mismatch = _only_findings(findings, "HOLDINGS_MISMATCH")
        assert any("NEW.BK" in f.title for f in mismatch)

    def test_shares_differ_beyond_tolerance_is_error(self):
        items = [_item("AOT.BK", 100.0)]
        state = _replay_state({"AOT.BK": 150.0})
        findings = _check_holdings_consistency(1, items, state)
        mismatch = _only_findings(findings, "HOLDINGS_MISMATCH")
        assert len(mismatch) == 1
        assert mismatch[0].details["difference"] == pytest.approx(50.0)

    def test_empty_both_is_pass(self):
        assert _check_holdings_consistency(1, [], _replay_state()) == []


class TestSnapshotCashConsistency:
    def test_matching_cash_is_pass(self):
        snaps = [_snap(1, "2026-01-31", cash=94_000.0)]
        states = {"2026-01-31": _replay_state(cash=94_000.0)}
        assert _check_snapshot_cash_consistency(1, snaps, states) == []

    def test_mismatch_is_warning(self):
        snaps = [_snap(1, "2026-01-31", cash=94_000.0)]
        states = {"2026-01-31": _replay_state(cash=90_000.0)}
        findings = _check_snapshot_cash_consistency(1, snaps, states)
        assert len(findings) == 1
        f = findings[0]
        assert f.check_id == "SNAPSHOT_CASH_MISMATCH"
        assert f.severity == FindingSeverity.WARNING
        assert f.details["difference"] == pytest.approx(-4000.0)

    def test_snapshot_date_not_in_state_by_date_is_skipped(self):
        snaps = [_snap(1, "2026-01-31", cash=94_000.0)]
        states: dict = {}  # date not captured
        assert _check_snapshot_cash_consistency(1, snaps, states) == []

    def test_within_tolerance_is_pass(self):
        snaps = [_snap(1, "2026-01-31", cash=94_000.0)]
        states = {"2026-01-31": _replay_state(cash=94_000.50)}
        assert _check_snapshot_cash_consistency(1, snaps, states, cash_tol=1.0) == []

    def test_multiple_snapshots_first_mismatch_second_ok(self):
        snaps = [
            _snap(1, "2026-01-31", cash=94_000.0),
            _snap(2, "2026-02-28", cash=87_000.0),
        ]
        states = {
            "2026-01-31": _replay_state(cash=90_000.0),   # mismatch
            "2026-02-28": _replay_state(cash=87_000.0),   # match
        }
        findings = _check_snapshot_cash_consistency(1, snaps, states)
        assert len(findings) == 1
        assert findings[0].details["snapshot_date"] == "2026-01-31"


# ══════════════════════════════════════════════════════════════════════════════
# LedgerValidationReport — properties
# ══════════════════════════════════════════════════════════════════════════════

class TestReportProperties:
    def _report(self, findings: list[LedgerFinding]) -> LedgerValidationReport:
        return LedgerValidationReport(
            portfolio_id=1, portfolio_name="Test",
            transactions_inspected=10, findings=findings,
        )

    def _finding(self, severity: FindingSeverity, check_id: str = "X") -> LedgerFinding:
        return LedgerFinding(
            check_id=check_id, severity=severity,
            portfolio_id=1, transaction_ids=[], symbol=None,
            normalized_symbol=None, title="t", explanation="e", recommendation="r",
        )

    def test_overall_severity_pass_when_no_findings(self):
        assert self._report([]).overall_severity == "PASS"

    def test_overall_severity_critical_when_critical_present(self):
        r = self._report([
            self._finding(FindingSeverity.WARNING),
            self._finding(FindingSeverity.CRITICAL),
            self._finding(FindingSeverity.ERROR),
        ])
        assert r.overall_severity == "CRITICAL"

    def test_overall_severity_error_when_error_but_no_critical(self):
        r = self._report([
            self._finding(FindingSeverity.WARNING),
            self._finding(FindingSeverity.ERROR),
        ])
        assert r.overall_severity == "ERROR"

    def test_overall_severity_warning_when_only_warnings(self):
        r = self._report([self._finding(FindingSeverity.WARNING)])
        assert r.overall_severity == "WARNING"

    def test_criticals_filter(self):
        r = self._report([
            self._finding(FindingSeverity.CRITICAL, "A"),
            self._finding(FindingSeverity.ERROR, "B"),
            self._finding(FindingSeverity.WARNING, "C"),
        ])
        assert len(r.criticals) == 1
        assert r.criticals[0].check_id == "A"

    def test_errors_filter(self):
        r = self._report([
            self._finding(FindingSeverity.CRITICAL, "A"),
            self._finding(FindingSeverity.ERROR, "B"),
        ])
        assert len(r.errors) == 1
        assert r.errors[0].check_id == "B"

    def test_warnings_filter(self):
        r = self._report([
            self._finding(FindingSeverity.WARNING, "C"),
            self._finding(FindingSeverity.CRITICAL, "A"),
        ])
        assert len(r.warnings) == 1
        assert r.warnings[0].check_id == "C"
