import type {
  ActionSummary,
  ActionSummaryEntry,
  AllocationAction,
  ExecutionOptimizationResult,
  NoActionReason,
  TargetAllocation,
  TradeExecutionState,
  TradeNecessity,
} from "@/lib/api";

// ─── Shared deferral rule ─────────────────────────────────────────────────────
// A row is "deferred" when either governance layer says today isn't the day to
// trade it: the noise filter (< 1% drift / < ฿5,000, mutates action to HOLD) or
// the stabilization drift-tolerance check (< 3% drift, action left as-is since
// the AI's underlying signal is still real — just not urgent). Both flags are
// computed once on the backend and reused here, not recalculated.
export function isDeferred(a: TargetAllocation): boolean {
  return !!(a.noise_suppressed || a.within_drift_tolerance);
}

export const NO_ACTION_REASON_LABELS: Record<NoActionReason, string> = {
  WELL_BALANCED:       "Well Balanced",
  LOW_CONFIDENCE:      "Low Confidence",
  HIGH_DISAGREEMENT:   "High Disagreement",
  CONSTRAINT_BLOCKED:  "Constraint Blocked",
  MARKET_UNCERTAINTY:  "Market Uncertainty",
  INSUFFICIENT_EDGE:   "Insufficient Edge",
  COOLDOWN_ACTIVE:     "Cooldown Active",
};

// ─── Execution plan derivation ────────────────────────────────────────────────
// The classification of allocations into actionable trades (deferral skipping,
// sell/reduce/accumulate/new_position buckets) is owned by the backend
// (services/optimizer_action_summary.py) and arrives as result.action_summary.
// This module only JOINS those buckets with target_allocations by symbol to
// attach the baht amounts — it never re-implements the classification rule.

export type ExecutionTradeGroup = "new_position" | "accumulate" | "reduce" | "sell";

export interface ExecutionTrade {
  symbol: string;
  group: ExecutionTradeGroup;
  /** Badge action — from the joined allocation when available. */
  action: AllocationAction;
  allocationChangePercent: number;
  /** Signed ฿: > 0 cash required, < 0 cash released. Null when the allocation
   *  row couldn't be joined (very old history payloads). */
  estimatedAmount: number | null;
  isNew: boolean;
  timingScore: number | null;
  reason: string | null;
  /** Execution Optimization metadata — present only for sell/reduce trades
   *  when result.execution_optimization is available (see
   *  OPTIMIZER_PHILOSOPHY.md §9). Absent for buy-side trades and for old
   *  history rows predating this stage. */
  necessity: TradeNecessity | null;
  executionState: TradeExecutionState | null;
  note: string | null;
}

export interface ExecutionPlan {
  trades: ExecutionTrade[];
  /** Discretionary sell/reduce trades not executing today — shown separately,
   *  never counted in cashRequired/cashReleased. */
  deferredTrades: ExecutionTrade[];
  cashRequired: number;
  cashReleased: number;
  deferredCount: number;
  hasTrades: boolean;
}

const GROUP_FALLBACK_ACTION: Record<ExecutionTradeGroup, AllocationAction> = {
  new_position: "BUY",
  accumulate:   "ACCUMULATE",
  reduce:       "REDUCE",
  sell:         "SELL",
};

// BUY side first (matches the investor's "what do I need cash for?" reading),
// then the funding side.
const GROUP_ORDER: ExecutionTradeGroup[] = ["new_position", "accumulate", "reduce", "sell"];

export function deriveExecutionPlan(
  actionSummary: ActionSummary | null | undefined,
  allocations: TargetAllocation[] | null | undefined,
  executionOptimization?: ExecutionOptimizationResult | null,
): ExecutionPlan {
  const bySymbol = new Map<string, TargetAllocation>();
  for (const a of allocations ?? []) bySymbol.set(a.symbol, a);

  // Execution Optimization only ever classifies sell/reduce candidates (see
  // execution_optimizer.py) — buy-side trades are never in this map.
  const optimizedBySymbol = new Map(
    (executionOptimization?.trades ?? []).map((t) => [t.symbol, t]),
  );

  const trades: ExecutionTrade[] = [];
  const deferredTrades: ExecutionTrade[] = [];

  for (const group of GROUP_ORDER) {
    const entries: ActionSummaryEntry[] = actionSummary?.[group] ?? [];
    for (const e of entries) {
      const alloc = bySymbol.get(e.symbol);
      const optimized = (group === "sell" || group === "reduce")
        ? optimizedBySymbol.get(e.symbol)
        : undefined;

      // A scaled/deferred trade releases less (or none) of the cash the raw
      // allocation implied — use the actually-executed amount when known.
      let estimatedAmount = alloc ? alloc.estimated_amount : null;
      if (optimized && estimatedAmount != null) {
        const sign = estimatedAmount < 0 ? -1 : 1;
        estimatedAmount = sign * optimized.executed_amount;
      }

      const trade: ExecutionTrade = {
        symbol: e.symbol,
        group,
        action: alloc?.action ?? GROUP_FALLBACK_ACTION[group],
        allocationChangePercent: e.allocation_change_percent,
        estimatedAmount,
        isNew: group === "new_position",
        timingScore: e.timing_score ?? alloc?.timing_score ?? null,
        reason: alloc?.reason ?? null,
        necessity: optimized?.necessity ?? null,
        executionState: optimized?.execution_state ?? null,
        note: optimized?.note ?? null,
      };

      if (optimized?.execution_state === "DEFERRED") {
        deferredTrades.push(trade);
      } else {
        trades.push(trade);
      }
    }
  }

  // Cash totals sum LISTED (executing) trades only, so the summary can never
  // contradict the visible trade list, and deferred trades never inflate it.
  let cashRequired = 0;
  let cashReleased = 0;
  for (const t of trades) {
    if (t.estimatedAmount == null) continue;
    if (t.estimatedAmount > 0) cashRequired += t.estimatedAmount;
    else if (t.estimatedAmount < 0) cashReleased += -t.estimatedAmount;
  }

  return {
    trades,
    deferredTrades,
    cashRequired,
    cashReleased,
    deferredCount: (allocations ?? []).filter(isDeferred).length + deferredTrades.length,
    hasTrades: trades.length > 0,
  };
}
