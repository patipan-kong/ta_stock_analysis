"""Tests for services/evaluation/trust_report.py and
verdict_composer.compose_trust_report — AI Evaluation M7 (UX S9).

Coverage
--------
1. compose_trust_report branch coverage (pure function): no_decisions,
   insufficient_evidence, tie, ai_ahead, human_ahead, with/without insight —
   never more than 3 sentences, at most one number-bearing clause each.
2. compute_trust_report cold start: no RecommendationSnapshot ever ->
   status="cold_start", single first-run sentence.
3. compute_trust_report with decisions: compliance count sourced from
   list_execution_ledger's decision_counts (APPROVED + PARTIAL_EXECUTION),
   sentences always present, status reflects scorecard's own status.
"""
from __future__ import annotations

import json
import sys
import os
from datetime import datetime, timedelta

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.evaluation.verdict_composer import compose_trust_report  # noqa: E402
from services.evaluation.trust_report import compute_trust_report, _pick_insight  # noqa: E402


# ─── compose_trust_report (pure) ──────────────────────────────────────────────

def test_no_decisions_branch():
    result = compose_trust_report(
        period_days=90, belief_avg_alpha=None, belief_status="cold_start",
        gap_b=None, gap_b_n=0, min_n_win_rate=5, tie_band_pct=0.3,
        followed_count=0, total_decisions=0, insight=None,
    )
    assert result["branch"] == "no_decisions"
    assert len(result["sentences"]) == 2
    assert "not yet recorded" in result["sentences"][1]["en"]


def test_insufficient_evidence_branch():
    result = compose_trust_report(
        period_days=90, belief_avg_alpha=1.5, belief_status="ok",
        gap_b=2.0, gap_b_n=2, min_n_win_rate=5, tie_band_pct=0.3,
        followed_count=3, total_decisions=4, insight=None,
    )
    assert result["branch"] == "insufficient_evidence"
    assert "followed 3 of 4" in result["sentences"][1]["en"]
    assert len(result["sentences"]) == 2


def test_tie_branch():
    result = compose_trust_report(
        period_days=90, belief_avg_alpha=1.0, belief_status="ok",
        gap_b=0.1, gap_b_n=10, min_n_win_rate=5, tie_band_pct=0.3,
        followed_count=8, total_decisions=11, insight=None,
    )
    assert result["branch"] == "tie"
    assert "about the same" in result["sentences"][1]["en"]


def test_ai_ahead_branch():
    result = compose_trust_report(
        period_days=90, belief_avg_alpha=1.0, belief_status="ok",
        gap_b=2.0, gap_b_n=10, min_n_win_rate=5, tie_band_pct=0.3,
        followed_count=8, total_decisions=11, insight=None,
    )
    assert result["branch"] == "ai_ahead"
    assert "following the AI's recommendations exactly" in result["sentences"][1]["en"]


def test_human_ahead_branch_matches_muji_wireframe_example():
    # UX S9 wireframe: "การตัดสินใจของคุณเองก็ทำได้ดี (+0.7%)"
    result = compose_trust_report(
        period_days=90, belief_avg_alpha=2.9, belief_status="ok",
        gap_b=-0.7, gap_b_n=10, min_n_win_rate=5, tie_band_pct=0.3,
        followed_count=8, total_decisions=11, insight=None,
    )
    assert result["branch"] == "human_ahead"
    assert "+0.7%" in result["sentences"][1]["en"]
    assert "+0.7%" in result["sentences"][1]["th"]


def test_insight_sentence_appended_when_present():
    result = compose_trust_report(
        period_days=90, belief_avg_alpha=1.0, belief_status="ok",
        gap_b=-0.5, gap_b_n=10, min_n_win_rate=5, tie_band_pct=0.3,
        followed_count=8, total_decisions=11,
        insight={"label": "Portfolio Improvement", "human_better": 3, "total": 4},
    )
    assert len(result["sentences"]) == 3
    assert "Portfolio Improvement" in result["sentences"][2]["en"]
    assert "ปรับสมดุล" not in result["sentences"][2]["th"]  # label passed through verbatim, not re-translated


def test_never_exceeds_three_sentences():
    result = compose_trust_report(
        period_days=90, belief_avg_alpha=1.0, belief_status="ok",
        gap_b=-0.5, gap_b_n=10, min_n_win_rate=5, tie_band_pct=0.3,
        followed_count=8, total_decisions=11,
        insight={"label": "Policy Enforcement", "human_better": 3, "total": 3},
    )
    assert len(result["sentences"]) <= 3


# ─── _pick_insight ─────────────────────────────────────────────────────────────

def test_pick_insight_requires_minimum_sample():
    by_class = {"Portfolio Improvement": {"human_better": 1, "ai_better": 0, "tie": 0, "total": 1}}
    assert _pick_insight(by_class) is None


def test_pick_insight_requires_majority():
    by_class = {"Portfolio Improvement": {"human_better": 1, "ai_better": 2, "tie": 0, "total": 3}}
    assert _pick_insight(by_class) is None


def test_pick_insight_picks_strongest_ratio():
    by_class = {
        "Portfolio Improvement": {"human_better": 2, "ai_better": 2, "tie": 0, "total": 4},
        "Policy Enforcement": {"human_better": 3, "ai_better": 0, "tie": 0, "total": 3},
    }
    picked = _pick_insight(by_class)
    assert picked is not None
    assert picked["label"] == "Policy Enforcement"


# ─── compute_trust_report (integration) ───────────────────────────────────────

@pytest.fixture()
def db():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from models.database import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture()
def ws_portfolio(db):
    from models.database import Workspace, Portfolio

    ws = Workspace(name="Test")
    db.add(ws)
    db.commit()
    db.refresh(ws)

    portfolio = Portfolio(workspace_id=ws.id, name="P1", cash_balance=100_000.0)
    db.add(portfolio)
    db.commit()
    db.refresh(portfolio)
    return ws, portfolio


def test_cold_start_no_snapshot_ever(db, ws_portfolio):
    ws, portfolio = ws_portfolio
    result = compute_trust_report(db, portfolio.id, period_days=90)

    assert result["status"] == "cold_start"
    assert len(result["sentences"]) == 1
    assert result["link"] == "/ai-analytics"


def test_with_decisions_reports_compliance_count(db, ws_portfolio):
    from models.database import OptimizerHistory, RecommendationSnapshot, UserExecutionDecision

    ws, portfolio = ws_portfolio

    oh = OptimizerHistory(
        workspace_id=ws.id, portfolio_id=portfolio.id, portfolio_name=portfolio.name,
        analyzed_at=datetime.utcnow(), swap_count=0,
        result_json=json.dumps({"target_allocations": [], "cash_balance": 50_000.0}),
    )
    db.add(oh)
    db.commit()
    db.refresh(oh)

    snap = RecommendationSnapshot(
        workspace_id=ws.id, optimizer_history_id=oh.id, portfolio_id=portfolio.id,
        total_portfolio_value=1_000_000.0,
        projected_allocations_json="[]",
        created_at=datetime.utcnow() - timedelta(days=10),
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)

    db.add(UserExecutionDecision(
        workspace_id=ws.id, portfolio_id=portfolio.id, recommendation_snapshot_id=snap.id,
        decision="APPROVED", executed_at=datetime.utcnow() - timedelta(days=9),
        is_system_generated=False,
    ))
    db.add(UserExecutionDecision(
        workspace_id=ws.id, portfolio_id=portfolio.id, recommendation_snapshot_id=snap.id,
        decision="REJECTED", executed_at=datetime.utcnow() - timedelta(days=8),
        is_system_generated=False,
    ))
    db.commit()

    result = compute_trust_report(db, portfolio.id, period_days=90)

    assert result["status"] in ("ok", "partial")
    assert "followed 1 of 2" in result["sentences"][1]["en"]
