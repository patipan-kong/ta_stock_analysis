import type {
  ActionSummary,
  ActionSummaryEntry,
  AllocationAction,
  NoActionReason,
  TargetAllocation,
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
}

export interface ExecutionPlan {
  trades: ExecutionTrade[];
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
): ExecutionPlan {
  const bySymbol = new Map<string, TargetAllocation>();
  for (const a of allocations ?? []) bySymbol.set(a.symbol, a);

  const trades: ExecutionTrade[] = [];
  for (const group of GROUP_ORDER) {
    const entries: ActionSummaryEntry[] = actionSummary?.[group] ?? [];
    for (const e of entries) {
      const alloc = bySymbol.get(e.symbol);
      trades.push({
        symbol: e.symbol,
        group,
        action: alloc?.action ?? GROUP_FALLBACK_ACTION[group],
        allocationChangePercent: e.allocation_change_percent,
        estimatedAmount: alloc ? alloc.estimated_amount : null,
        isNew: group === "new_position",
        timingScore: e.timing_score ?? alloc?.timing_score ?? null,
        reason: alloc?.reason ?? null,
      });
    }
  }

  // Cash totals sum LISTED trades only, so the summary can never contradict the
  // visible trade list. (The old CashFlowSummary also counted non-deferred HOLD
  // rows with a nonzero estimated_amount — an intentional micro-change.)
  let cashRequired = 0;
  let cashReleased = 0;
  for (const t of trades) {
    if (t.estimatedAmount == null) continue;
    if (t.estimatedAmount > 0) cashRequired += t.estimatedAmount;
    else if (t.estimatedAmount < 0) cashReleased += -t.estimatedAmount;
  }

  return {
    trades,
    cashRequired,
    cashReleased,
    deferredCount: (allocations ?? []).filter(isDeferred).length,
    hasTrades: trades.length > 0,
  };
}
