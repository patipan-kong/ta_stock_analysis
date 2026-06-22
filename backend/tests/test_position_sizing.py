"""Tests for Phase 4D.1 — Constraint-Aware Position Sizing.

All tests use compute_position_sizes() (pure function, no DB).
"""
import pytest
from services.position_sizing import (
    PositionSizingResult,
    PositionSuggestion,
    compute_position_sizes,
)

# ── Shared fixtures ───────────────────────────────────────────────────────────

_SECTOR_LIMITS = {
    "Technology":  60.0,
    "Healthcare":  40.0,
    "Financial":   40.0,
    "Energy":      40.0,
    "Consumer":    40.0,
    "Industrial":  40.0,
    "Real Estate": 40.0,
    "Utilities":   40.0,
    "Other":       40.0,
}

_DEFAULT_DATA: dict = {
    "signal":                "BUY",
    "confidence":            0.85,
    "strategic_fit_score":   7.0,
    "portfolio_priority":    "HIGH",
}


def _size(
    symbols: list[str],
    *,
    symbol_data: dict[str, dict] | None = None,
    symbol_sectors: dict[str, str] | None = None,
    cash_pct: float = 20.0,
    sector_weights: dict[str, float] | None = None,
    sector_limits: dict[str, float] | None = None,
    cash_min_pct: float = 5.0,
    portfolio_id: int = 1,
) -> PositionSizingResult:
    sd: dict[str, dict] = {sym: dict(_DEFAULT_DATA) for sym in symbols}
    if symbol_data:
        for sym, data in symbol_data.items():
            sd[sym] = data
    return compute_position_sizes(
        portfolio_id=portfolio_id,
        symbols=symbols,
        symbol_data=sd,
        symbol_sectors=symbol_sectors or {},
        cash_pct=cash_pct,
        sector_weights=sector_weights or {},
        sector_limits=sector_limits if sector_limits is not None else dict(_SECTOR_LIMITS),
        cash_min_pct=cash_min_pct,
    )


# ── 1: Empty input ────────────────────────────────────────────────────────────

def test_empty_input():
    r = _size([])
    assert r.status == "FAIL"
    assert r.suggestions == []
    assert r.total_allocated_pct == 0.0
    assert r.deployable_cash_pct == pytest.approx(15.0)  # 20 - 5
    assert "No symbols provided" in r.reasoning[0]


# ── 2: Single symbol ──────────────────────────────────────────────────────────

def test_single_symbol():
    r = _size(["AAPL"])
    assert len(r.suggestions) == 1
    assert r.suggestions[0].symbol == "AAPL"
    assert r.suggestions[0].suggested_pct > 0
    assert r.total_allocated_pct == pytest.approx(r.suggestions[0].suggested_pct)


# ── 3: Multiple symbols proportional ─────────────────────────────────────────

def test_multiple_symbols_proportional():
    # Same data for both → equal scores → equal allocation
    r = _size(["AAPL", "BH"])
    assert len(r.suggestions) == 2
    pcts = [s.suggested_pct for s in r.suggestions]
    assert pcts[0] == pytest.approx(pcts[1], rel=0.01)
    # Total should equal deployable (20 - 5 = 15%)
    assert sum(pcts) == pytest.approx(15.0, rel=0.001)


# ── 4: Score calculation ──────────────────────────────────────────────────────

def test_score_calculation():
    data = {
        "signal":              "BUY",      # 4.0
        "confidence":          0.8,        # 0.8 × 5 = 4.0
        "strategic_fit_score": 6.0,        # 6 / 2 = 3.0
        "portfolio_priority":  "HIGH",     # 3.0
    }
    # Total = 4 + 4 + 3 + 3 = 14.0
    r = _size(["AAPL"], symbol_data={"AAPL": data})
    assert r.suggestions[0].position_score == pytest.approx(14.0)
    bd = r.suggestions[0].breakdown
    assert bd.signal_points == pytest.approx(4.0)
    assert bd.confidence_points == pytest.approx(4.0)
    assert bd.fit_points == pytest.approx(3.0)
    assert bd.priority_points == pytest.approx(3.0)


# ── 5: Confidence weighting ───────────────────────────────────────────────────

def test_confidence_weighting():
    base = {"signal": "BUY", "strategic_fit_score": 7.0, "portfolio_priority": "MEDIUM"}
    symbol_data = {
        "HIGH_CONF": {**base, "confidence": 0.90},
        "LOW_CONF":  {**base, "confidence": 0.30},
    }
    r = _size(["HIGH_CONF", "LOW_CONF"], symbol_data=symbol_data)
    high = next(s.suggested_pct for s in r.suggestions if s.symbol == "HIGH_CONF")
    low  = next(s.suggested_pct for s in r.suggestions if s.symbol == "LOW_CONF")
    assert high > low


# ── 6: Strategic fit weighting ────────────────────────────────────────────────

def test_strategic_fit_weighting():
    base = {"signal": "BUY", "confidence": 0.7, "portfolio_priority": "MEDIUM"}
    symbol_data = {
        "HIGH_FIT": {**base, "strategic_fit_score": 9.0},
        "LOW_FIT":  {**base, "strategic_fit_score": 2.0},
    }
    r = _size(["HIGH_FIT", "LOW_FIT"], symbol_data=symbol_data)
    high = next(s.suggested_pct for s in r.suggestions if s.symbol == "HIGH_FIT")
    low  = next(s.suggested_pct for s in r.suggestions if s.symbol == "LOW_FIT")
    assert high > low


# ── 7: Priority weighting ─────────────────────────────────────────────────────

def test_priority_weighting():
    base = {"signal": "BUY", "confidence": 0.7, "strategic_fit_score": 6.0}
    symbol_data = {
        "HIGH_PRI": {**base, "portfolio_priority": "HIGH"},
        "LOW_PRI":  {**base, "portfolio_priority": "LOW"},
    }
    r = _size(["HIGH_PRI", "LOW_PRI"], symbol_data=symbol_data)
    high = next(s.suggested_pct for s in r.suggestions if s.symbol == "HIGH_PRI")
    low  = next(s.suggested_pct for s in r.suggestions if s.symbol == "LOW_PRI")
    assert high > low


# ── 8: Allocation normalization ───────────────────────────────────────────────

def test_allocation_normalization():
    # No sector constraints → total == deployable
    r = _size(["A", "B", "C"])
    deployable = 20.0 - 5.0
    assert r.total_allocated_pct == pytest.approx(deployable, rel=0.001)
    assert r.status == "PASS"


# ── 9: Cash reserve protection ───────────────────────────────────────────────

def test_cash_reserve_protection():
    # Cash = 12%, min = 5% → deployable = 7%, not 12%
    r = _size(["AAPL"], cash_pct=12.0, cash_min_pct=5.0)
    assert r.deployable_cash_pct == pytest.approx(7.0)
    assert r.suggestions[0].suggested_pct == pytest.approx(7.0)


# ── 10: Constraint scaling ────────────────────────────────────────────────────

def test_constraint_scaling():
    # Both symbols in Technology, sector at 55%, limit 60% → headroom = 5%
    # Equal scores → each gets half of 15% = 7.5%, total sector = 15% > headroom 5%
    # Scale factor = 5 / 15 = 0.333 → each gets ~2.5%, total = ~5%
    equal_data = {"signal": "BUY", "confidence": 0.85, "strategic_fit_score": 7.0, "portfolio_priority": "HIGH"}
    r = _size(
        ["AAPL", "MSFT"],
        symbol_data={"AAPL": equal_data, "MSFT": equal_data},
        symbol_sectors={"AAPL": "Technology", "MSFT": "Technology"},
        sector_weights={"Technology": 55.0},
        sector_limits={**_SECTOR_LIMITS, "Technology": 60.0},
    )
    assert r.status == "WARNING"
    assert r.total_allocated_pct <= 5.0 + 0.01  # within sector headroom
    assert r.total_allocated_pct > 0              # but still allocated something


# ── 11: Deterministic output ──────────────────────────────────────────────────

def test_deterministic():
    symbol_data = {
        "AAPL": {"signal": "BUY",        "confidence": 0.90, "strategic_fit_score": 8.0, "portfolio_priority": "HIGH"},
        "BH":   {"signal": "ACCUMULATE", "confidence": 0.75, "strategic_fit_score": 6.0, "portfolio_priority": "MEDIUM"},
        "SCC":  {"signal": "WATCH",      "confidence": 0.50, "strategic_fit_score": 4.0, "portfolio_priority": "LOW"},
    }
    r1 = _size(["AAPL", "BH", "SCC"], symbol_data=symbol_data)
    r2 = _size(["AAPL", "BH", "SCC"], symbol_data=symbol_data)
    assert r1.status == r2.status
    assert r1.total_allocated_pct == r2.total_allocated_pct
    for s1, s2 in zip(r1.suggestions, r2.suggestions):
        assert s1.symbol == s2.symbol
        assert s1.suggested_pct == s2.suggested_pct
        assert s1.position_score == s2.position_score


# ── 12: Suggestions sorted by score desc ─────────────────────────────────────

def test_suggestions_sorted_by_score():
    symbol_data = {
        "TOP": {"signal": "ACCUMULATE", "confidence": 0.95, "strategic_fit_score": 9.0, "portfolio_priority": "HIGH"},
        "MID": {"signal": "BUY",        "confidence": 0.70, "strategic_fit_score": 6.0, "portfolio_priority": "MEDIUM"},
        "BOT": {"signal": "WATCH",      "confidence": 0.40, "strategic_fit_score": 3.0, "portfolio_priority": "LOW"},
    }
    r = _size(["TOP", "MID", "BOT"], symbol_data=symbol_data)
    scores = [s.position_score for s in r.suggestions]
    assert scores == sorted(scores, reverse=True)
    assert r.suggestions[0].symbol == "TOP"
    assert r.suggestions[-1].symbol == "BOT"
