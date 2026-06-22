"""Tests for Phase 4C.5B — Portfolio Construction Assistant.

All tests use compute_portfolio_construction() (pure function, no DB).
"""
import pytest
from services.portfolio_construction import (
    PortfolioConstructionResult,
    SuggestedBasketAllocation,
    compute_portfolio_construction,
)

# ── Shared fixtures ───────────────────────────────────────────────────────────

_SECTOR_LIMITS = {
    "Technology": 60.0,
    "Healthcare": 40.0,
    "Financial": 40.0,
    "Energy": 40.0,
    "Consumer": 40.0,
    "Industrial": 40.0,
    "Real Estate": 40.0,
    "Utilities": 40.0,
    "Other": 40.0,
}

_SECTOR_WEIGHTS = {
    "Technology": 30.0,
    "Healthcare": 8.0,
}

_PORT_ID = 1


def _cons(
    symbols: list[str],
    *,
    symbol_sectors: dict[str, str] | None = None,
    cash_pct: float = 30.0,
    sector_weights: dict[str, float] | None = None,
    sector_limits: dict[str, float] | None = None,
    cash_min_pct: float = 5.0,
    start_pct: float = 5.0,
    min_pct: float = 1.0,
    portfolio_id: int = _PORT_ID,
) -> PortfolioConstructionResult:
    return compute_portfolio_construction(
        portfolio_id=portfolio_id,
        symbols=symbols,
        symbol_sectors=symbol_sectors or {},
        cash_pct=cash_pct,
        sector_weights=sector_weights if sector_weights is not None else dict(_SECTOR_WEIGHTS),
        sector_limits=sector_limits if sector_limits is not None else dict(_SECTOR_LIMITS),
        cash_min_pct=cash_min_pct,
        start_pct=start_pct,
        min_pct=min_pct,
    )


# ── 1: Empty basket ───────────────────────────────────────────────────────────

def test_empty_basket():
    r = _cons([])
    assert r.overall_status == "PASS"
    assert r.allocations == []
    assert r.recommended_allocation_pct == 0.0
    assert r.total_deployment_pct == 0.0
    assert r.reasoning == ["No symbols provided."]


# ── 2: Single symbol ──────────────────────────────────────────────────────────

def test_single_symbol():
    r = _cons(["AAPL"], symbol_sectors={"AAPL": "Technology"})
    assert len(r.allocations) == 1
    assert r.allocations[0].symbol == "AAPL"
    assert r.allocations[0].suggested_pct == r.recommended_allocation_pct
    assert r.total_deployment_pct == r.recommended_allocation_pct * 1


# ── 3: Multiple symbols ───────────────────────────────────────────────────────

def test_multiple_symbols():
    syms = ["AAPL", "BH", "SCC"]
    sectors = {"AAPL": "Technology", "BH": "Healthcare", "SCC": "Industrial"}
    r = _cons(syms, symbol_sectors=sectors)
    assert {a.symbol for a in r.allocations} == set(syms)
    assert all(a.suggested_pct == r.recommended_allocation_pct for a in r.allocations)
    assert r.total_deployment_pct == pytest.approx(len(syms) * r.recommended_allocation_pct)


# ── 4: Immediate PASS ─────────────────────────────────────────────────────────

def test_immediate_pass():
    # Technology at 30%, limit 60% → 30+5=35 < 48 (80%) → PASS
    # Cash 30% - 5% = 25% >> 5% → PASS
    r = _cons(["AAPL"], symbol_sectors={"AAPL": "Technology"})
    assert r.overall_status == "PASS"
    assert r.recommended_allocation_pct == 5.0
    assert len(r.reasoning) == 1
    assert "5%" in r.reasoning[0]
    assert "satisfies" in r.reasoning[0]


# ── 5: Requires reduction ─────────────────────────────────────────────────────

def test_requires_reduction():
    # Technology at 30%, limit 40%:
    # 5%→35>=32 WARNING, 4%→34>=32 WARNING, 3%→33>=32 WARNING,
    # 2%→32==32 WARNING, 1%→31<32 PASS
    limits = {**_SECTOR_LIMITS, "Technology": 40.0}
    r = _cons(
        ["AAPL"],
        symbol_sectors={"AAPL": "Technology"},
        sector_weights={"Technology": 30.0},
        sector_limits=limits,
    )
    assert r.overall_status == "PASS"
    assert r.recommended_allocation_pct == 1.0
    assert len(r.reasoning) == 2
    assert "5%" in r.reasoning[0]
    assert "1%" in r.reasoning[1]
    assert "satisfies" in r.reasoning[1]


# ── 6: FAIL at minimum size ───────────────────────────────────────────────────

def test_fail_at_minimum():
    # Technology at 55%, limit 40% → 55+1=56 >= 40 → FAIL at every step
    limits = {**_SECTOR_LIMITS, "Technology": 40.0}
    r = _cons(
        ["AAPL"],
        symbol_sectors={"AAPL": "Technology"},
        sector_weights={"Technology": 55.0},
        sector_limits=limits,
    )
    assert r.overall_status == "FAIL"
    assert "No viable allocation found" in r.reasoning[0]
    assert r.recommended_allocation_pct == 1.0  # set to min_pct


# ── 7: Cash constraint binding ────────────────────────────────────────────────

def test_cash_constraint():
    # 2 symbols × 5% = 10% → cash 10−10=0% < 5% → WARNING
    # 2 × 4% = 8% → cash 2% < 5% → WARNING
    # 2 × 3% = 6% → cash 4% < 5% → WARNING
    # 2 × 2% = 4% → cash 6% >= 5% → PASS
    r = _cons(
        ["AAPL", "MSFT"],
        symbol_sectors={"AAPL": "Technology", "MSFT": "Technology"},
        cash_pct=10.0,
        cash_min_pct=5.0,
        sector_weights={"Technology": 30.0},
        sector_limits={"Technology": 60.0, "Other": 40.0},
    )
    assert r.overall_status == "PASS"
    assert r.cash_after_pct >= 5.0
    assert r.recommended_allocation_pct == 2.0


# ── 8: Sector constraint never satisfiable ────────────────────────────────────

def test_sector_constraint_never_satisfiable():
    # Healthcare at 38%, limit 40% → any add ≥ 1% puts after at 39%
    # 39% >= 40*0.8=32% → WARNING at every level; never PASS
    limits = {**_SECTOR_LIMITS, "Healthcare": 40.0}
    r = _cons(
        ["BH"],
        symbol_sectors={"BH": "Healthcare"},
        sector_weights={"Healthcare": 38.0},
        sector_limits=limits,
    )
    assert r.overall_status != "PASS"
    assert "No viable allocation found" in r.reasoning[0]


# ── 9: Equal allocation for all symbols ───────────────────────────────────────

def test_equal_allocation_output():
    syms = ["AAPL", "MSFT", "NVDA"]
    sectors = {s: "Technology" for s in syms}
    r = _cons(syms, symbol_sectors=sectors)
    pcts = [a.suggested_pct for a in r.allocations]
    assert len(set(pcts)) == 1, "all symbols must receive the same allocation"
    assert pcts[0] == r.recommended_allocation_pct


# ── 10: portfolio_id threads through to embedded simulation ───────────────────

def test_portfolio_id_threaded():
    r = _cons(["AAPL"], symbol_sectors={"AAPL": "Technology"}, portfolio_id=99)
    assert r.simulation.portfolio_id == 99


# ── 11: Reasoning generation ──────────────────────────────────────────────────

def test_reasoning_generation():
    # Immediate pass → exactly 1 line
    r_pass = _cons(["BH"], symbol_sectors={"BH": "Healthcare"}, cash_pct=50.0)
    assert len(r_pass.reasoning) == 1
    assert "satisfies" in r_pass.reasoning[0].lower()

    # After reduction → exactly 2 lines (failure reason + success)
    limits = {**_SECTOR_LIMITS, "Technology": 40.0}
    r_reduced = _cons(
        ["AAPL"],
        symbol_sectors={"AAPL": "Technology"},
        sector_weights={"Technology": 30.0},
        sector_limits=limits,
    )
    assert len(r_reduced.reasoning) == 2
    assert "5%" in r_reduced.reasoning[0]
    assert "satisfies" in r_reduced.reasoning[1].lower()


# ── 12: Deterministic / stable output ────────────────────────────────────────

def test_deterministic():
    syms = ["AAPL", "BH"]
    sectors = {"AAPL": "Technology", "BH": "Healthcare"}
    r1 = _cons(syms, symbol_sectors=sectors)
    r2 = _cons(syms, symbol_sectors=sectors)
    assert r1.overall_status == r2.overall_status
    assert r1.recommended_allocation_pct == r2.recommended_allocation_pct
    assert r1.total_deployment_pct == r2.total_deployment_pct
    assert r1.cash_after_pct == r2.cash_after_pct
    assert [a.symbol for a in r1.allocations] == [a.symbol for a in r2.allocations]
