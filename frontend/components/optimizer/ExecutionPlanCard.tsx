"use client";

import Link from "next/link";
import SignalBadge from "@/components/SignalBadge";
import type { OptimizerResult } from "@/lib/api";
import {
  deriveExecutionPlan,
  NO_ACTION_REASON_LABELS,
  type ExecutionTrade,
} from "@/lib/executionPlan";

// ─── No-trade reason resolution ──────────────────────────────────────────────

interface NoTradeReason {
  headline: string;
  detail?: string | null;
  href: string;
  linkLabel: string;
}

/** Ordered, first match becomes the headline; the rest render as chips. */
function resolveNoTradeReasons(result: OptimizerResult): NoTradeReason[] {
  const reasons: NoTradeReason[] = [];
  const stab = result.stabilization;
  const consensus = result.consensus;

  if (stab?.status === "COOLDOWN_ACTIVE") {
    const days = stab.cooldown?.days_remaining;
    reasons.push({
      headline: days != null && days > 0
        ? `Rebalance cooldown active — ${days} day${days !== 1 ? "s" : ""} remaining`
        : "Rebalance cooldown active",
      detail: stab.reason,
      href: "#portfolio-drift",
      linkLabel: "View Portfolio Drift",
    });
  }
  if (result.status === "NO_ACTION") {
    const label = result.no_action_reason
      ? NO_ACTION_REASON_LABELS[result.no_action_reason] ?? result.no_action_reason
      : "No Action";
    reasons.push({
      headline: `Committee decision: ${label}`,
      detail: result.no_action_summary,
      href: "#ai-recommendation",
      linkLabel: "View Committee Decision",
    });
  }
  if (
    result.status !== "NO_ACTION" &&
    (consensus?.consensus_type === "NO_ACTION_CONSENSUS" ||
      consensus?.consensus_type === "NO_REBALANCE_CONSENSUS")
  ) {
    reasons.push({
      headline: "Committee consensus: no rebalancing action",
      detail: consensus?.refinement_summary,
      href: "#ai-recommendation",
      linkLabel: "View Committee Decision",
    });
  }
  if (stab && (stab.status === "NO_REBALANCE_REQUIRED" || stab.status === "OPTIMAL" || stab.all_within_tolerance)) {
    reasons.push({
      headline: `Portfolio already within ${stab.drift_threshold_pct}% drift tolerance`,
      href: "#portfolio-drift",
      linkLabel: "View Portfolio Drift",
    });
  }
  if (stab?.minimum_impact && (stab.minimum_impact.suppressed || !stab.minimum_impact.passes_threshold)) {
    const mi = stab.minimum_impact;
    reasons.push({
      headline: `Expected net benefit ${mi.net_benefit_pct >= 0 ? "+" : ""}${mi.net_benefit_pct.toFixed(2)}% is below the ${mi.threshold_pct}% cost threshold`,
      href: "#portfolio-drift",
      linkLabel: "View Portfolio Drift",
    });
  }
  if (reasons.length === 0) {
    reasons.push({
      headline: "All proposed changes are below the noise / drift thresholds",
      href: "#portfolio-drift",
      linkLabel: "View Portfolio Drift",
    });
  }
  return reasons;
}

// ─── Sub-components ───────────────────────────────────────────────────────────

/** Necessity/state badge for sell/reduce trades — omitted for buy-side rows
 *  and for old history payloads predating Execution Optimization. */
function NecessityBadge({ trade }: { trade: ExecutionTrade }) {
  if (!trade.necessity) return null;
  if (trade.necessity === "NECESSARY") {
    return (
      <span
        className="text-[9px] font-bold px-1.5 py-0.5 rounded-full border bg-gray-800 border-gray-800 text-white"
        title={trade.note ?? undefined}
      >
        Required
      </span>
    );
  }
  if (trade.executionState === "SCALED") {
    return (
      <span
        className="text-[9px] font-bold px-1.5 py-0.5 rounded-full border bg-amber-50 border-amber-300 text-amber-700"
        title={trade.note ?? undefined}
      >
        Partial
      </span>
    );
  }
  return null;
}

function TradeRow({ trade }: { trade: ExecutionTrade }) {
  const chg = trade.allocationChangePercent;
  const chgCls = chg > 0 ? "text-green-600" : chg < 0 ? "text-red-500" : "text-gray-400";
  const amt = trade.estimatedAmount;

  return (
    <div className="flex items-center gap-3 px-3 py-2 border-b last:border-b-0 hover:bg-gray-50 flex-wrap">
      <div className="w-24 shrink-0">
        <SignalBadge signal={trade.action} />
      </div>
      <div className="flex items-center gap-1.5 min-w-[7rem]">
        <Link
          href={`/stock/${encodeURIComponent(trade.symbol)}`}
          className="text-sm font-semibold text-blue-600 hover:underline"
        >
          {trade.symbol.replace(".BK", "")}
          {trade.symbol.endsWith(".BK") && <span className="text-xs text-gray-400 font-normal">.BK</span>}
        </Link>
        {trade.isNew && (
          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-green-100 border border-green-300 text-green-700">
            New
          </span>
        )}
        <NecessityBadge trade={trade} />
      </div>
      <span className={`text-xs font-semibold tabular-nums w-14 text-right ${chgCls}`}>
        {chg >= 0 ? "+" : ""}{chg.toFixed(1)}%
      </span>
      <span className="text-sm tabular-nums ml-auto text-right">
        {amt == null || amt === 0 ? (
          <span className="text-gray-400">—</span>
        ) : amt > 0 ? (
          <span className="font-semibold text-gray-800">
            ฿{amt.toLocaleString("th-TH")} <span className="text-xs text-gray-400 font-normal">required</span>
          </span>
        ) : (
          <span className="font-semibold text-gray-800">
            ฿{Math.abs(amt).toLocaleString("th-TH")} <span className="text-xs text-gray-400 font-normal">released</span>
          </span>
        )}
      </span>
      {trade.timingScore != null && (
        <span className="text-[10px] text-gray-400 tabular-nums w-16 text-right hidden sm:inline">
          Timing {trade.timingScore.toFixed(0)}
        </span>
      )}
    </div>
  );
}

/** A discretionary sell/reduce trade that isn't executing today — the
 *  Belief's case for it still stands, it's just not needed for today's
 *  cash flow. Shown with its reason so it never reads as an unexplained
 *  omission (OPTIMIZER_PHILOSOPHY.md §9/§13). */
function DeferredTradeRow({ trade }: { trade: ExecutionTrade }) {
  return (
    <div className="flex items-start gap-3 px-3 py-2 border-b last:border-b-0">
      <div className="w-24 shrink-0 opacity-60">
        <SignalBadge signal={trade.action} />
      </div>
      <div className="flex-1 min-w-0">
        <span className="text-sm font-semibold text-gray-500">
          {trade.symbol.replace(".BK", "")}
        </span>
        {trade.note && <p className="text-xs text-gray-400 mt-0.5">{trade.note}</p>}
      </div>
    </div>
  );
}

function CashStat({ label, value, tone }: { label: string; value: number; tone?: "warn" }) {
  return (
    <div>
      <span className="text-xs text-gray-500">{label}</span>
      <p className={`font-semibold ${tone === "warn" ? "text-red-600" : "text-gray-800"}`}>
        {value < 0 ? "−" : ""}฿{Math.abs(value).toLocaleString("th-TH")}
      </p>
    </div>
  );
}

// ─── Main export ──────────────────────────────────────────────────────────────

/** Primary output of the Execution section: "what should I actually do today?"
 *  A display-only view derived from the canonical recommendation
 *  (action_summary classification joined with target_allocations amounts) —
 *  nothing here is persisted or written back. */
export default function ExecutionPlanCard({
  result,
  portfolioId,
}: {
  result: OptimizerResult;
  portfolioId?: number;
}) {
  const plan = deriveExecutionPlan(
    result.action_summary,
    result.target_allocations,
    result.execution_optimization,
  );
  const emergency = result.active_policy?.emergency_override
    ? result.active_policy.emergency_reason ?? "Emergency risk policy active"
    : null;
  // Investor-facing cash position after execution: what's left in the account
  // once released proceeds fund the buys, starting from today's actual cash
  // balance (not just the delta between required/released). Negative means a
  // funding shortfall — more cash is needed than trades free up.
  const cashOnHand = result.cash_balance ?? 0;
  const cashRemaining = cashOnHand + plan.cashReleased - plan.cashRequired;

  return (
    <section className="bg-white border border-blue-200 rounded-xl shadow-sm overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-3 px-4 py-3 bg-blue-50/60 border-b border-blue-100">
        <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wider">Execution Plan</h3>
        {plan.hasTrades ? (
          <span className="text-xs font-semibold px-2 py-0.5 rounded-full border bg-blue-50 border-blue-200 text-blue-700">
            {plan.trades.length} trade{plan.trades.length !== 1 ? "s" : ""} today
          </span>
        ) : (
          <span className="text-xs font-semibold px-2 py-0.5 rounded-full border bg-green-50 border-green-200 text-green-700">
            No trades today
          </span>
        )}
        {/* AI Evaluation M7 entry point (UX §2.3): "AI's track record on
            calls like this" -> Human vs AI, scoped to this portfolio. */}
        {portfolioId != null && (
          <Link
            href="/ai-analytics/human-vs-ai"
            className="ml-auto text-xs font-semibold text-blue-700 hover:underline whitespace-nowrap"
          >
            AI's track record on calls like this →
          </Link>
        )}
      </div>

      {/* Emergency override banner — shown in both states */}
      {emergency && (
        <div className="flex items-start gap-2 px-4 py-2.5 bg-amber-50 border-b border-amber-200 text-xs text-amber-800">
          <span className="font-bold shrink-0">⚠ Emergency override:</span>
          <span className="flex-1">{emergency}</span>
          <a href="#supporting-analytics" className="shrink-0 font-semibold text-amber-700 underline hover:text-amber-900">
            View Active Policy
          </a>
        </div>
      )}

      {plan.hasTrades ? (
        <>
          <p className="px-4 pt-3 text-xs font-semibold text-gray-500 uppercase tracking-wide">Today&apos;s Trades</p>
          <div className="px-1 py-1">
            {plan.trades.map((t) => <TradeRow key={t.symbol} trade={t} />)}
          </div>

          {/* Cash summary — Cash Required/Released totals cover the listed trades
              only, so they always match the list above. Cash Remaining After
              Execution reflects today's actual cash balance, not just the
              trade-side delta. */}
          <div className="flex flex-wrap gap-4 px-4 py-3 border-t bg-gray-50/60 text-sm">
            <CashStat label="Cash Required" value={plan.cashRequired} />
            <CashStat label="Cash Released" value={plan.cashReleased} />
            <CashStat
              label="Cash Remaining After Execution"
              value={cashRemaining}
              tone={cashRemaining < 0 ? "warn" : undefined}
            />
          </div>
          {cashRemaining < 0 && (
            <p className="px-4 pb-1 text-xs text-red-600">
              Shortfall — additional funding needed to complete these trades.
            </p>
          )}

          {/* Execution Optimization deferrals — a discretionary sell/reduce
              whose own case still stands but isn't needed for today's cash
              flow. Shown separately with its reason so it never reads as an
              unexplained gap between what the AI proposed and what executes
              today (OPTIMIZER_PHILOSOPHY.md §9). */}
          {plan.deferredTrades.length > 0 && (
            <>
              <p className="px-4 pt-3 text-xs font-semibold text-gray-400 uppercase tracking-wide">
                Not Executing Today ({plan.deferredTrades.length})
              </p>
              <div className="px-1 py-1">
                {plan.deferredTrades.map((t) => <DeferredTradeRow key={t.symbol} trade={t} />)}
              </div>
            </>
          )}

          {plan.deferredCount > 0 && (
            <p className="px-4 pb-3 pt-1 text-xs text-gray-400 italic">
              {plan.deferredCount} change{plan.deferredCount !== 1 ? "s" : ""} deferred (within drift tolerance, below noise threshold, or not needed for funding) —{" "}
              <a href="#portfolio-drift" className="text-blue-500 hover:underline not-italic">see Portfolio Drift</a>
            </p>
          )}
        </>
      ) : (
        <NoTradesBody result={result} deferredCount={plan.deferredCount} />
      )}
    </section>
  );
}

function NoTradesBody({ result, deferredCount }: { result: OptimizerResult; deferredCount: number }) {
  const [primary, ...rest] = resolveNoTradeReasons(result);

  return (
    <div className="px-4 py-4 space-y-3">
      <div className="flex items-start gap-3">
        <span className="shrink-0 w-8 h-8 rounded-full bg-green-100 border border-green-300 flex items-center justify-center text-sm font-bold text-green-700">
          ✓
        </span>
        <div className="flex-1 min-w-0 space-y-1">
          <p className="text-sm font-semibold text-gray-800">No trades recommended today</p>
          <p className="text-sm text-gray-600">{primary.headline}</p>
          {primary.detail && <p className="text-xs text-gray-500 leading-relaxed">{primary.detail}</p>}
          <a href={primary.href} className="inline-block text-xs font-semibold text-blue-600 hover:underline">
            {primary.linkLabel} ↑
          </a>
        </div>
      </div>

      {rest.length > 0 && (
        <div className="flex flex-wrap gap-1.5 pl-11">
          {rest.map((r, i) => (
            <a
              key={i}
              href={r.href}
              className="text-[11px] px-2 py-1 rounded-full border bg-gray-50 border-gray-200 text-gray-600 hover:bg-gray-100"
              title={r.detail ?? undefined}
            >
              {r.headline}
            </a>
          ))}
        </div>
      )}

      {deferredCount > 0 && (
        <p className="pl-11 text-xs text-gray-400 italic">
          {deferredCount} proposed change{deferredCount !== 1 ? "s" : ""} deferred —{" "}
          <a href="#portfolio-drift" className="text-blue-500 hover:underline not-italic">see Portfolio Drift</a>
        </p>
      )}
    </div>
  );
}
