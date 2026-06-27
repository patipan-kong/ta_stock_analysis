"""Tests for Phase 4D.2 — Risk Budget Allocation Engine.

All tests use compute_allocations() (pure function, no DB).
Tests 17-22 cover the scale-normalisation fix (suggest_risk_budget) added in
the 4D.2 audit: agent scores are small integers, not 0-100.
"""
import pytest
from services.allocation_engine import (
    AllocationItem,
    RiskBudgetResult,
    _FA_MAX,
    _FA_MIN,
    _TA_MAX,
    _TA_MIN,
    _normalize_agent_score,
    compute_allocations,
)

# ── Shared fixtures ───────────────────────────────────────────────────────────

_DEFAULT_REC: dict = {
    "technical_score":   70.0,
    "fundamental_score": 65.0,
    "risk_score":        30.0,
    "confidence_score":  75.0,
    "sector":            "Technology",
}


def _rec(symbol: str, **overrides) -> dict:
    return {"symbol": symbol, **{**_DEFAULT_REC, **overrides}}


def _alloc(
    recommendations: list[dict],
    **kwargs,
) -> RiskBudgetResult:
    return compute_allocations(recommendations, **kwargs)


# ── 1: Empty input ────────────────────────────────────────────────────────────

def test_empty_input():
    r = _alloc([])
    assert r.status == "FAIL"
    assert r.allocations == []
    assert r.total_weight_pct == 0.0
    assert "No recommendations provided" in r.reasoning[0]


# ── 2: All excluded by confidence ─────────────────────────────────────────────

def test_all_excluded_by_confidence():
    recs = [
        _rec("A", confidence_score=40.0),
        _rec("B", confidence_score=30.0),
    ]
    r = _alloc(recs)
    assert r.status == "FAIL"
    assert r.allocations == []
    assert len(r.excluded) == 2
    assert all("confidence" in e.reason.lower() for e in r.excluded)


# ── 3: Confidence threshold excludes low-confidence symbols ───────────────────

def test_confidence_filter():
    recs = [
        _rec("PASS_A", confidence_score=80.0),
        _rec("PASS_B", confidence_score=55.0),
        _rec("FAIL_C", confidence_score=49.9),
    ]
    r = _alloc(recs)
    symbols_included = {a.symbol for a in r.allocations}
    symbols_excluded = {e.symbol for e in r.excluded}

    assert "PASS_A" in symbols_included
    assert "PASS_B" in symbols_included
    assert "FAIL_C" in symbols_excluded
    assert "FAIL_C" not in symbols_included


# ── 4: Weights sum to approximately 100 % ─────────────────────────────────────

def test_weights_sum_to_100():
    recs = [_rec(s) for s in ["A", "B", "C"]]
    r = _alloc(recs)
    assert r.total_weight_pct == pytest.approx(100.0, abs=0.05)


# ── 5: Higher expected return → larger allocation ─────────────────────────────

def test_higher_expected_return_gets_more():
    recs = [
        _rec("STRONG", technical_score=90, fundamental_score=90, confidence_score=90, risk_score=20),
        _rec("WEAK",   technical_score=30, fundamental_score=30, confidence_score=60, risk_score=20),
    ]
    r = _alloc(recs)
    strong = next(a for a in r.allocations if a.symbol == "STRONG")
    weak   = next(a for a in r.allocations if a.symbol == "WEAK")
    assert strong.weight_pct > weak.weight_pct


# ── 6: Lower risk → larger allocation (same expected return) ──────────────────

def test_lower_risk_gets_more():
    base = {"technical_score": 70, "fundamental_score": 70, "confidence_score": 75}
    recs = [
        _rec("LOW_RISK",  **base, risk_score=20.0),
        _rec("HIGH_RISK", **base, risk_score=60.0),
    ]
    r = _alloc(recs)
    low  = next(a for a in r.allocations if a.symbol == "LOW_RISK")
    high = next(a for a in r.allocations if a.symbol == "HIGH_RISK")
    assert low.weight_pct > high.weight_pct


# ── 7: High-risk cap (risk_score > 80 → max 5 %) ─────────────────────────────

def test_high_risk_cap():
    recs = [
        _rec("RISKY",  risk_score=85.0, confidence_score=60.0),
        _rec("SAFE_A", risk_score=20.0, confidence_score=60.0),
        _rec("SAFE_B", risk_score=20.0, confidence_score=60.0),
    ]
    r = _alloc(recs, high_risk_threshold=80.0, high_risk_cap_pct=5.0)
    risky = next(a for a in r.allocations if a.symbol == "RISKY")
    assert risky.weight_pct <= 5.0 + 0.05   # tolerance
    assert risky.capped
    assert risky.cap_reason is not None
    assert "risk" in risky.cap_reason.lower()


# ── 8: Max position cap ───────────────────────────────────────────────────────

def test_max_position_cap():
    # Single symbol should be capped at max_position_pct when alone
    recs = [_rec("ONLY", risk_score=10.0, confidence_score=90.0)]
    r = _alloc(recs, max_position_pct=20.0)
    a = r.allocations[0]
    # With a single symbol, all weight goes to it → renormalized to 100%
    # Cap is 20%; with only 1 uncapped symbol the weight redistributes back
    # to fill the total.  The cap only binds when there are other symbols.
    assert r.total_weight_pct == pytest.approx(100.0, abs=0.1)


def test_max_position_cap_binds_with_multiple():
    # Two equally-scored symbols; one starts at ~50%, which exceeds the 30% cap.
    # After cap + redistribution both should be at 30% → total = 60%.
    # But since both are capped equally, total weight after renorm = 100%.
    recs = [_rec(s, risk_score=10.0, confidence_score=75.0) for s in ["A", "B", "C", "D"]]
    r = _alloc(recs, max_position_pct=30.0)
    for a in r.allocations:
        assert a.weight_pct <= 30.0 + 0.05


# ── 9: Sector concentration cap ───────────────────────────────────────────────

def test_sector_cap():
    recs = [
        _rec("T1", sector="Technology"),
        _rec("T2", sector="Technology"),
        _rec("T3", sector="Technology"),
        _rec("H1", sector="Healthcare"),
    ]
    # With 3 tech stocks of equal score the raw tech weight would be ~75%
    # Sector cap forces tech ≤ 40%
    sector_caps = {"Technology": 40.0, "Healthcare": 40.0}
    r = _alloc(recs, sector_caps=sector_caps, max_position_pct=50.0)
    tech_total = sum(a.weight_pct for a in r.allocations if a.sector == "Technology")
    assert tech_total <= 40.0 + 0.1


# ── 10: Expected return formula ───────────────────────────────────────────────

def test_expected_return_formula():
    ta, fa, conf = 80.0, 70.0, 60.0
    recs = [_rec("X", technical_score=ta, fundamental_score=fa, confidence_score=conf, risk_score=50.0)]
    r = _alloc(recs)
    a = r.allocations[0]
    expected = ta * 0.40 + fa * 0.40 + conf * 0.20
    assert a.expected_return == pytest.approx(expected, abs=0.01)


# ── 11: Allocation score formula ──────────────────────────────────────────────

def test_allocation_score_formula():
    ta, fa, conf, risk = 80.0, 70.0, 60.0, 25.0
    recs = [_rec("X", technical_score=ta, fundamental_score=fa, confidence_score=conf, risk_score=risk)]
    r = _alloc(recs)
    a = r.allocations[0]
    expected_return = ta * 0.40 + fa * 0.40 + conf * 0.20
    expected_score  = expected_return / max(risk, 1)
    assert a.allocation_score == pytest.approx(expected_score, rel=0.001)


# ── 12: Deterministic output ──────────────────────────────────────────────────

def test_deterministic():
    recs = [
        _rec("A", technical_score=80, fundamental_score=70, risk_score=25, confidence_score=85),
        _rec("B", technical_score=60, fundamental_score=65, risk_score=40, confidence_score=70),
        _rec("C", technical_score=45, fundamental_score=50, risk_score=55, confidence_score=60),
    ]
    r1 = _alloc(recs)
    r2 = _alloc(recs)
    assert r1.status == r2.status
    assert r1.total_weight_pct == r2.total_weight_pct
    for a1, a2 in zip(r1.allocations, r2.allocations):
        assert a1.symbol == a2.symbol
        assert a1.weight_pct == a2.weight_pct


# ── 13: Sorted by weight desc ─────────────────────────────────────────────────

def test_sorted_by_weight_descending():
    recs = [
        _rec("C", technical_score=40, fundamental_score=40, risk_score=50, confidence_score=60),
        _rec("A", technical_score=90, fundamental_score=85, risk_score=20, confidence_score=90),
        _rec("B", technical_score=65, fundamental_score=60, risk_score=35, confidence_score=75),
    ]
    r = _alloc(recs)
    weights = [a.weight_pct for a in r.allocations]
    assert weights == sorted(weights, reverse=True)
    assert r.allocations[0].symbol == "A"


# ── 14: PASS status when no constraints bind ─────────────────────────────────

def test_status_pass_when_no_constraints():
    # Two symbols, good scores, no sector or position issue
    recs = [
        _rec("A", risk_score=20, confidence_score=80, sector="Technology"),
        _rec("B", risk_score=20, confidence_score=80, sector="Healthcare"),
    ]
    r = _alloc(recs, max_position_pct=60.0, sector_caps={"Technology": 60.0, "Healthcare": 60.0})
    assert r.status == "PASS"


# ── 15: WARNING status when a cap applies ─────────────────────────────────────

def test_status_warning_when_capped():
    recs = [
        _rec("RISKY", risk_score=85, confidence_score=60),
        _rec("SAFE",  risk_score=20, confidence_score=80),
    ]
    r = _alloc(recs, high_risk_threshold=80.0, high_risk_cap_pct=5.0)
    assert r.status == "WARNING"
    capped = next(a for a in r.allocations if a.symbol == "RISKY")
    assert capped.capped


# ── 16: Custom confidence threshold ───────────────────────────────────────────

def test_custom_confidence_threshold():
    recs = [
        _rec("A", confidence_score=70.0),
        _rec("B", confidence_score=60.0),
    ]
    # Default threshold is 50 — both pass
    r_default = _alloc(recs)
    assert len(r_default.allocations) == 2

    # Raise threshold to 65 — B excluded
    r_strict = _alloc(recs, confidence_threshold=65.0)
    assert len(r_strict.allocations) == 1
    assert r_strict.allocations[0].symbol == "A"
    assert r_strict.excluded[0].symbol == "B"


# ── 17-22: Agent-score normalisation (4D.2 audit fix) ────────────────────────
# Agent ta_score is ≈ -7..+7; fa_score is ≈ -6..+6.
# _normalize_agent_score() must map these to 0-100 correctly so that
# compute_allocations() formulas work on a consistent scale.

def test_normalize_minimum_scores():
    """Raw minimum values map to 0%."""
    assert _normalize_agent_score(_TA_MIN, _TA_MIN, _TA_MAX) == 0.0
    assert _normalize_agent_score(_FA_MIN, _FA_MIN, _FA_MAX) == 0.0


def test_normalize_maximum_scores():
    """Raw maximum values map to 100%."""
    assert _normalize_agent_score(_TA_MAX, _TA_MIN, _TA_MAX) == 100.0
    assert _normalize_agent_score(_FA_MAX, _FA_MIN, _FA_MAX) == 100.0


def test_normalize_neutral_scores():
    """Raw 0 (neutral mid-point) maps to approximately 50%."""
    ta_pct = _normalize_agent_score(0, _TA_MIN, _TA_MAX)
    fa_pct = _normalize_agent_score(0, _FA_MIN, _FA_MAX)
    assert ta_pct == pytest.approx(50.0, abs=1.0)
    assert fa_pct == pytest.approx(50.0, abs=1.0)


def test_normalized_moderate_score_risk_not_high_risk():
    """After normalisation, a moderate agent score (ta=2, fa=2) must NOT
    produce risk > 80 (the bug: raw 2 gave risk=98; normalised gives ~34)."""
    ta_pct = _normalize_agent_score(2, _TA_MIN, _TA_MAX)
    fa_pct = _normalize_agent_score(2, _FA_MIN, _FA_MAX)
    risk = max(0, min(100, 100 - round((ta_pct + fa_pct) / 2)))
    assert risk <= 80, (
        f"Moderate scores should not be high-risk; got risk={risk} "
        f"(ta_pct={ta_pct}, fa_pct={fa_pct})"
    )


def test_normalized_bearish_score_triggers_high_risk():
    """Clearly bearish agent scores (ta=-6, fa=-5) should still be high-risk
    after normalisation, confirming the cap is not disabled entirely."""
    ta_pct = _normalize_agent_score(-6, _TA_MIN, _TA_MAX)
    fa_pct = _normalize_agent_score(-5, _FA_MIN, _FA_MAX)
    risk = max(0, min(100, 100 - round((ta_pct + fa_pct) / 2)))
    assert risk > 80, (
        f"Bearish scores should be high-risk; got risk={risk}"
    )


def test_allocation_distribution_not_all_capped():
    """Simulate the previously-broken case: 4 moderate-quality stocks passed
    through suggest_risk_budget normalisation.  Allocations must NOT all be 5%
    and total must be ≈ 100%."""
    # These are the normalised values that suggest_risk_budget would produce
    # for typical Thai SET stocks with ta_raw ≈ 1-4 and fa_raw ≈ 1-3.
    ta_raw = [4, 2, 1, 3]
    fa_raw = [3, 2, 1, 4]
    recs = []
    for i, sym in enumerate(["BH", "GULF", "TOA", "KCE"]):
        ta_pct = _normalize_agent_score(ta_raw[i], _TA_MIN, _TA_MAX)
        fa_pct = _normalize_agent_score(fa_raw[i], _FA_MIN, _FA_MAX)
        risk   = max(0, min(100, 100 - round((ta_pct + fa_pct) / 2)))
        recs.append({
            "symbol":            sym,
            "sector":            "Healthcare",
            "technical_score":   ta_pct,
            "fundamental_score": fa_pct,
            "confidence_score":  60.0,
            "risk_score":        float(risk),
        })

    r = compute_allocations(recs)

    # No symbol should be at exactly the high-risk cap (5%)
    for a in r.allocations:
        assert a.weight_pct > 5.0 + 0.1, (
            f"{a.symbol} is still capped at 5% after normalisation fix "
            f"(risk={a.risk_score:.0f}, weight={a.weight_pct:.1f}%)"
        )

    # Weights should sum to ≈ 100%
    assert r.total_weight_pct == pytest.approx(100.0, abs=1.0), (
        f"Total weight should be ≈100% but got {r.total_weight_pct}%"
    )

    # Allocations should differ — not all identical
    weights = [a.weight_pct for a in r.allocations]
    assert max(weights) - min(weights) > 1.0, (
        "Allocations should vary with score quality, not all be equal"
    )
