"""Phase UX.2L — Funding Source Analysis.

Pure service — no AI calls, no DB mutations, no side effects.
Converts optimizer signals into a structured funding flow:

    SELL holdings  →  cash released
    REDUCE holdings →  partial cash released
    Existing cash  →  available immediately
    ─────────────────────────────────────────
    Total Funding  →  vs. Total Deployment  →  Surplus / Shortfall

See OPTIMIZER_PHILOSOPHY.md §10 — existing cash is always the first funding
source; a sale is a funding source only if it already justifies itself.

Execution Optimization update: the selection of which SELL/REDUCE candidates
actually execute today — and how much of each — is delegated to
services/optimizer/execution_optimizer.py::resolve_funding_gap(), the single
source of truth for the necessity/funding-gap algorithm (see that module's
docstring for the Reason/Necessity/Execution Role/Execution State design).
This module's job is narrower: build FundingCandidate rows from raw holdings
data and reshape the resolved trades into the FundingSourceResult display
schema the frontend already understands.

Public API
----------
build_funding_sources(item_values, signal_map, cash_available, buy_set,
                      total_deployment, reduce_pct_override)
    -> FundingSourceResult
"""
from __future__ import annotations

from pydantic import BaseModel

_DEFAULT_REDUCE_RELEASE_PCT = 0.25   # release 25% of a REDUCE position (heuristic)


# ── Models ────────────────────────────────────────────────────────────────────

class FundingSourceItem(BaseModel):
    action: str              # "SELL" | "REDUCE"
    symbol: str
    current_value: float     # estimated position value (avg_cost × shares)
    release_pct: float       # fraction of position actually released
    estimated_release: float # amount actually released today
    # Execution Optimization metadata (see execution_optimizer.py)
    necessity: str | None = None          # "NECESSARY" | "DISCRETIONARY"
    execution_state: str | None = None    # "FULL" | "SCALED" | "DEFERRED"
    note: str | None = None               # human explanation, always present when set


class CashSource(BaseModel):
    amount: float
    label: str = "Existing Cash"


class FundingSourceResult(BaseModel):
    sell_sources: list[FundingSourceItem]
    reduce_sources: list[FundingSourceItem]
    cash_source: CashSource
    total_released: float    # sell + reduce proceeds actually executed
    total_funding: float     # total_released + cash
    total_deployment: float  # expected spend on buys
    surplus_cash: float      # total_funding − total_deployment
    status: str              # "FUNDED" | "INSUFFICIENT" | "CASH_ONLY"
    deferred_sources: list[FundingSourceItem] = []  # discretionary trades not needed today


# ── Core function ─────────────────────────────────────────────────────────────

def build_funding_sources(
    item_values: dict[str, float],
    signal_map: dict[str, str],
    cash_available: float,
    buy_set: set[str],
    total_deployment: float = 0.0,
    reduce_pct_override: dict[str, float] | None = None,
) -> FundingSourceResult:
    """Build a structured funding source breakdown.

    Args:
        item_values:          {symbol: estimated_value} for each holding.
        signal_map:           {symbol: signal} — SELL / REDUCE / HOLD / …
        cash_available:       Current cash balance in the portfolio.
        buy_set:              Symbols earmarked as buy targets (excluded from
                              funding sources to avoid self-funding loops).
        total_deployment:     Total amount the buy actions intend to spend.
        reduce_pct_override:  Optional {symbol: pct} to override the default
                              25 % release for REDUCE positions (e.g. from
                              optimizer target-weight deltas).
    """
    from services.optimizer.execution_optimizer import FundingCandidate, resolve_funding_gap

    reduce_pcts = reduce_pct_override or {}
    buy_upper = {s.upper() for s in buy_set}

    candidates: list[FundingCandidate] = []
    for symbol, current_value in item_values.items():
        if symbol.upper() in buy_upper:
            continue

        signal = signal_map.get(symbol, "HOLD").upper()
        if signal not in ("SELL", "REDUCE"):
            continue

        if signal == "SELL":
            full_release = current_value
        else:
            pct = reduce_pcts.get(symbol, reduce_pcts.get(symbol.upper(), _DEFAULT_REDUCE_RELEASE_PCT))
            full_release = current_value * pct

        candidates.append(FundingCandidate(
            symbol=symbol, action=signal, sector=None,
            full_amount=round(full_release, 2),
        ))

    eo = resolve_funding_gap(candidates, cash_available=cash_available, total_buy_deployment=total_deployment)

    sell_sources: list[FundingSourceItem] = []
    reduce_sources: list[FundingSourceItem] = []
    deferred_sources: list[FundingSourceItem] = []

    for t in eo.trades:
        item = FundingSourceItem(
            action=t.action,
            symbol=t.symbol,
            current_value=t.full_recommended_amount,
            release_pct=round((t.executed_amount / t.full_recommended_amount) if t.full_recommended_amount else 0.0, 4),
            estimated_release=t.executed_amount,
            necessity=t.necessity,
            execution_state=t.execution_state,
            note=t.note,
        )
        if t.execution_state == "DEFERRED":
            deferred_sources.append(item)
        elif t.action == "SELL":
            sell_sources.append(item)
        else:
            reduce_sources.append(item)

    # Largest executed release first within each group
    sell_sources.sort(key=lambda x: -x.estimated_release)
    reduce_sources.sort(key=lambda x: -x.estimated_release)

    total_released = (
        sum(s.estimated_release for s in sell_sources)
        + sum(s.estimated_release for s in reduce_sources)
    )
    total_funding = cash_available + total_released
    surplus_cash = round(total_funding - total_deployment, 2)

    if not sell_sources and not reduce_sources:
        status = "CASH_ONLY"
    elif surplus_cash < 0:
        status = "INSUFFICIENT"
    else:
        status = "FUNDED"

    return FundingSourceResult(
        sell_sources=sell_sources,
        reduce_sources=reduce_sources,
        cash_source=CashSource(amount=round(cash_available, 2)),
        total_released=round(total_released, 2),
        total_funding=round(total_funding, 2),
        total_deployment=round(total_deployment, 2),
        surplus_cash=surplus_cash,
        status=status,
        deferred_sources=deferred_sources,
    )
