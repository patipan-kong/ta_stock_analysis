"""Execution Optimization — deterministic post-processing stage.

See OPTIMIZER_PHILOSOPHY.md §5 (pipeline placement), §7 (why this stage
exists and what it must never do), §9 (Reason vs. Execution Role), §10
(Funding Philosophy). Pure function — no AI calls, no DB access, no side
effects. Operates only on already-computed target_allocations / holdings
data; never mutates its inputs, never re-runs L1/L2/L3, never touches
RecommendationSnapshot.

Three axes are assigned per candidate SELL/REDUCE trade, deliberately kept
independent rather than flattened into one status field:

    reason           durable, belief-side — why does this trade exist at
                     all? (Mandatory Risk Reduction, Policy Enforcement,
                     Portfolio Improvement — Optional Rebalancing never
                     reaches this stage; it is already resolved by the
                     noise filter / stabilization drift-tolerance layer
                     before build_action_summary() buckets anything.)
    necessity        NECESSARY (ships regardless of cash) or DISCRETIONARY
                     (deferrable) — a pure function of reason, not an
                     independent judgment call.
    execution_role   what job, if any, a trade performs in TODAY's plan:
                     STANDALONE (necessary trades — they execute on their
                     own account, not "serving" anything), FUNDING_SOURCE
                     (a discretionary trade tapped to cover today's cash
                     gap), or NOT_NEEDED_TODAY (a discretionary trade with
                     no funding job this cycle).
    execution_state  how much of the trade's OWN recommended size actually
                     executes today: FULL, SCALED (partially released —
                     only discretionary FUNDING_SOURCE trades can be
                     SCALED; necessary trades are always FULL), DEFERRED.

Reason classification reuses fields already computed upstream — no new AI
output, no new signal lookups:
  - action == "SELL" already means "AI wants this position fully gone"
    (ARCH_SPEC Signal Enum: SELL = deteriorating thesis / major negative
    catalyst) — exactly what Mandatory Risk Reduction means.
  - action == "REDUCE" means a valuation/TA-driven trim (ARCH_SPEC:
    REDUCE = TA bearish / valuation stretch) — a Portfolio Improvement
    view, UNLESS this symbol or its sector currently carries a live
    SECTOR_BREACH/CONCENTRATION_BREACH (from PolicyEnvelope.violations),
    in which case trimming it is enforcing an already-declared limit,
    not merely improving the allocation.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel

# ── Reason (belief-side, durable) ───────────────────────────────────────────
REASON_MANDATORY_RISK_REDUCTION = "MANDATORY_RISK_REDUCTION"
REASON_POLICY_ENFORCEMENT       = "POLICY_ENFORCEMENT"
REASON_PORTFOLIO_IMPROVEMENT    = "PORTFOLIO_IMPROVEMENT"

# ── Necessity (pure function of Reason) ─────────────────────────────────────
NECESSITY_NECESSARY     = "NECESSARY"
NECESSITY_DISCRETIONARY = "DISCRETIONARY"

# ── Execution Role (job in today's plan) ────────────────────────────────────
ROLE_STANDALONE       = "STANDALONE"
ROLE_FUNDING_SOURCE   = "FUNDING_SOURCE"
ROLE_NOT_NEEDED_TODAY = "NOT_NEEDED_TODAY"

# ── Execution State (how much of the trade's own plan executes today) ──────
STATE_FULL     = "FULL"
STATE_SCALED   = "SCALED"
STATE_DEFERRED = "DEFERRED"

_EPSILON = 0.01  # matches the NAV-reconciliation tolerance used elsewhere (PORTFOLIO_CALCULATION_RULES.md §9)


# ── Models ────────────────────────────────────────────────────────────────────

class FundingCandidate(BaseModel):
    """A candidate SELL/REDUCE trade before necessity/role/state are resolved."""
    symbol: str
    action: str                 # "SELL" | "REDUCE"
    sector: str | None = None
    full_amount: float          # this trade's own full recommended release, before any scaling


class OptimizedTrade(BaseModel):
    symbol: str
    action: str                 # "SELL" | "REDUCE"
    sector: str | None = None
    reason: str
    necessity: str
    execution_role: str
    execution_state: str
    full_recommended_amount: float
    executed_amount: float
    note: str


class ExecutionOptimizationResult(BaseModel):
    cash_available: float
    total_buy_deployment: float
    funding_gap: float           # max(0, total_buy_deployment - cash_available)
    trades: list[OptimizedTrade]
    idle_cash_after: float


# ── Reason / Necessity classification ────────────────────────────────────────

def classify_reason(symbol: str, action: str, sector: str | None, violations: list[str] | None) -> str:
    """Assign a durable Reason to a candidate SELL/REDUCE trade.

    Belief-free by construction (§7): only reuses the action already chosen
    upstream and this trade's own presence in an already-computed violations
    list — never scores a stock, never forecasts return, never invents a
    reason the Belief Engine didn't already imply through its own action.

    Checks both breach shapes policy_engine._detect_violations() emits:
    position-level ("CONCENTRATION_BREACH: {symbol} at ...") and sector-level
    ("SECTOR_BREACH: {sector} at ..."). Matching sector alone missed live
    single-position breaches, silently downgrading them to discretionary
    Portfolio Improvement — the fix caught during design review.
    """
    if action == "SELL":
        return REASON_MANDATORY_RISK_REDUCTION
    violations = violations or []
    if any("BREACH" in v and (symbol in v or (sector and sector in v)) for v in violations):
        return REASON_POLICY_ENFORCEMENT
    return REASON_PORTFOLIO_IMPROVEMENT


def necessity_for(reason: str) -> str:
    """Necessity is a pure function of Reason — not an independent judgment.

    Mandatory Risk Reduction and Policy Enforcement clear Priority 1/2 of
    the objective hierarchy (§2) and must ship regardless of today's cash
    position. Portfolio Improvement is deferrable by design (§2 Priority 5,
    §3 — tracking error against the ideal is measured, never outlawed).
    """
    if reason in (REASON_MANDATORY_RISK_REDUCTION, REASON_POLICY_ENFORCEMENT):
        return NECESSITY_NECESSARY
    return NECESSITY_DISCRETIONARY


# ── Core algorithm ────────────────────────────────────────────────────────────

def resolve_funding_gap(
    candidates: list[FundingCandidate],
    cash_available: float,
    total_buy_deployment: float,
    violations: list[str] | None = None,
) -> ExecutionOptimizationResult:
    """Implement OPTIMIZER_PHILOSOPHY.md §10's funding sequence deterministically.

    1. Necessary trades (Mandatory Risk Reduction, Policy Enforcement) ship
       in FULL, unconditionally — their released cash counts toward the
       gap as a side effect, never as a chosen role.
    2. Remaining gap = total_buy_deployment - cash_available - cash already
       released by necessary trades.
    3. Discretionary (Portfolio Improvement) candidates are sorted ascending
       by their own full recommended size, then walked in that order: each
       executes in FULL as long as it doesn't overshoot the remaining gap.
       The first candidate that WOULD overshoot is the single SCALED
       candidate — cut to exactly close the remainder. Everything after it
       is DEFERRED, untouched.
       This guarantees the fewest positions disturbed for a given gap, and
       that at most one trade is ever partially executed — using small,
       cleanly-fittable candidates in full before ever cutting a larger one
       short (cutting a large position's plan short is a bigger deviation
       from what the Belief actually recommended than cutting a small one).
    4. Deterministic tie-break when two+ discretionary candidates share the
       same full_amount: prefer scaling a REDUCE over a SELL (a partial cut
       of an already-partial trim is a smaller deviation-in-kind than a
       partial cut of an intended full exit), then symbol ascending — a
       pure, arbitrary-but-total order so the result never depends on input
       ordering (Invariant 3: same inputs, same plan, every time).
    """
    reasoned: list[dict[str, Any]] = []
    for c in candidates:
        reason = classify_reason(c.symbol, c.action, c.sector, violations)
        reasoned.append({
            "symbol": c.symbol,
            "action": c.action,
            "sector": c.sector,
            "reason": reason,
            "necessity": necessity_for(reason),
            "full_amount": max(0.0, float(c.full_amount)),
        })

    funding_gap = max(0.0, total_buy_deployment - cash_available)
    remaining_gap = funding_gap

    trades: list[OptimizedTrade] = []

    necessary = [c for c in reasoned if c["necessity"] == NECESSITY_NECESSARY]
    discretionary = [c for c in reasoned if c["necessity"] == NECESSITY_DISCRETIONARY]

    for c in necessary:
        note = (
            "Ships regardless of cash — "
            + ("deteriorating thesis (Mandatory Risk Reduction)." if c["reason"] == REASON_MANDATORY_RISK_REDUCTION
               else "enforces an active sector/position policy limit (Policy Enforcement).")
        )
        trades.append(OptimizedTrade(
            symbol=c["symbol"], action=c["action"], sector=c["sector"],
            reason=c["reason"], necessity=c["necessity"],
            execution_role=ROLE_STANDALONE, execution_state=STATE_FULL,
            full_recommended_amount=round(c["full_amount"], 2),
            executed_amount=round(c["full_amount"], 2),
            note=note,
        ))
        remaining_gap -= c["full_amount"]

    discretionary.sort(key=lambda c: (
        c["full_amount"],
        0 if c["action"] == "REDUCE" else 1,
        c["symbol"],
    ))

    for c in discretionary:
        if remaining_gap <= _EPSILON:
            trades.append(OptimizedTrade(
                symbol=c["symbol"], action=c["action"], sector=c["sector"],
                reason=c["reason"], necessity=c["necessity"],
                execution_role=ROLE_NOT_NEEDED_TODAY, execution_state=STATE_DEFERRED,
                full_recommended_amount=round(c["full_amount"], 2),
                executed_amount=0.0,
                note=(
                    "Deferred — no funding need this cycle. Existing cash and "
                    "any required trades already cover today's buys. This "
                    "trade's own case still stands and will be re-derived next run."
                ),
            ))
            continue

        if c["full_amount"] <= remaining_gap + _EPSILON:
            trades.append(OptimizedTrade(
                symbol=c["symbol"], action=c["action"], sector=c["sector"],
                reason=c["reason"], necessity=c["necessity"],
                execution_role=ROLE_FUNDING_SOURCE, execution_state=STATE_FULL,
                full_recommended_amount=round(c["full_amount"], 2),
                executed_amount=round(c["full_amount"], 2),
                note="Executed in full — funds part of today's purchases.",
            ))
            remaining_gap -= c["full_amount"]
        else:
            executed = round(remaining_gap, 2)
            full_amt = round(c["full_amount"], 2)
            trades.append(OptimizedTrade(
                symbol=c["symbol"], action=c["action"], sector=c["sector"],
                reason=c["reason"], necessity=c["necessity"],
                execution_role=ROLE_FUNDING_SOURCE, execution_state=STATE_SCALED,
                full_recommended_amount=full_amt,
                executed_amount=executed,
                note=(
                    f"Releasing only ฿{executed:,.0f} of a ฿{full_amt:,.0f} planned "
                    f"{c['action'].lower()} — the funding gap requires this much, no more."
                ),
            ))
            remaining_gap = 0.0

    total_released = sum(t.executed_amount for t in trades)
    idle_cash_after = round(cash_available + total_released - total_buy_deployment, 2)

    return ExecutionOptimizationResult(
        cash_available=round(cash_available, 2),
        total_buy_deployment=round(total_buy_deployment, 2),
        funding_gap=round(funding_gap, 2),
        trades=trades,
        idle_cash_after=idle_cash_after,
    )


# ── Convenience wrapper for the optimizer-page surface ───────────────────────

def optimize_execution(
    action_summary: dict[str, Any],
    target_allocations: list[dict[str, Any]],
    cash_available: float,
    violations: list[str] | None = None,
) -> ExecutionOptimizationResult:
    """Build funding candidates from the already-computed action_summary +
    target_allocations (main.py's optimizer-page surface) and resolve them.

    Reuses build_action_summary()'s bucketing (services/optimizer_action_summary.py)
    instead of re-deriving which symbols are actionable — that classification
    (noise/drift-deferred rows already excluded, HOLD-threshold already
    applied) is owned there; this function only adds Reason/Necessity/Role/
    State and the funding-gap arithmetic on top.
    """
    by_symbol = {a.get("symbol"): a for a in (target_allocations or []) if a.get("symbol")}

    total_buy_deployment = 0.0
    for group in ("accumulate", "new_position"):
        for entry in (action_summary or {}).get(group, []):
            alloc = by_symbol.get(entry.get("symbol"))
            if alloc:
                total_buy_deployment += abs(float(alloc.get("estimated_amount") or 0.0))

    candidates: list[FundingCandidate] = []
    for group, action in (("sell", "SELL"), ("reduce", "REDUCE")):
        for entry in (action_summary or {}).get(group, []):
            alloc = by_symbol.get(entry.get("symbol"))
            if not alloc:
                continue
            candidates.append(FundingCandidate(
                symbol=entry["symbol"],
                action=action,
                sector=alloc.get("sector"),
                full_amount=abs(float(alloc.get("estimated_amount") or 0.0)),
            ))

    return resolve_funding_gap(candidates, cash_available, total_buy_deployment, violations=violations)
