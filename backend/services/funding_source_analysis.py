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
    release_pct: float       # fraction of position to release
    estimated_release: float # current_value × release_pct


class CashSource(BaseModel):
    amount: float
    label: str = "Existing Cash"


class FundingSourceResult(BaseModel):
    sell_sources: list[FundingSourceItem]
    reduce_sources: list[FundingSourceItem]
    cash_source: CashSource
    total_released: float    # sell + reduce proceeds
    total_funding: float     # total_released + cash
    total_deployment: float  # expected spend on buys
    surplus_cash: float      # total_funding − total_deployment
    status: str              # "FUNDED" | "INSUFFICIENT" | "CASH_ONLY"


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
    reduce_pcts = reduce_pct_override or {}
    buy_upper = {s.upper() for s in buy_set}

    sell_sources: list[FundingSourceItem] = []
    reduce_sources: list[FundingSourceItem] = []

    for symbol, current_value in item_values.items():
        if symbol.upper() in buy_upper:
            continue

        signal = signal_map.get(symbol, "HOLD").upper()
        if signal not in ("SELL", "REDUCE"):
            continue

        if signal == "SELL":
            sell_sources.append(FundingSourceItem(
                action="SELL",
                symbol=symbol,
                current_value=round(current_value, 2),
                release_pct=1.0,
                estimated_release=round(current_value, 2),
            ))
        else:
            pct = reduce_pcts.get(symbol, reduce_pcts.get(symbol.upper(), _DEFAULT_REDUCE_RELEASE_PCT))
            release = current_value * pct
            reduce_sources.append(FundingSourceItem(
                action="REDUCE",
                symbol=symbol,
                current_value=round(current_value, 2),
                release_pct=round(pct, 4),
                estimated_release=round(release, 2),
            ))

    # Largest release first within each group
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
    )
