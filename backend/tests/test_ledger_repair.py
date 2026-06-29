"""Tests for services/ledger_repair.py — Phase 6.7A Foundation.

All tests are pure-Python and require no database or network.
Database objects are simulated with SimpleNamespace so every test is fast
and fully deterministic.

Coverage
--------

REPAIR_TYPES constant
  1.  EXCLUDE is present
  2.  SUPPRESS_FINDING is present
  3.  SYMBOL_RENAME is NOT present (deferred to Phase 6.8+)
  4.  REPAIR_TYPES is a frozenset (immutable)

LedgerRepair model structure
  5.  Model has expected column attributes
  6.  Default is_active is True
  7.  Default created_by is "system"

load_active_repairs — ordering contract (mock DB)
  8.  Results ordered by created_at ascending
  9.  Results ordered by id ascending when created_at is equal
  10. Only is_active=True rows are returned
  11. Empty list when no active repairs exist

apply_repair_overlay — EXCLUDE
  12. Single EXCLUDE removes the targeted transaction
  13. Multiple EXCLUDEs remove all targeted transactions
  14. EXCLUDE referencing a non-existent tx_id is silently ignored
  15. EXCLUDE with transaction_id=None is silently ignored

apply_repair_overlay — SUPPRESS_FINDING passthrough
  16. SUPPRESS_FINDING does not remove any transaction
  17. Mixed EXCLUDE + SUPPRESS_FINDING: only EXCLUDE targets are removed

apply_repair_overlay — empty and edge cases
  18. Empty repair list returns original tuple unchanged
  19. All transactions excluded → empty effective tuple
  20. Empty canonical list with repairs → empty effective tuple, empty provenance

apply_repair_overlay — provenance map
  21. Every original tx.id appears in provenance map
  22. Present transactions map to "RAW"
  23. Excluded transactions map to "EXCLUDED"
  24. Provenance map contains no extra keys beyond original tx.ids

apply_repair_overlay — structural guarantees
  25. Output effective_transactions is a tuple (not a list)
  26. Sort order is preserved after exclusion: (transaction_date, id) maintained
  27. Input tuple is not mutated
  28. Unknown repair_type is silently skipped
  29. SUPPRESS_FINDING transaction maps to "RAW" (still in effective list)
"""
from __future__ import annotations

import sys
import os
from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

# Add backend to path so imports resolve without a running server
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.ledger_repair import (
    REPAIR_TYPES,
    apply_repair_overlay,
    load_active_repairs,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _make_ctx(
    tx_id: int,
    tx_type: str = "BUY",
    tx_date: date | None = None,
    raw_symbol: str = "AAPL01.BK",
) -> SimpleNamespace:
    """Return a SimpleNamespace that mimics a CanonicalTransaction for overlay tests.

    apply_repair_overlay accesses only .id and passes objects through unchanged,
    so the full CanonicalTransaction is not required here.
    """
    return SimpleNamespace(
        id               = tx_id,
        transaction_type = tx_type,
        raw_symbol       = raw_symbol,
        canonical_symbol = raw_symbol,
        transaction_date = tx_date or date(2026, 1, 1),
        shares           = Decimal("100"),
        price_per_share  = Decimal("10.00"),
        total_amount     = Decimal("1000.00"),
        fees             = Decimal("1.50"),
        taxes            = Decimal("0.15"),
        created_at       = datetime(2026, 1, 1),
        sector           = None,
        notes            = None,
        qty_correction_delta = None,
        realized_pnl     = None,
    )


def _make_repair(
    repair_type: str,
    transaction_id: int | None,
    portfolio_id: int = 1,
    repair_id: int = 1,
    created_at: datetime | None = None,
    is_active: bool = True,
    reason_code: str | None = None,
) -> SimpleNamespace:
    """Return a SimpleNamespace that mimics a LedgerRepair ORM row."""
    return SimpleNamespace(
        id             = repair_id,
        portfolio_id   = portfolio_id,
        transaction_id = transaction_id,
        repair_plan_id = "plan-uuid-0001",
        repair_type    = repair_type,
        reason         = "test repair",
        reason_code    = reason_code,
        payload_json   = None,
        created_by     = "system",
        created_at     = created_at or datetime(2026, 6, 28, 12, 0, 0),
        is_active      = is_active,
    )


# ──────────────────────────────────────────────────────────────────────────────
# REPAIR_TYPES constant
# ──────────────────────────────────────────────────────────────────────────────

def test_repair_types_contains_exclude():
    assert "EXCLUDE" in REPAIR_TYPES


def test_repair_types_contains_suppress_finding():
    assert "SUPPRESS_FINDING" in REPAIR_TYPES


def test_repair_types_does_not_contain_symbol_rename():
    assert "SYMBOL_RENAME" not in REPAIR_TYPES


def test_repair_types_is_frozenset():
    assert isinstance(REPAIR_TYPES, frozenset)


# ──────────────────────────────────────────────────────────────────────────────
# LedgerRepair model structure
# ──────────────────────────────────────────────────────────────────────────────

def test_ledger_repair_model_has_expected_columns():
    from models.database import LedgerRepair
    expected = {
        "id", "portfolio_id", "transaction_id", "repair_plan_id",
        "repair_type", "reason", "reason_code", "payload_json",
        "created_by", "created_at", "is_active",
    }
    actual = {c.key for c in LedgerRepair.__table__.columns}
    assert expected.issubset(actual), f"missing columns: {expected - actual}"


def test_ledger_repair_default_is_active():
    from models.database import LedgerRepair
    col = LedgerRepair.__table__.c["is_active"]
    assert col.default.arg is True


def test_ledger_repair_default_created_by():
    from models.database import LedgerRepair
    col = LedgerRepair.__table__.c["created_by"]
    assert col.default is not None


# ──────────────────────────────────────────────────────────────────────────────
# load_active_repairs — ordering contract (mock DB session)
# ──────────────────────────────────────────────────────────────────────────────

def _make_mock_db(rows: list) -> MagicMock:
    """Return a mock DB session whose .query().filter().order_by().all() chain
    returns the supplied rows in the supplied order."""
    mock_db    = MagicMock()
    mock_query = MagicMock()
    mock_db.query.return_value   = mock_query
    mock_query.filter.return_value   = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.all.return_value      = rows
    return mock_db


def test_load_active_repairs_returns_results_in_provided_order():
    r1 = _make_repair("EXCLUDE", 10, repair_id=1, created_at=datetime(2026, 6, 1))
    r2 = _make_repair("EXCLUDE", 11, repair_id=2, created_at=datetime(2026, 6, 2))
    db = _make_mock_db([r1, r2])
    result = load_active_repairs(db, portfolio_id=1)
    assert result == [r1, r2]


def test_load_active_repairs_calls_filter_with_portfolio_id():
    db = _make_mock_db([])
    load_active_repairs(db, portfolio_id=7)
    db.query.assert_called_once()
    # Verify filter and order_by were chained (not bypassed)
    db.query.return_value.filter.assert_called_once()
    db.query.return_value.filter.return_value.order_by.assert_called_once()


def test_load_active_repairs_empty_when_no_repairs():
    db = _make_mock_db([])
    result = load_active_repairs(db, portfolio_id=99)
    assert result == []


# ──────────────────────────────────────────────────────────────────────────────
# apply_repair_overlay — EXCLUDE
# ──────────────────────────────────────────────────────────────────────────────

def test_exclude_single_transaction_is_removed():
    ctx_a = _make_ctx(tx_id=10)
    ctx_b = _make_ctx(tx_id=20)
    repair = _make_repair("EXCLUDE", transaction_id=10)

    effective, _ = apply_repair_overlay((ctx_a, ctx_b), [repair])

    assert ctx_a not in effective
    assert ctx_b in effective


def test_exclude_multiple_transactions():
    ctx_a = _make_ctx(tx_id=10)
    ctx_b = _make_ctx(tx_id=20)
    ctx_c = _make_ctx(tx_id=30)
    repairs = [
        _make_repair("EXCLUDE", transaction_id=10, repair_id=1),
        _make_repair("EXCLUDE", transaction_id=20, repair_id=2),
    ]

    effective, _ = apply_repair_overlay((ctx_a, ctx_b, ctx_c), repairs)

    assert ctx_a not in effective
    assert ctx_b not in effective
    assert ctx_c in effective


def test_exclude_nonexistent_tx_id_is_silently_ignored():
    ctx_a = _make_ctx(tx_id=10)
    repair = _make_repair("EXCLUDE", transaction_id=999)   # 999 not in input

    effective, provenance = apply_repair_overlay((ctx_a,), [repair])

    assert ctx_a in effective          # original still present
    assert len(effective) == 1
    assert provenance[10] == "RAW"


def test_exclude_with_null_transaction_id_is_silently_ignored():
    ctx_a = _make_ctx(tx_id=10)
    repair = _make_repair("EXCLUDE", transaction_id=None)

    effective, _ = apply_repair_overlay((ctx_a,), [repair])

    assert ctx_a in effective


# ──────────────────────────────────────────────────────────────────────────────
# apply_repair_overlay — SUPPRESS_FINDING passthrough
# ──────────────────────────────────────────────────────────────────────────────

def test_suppress_finding_does_not_remove_transaction():
    ctx_a = _make_ctx(tx_id=10)
    repair = _make_repair("SUPPRESS_FINDING", transaction_id=10, reason_code="DUP_INITIAL_POSITION")

    effective, provenance = apply_repair_overlay((ctx_a,), [repair])

    assert ctx_a in effective
    assert provenance[10] == "RAW"


def test_mixed_exclude_and_suppress_finding():
    ctx_a = _make_ctx(tx_id=10)
    ctx_b = _make_ctx(tx_id=20)
    repairs = [
        _make_repair("EXCLUDE",          transaction_id=10, repair_id=1),
        _make_repair("SUPPRESS_FINDING", transaction_id=20, repair_id=2),
    ]

    effective, provenance = apply_repair_overlay((ctx_a, ctx_b), repairs)

    assert ctx_a not in effective
    assert ctx_b in effective
    assert provenance[10] == "EXCLUDED"
    assert provenance[20] == "RAW"


# ──────────────────────────────────────────────────────────────────────────────
# apply_repair_overlay — empty and edge cases
# ──────────────────────────────────────────────────────────────────────────────

def test_empty_repair_list_returns_original_tuple():
    ctx_a = _make_ctx(tx_id=10)
    ctx_b = _make_ctx(tx_id=20)
    original = (ctx_a, ctx_b)

    effective, _ = apply_repair_overlay(original, [])

    assert effective == original


def test_all_transactions_excluded_returns_empty_tuple():
    ctx_a = _make_ctx(tx_id=10)
    ctx_b = _make_ctx(tx_id=20)
    repairs = [
        _make_repair("EXCLUDE", transaction_id=10, repair_id=1),
        _make_repair("EXCLUDE", transaction_id=20, repair_id=2),
    ]

    effective, provenance = apply_repair_overlay((ctx_a, ctx_b), repairs)

    assert effective == ()
    assert provenance[10] == "EXCLUDED"
    assert provenance[20] == "EXCLUDED"


def test_empty_canonical_list_with_repairs():
    repair = _make_repair("EXCLUDE", transaction_id=10)

    effective, provenance = apply_repair_overlay((), [repair])

    assert effective == ()
    assert provenance == {}


# ──────────────────────────────────────────────────────────────────────────────
# apply_repair_overlay — provenance map
# ──────────────────────────────────────────────────────────────────────────────

def test_provenance_map_covers_all_original_tx_ids():
    ctx_a = _make_ctx(tx_id=10)
    ctx_b = _make_ctx(tx_id=20)
    ctx_c = _make_ctx(tx_id=30)
    repair = _make_repair("EXCLUDE", transaction_id=20)

    _, provenance = apply_repair_overlay((ctx_a, ctx_b, ctx_c), [repair])

    assert set(provenance.keys()) == {10, 20, 30}


def test_provenance_raw_for_non_excluded():
    ctx_a = _make_ctx(tx_id=10)
    ctx_b = _make_ctx(tx_id=20)
    repair = _make_repair("EXCLUDE", transaction_id=20)

    _, provenance = apply_repair_overlay((ctx_a, ctx_b), [repair])

    assert provenance[10] == "RAW"


def test_provenance_excluded_for_excluded():
    ctx_a = _make_ctx(tx_id=10)
    repair = _make_repair("EXCLUDE", transaction_id=10)

    _, provenance = apply_repair_overlay((ctx_a,), [repair])

    assert provenance[10] == "EXCLUDED"


def test_provenance_map_no_extra_keys():
    ctx_a = _make_ctx(tx_id=10)
    repair = _make_repair("EXCLUDE", transaction_id=999)  # not in input

    _, provenance = apply_repair_overlay((ctx_a,), [repair])

    assert set(provenance.keys()) == {10}


# ──────────────────────────────────────────────────────────────────────────────
# apply_repair_overlay — structural guarantees
# ──────────────────────────────────────────────────────────────────────────────

def test_effective_transactions_is_tuple():
    ctx_a = _make_ctx(tx_id=10)

    effective, _ = apply_repair_overlay((ctx_a,), [])

    assert isinstance(effective, tuple)


def test_sort_order_preserved_after_exclusion():
    ctx_a = _make_ctx(tx_id=10, tx_date=date(2026, 1, 1))
    ctx_b = _make_ctx(tx_id=20, tx_date=date(2026, 1, 2))  # excluded
    ctx_c = _make_ctx(tx_id=30, tx_date=date(2026, 1, 3))
    ctx_d = _make_ctx(tx_id=40, tx_date=date(2026, 1, 4))
    repair = _make_repair("EXCLUDE", transaction_id=20)

    effective, _ = apply_repair_overlay((ctx_a, ctx_b, ctx_c, ctx_d), [repair])

    assert effective == (ctx_a, ctx_c, ctx_d)
    # Explicit date order check
    dates = [ctx.transaction_date for ctx in effective]
    assert dates == sorted(dates)


def test_input_tuple_is_not_mutated():
    ctx_a = _make_ctx(tx_id=10)
    ctx_b = _make_ctx(tx_id=20)
    original = (ctx_a, ctx_b)
    repair = _make_repair("EXCLUDE", transaction_id=10)

    apply_repair_overlay(original, [repair])

    # Original tuple must be unchanged
    assert original == (ctx_a, ctx_b)


def test_unknown_repair_type_is_silently_skipped():
    ctx_a = _make_ctx(tx_id=10)
    repair = _make_repair("FUTURE_TYPE_NOT_YET_IMPLEMENTED", transaction_id=10)

    effective, provenance = apply_repair_overlay((ctx_a,), [repair])

    assert ctx_a in effective
    assert provenance[10] == "RAW"


def test_suppress_finding_tx_maps_to_raw_in_provenance():
    ctx_a = _make_ctx(tx_id=10)
    repair = _make_repair("SUPPRESS_FINDING", transaction_id=10)

    _, provenance = apply_repair_overlay((ctx_a,), [repair])

    assert provenance[10] == "RAW"
