"""Unit tests for Phase 4C.5A — Basket Simulation Engine.

All tests use compute_basket_simulation() (pure function, no DB required).

Coverage:
  1.  Empty basket → no impacts, PASS, zero capital required
  2.  Single symbol → one impact entry for its sector
  3.  Multiple symbols in different sectors → separate impact per sector
  4.  Equal allocation applied to every symbol
  5.  Sector PASS — after_pct well below limit
  6.  Sector WARNING — after_pct ≥ 80% of limit
  7.  Sector FAIL — after_pct ≥ limit
  8.  Cash WARNING — cash_after falls below cash_min_pct
  9.  Overall PASS — all sectors OK, cash OK
 10.  Overall WARNING — no FAIL, but WARNING present
 11.  Overall FAIL — sector limit breached
 12.  portfolio_id is threaded through to result (workspace isolation)
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.basket_simulation import (
    BasketImpact,
    BasketSimulationResult,
    compute_basket_simulation,
)

# ── Default sector limits used across tests ───────────────────────────────────

_LIMITS = {
    "Technology":  60.0,
    "Healthcare":  40.0,
    "Financial":   40.0,
    "Consumer":    40.0,
    "Energy":      40.0,
    "Industrial":  40.0,
    "Real Estate": 40.0,
    "Utilities":   40.0,
    "Other":       40.0,
}

_WEIGHTS = {
    "Technology": 30.0,
    "Healthcare":  8.0,
}

_PORTFOLIO_ID = 1


def _sim(
    symbols: list[str],
    symbol_sectors: dict[str, str],
    allocation_pct: float = 5.0,
    cash_pct: float = 22.0,
    sector_weights: dict | None = None,
    sector_limits: dict | None = None,
    cash_min_pct: float = 5.0,
    portfolio_id: int = _PORTFOLIO_ID,
) -> BasketSimulationResult:
    return compute_basket_simulation(
        portfolio_id=portfolio_id,
        symbols=symbols,
        symbol_sectors=symbol_sectors,
        allocation_pct=allocation_pct,
        cash_pct=cash_pct,
        sector_weights=sector_weights if sector_weights is not None else _WEIGHTS,
        sector_limits=sector_limits if sector_limits is not None else _LIMITS,
        cash_min_pct=cash_min_pct,
    )


# ── Test 1: Empty basket ──────────────────────────────────────────────────────

def test_empty_basket_returns_pass_with_no_impacts():
    result = _sim(symbols=[], symbol_sectors={})

    assert result.overall_status == "PASS"
    assert result.impacts == []
    assert result.warnings == []
    assert result.total_capital_required_pct == 0.0
    assert result.cash_after_pct == result.cash_before_pct


# ── Test 2: Single symbol ─────────────────────────────────────────────────────

def test_single_symbol_produces_one_impact_entry():
    result = _sim(
        symbols=["BH"],
        symbol_sectors={"BH": "Healthcare"},
        allocation_pct=5.0,
    )

    assert len(result.impacts) == 1
    assert result.impacts[0].sector == "Healthcare"
    assert result.impacts[0].delta_pct == 5.0
    assert result.impacts[0].before_pct == 8.0   # from _WEIGHTS
    assert result.impacts[0].after_pct == 13.0


# ── Test 3: Multiple symbols in different sectors ─────────────────────────────

def test_multiple_symbols_in_different_sectors_produce_separate_impacts():
    result = _sim(
        symbols=["AAPL", "JPM"],
        symbol_sectors={"AAPL": "Technology", "JPM": "Financial"},
        allocation_pct=5.0,
    )

    sectors = {imp.sector for imp in result.impacts}
    assert "Technology" in sectors
    assert "Financial" in sectors
    assert len(result.impacts) == 2


# ── Test 4: Equal allocation applied to all symbols ──────────────────────────

def test_equal_allocation_applied_to_each_symbol():
    # 3 symbols × 5% = 15% total
    result = _sim(
        symbols=["A", "B", "C"],
        symbol_sectors={"A": "Healthcare", "B": "Financial", "C": "Energy"},
        allocation_pct=5.0,
        cash_pct=30.0,
    )

    assert result.total_capital_required_pct == 15.0
    assert result.cash_after_pct == 15.0   # 30 - 15

    for imp in result.impacts:
        assert imp.delta_pct == 5.0


# ── Test 5: Sector PASS — within limit ────────────────────────────────────────

def test_sector_pass_when_after_pct_well_below_limit():
    # Technology: 30% + 5% = 35% vs 60% limit → well under 80% of 60 (=48%)
    result = _sim(
        symbols=["AAPL"],
        symbol_sectors={"AAPL": "Technology"},
        allocation_pct=5.0,
    )

    tech = next(i for i in result.impacts if i.sector == "Technology")
    assert tech.status == "PASS"
    assert tech.after_pct == 35.0


# ── Test 6: Sector WARNING — above 80% of limit ───────────────────────────────

def test_sector_warning_when_approaching_limit():
    # Technology: 30% + 20% = 50% vs 60% limit → 50 >= 60*0.8=48 → WARNING
    result = _sim(
        symbols=["A", "B", "C", "D"],
        symbol_sectors={"A": "Technology", "B": "Technology",
                        "C": "Technology", "D": "Technology"},
        allocation_pct=5.0,
    )

    tech = next(i for i in result.impacts if i.sector == "Technology")
    assert tech.status == "WARNING"
    assert tech.after_pct == 50.0
    assert any("80%" in w for w in result.warnings)


# ── Test 7: Sector FAIL — exceeds limit ──────────────────────────────────────

def test_sector_fail_when_limit_exceeded():
    # Technology: 30% + 35% = 65% vs 60% limit → FAIL
    result = _sim(
        symbols=["A", "B", "C", "D", "E", "F", "G"],
        symbol_sectors={s: "Technology" for s in ["A", "B", "C", "D", "E", "F", "G"]},
        allocation_pct=5.0,
    )

    tech = next(i for i in result.impacts if i.sector == "Technology")
    assert tech.status == "FAIL"
    assert tech.after_pct == 65.0
    assert any("exceeds limit" in w for w in result.warnings)


# ── Test 8: Cash WARNING — falls below minimum threshold ─────────────────────

def test_cash_warning_when_cash_falls_below_minimum():
    # cash: 10%, basket deploys 8% → cash_after=2% which is < cash_min=5%
    result = _sim(
        symbols=["A", "B"],
        symbol_sectors={"A": "Healthcare", "B": "Financial"},
        allocation_pct=4.0,
        cash_pct=10.0,
        cash_min_pct=5.0,
    )

    assert result.cash_after_pct == 2.0
    assert any("minimum threshold" in w for w in result.warnings)


# ── Test 9: Overall PASS — all clear ─────────────────────────────────────────

def test_overall_pass_when_all_constraints_satisfied():
    result = _sim(
        symbols=["BH"],
        symbol_sectors={"BH": "Healthcare"},
        allocation_pct=2.0,
        cash_pct=25.0,
        cash_min_pct=5.0,
    )

    assert result.overall_status == "PASS"
    assert result.warnings == []


# ── Test 10: Overall WARNING — warning present, no FAIL ──────────────────────

def test_overall_warning_when_sector_approaches_limit():
    # Technology: 30% + 20% = 50% → WARNING (80% of 60 = 48)
    # No FAIL → WARNING
    result = _sim(
        symbols=["A", "B", "C", "D"],
        symbol_sectors={s: "Technology" for s in ["A", "B", "C", "D"]},
        allocation_pct=5.0,
        cash_pct=40.0,
        cash_min_pct=5.0,
    )

    assert result.overall_status == "WARNING"
    assert not any(imp.status == "FAIL" for imp in result.impacts)


# ── Test 11: Overall FAIL — sector limit breached ────────────────────────────

def test_overall_fail_when_sector_limit_exceeded():
    # Technology: 30% + 35% = 65% > 60% → FAIL
    result = _sim(
        symbols=["A", "B", "C", "D", "E", "F", "G"],
        symbol_sectors={s: "Technology" for s in ["A", "B", "C", "D", "E", "F", "G"]},
        allocation_pct=5.0,
        cash_pct=50.0,
    )

    assert result.overall_status == "FAIL"


# ── Test 12: portfolio_id threaded through to result ─────────────────────────

def test_portfolio_id_is_preserved_in_result():
    result = _sim(
        symbols=["BH"],
        symbol_sectors={"BH": "Healthcare"},
        portfolio_id=99,
    )

    assert result.portfolio_id == 99
    assert result.symbols == ["BH"]
