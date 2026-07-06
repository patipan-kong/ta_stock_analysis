"""Stabilization Layer — Portfolio Optimizer Stabilization Sprint.

Prevents optimizer hyperactivity through four deterministic mechanisms:

1. Drift Threshold Buffer   — suppress individual trades with < 3% allocation drift
2. Rebalance Cooldown       — 7-day portfolio-level cooldown after last rebalance
3. NO_REBALANCE_REQUIRED    — first-class consensus state when all checks pass clean
4. Minimum Impact Filter    — suppress when estimated net benefit < 0.20% of NAV

These checks run AFTER the AI pipeline completes and BEFORE the result is returned to
the frontend. They are purely deterministic — no additional AI calls are made.

See OPTIMIZER_PHILOSOPHY.md §8 — every trade is guilty until proven necessary;
this layer is where that default is enforced.

Override conditions bypass the cooldown when urgent action is warranted:
  - Market regime change since last rebalance
  - Sector concentration breach detected
  - Single-position limit breach detected
  - Risk policy violation (governance flags)
  - Drawdown / emergency event
  - Confidence collapse (consensus_strength_score < 30)
  - Manual override requested by user (force_rebalance=True)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta

log = logging.getLogger(__name__)

# ── Configurable defaults ────────────────────────────────────────────────────

DRIFT_THRESHOLD_PCT: float = 3.0        # allocation drift below this → within tolerance
COOLDOWN_DAYS: int = 7                  # days between rebalances (portfolio-level)
NET_BENEFIT_THRESHOLD_PCT: float = 0.20  # minimum net benefit (% of NAV) to justify trading
EST_TRADE_COST_BPS_PER_PCT: float = 0.0015 # estimated cost as % of NAV per 1% of turnover (0.15% × 1% = 0.0015%)
EXPECTED_GAIN_SCALE: float = 0.40        # fraction of buy-turnover → expected quality gain

# ── Override trigger labels ──────────────────────────────────────────────────

OVERRIDE_REGIME_CHANGE       = "REGIME_CHANGE"
OVERRIDE_SECTOR_BREACH       = "SECTOR_CONCENTRATION_BREACH"
OVERRIDE_POSITION_BREACH     = "SINGLE_POSITION_BREACH"
OVERRIDE_RISK_VIOLATION      = "RISK_POLICY_VIOLATION"
OVERRIDE_DRAWDOWN_EVENT      = "DRAWDOWN_EVENT"
OVERRIDE_CONFIDENCE_COLLAPSE = "CONFIDENCE_COLLAPSE"
OVERRIDE_MANUAL              = "MANUAL_OVERRIDE"

# ── Stabilized status values ─────────────────────────────────────────────────

STATUS_REBALANCE_REQUIRED    = "REBALANCE_REQUIRED"
STATUS_NO_REBALANCE          = "NO_REBALANCE_REQUIRED"
STATUS_COOLDOWN_ACTIVE       = "COOLDOWN_ACTIVE"
STATUS_OPTIMAL               = "OPTIMAL"


# ─── Dataclasses ──────────────────────────────────────────────────────────────

@dataclass
class DriftResult:
    symbol: str
    current_weight: float
    target_weight: float
    allocation_drift: float
    within_tolerance: bool
    threshold_pct: float


@dataclass
class CooldownState:
    active: bool
    last_rebalance_at: datetime | None
    days_elapsed: int
    days_remaining: int
    cooldown_days: int
    overridden: bool
    override_reasons: list[str] = field(default_factory=list)


@dataclass
class MinimumImpactResult:
    expected_improvement_pct: float
    estimated_cost_pct: float
    net_benefit_pct: float
    passes_threshold: bool
    threshold_pct: float
    suppressed: bool
    total_turnover_pct: float


@dataclass
class StabilizationDecision:
    stabilized_status: str
    original_status: str
    reason: str | None
    drift_threshold_pct: float
    cooldown: CooldownState
    minimum_impact: MinimumImpactResult | None
    drift_analysis: list[DriftResult]
    positions_within_tolerance: int
    positions_needing_action: int
    overrides_active: list[str]


# ─── Drift analysis ────────────────────────────────────────────────────────────

def compute_drift_analysis(
    target_allocations: list[dict],
    drift_threshold_pct: float = DRIFT_THRESHOLD_PCT,
) -> list[DriftResult]:
    """Classify each allocation position as within/outside the drift tolerance band.

    SELL-signal positions are always marked as needing action regardless of drift.
    """
    results: list[DriftResult] = []
    for a in target_allocations:
        sym = a.get("symbol", "?")
        current_w = round(float(a.get("current_weight") or 0), 2)
        action = (a.get("action") or "HOLD").upper()

        if action == "SELL":
            # Forced exits are always needed — drift is irrelevant
            results.append(DriftResult(
                symbol=sym,
                current_weight=current_w,
                target_weight=0.0,
                allocation_drift=current_w,
                within_tolerance=False,
                threshold_pct=drift_threshold_pct,
            ))
            continue

        target_w = round(float(a.get("target_weight") or current_w), 2)
        drift = round(abs(current_w - target_w), 2)
        results.append(DriftResult(
            symbol=sym,
            current_weight=current_w,
            target_weight=target_w,
            allocation_drift=drift,
            within_tolerance=drift < drift_threshold_pct,
            threshold_pct=drift_threshold_pct,
        ))
    return results


# ─── Cooldown engine ──────────────────────────────────────────────────────────

def check_cooldown(
    last_rebalance_at: datetime | None,
    cooldown_days: int = COOLDOWN_DAYS,
) -> CooldownState:
    """Return cooldown state for a portfolio given the timestamp of its last rebalance."""
    if last_rebalance_at is None:
        return CooldownState(
            active=False, last_rebalance_at=None,
            days_elapsed=0, days_remaining=0,
            cooldown_days=cooldown_days, overridden=False,
        )
    now = datetime.utcnow()
    elapsed = (now - last_rebalance_at).days
    remaining = max(0, cooldown_days - elapsed)
    return CooldownState(
        active=remaining > 0,
        last_rebalance_at=last_rebalance_at,
        days_elapsed=elapsed,
        days_remaining=remaining,
        cooldown_days=cooldown_days,
        overridden=False,
    )


def detect_cooldown_overrides(
    cooldown: CooldownState,
    policy_context: dict | None = None,
    regime_context: dict | None = None,
    prev_regime: str | None = None,
    consensus: dict | None = None,
    force_rebalance: bool = False,
) -> CooldownState:
    """Detect conditions that should bypass the rebalance cooldown.

    Only active when cooldown.active=True.  Returns a new CooldownState with
    overridden=True and override_reasons populated if any condition fires.
    """
    if not cooldown.active:
        return cooldown

    overrides: list[str] = []

    # Manual override always wins
    if force_rebalance:
        overrides.append(OVERRIDE_MANUAL)

    # Regime changed since last rebalance
    current_regime = (regime_context or {}).get("regime")
    if current_regime and prev_regime and current_regime != prev_regime:
        overrides.append(OVERRIDE_REGIME_CHANGE)
        log.info("[COOLDOWN_OVERRIDE] regime_change: %s → %s", prev_regime, current_regime)

    # Emergency / drawdown event
    if (policy_context or {}).get("emergency_override"):
        overrides.append(OVERRIDE_DRAWDOWN_EVENT)

    # Active policy violations
    violations: list[str] = (policy_context or {}).get("violations", [])
    for v in violations:
        if "CONCENTRATION_BREACH" in v or "SINGLE_POSITION" in v:
            if OVERRIDE_POSITION_BREACH not in overrides:
                overrides.append(OVERRIDE_POSITION_BREACH)
        if "SECTOR_BREACH" in v:
            if OVERRIDE_SECTOR_BREACH not in overrides:
                overrides.append(OVERRIDE_SECTOR_BREACH)

    # Risk / governance flags
    gov_flags: list[str] = (policy_context or {}).get("governance_flags", [])
    for f in gov_flags:
        if any(kw in f for kw in ("POLICY_VIOLATION", "CONCENTRATION_BREACH", "SECTOR_LIMIT")):
            if OVERRIDE_RISK_VIOLATION not in overrides:
                overrides.append(OVERRIDE_RISK_VIOLATION)

    # Confidence collapse (very low consensus strength)
    strength = float((consensus or {}).get("consensus_strength_score", 50))
    if strength < 30:
        overrides.append(OVERRIDE_CONFIDENCE_COLLAPSE)

    if overrides:
        log.info("[COOLDOWN_OVERRIDE] bypassing cooldown: reasons=%s", overrides)
        return CooldownState(
            active=False,
            last_rebalance_at=cooldown.last_rebalance_at,
            days_elapsed=cooldown.days_elapsed,
            days_remaining=cooldown.days_remaining,
            cooldown_days=cooldown.cooldown_days,
            overridden=True,
            override_reasons=overrides,
        )

    return CooldownState(
        active=cooldown.active,
        last_rebalance_at=cooldown.last_rebalance_at,
        days_elapsed=cooldown.days_elapsed,
        days_remaining=cooldown.days_remaining,
        cooldown_days=cooldown.cooldown_days,
        overridden=False,
    )


# ─── Minimum impact filter ────────────────────────────────────────────────────

def compute_minimum_impact(
    target_allocations: list[dict],
    xai_score: int = 50,
    est_trade_cost_bps_per_pct: float = EST_TRADE_COST_BPS_PER_PCT,
    net_benefit_threshold: float = NET_BENEFIT_THRESHOLD_PCT,
) -> MinimumImpactResult:
    """Estimate net benefit of the proposed rebalancing vs estimated transaction costs.

    Expected improvement is derived conservatively from the AI rebalance_opportunity_score
    (scaled to a % of NAV) minus estimated round-trip trading friction.

    The intent is to suppress rebalances where transaction costs consume all expected gains.

    Args:
        target_allocations        : L2 target allocations
        xai_score                 : rebalance_opportunity_score (0-100) from L2
        est_trade_cost_bps_per_pct: cost % of NAV per 1% of portfolio turnover
        net_benefit_threshold     : minimum net benefit (%) to justify trading
    """
    # Total turnover = sum of absolute allocation changes (each direction counted once)
    total_turnover_pct = round(
        sum(abs(a.get("allocation_change_percent") or 0) for a in target_allocations
            if (a.get("action") or "HOLD").upper() not in ("HOLD", "WATCH")) / 2,
        2,
    )

    # Buy-side turnover (net new capital deployed)
    buy_turnover_pct = sum(
        abs(a.get("allocation_change_percent") or 0)
        for a in target_allocations
        if (a.get("action") or "HOLD").upper() in ("BUY", "ACCUMULATE")
    )

    # Estimated cost: each % of NAV moved incurs trading friction (both sides)
    estimated_cost_pct = round(total_turnover_pct * est_trade_cost_bps_per_pct, 4)

    # Expected improvement: opportunity score drives the expected gain (conservative scale)
    # At score=100 we expect 0.5% NAV improvement from the rebalance; at score=20 → 0.10%
    expected_improvement_pct = round(max(0.0, (xai_score / 100) * 0.50), 4)

    # All values are expressed as % of NAV (e.g. 0.25 means 0.25% of NAV)
    net_benefit_pct = round(expected_improvement_pct - estimated_cost_pct, 4)
    passes = net_benefit_pct >= net_benefit_threshold

    log.info(
        "[MIN_IMPACT] xai_score=%d turnover=%.1f%% cost=%.4f%% expected=%.4f%% net=%.4f%% "
        "threshold=%.2f%% passes=%s",
        xai_score, total_turnover_pct, estimated_cost_pct, expected_improvement_pct,
        net_benefit_pct, net_benefit_threshold, passes,
    )

    return MinimumImpactResult(
        expected_improvement_pct=expected_improvement_pct,
        estimated_cost_pct=estimated_cost_pct,
        net_benefit_pct=net_benefit_pct,  # already in % of NAV
        passes_threshold=passes,
        threshold_pct=net_benefit_threshold,
        suppressed=not passes,
        total_turnover_pct=total_turnover_pct,
    )


# ─── Duplicate ticker diagnostic ─────────────────────────────────────────────

def diagnose_duplicate_tickers(result: dict) -> dict:
    """Scan pipeline outputs for duplicate ticker symbols and identify root cause layer.

    Returns a diagnostic report dict.  No changes are made to `result`.
    """
    report: dict[str, list[str]] = {
        "layer1_swaps": [],
        "layer2_allocations": [],
        "final_allocations": [],
        "swap_suggestions": [],
        "watchlist_ranking": [],
    }
    duplicates_found: list[dict] = []

    def _find_dupes(lst: list, key: str, layer: str) -> list[str]:
        seen: dict[str, int] = {}
        dupes: list[str] = []
        for item in lst:
            sym = item.get(key, "?")
            seen[sym] = seen.get(sym, 0) + 1
        for sym, cnt in seen.items():
            if cnt > 1:
                dupes.append(sym)
                duplicates_found.append({"symbol": sym, "count": cnt, "layer": layer})
        return dupes

    l1 = result.get("layer1_result", {}) or {}
    l2 = result.get("layer2_result", {}) or {}

    report["layer1_swaps"] = _find_dupes(l1.get("swap_suggestions", []) or [], "sell_symbol", "L1_SWAPS")
    report["layer2_allocations"] = _find_dupes(l2.get("target_allocations", []) or [], "symbol", "L2_ALLOCS")
    report["final_allocations"] = _find_dupes(result.get("target_allocations", []) or [], "symbol", "FINAL_ALLOCS")
    report["swap_suggestions"] = _find_dupes(result.get("swap_suggestions", []) or [], "sell_symbol", "SWAP_SUGGESTIONS")
    report["watchlist_ranking"] = _find_dupes(result.get("watchlist_ranking", []) or [], "symbol", "WATCHLIST_RANKING")

    total = len(duplicates_found)
    if total > 0:
        log.warning(
            "[DUPLICATE_TICKER_DIAGNOSTIC] found %d duplicate(s): %s",
            total, duplicates_found,
        )

    return {
        "total_duplicates_found": total,
        "duplicates": duplicates_found,
        "by_layer": {k: v for k, v in report.items() if v},
        "root_cause_hypothesis": _hypothesize_root_cause(report),
    }


def _hypothesize_root_cause(report: dict[str, list[str]]) -> str | None:
    if report["layer2_allocations"]:
        return "OPTIMIZER_OUTPUT — duplicate symbols in L2 AI allocation output"
    if report["final_allocations"] and not report["layer2_allocations"]:
        return "API_SERIALIZATION — duplication introduced during post-processing"
    if report["swap_suggestions"] and not report["final_allocations"]:
        return "API_SERIALIZATION — swap derivation creates duplicate entries"
    if report["layer1_swaps"]:
        return "OPTIMIZER_OUTPUT — duplicate sell_symbol entries in L1 swap output"
    if report["watchlist_ranking"]:
        return "PORTFOLIO_AGGREGATION — duplicate symbol in watchlist ranking"
    return None


# ─── Main public API ──────────────────────────────────────────────────────────

def apply_stabilization(
    result: dict,
    last_rebalance_at: datetime | None,
    prev_regime: str | None = None,
    drift_threshold_pct: float = DRIFT_THRESHOLD_PCT,
    cooldown_days: int = COOLDOWN_DAYS,
    net_benefit_threshold: float = NET_BENEFIT_THRESHOLD_PCT,
    force_rebalance: bool = False,
) -> dict:
    """Apply all stabilization checks to an optimizer result dict.

    Modifies and returns `result` with a `stabilization` key added.
    The `status` field may be overridden from REBALANCE to NO_REBALANCE_REQUIRED
    or COOLDOWN_ACTIVE when checks trigger.

    Args:
        result               : full optimizer result from run_layered_optimizer
        last_rebalance_at    : UTC datetime of last REBALANCE optimizer run for this portfolio
        prev_regime          : market regime recorded in the last rebalance result
        drift_threshold_pct  : allocation drift below this is within tolerance
        cooldown_days        : days between allowed rebalances
        net_benefit_threshold: minimum net benefit % to justify trading
        force_rebalance      : user-requested override of all stabilization blocks
    """
    target_allocations = result.get("target_allocations") or []
    consensus          = result.get("consensus") or {}
    policy_context     = result.get("active_policy")
    regime_context     = result.get("market_regime")
    xai_score          = int(result.get("rebalance_opportunity_score") or 0)
    original_status    = result.get("status", "REBALANCE")

    # ── 1. Drift analysis ────────────────────────────────────────────────────
    drift_analysis    = compute_drift_analysis(target_allocations, drift_threshold_pct)
    within_tol        = [d for d in drift_analysis if d.within_tolerance]
    needing_action    = [d for d in drift_analysis if not d.within_tolerance]
    suppressed_syms   = {d.symbol for d in within_tol}

    # ── 2. Cooldown check ────────────────────────────────────────────────────
    cooldown = check_cooldown(last_rebalance_at, cooldown_days)
    cooldown = detect_cooldown_overrides(
        cooldown, policy_context, regime_context, prev_regime, consensus, force_rebalance,
    )

    # ── 3. Minimum impact filter ─────────────────────────────────────────────
    min_impact = compute_minimum_impact(target_allocations, xai_score, net_benefit_threshold=net_benefit_threshold)

    # ── 4. Diagnostic ────────────────────────────────────────────────────────
    dup_report = diagnose_duplicate_tickers(result)

    # ── 5. Determine stabilized status ───────────────────────────────────────
    overrides_active = cooldown.override_reasons.copy()

    has_sell            = any((a.get("action") or "").upper() == "SELL" for a in target_allocations)
    has_violations      = bool((policy_context or {}).get("violations"))
    has_risk_flags      = any(
        (f.get("severity") or "").upper() in ("HIGH", "CRITICAL")
        for f in (result.get("layer3_result") or {}).get("risk_flags", [])
    )
    all_within_tol      = not needing_action and not has_sell
    already_no_action   = original_status in ("NO_ACTION", "NO_REBALANCE_REQUIRED", "COOLDOWN_ACTIVE")

    stabilized_status = original_status
    stabilization_reason: str | None = None

    if force_rebalance:
        # User explicitly requested — pass through regardless
        stabilized_status = "REBALANCE"
        stabilization_reason = "Manual override requested — all stabilization filters bypassed."
        overrides_active = list({*overrides_active, OVERRIDE_MANUAL})

    elif already_no_action:
        # AI already said no action — keep that decision, just enrich metadata
        stabilized_status = original_status

    elif all_within_tol and not has_violations and not has_risk_flags:
        # Every position already within tolerance and portfolio is clean
        stabilized_status = STATUS_NO_REBALANCE
        stabilization_reason = (
            f"All {len(within_tol)} position(s) are within the "
            f"{drift_threshold_pct:.0f}% drift tolerance band. "
            "No policy violations or risk breaches detected."
        )
        log.info("[STABILIZATION] NO_REBALANCE_REQUIRED — all within tolerance (%d positions)", len(within_tol))

    elif cooldown.active and not cooldown.overridden:
        # In cooldown window and no urgent override — checked before minimum impact so the
        # user sees "cooldown active" rather than the less informative "insufficient edge"
        stabilized_status = STATUS_COOLDOWN_ACTIVE
        stabilization_reason = (
            f"Portfolio rebalanced {cooldown.days_elapsed} day(s) ago. "
            f"{cooldown.days_remaining} day(s) remaining in the "
            f"{cooldown.cooldown_days}-day cooldown window."
        )
        log.info("[STABILIZATION] COOLDOWN_ACTIVE — %d days remaining", cooldown.days_remaining)

    elif not has_sell and not has_violations and not has_risk_flags and min_impact.suppressed:
        # Net benefit does not justify transaction friction
        stabilized_status = STATUS_NO_REBALANCE
        stabilization_reason = (
            f"Expected net benefit ({min_impact.net_benefit_pct:.3f}%) is below the "
            f"{net_benefit_threshold:.2f}% minimum threshold. "
            "Transaction costs would consume the projected gain."
        )
        log.info("[STABILIZATION] NO_REBALANCE_REQUIRED — minimum impact filter triggered (net=%.3f%%)", min_impact.net_benefit_pct)

    else:
        stabilized_status = original_status  # pass through as REBALANCE

    # ── 6. Mark within-tolerance allocations (for frontend badge) ────────────
    # Only meaningful when the overall run is still REBALANCE (a mixed bag —
    # some positions need action, others don't). HOLD rows don't need the
    # badge (they render as "N positions held unchanged" already); every
    # other action, including WATCH, gets tagged so the table and the
    # Portfolio Drift card never disagree about the same position.
    drift_by_symbol = {d.symbol: d.allocation_drift for d in drift_analysis}
    if stabilized_status == "REBALANCE":
        for a in target_allocations:
            sym = a.get("symbol")
            if sym in suppressed_syms and (a.get("action") or "HOLD").upper() != "HOLD":
                a["within_drift_tolerance"] = True
                a["allocation_drift_pct"] = drift_by_symbol.get(sym)

    # ── 7. Patch result fields when status overridden ────────────────────────
    result = dict(result)
    if stabilized_status != original_status:
        result["status"] = stabilized_status
        new_consensus = dict(consensus)
        new_consensus["consensus_decision"] = stabilized_status
        if stabilized_status in (STATUS_NO_REBALANCE, STATUS_OPTIMAL):
            new_consensus["recommended_action"] = (
                stabilization_reason or "Portfolio is currently optimized. No action required."
            )
        result["consensus"] = new_consensus

        if stabilized_status in (STATUS_NO_REBALANCE, STATUS_OPTIMAL, STATUS_COOLDOWN_ACTIVE):
            result["no_action_summary"] = stabilization_reason or "Portfolio stability parameters met."
            if stabilized_status == STATUS_COOLDOWN_ACTIVE:
                result["no_action_reason"] = "COOLDOWN_ACTIVE"
            elif stabilized_status == STATUS_NO_REBALANCE:
                result["no_action_reason"] = (
                    "WELL_BALANCED" if all_within_tol else "INSUFFICIENT_EDGE"
                )
            if not result.get("optimization_notes") or original_status == "REBALANCE":
                result["optimization_notes"] = (
                    stabilization_reason or "Portfolio is currently optimized. No action required."
                )

    # ── 8. Attach stabilization metadata ────────────────────────────────────
    result["stabilization"] = {
        "enabled": True,
        "status": stabilized_status,
        "original_optimizer_status": original_status,
        "reason": stabilization_reason,
        "drift_threshold_pct": drift_threshold_pct,
        "cooldown_days": cooldown_days,
        "net_benefit_threshold_pct": net_benefit_threshold,
        "positions_within_tolerance": len(within_tol),
        "positions_needing_action": len(needing_action),
        "all_within_tolerance": all_within_tol,
        "drift_analysis": [
            {
                "symbol": d.symbol,
                "current_weight": d.current_weight,
                "target_weight": d.target_weight,
                "allocation_drift": d.allocation_drift,
                "within_tolerance": d.within_tolerance,
            }
            for d in drift_analysis
        ],
        "cooldown": {
            "active": cooldown.active,
            "last_rebalance_at": (
                cooldown.last_rebalance_at.isoformat() + "Z"
                if cooldown.last_rebalance_at else None
            ),
            "days_elapsed": cooldown.days_elapsed,
            "days_remaining": cooldown.days_remaining,
            "cooldown_days": cooldown.cooldown_days,
            "overridden": cooldown.overridden,
            "override_reasons": cooldown.override_reasons,
        },
        "minimum_impact": {
            "expected_improvement_pct": min_impact.expected_improvement_pct,
            "estimated_cost_pct": min_impact.estimated_cost_pct,
            "net_benefit_pct": min_impact.net_benefit_pct,
            "passes_threshold": min_impact.passes_threshold,
            "threshold_pct": min_impact.threshold_pct,
            "suppressed": min_impact.suppressed,
            "total_turnover_pct": min_impact.total_turnover_pct,
        },
        "overrides_active": overrides_active,
        "force_rebalance": force_rebalance,
        "duplicate_ticker_diagnostic": dup_report,
    }

    log.info(
        "[STABILIZATION] original=%s → stabilized=%s drift_in_tol=%d/%d "
        "cooldown_active=%s cooldown_overridden=%s impact_passes=%s force=%s",
        original_status, stabilized_status,
        len(within_tol), len(drift_analysis),
        cooldown.active, cooldown.overridden,
        min_impact.passes_threshold, force_rebalance,
    )

    return result
