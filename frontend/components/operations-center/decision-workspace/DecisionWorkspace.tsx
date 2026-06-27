"use client";

import { useState, useCallback } from "react";
import {
  reviewIdeas,
  suggestAllocation,
  suggestPositionSizes,
  scoreTimingIntelligence,
  buildExecutionPlan,
  calculateRiskBudget,
  type IdeaReview,
  type IdeaReviewPortfolioContext,
  type PortfolioConstructionResult,
  type PositionSizingResult,
  type BasketSimulationResult,
  type StockTimingResult,
  type ExecutionPlanResult,
  type FundingAction,
  type BuyAction,
  type FundingSourceItem,
  type FundingBreakdown,
  type RiskBudgetResult,
  type AllocationItem,
} from "@/lib/api";
import IdeaIntakeCard from "../idea-intake/IdeaIntakeCard";
import BasketSimulationCard from "../basket-simulation/BasketSimulationCard";
import PortfolioConstructionCard from "../portfolio-construction/PortfolioConstructionCard";
import PositionSizingCard from "../position-sizing/PositionSizingCard";

// ─── Types ────────────────────────────────────────────────────────────────────

type WorkspaceStep =
  | "idle"
  | "reviewing"
  | "timing"
  | "constructing"
  | "sizing"
  | "allocating"
  | "planning"
  | "done";

type GateStatus = "ELIGIBLE" | "WATCHLIST" | "EXCLUDED";

// ─── Colour maps ──────────────────────────────────────────────────────────────

const DECISION_STYLE: Record<string, string> = {
  APPROVE: "bg-emerald-100 text-emerald-800 border-emerald-200",
  WATCH:   "bg-blue-100 text-blue-800 border-blue-200",
  REVIEW:  "bg-amber-100 text-amber-800 border-amber-200",
  DECLINE: "bg-red-100 text-red-800 border-red-200",
};

const SIGNAL_STYLE: Record<string, string> = {
  ACCUMULATE: "text-emerald-700",
  BUY:        "text-emerald-600",
  WATCH:      "text-blue-600",
  HOLD:       "text-gray-500",
  REDUCE:     "text-amber-700",
  SELL:       "text-red-700",
};

const STATUS_BORDER: Record<string, string> = {
  PASS:    "border-emerald-200 bg-emerald-50 text-emerald-800",
  WARNING: "border-amber-200 bg-amber-50 text-amber-800",
  FAIL:    "border-red-200 bg-red-50 text-red-800",
};

const STATUS_DOT: Record<string, string> = {
  PASS:    "bg-emerald-500",
  WARNING: "bg-amber-500",
  FAIL:    "bg-red-500",
};

const PRIORITY_STYLE: Record<string, string> = {
  HIGH:   "bg-emerald-100 text-emerald-800",
  MEDIUM: "bg-blue-100 text-blue-800",
  LOW:    "bg-amber-100 text-amber-800",
  DEFER:  "bg-gray-100 text-gray-500",
};

const CATEGORY_STYLE: Record<string, string> = {
  STRONG:  "text-emerald-700 font-bold",
  GOOD:    "text-emerald-600",
  NEUTRAL: "text-gray-500",
  WEAK:    "text-amber-700",
  POOR:    "text-red-600",
};

const GATE_BADGE: Record<GateStatus, string> = {
  ELIGIBLE:  "bg-emerald-100 text-emerald-800",
  WATCHLIST: "bg-amber-100 text-amber-800",
  EXCLUDED:  "bg-red-100 text-red-600",
};

const MOMENTUM_LABEL: Record<string, string> = {
  STRONG_UPTREND:   "Strong Uptrend",
  UPTREND:          "Uptrend",
  SIDEWAYS:         "Sideways",
  DOWNTREND:        "Downtrend",
  STRONG_DOWNTREND: "Strong Downtrend",
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

const STATUS_RANK: Record<string, number> = { PASS: 2, WARNING: 1, FAIL: 0 };

function worstStatus(a: string, b: string): string {
  return (STATUS_RANK[a] ?? 2) <= (STATUS_RANK[b] ?? 2) ? a : b;
}

function parseSymbols(raw: string): string[] {
  return raw
    .split(/[\n,\s]+/)
    .map((s) => s.trim().toUpperCase())
    .filter(Boolean);
}

function applyGate(r: StockTimingResult): GateStatus {
  if (r.execution_priority === "DEFER" || r.timing_score < 40) return "EXCLUDED";
  if (r.timing_score < 60) return "WATCHLIST";
  return "ELIGIBLE";
}

function gateReason(r: StockTimingResult, gate: GateStatus): string {
  if (gate === "EXCLUDED") {
    return r.execution_priority === "DEFER"
      ? `Priority DEFER (score ${r.timing_score})`
      : `Score ${r.timing_score} — below minimum threshold`;
  }
  if (gate === "WATCHLIST") return `Score ${r.timing_score} — monitoring, reduced weight`;
  return `Score ${r.timing_score} — entry conditions met`;
}

// ─── Progress strip ───────────────────────────────────────────────────────────

const STAGES = [
  { key: "reviewing",    label: "Committee" },
  { key: "timing",       label: "Timing" },
  { key: "constructing", label: "Impact" },
  { key: "sizing",       label: "Sizing" },
  { key: "allocating",   label: "Budget" },
  { key: "planning",     label: "Plan" },
];
const STAGE_ORDER: WorkspaceStep[] = [
  "reviewing", "timing", "constructing", "sizing", "allocating", "planning", "done",
];

function ProgressStrip({ step }: { step: WorkspaceStep }) {
  const currentIdx = STAGE_ORDER.indexOf(step);
  return (
    <div className="flex items-center gap-1">
      {STAGES.map((stage, i) => {
        const done = currentIdx > i;
        const active = !done && currentIdx === i;
        return (
          <div key={stage.key} className="flex items-center gap-1">
            {i > 0 && (
              <div className={`h-px w-5 shrink-0 ${done ? "bg-emerald-300" : "bg-gray-200"}`} />
            )}
            <div
              className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-semibold whitespace-nowrap ${
                done
                  ? "bg-emerald-100 text-emerald-800"
                  : active
                  ? "bg-gray-900 text-white"
                  : "bg-gray-100 text-gray-400"
              }`}
            >
              {done && <span>✓</span>}
              {active && (
                <span className="inline-block h-2 w-2 rounded-full border-2 border-white border-t-transparent animate-spin" />
              )}
              <span>{stage.label}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Section 1: Committee Summary ────────────────────────────────────────────

function CommitteeSummary({
  reviews,
  ctx,
}: {
  reviews: IdeaReview[];
  ctx: IdeaReviewPortfolioContext | null;
}) {
  const noData = reviews.filter((r) => !r.data_available);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <h4 className="text-[11px] font-bold text-gray-500 uppercase tracking-wide">
          1 · Committee
        </h4>
        {ctx && (
          <span className="text-[10px] text-gray-400 font-mono">
            {ctx.persona}
            {ctx.regime ? ` · ${ctx.regime}` : ""}
            {ctx.emergency_active ? " · EMERGENCY ACTIVE" : ""}
          </span>
        )}
      </div>

      {noData.length > 0 && (
        <div className="rounded-lg border border-orange-200 bg-orange-50 px-3 py-2 text-[11px] text-orange-700">
          ⚠ No analysis data for:{" "}
          <span className="font-mono font-semibold">
            {noData.map((r) => r.symbol).join(", ")}
          </span>{" "}
          — run Stock Analysis first
        </div>
      )}

      <div className="rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-100">
              <th className="px-3 py-2 text-left text-[10px] font-semibold text-gray-500 uppercase tracking-wide">
                Symbol
              </th>
              <th className="px-3 py-2 text-left text-[10px] font-semibold text-gray-500 uppercase tracking-wide">
                Decision
              </th>
              <th className="px-3 py-2 text-left text-[10px] font-semibold text-gray-500 uppercase tracking-wide">
                Signal
              </th>
              <th className="px-3 py-2 text-right text-[10px] font-semibold text-gray-500 uppercase tracking-wide">
                Fit
              </th>
              <th className="px-3 py-2 text-left text-[10px] font-semibold text-gray-500 uppercase tracking-wide">
                Priority
              </th>
            </tr>
          </thead>
          <tbody>
            {reviews.map((r, i) => (
              <tr
                key={r.symbol}
                className={`border-b border-gray-50 last:border-0 ${
                  i % 2 === 0 ? "bg-white" : "bg-gray-50/30"
                }`}
              >
                <td className="px-3 py-2.5 font-mono font-semibold text-gray-800 text-xs">
                  {r.symbol}
                </td>
                <td className="px-3 py-2.5">
                  <span
                    className={`rounded-full px-2 py-0.5 text-[9px] font-bold border ${
                      DECISION_STYLE[r.committee_decision] ??
                      "bg-gray-100 text-gray-600 border-gray-200"
                    }`}
                  >
                    {r.committee_decision}
                  </span>
                </td>
                <td
                  className={`px-3 py-2.5 text-[11px] font-semibold ${
                    r.existing_signal
                      ? (SIGNAL_STYLE[r.existing_signal] ?? "text-gray-500")
                      : "text-gray-300"
                  }`}
                >
                  {r.existing_signal ?? "—"}
                </td>
                <td className="px-3 py-2.5 text-right font-mono text-gray-600 text-[11px]">
                  {r.data_available ? `${r.strategic_fit_score.toFixed(0)}/10` : "—"}
                </td>
                <td className="px-3 py-2.5">
                  <span
                    className={`text-[10px] font-semibold ${
                      r.portfolio_priority === "HIGH"
                        ? "text-emerald-600"
                        : r.portfolio_priority === "MEDIUM"
                        ? "text-blue-600"
                        : "text-gray-400"
                    }`}
                  >
                    {r.portfolio_priority}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Section 2: Timing Intelligence ──────────────────────────────────────────

function TimingIntelligence({ results }: { results: StockTimingResult[] }) {
  return (
    <div className="space-y-3">
      <h4 className="text-[11px] font-bold text-gray-500 uppercase tracking-wide">
        2 · Timing Intelligence
      </h4>

      <div className="rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-100">
              <th className="px-3 py-2 text-left text-[10px] font-semibold text-gray-500 uppercase tracking-wide">
                Symbol
              </th>
              <th className="px-3 py-2 text-right text-[10px] font-semibold text-gray-500 uppercase tracking-wide">
                Score
              </th>
              <th className="px-3 py-2 text-left text-[10px] font-semibold text-gray-500 uppercase tracking-wide">
                Trend
              </th>
              <th className="px-3 py-2 text-left text-[10px] font-semibold text-gray-500 uppercase tracking-wide">
                Priority
              </th>
              <th className="px-3 py-2 text-left text-[10px] font-semibold text-gray-500 uppercase tracking-wide hidden sm:table-cell">
                Signal
              </th>
            </tr>
          </thead>
          <tbody>
            {results.map((r, i) => (
              <tr
                key={r.symbol}
                className={`border-b border-gray-50 last:border-0 ${
                  i % 2 === 0 ? "bg-white" : "bg-gray-50/30"
                }`}
              >
                <td className="px-3 py-2.5 font-mono font-semibold text-gray-800 text-xs">
                  {r.symbol}
                </td>
                <td className="px-3 py-2.5 text-right">
                  {r.data_available ? (
                    <div className="flex items-center justify-end gap-1.5">
                      <span
                        className={`font-mono font-bold text-sm ${
                          CATEGORY_STYLE[r.timing_category] ?? "text-gray-500"
                        }`}
                      >
                        {r.timing_score}
                      </span>
                      <span
                        className={`text-[9px] font-semibold ${
                          CATEGORY_STYLE[r.timing_category] ?? "text-gray-400"
                        }`}
                      >
                        {r.timing_category}
                      </span>
                    </div>
                  ) : (
                    <span className="text-gray-300 text-[10px]">—</span>
                  )}
                </td>
                <td className="px-3 py-2.5 text-[10px] text-gray-600">
                  {r.data_available
                    ? MOMENTUM_LABEL[r.momentum] ?? r.momentum
                    : "—"}
                </td>
                <td className="px-3 py-2.5">
                  <span
                    className={`rounded-full px-2 py-0.5 text-[9px] font-bold ${
                      PRIORITY_STYLE[r.execution_priority] ?? "bg-gray-100 text-gray-500"
                    }`}
                  >
                    {r.execution_priority}
                  </span>
                </td>
                <td className="px-3 py-2.5 hidden sm:table-cell">
                  {r.data_available && r.reasons.length > 0 ? (
                    <span className="text-[10px] text-gray-500 italic">
                      {r.reasons[0]}
                    </span>
                  ) : (
                    <span className="text-gray-300 text-[10px]">No data</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center gap-3 text-[9px] text-gray-400 font-mono">
        <span className="text-emerald-600 font-semibold">80+ STRONG</span>
        <span>60 GOOD</span>
        <span>40 NEUTRAL</span>
        <span>20 WEAK</span>
        <span className="text-red-500">0 POOR</span>
      </div>
    </div>
  );
}

// ─── Section 3: Selected Basket ───────────────────────────────────────────────

function SelectedBasket({ timingResults }: { timingResults: StockTimingResult[] }) {
  const eligible  = timingResults.filter((r) => applyGate(r) === "ELIGIBLE");
  const watchlist = timingResults.filter((r) => applyGate(r) === "WATCHLIST");
  const excluded  = timingResults.filter((r) => applyGate(r) === "EXCLUDED");

  return (
    <div className="space-y-3">
      <h4 className="text-[11px] font-bold text-gray-500 uppercase tracking-wide">
        3 · Selected Basket
      </h4>

      {/* Eligible */}
      {eligible.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-[10px] font-semibold text-emerald-700 uppercase tracking-wide">
            Eligible ({eligible.length})
          </p>
          <div className="space-y-1">
            {eligible.map((r) => (
              <div
                key={r.symbol}
                className="flex items-center justify-between rounded-lg bg-emerald-50 border border-emerald-100 px-3 py-2"
              >
                <span className="font-mono font-semibold text-gray-800 text-xs">
                  {r.symbol}
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-emerald-700 font-mono">
                    Score {r.timing_score}
                  </span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[9px] font-bold ${GATE_BADGE.ELIGIBLE}`}
                  >
                    ELIGIBLE
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Watchlist */}
      {watchlist.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-[10px] font-semibold text-amber-700 uppercase tracking-wide">
            Watchlist ({watchlist.length}) — reduced weighting
          </p>
          <div className="space-y-1">
            {watchlist.map((r) => (
              <div
                key={r.symbol}
                className="flex items-center justify-between rounded-lg bg-amber-50 border border-amber-100 px-3 py-2"
              >
                <span className="font-mono font-semibold text-gray-800 text-xs">
                  {r.symbol}
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-amber-700 font-mono">
                    Score {r.timing_score}
                  </span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[9px] font-bold ${GATE_BADGE.WATCHLIST}`}
                  >
                    WATCHLIST
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Excluded */}
      {excluded.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-[10px] font-semibold text-red-600 uppercase tracking-wide">
            Excluded ({excluded.length}) — no allocation
          </p>
          <div className="space-y-1">
            {excluded.map((r) => {
              const gate = applyGate(r);
              return (
                <div
                  key={r.symbol}
                  className="flex items-center justify-between rounded-lg bg-gray-50 border border-gray-100 px-3 py-2"
                >
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-semibold text-gray-400 text-xs line-through">
                      {r.symbol}
                    </span>
                    <span className="text-[10px] text-gray-400 italic">
                      {gateReason(r, gate)}
                    </span>
                  </div>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[9px] font-bold ${GATE_BADGE.EXCLUDED}`}
                  >
                    EXCLUDED
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {eligible.length === 0 && watchlist.length === 0 && (
        <div className="rounded-lg border border-red-100 bg-red-50 px-3 py-2.5 text-[11px] text-red-700">
          All symbols excluded by timing gate — improve timing before deploying capital.
        </div>
      )}
    </div>
  );
}

// ─── Section 4: Portfolio Impact ──────────────────────────────────────────────

function PortfolioImpact({ sim }: { sim: BasketSimulationResult }) {
  const moved = sim.impacts.filter((im) => Math.abs(im.delta_pct) > 0.01);

  return (
    <div className="space-y-3">
      <h4 className="text-[11px] font-bold text-gray-500 uppercase tracking-wide">
        4 · Portfolio Impact
      </h4>

      {/* Cash bar */}
      <div className="rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 flex items-center justify-between">
        <span className="text-xs text-gray-500">Cash</span>
        <div className="flex items-center gap-2 font-mono text-sm">
          <span className="text-gray-400">{sim.cash_before_pct.toFixed(1)}%</span>
          <span className="text-gray-300">→</span>
          <span
            className={`font-bold ${
              sim.cash_after_pct < 5 ? "text-amber-700" : "text-gray-800"
            }`}
          >
            {sim.cash_after_pct.toFixed(1)}%
          </span>
          {sim.cash_after_pct < 5 && (
            <span className="text-[9px] font-bold text-amber-600">LOW</span>
          )}
        </div>
      </div>

      {/* Sector bars */}
      {moved.length > 0 && (
        <div className="space-y-2.5">
          {moved.map((impact) => {
            const fillPct = Math.min(
              100,
              impact.sector_limit_pct > 0
                ? (impact.after_pct / impact.sector_limit_pct) * 100
                : 0,
            );
            const isFail = impact.status === "FAIL";
            const isWarn = impact.status === "WARNING";
            return (
              <div key={impact.sector} className="space-y-1">
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-gray-600">{impact.sector}</span>
                  <div className="flex items-center gap-1.5 font-mono">
                    <span className="text-gray-400">{impact.before_pct.toFixed(1)}%</span>
                    <span className="text-gray-300">→</span>
                    <span
                      className={`font-bold ${
                        isFail
                          ? "text-red-700"
                          : isWarn
                          ? "text-amber-700"
                          : "text-gray-800"
                      }`}
                    >
                      {impact.after_pct.toFixed(1)}%
                    </span>
                    {isFail && (
                      <span className="text-[9px] font-bold text-red-600">BREACH</span>
                    )}
                    {isWarn && (
                      <span className="text-[9px] font-bold text-amber-600">NEAR LIMIT</span>
                    )}
                  </div>
                </div>
                <div className="h-1.5 rounded-full bg-gray-100">
                  <div
                    className={`h-1.5 rounded-full transition-all ${
                      isFail ? "bg-red-400" : isWarn ? "bg-amber-400" : "bg-blue-400"
                    }`}
                    style={{ width: `${fillPct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Warnings */}
      {sim.warnings.length > 0 && (
        <div className="space-y-1">
          {sim.warnings.map((w, i) => (
            <p key={i} className="text-[11px] text-amber-700 flex items-start gap-1.5">
              <span className="shrink-0">⚠</span>
              <span>{w}</span>
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Section 5: Suggested Allocation ─────────────────────────────────────────

function SuggestedAllocation({ sizing }: { sizing: PositionSizingResult }) {
  const maxPct = Math.max(...sizing.suggestions.map((s) => s.suggested_pct), 0.01);

  return (
    <div className="space-y-3">
      <h4 className="text-[11px] font-bold text-gray-500 uppercase tracking-wide">
        5 · Suggested Allocation
      </h4>

      {sizing.suggestions.length === 0 ? (
        <p className="text-xs text-gray-400 italic">No positions to size.</p>
      ) : (
        <div className="space-y-3">
          {sizing.suggestions.map((s) => {
            const hasBoost = s.timing_multiplier > 1.0;
            const hasReduced = s.timing_multiplier < 1.0 && s.timing_multiplier > 0;
            return (
              <div key={s.symbol} className="space-y-1">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-semibold text-gray-800 text-xs">
                      {s.symbol}
                    </span>
                    <span
                      className={`text-[9px] font-semibold ${
                        SIGNAL_STYLE[s.signal] ?? "text-gray-400"
                      }`}
                    >
                      {s.signal}
                    </span>
                    {hasBoost && (
                      <span className="text-[9px] text-emerald-600 font-semibold">
                        ×{s.timing_multiplier.toFixed(2)}
                      </span>
                    )}
                    {hasReduced && (
                      <span className="text-[9px] text-amber-600 font-semibold">
                        ×{s.timing_multiplier.toFixed(2)}
                      </span>
                    )}
                  </div>
                  <span className="font-mono font-bold text-emerald-700 text-sm">
                    {s.suggested_pct.toFixed(2)}%
                  </span>
                </div>
                <div className="h-2 rounded-full bg-gray-100">
                  <div
                    className={`h-2 rounded-full ${hasBoost ? "bg-emerald-500" : hasReduced ? "bg-amber-400" : "bg-emerald-400"}`}
                    style={{ width: `${(s.suggested_pct / maxPct) * 100}%` }}
                  />
                </div>
              </div>
            );
          })}

          <div className="border-t border-gray-200 pt-2 flex items-center justify-between text-xs font-semibold text-gray-700">
            <span>Total</span>
            <span className="font-mono">{sizing.total_allocated_pct.toFixed(2)}%</span>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Section 6: Execution Plan ────────────────────────────────────────────────

const PLAN_STATUS_STYLE: Record<string, string> = {
  READY:           "border-emerald-200 bg-emerald-50 text-emerald-800",
  NO_SELLS_NEEDED: "border-blue-200 bg-blue-50 text-blue-800",
  INSUFFICIENT:    "border-red-200 bg-red-50 text-red-800",
};

const PLAN_STATUS_DOT: Record<string, string> = {
  READY:           "bg-emerald-500",
  NO_SELLS_NEEDED: "bg-blue-400",
  INSUFFICIENT:    "bg-red-500",
};

const PLAN_STATUS_LABEL: Record<string, string> = {
  READY:           "Ready to Execute",
  NO_SELLS_NEEDED: "Funded from Cash",
  INSUFFICIENT:    "Insufficient Capital",
};

const FUND_STATUS_STYLE: Record<string, string> = {
  FUNDED:       "border-emerald-300 bg-emerald-100 text-emerald-900",
  INSUFFICIENT: "border-red-300 bg-red-100 text-red-900",
  CASH_ONLY:    "border-blue-200 bg-blue-50 text-blue-900",
};

function fmt(n: number): string {
  return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

// ─── Funding Flow Card (UX.2L) ────────────────────────────────────────────────

function FundingFlowCard({ bd, buyActions }: { bd: FundingBreakdown; buyActions: BuyAction[] }) {
  const hasSells   = bd.sell_sources.length > 0;
  const hasReduces = bd.reduce_sources.length > 0;
  const hasTrades  = hasSells || hasReduces;

  return (
    <div className="rounded-xl border border-gray-200 overflow-hidden">
      {/* ── SELL sources ────────────────────────────────────────────── */}
      {hasSells && (
        <div className="bg-red-50 border-b border-gray-100">
          <div className="px-4 pt-3 pb-1">
            <p className="text-[9px] font-bold text-red-600 uppercase tracking-wide mb-2">
              Sell
            </p>
            <div className="space-y-1.5 pb-2">
              {bd.sell_sources.map((src: FundingSourceItem) => (
                <div key={src.symbol} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-red-200 text-red-800">
                      SELL
                    </span>
                    <span className="font-mono font-semibold text-gray-800 text-xs">
                      {src.symbol}
                    </span>
                    <span className="text-[10px] text-red-500 font-mono">full position</span>
                  </div>
                  <span className="font-mono font-bold text-red-700 text-[13px] tabular-nums">
                    +{fmt(src.estimated_release)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── REDUCE sources ──────────────────────────────────────────── */}
      {hasReduces && (
        <div className="bg-amber-50 border-b border-gray-100">
          <div className="px-4 pt-3 pb-1">
            <p className="text-[9px] font-bold text-amber-600 uppercase tracking-wide mb-2">
              Reduce
            </p>
            <div className="space-y-1.5 pb-2">
              {bd.reduce_sources.map((src: FundingSourceItem) => (
                <div key={src.symbol} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-amber-200 text-amber-800">
                      REDUCE
                    </span>
                    <span className="font-mono font-semibold text-gray-800 text-xs">
                      {src.symbol}
                    </span>
                    <span className="text-[10px] text-amber-600 font-mono">
                      {(src.release_pct * 100).toFixed(0)}% released
                    </span>
                  </div>
                  <span className="font-mono font-bold text-amber-700 text-[13px] tabular-nums">
                    +{fmt(src.estimated_release)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── Existing Cash ────────────────────────────────────────────── */}
      <div className="bg-blue-50 border-b border-gray-100 px-4 py-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-blue-200 text-blue-800">
              CASH
            </span>
            <span className="text-xs text-blue-700">{bd.cash_source.label}</span>
          </div>
          <span className="font-mono font-bold text-blue-700 text-[13px] tabular-nums">
            +{fmt(bd.cash_source.amount)}
          </span>
        </div>
      </div>

      {/* ── Total Funding ─────────────────────────────────────────────── */}
      <div className="bg-gray-50 border-b border-gray-200 px-4 py-2.5 flex items-center justify-between">
        <span className="text-[11px] font-bold text-gray-600 uppercase tracking-wide">
          Total Funding
        </span>
        <span className="font-mono font-bold text-gray-800 text-sm tabular-nums">
          {fmt(bd.total_funding)}
        </span>
      </div>

      {/* ── Buy targets ──────────────────────────────────────────────── */}
      {buyActions.length > 0 && (
        <div className="bg-emerald-50 border-b border-gray-100">
          <div className="px-4 pt-3 pb-1">
            <p className="text-[9px] font-bold text-emerald-600 uppercase tracking-wide mb-2">
              Buy Targets
            </p>
            <div className="space-y-1.5 pb-2">
              {buyActions.map((ba: BuyAction) => (
                <div key={ba.symbol} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-[9px] font-bold px-1.5 py-0.5 rounded bg-emerald-200 text-emerald-800">
                      BUY
                    </span>
                    <span className="font-mono font-semibold text-gray-800 text-xs">
                      {ba.symbol}
                    </span>
                    <span className="text-[10px] text-emerald-600 font-mono">
                      {ba.allocation_pct.toFixed(2)}%
                      {ba.timing_score !== null ? ` · t${ba.timing_score}` : ""}
                    </span>
                  </div>
                  <span className="font-mono font-bold text-emerald-700 text-[13px] tabular-nums">
                    −{fmt(ba.estimated_amount)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* ── Summary bar ──────────────────────────────────────────────── */}
      <div className={`border-t-2 px-4 py-3 ${FUND_STATUS_STYLE[bd.status] ?? "border-gray-200 bg-gray-50 text-gray-800"}`}>
        <div className="flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-4 text-[11px]">
            <span>
              Available{" "}
              <span className="font-mono font-bold tabular-nums">{fmt(bd.total_funding)}</span>
            </span>
            <span className="opacity-40">·</span>
            <span>
              Needed{" "}
              <span className="font-mono font-bold tabular-nums">{fmt(bd.total_deployment)}</span>
            </span>
            <span className="opacity-40">·</span>
            <span>
              {bd.surplus_cash >= 0 ? "Surplus" : "Shortfall"}{" "}
              <span className="font-mono font-bold tabular-nums">
                {fmt(Math.abs(bd.surplus_cash))}
              </span>
            </span>
          </div>
          <span className="text-[10px] font-bold uppercase tracking-wide">
            {bd.status === "FUNDED" ? "FUNDED" : bd.status === "CASH_ONLY" ? "CASH ONLY" : "INSUFFICIENT"}
          </span>
        </div>
      </div>
    </div>
  );
}

// ─── Legacy cash-only fallback ────────────────────────────────────────────────

function LegacyCashSummary({ plan }: { plan: ExecutionPlanResult }) {
  const { cash_summary } = plan;
  return (
    <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
      <p className="text-[10px] font-bold text-gray-500 uppercase tracking-wide mb-3">
        Cash Summary
      </p>
      <div className="space-y-2">
        {[
          { label: "Cash before",      value: cash_summary.cash_before,      muted: true },
          { label: "Cash released",    value: cash_summary.cash_released,    muted: false },
          { label: "Total deployable", value: cash_summary.total_deployable, muted: false, bold: true },
          { label: "Total deployed",   value: -cash_summary.total_deployed,  muted: false },
        ].map(({ label, value, muted, bold }) => (
          <div key={label} className="flex items-center justify-between text-xs">
            <span className={muted ? "text-gray-400" : "text-gray-600"}>{label}</span>
            <span
              className={`font-mono tabular-nums ${
                bold ? "font-bold text-gray-800" : muted ? "text-gray-400" : "text-gray-700"
              }`}
            >
              {value < 0 ? `(${fmt(Math.abs(value))})` : fmt(value)}
            </span>
          </div>
        ))}
        <div className="border-t border-gray-200 pt-2 flex items-center justify-between text-xs">
          <span className="font-semibold text-gray-700">Expected remaining cash</span>
          <span
            className={`font-mono font-bold tabular-nums ${
              cash_summary.cash_remaining < 0 ? "text-red-600" : "text-gray-900"
            }`}
          >
            {cash_summary.cash_remaining < 0
              ? `(${fmt(Math.abs(cash_summary.cash_remaining))})`
              : fmt(cash_summary.cash_remaining)}
          </span>
        </div>
      </div>
      <p className="text-[9px] text-gray-300 mt-3">
        Amounts estimated from avg cost × shares — no live prices. No trades are placed.
      </p>
    </div>
  );
}

function ExecutionPlanSection({ plan }: { plan: ExecutionPlanResult }) {
  const { status, warnings, funding_breakdown, buy_actions } = plan;

  return (
    <div className="space-y-4">
      <h4 className="text-[11px] font-bold text-gray-500 uppercase tracking-wide">
        7 · Execution Plan
      </h4>

      {/* Status banner */}
      <div
        className={`rounded-xl border px-4 py-3 flex items-center gap-2.5 ${
          PLAN_STATUS_STYLE[status] ?? "border-gray-200 bg-gray-50 text-gray-700"
        }`}
      >
        <div
          className={`h-2.5 w-2.5 rounded-full shrink-0 ${
            PLAN_STATUS_DOT[status] ?? "bg-gray-400"
          }`}
        />
        <span className="text-xs font-bold">{PLAN_STATUS_LABEL[status] ?? status}</span>
      </div>

      {/* Warnings */}
      {warnings.length > 0 && (
        <div className="space-y-1">
          {warnings.map((w, i) => (
            <p key={i} className="text-[11px] text-amber-700 flex items-start gap-1.5">
              <span className="shrink-0">⚠</span>
              <span>{w}</span>
            </p>
          ))}
        </div>
      )}

      {/* Funding flow (UX.2L) — shows full SELL→REDUCE→CASH→BUY chain */}
      {funding_breakdown ? (
        <FundingFlowCard bd={funding_breakdown} buyActions={buy_actions} />
      ) : (
        // Backward-compatible fallback if backend doesn't return breakdown
        <LegacyCashSummary plan={plan} />
      )}

      <p className="text-[9px] text-gray-300">
        Amounts estimated from avg cost × shares — no live prices. No trades are placed.
      </p>
    </div>
  );
}

// ─── Section 7: Final Decision ────────────────────────────────────────────────

function FinalDecision({
  construction,
  sizing,
  timingResults,
}: {
  construction: PortfolioConstructionResult;
  sizing: PositionSizingResult;
  timingResults: StockTimingResult[];
}) {
  const overall = worstStatus(construction.overall_status, sizing.status);
  const cashAfter = Math.max(
    0,
    construction.simulation.cash_before_pct - sizing.total_allocated_pct,
  );
  const reasonings = [...construction.reasoning, ...sizing.reasoning];

  const selected = timingResults.filter((r) => applyGate(r) !== "EXCLUDED");
  const excludedList = timingResults.filter((r) => applyGate(r) === "EXCLUDED");

  const priorities = timingResults.filter((r) => r.data_available && applyGate(r) !== "EXCLUDED").map((r) => r.execution_priority);
  const topPriority =
    priorities.includes("HIGH")
      ? "HIGH"
      : priorities.includes("MEDIUM")
      ? "MEDIUM"
      : priorities.includes("LOW")
      ? "LOW"
      : priorities.length > 0
      ? "DEFER"
      : null;

  return (
    <div className="space-y-3">
      <h4 className="text-[11px] font-bold text-gray-500 uppercase tracking-wide">
        8 · Final Decision
      </h4>

      <div className={`rounded-xl border-2 p-5 space-y-5 ${STATUS_BORDER[overall]}`}>
        {/* Status */}
        <div className="flex items-center gap-2.5">
          <div
            className={`h-3 w-3 rounded-full shrink-0 ${STATUS_DOT[overall]}`}
          />
          <span className="text-sm font-bold uppercase tracking-wide">{overall}</span>
        </div>

        {/* Numbers */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div>
            <p className="text-[10px] opacity-60 uppercase tracking-wide mb-1">
              Selected
            </p>
            <p className="text-2xl font-bold font-mono">
              {selected.length}
              <span className="text-base opacity-50"> / {timingResults.length}</span>
            </p>
          </div>
          <div>
            <p className="text-[10px] opacity-60 uppercase tracking-wide mb-1">
              Deployment
            </p>
            <p className="text-2xl font-bold font-mono">
              {sizing.total_allocated_pct.toFixed(2)}%
            </p>
          </div>
          <div>
            <p className="text-[10px] opacity-60 uppercase tracking-wide mb-1">
              Cash Remaining
            </p>
            <p className="text-2xl font-bold font-mono">{cashAfter.toFixed(1)}%</p>
          </div>
          {topPriority && (
            <div>
              <p className="text-[10px] opacity-60 uppercase tracking-wide mb-1">
                Priority
              </p>
              <p className={`text-2xl font-bold ${CATEGORY_STYLE[topPriority] ?? ""}`}>
                {topPriority}
              </p>
            </div>
          )}
        </div>

        {/* Excluded list */}
        {excludedList.length > 0 && (
          <div className="space-y-1 border-t border-current border-opacity-10 pt-3">
            <p className="text-[10px] font-semibold opacity-60 uppercase tracking-wide">
              Excluded by timing gate
            </p>
            {excludedList.map((r) => (
              <p key={r.symbol} className="text-[11px] opacity-70 flex items-center gap-2">
                <span className="font-mono font-semibold">{r.symbol}</span>
                <span className="opacity-60">— Timing Score {r.timing_score}</span>
              </p>
            ))}
          </div>
        )}

        {/* Reasoning */}
        {reasonings.length > 0 && (
          <div className="space-y-1 border-t border-current border-opacity-10 pt-3">
            {reasonings.map((line, i) => (
              <p key={i} className="text-[11px] opacity-75 leading-relaxed">
                · {line}
              </p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Section 6: Risk Budget Allocation ───────────────────────────────────────

const RISK_BAND_STYLE = (risk: number): string => {
  if (risk <= 30)  return "text-emerald-600";
  if (risk <= 60)  return "text-gray-600";
  if (risk <= 80)  return "text-amber-700";
  return "text-red-600";
};

function RiskBudgetSection({ result }: { result: RiskBudgetResult }) {
  const { allocations, excluded, status } = result;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-2">
        <h4 className="text-[11px] font-bold text-gray-500 uppercase tracking-wide">
          6 · Risk Budget
        </h4>
        <span
          className={`text-[9px] font-bold px-2 py-0.5 rounded-full border ${
            STATUS_BORDER[status] ?? "border-gray-200 bg-gray-100 text-gray-500"
          }`}
        >
          {status}
        </span>
      </div>

      {/* Allocation bars */}
      {allocations.length > 0 && (() => {
        const maxPct = Math.max(...allocations.map((a) => a.weight_pct), 0.01);
        return (
          <div className="space-y-2.5">
            {allocations.map((a) => (
              <div key={a.symbol} className="space-y-1">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-semibold text-gray-800 text-xs">
                      {a.symbol}
                    </span>
                    <span className="text-[10px] text-gray-400">{a.sector}</span>
                    {a.capped && (
                      <span className="text-[9px] font-semibold text-amber-600">
                        capped
                      </span>
                    )}
                  </div>
                  <span className="font-mono font-bold text-gray-800 text-sm">
                    {a.weight_pct.toFixed(1)}%
                  </span>
                </div>
                <div className="h-2 rounded-full bg-gray-100">
                  <div
                    className={`h-2 rounded-full ${
                      a.capped ? "bg-amber-400" : "bg-indigo-500"
                    }`}
                    style={{ width: `${(a.weight_pct / maxPct) * 100}%` }}
                  />
                </div>
                {/* Driver metrics */}
                <div className="flex items-center gap-3 text-[10px] font-mono text-gray-500">
                  <span>Return <span className="font-semibold text-gray-700">{a.expected_return.toFixed(0)}</span></span>
                  <span className="text-gray-300">·</span>
                  <span className={RISK_BAND_STYLE(a.risk_score)}>Risk <span className="font-semibold">{a.risk_score.toFixed(0)}</span></span>
                  <span className="text-gray-300">·</span>
                  <span>Conf <span className="font-semibold text-gray-700">{a.confidence_score.toFixed(0)}</span></span>
                </div>
                {/* Reasoning badges */}
                {a.reasons.length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {a.reasons.map((r, ri) => (
                      <span key={ri} className="text-[9px] px-1.5 py-0.5 rounded bg-gray-100 text-gray-500">
                        ✓ {r}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}

            <div className="border-t border-gray-200 pt-2 flex items-center justify-between text-xs font-semibold text-gray-700">
              <span>Target Total</span>
              <span className="font-mono">
                {result.total_weight_pct.toFixed(1)}%
              </span>
            </div>
          </div>
        );
      })()}

      {/* Excluded by confidence */}
      {excluded.length > 0 && (
        <div className="rounded-lg border border-amber-100 bg-amber-50 px-3 py-2 space-y-1">
          <p className="text-[10px] font-semibold text-amber-700 uppercase tracking-wide">
            Excluded by confidence filter
          </p>
          {excluded.map((e) => (
            <p key={e.symbol} className="text-[11px] text-amber-700 flex items-center gap-2">
              <span className="font-mono font-semibold">{e.symbol}</span>
              <span className="opacity-60">— {e.reason}</span>
            </p>
          ))}
        </div>
      )}

      {/* Reasoning */}
      {result.reasoning.length > 0 && (
        <div className="space-y-1">
          {result.reasoning.map((line, i) => (
            <p key={i} className="text-[11px] text-gray-500 flex items-start gap-1.5">
              <span className="shrink-0">·</span>
              <span>{line}</span>
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Advanced Tools accordion ─────────────────────────────────────────────────

function AdvancedTools({ portfolioId }: { portfolioId: number }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="border-t border-gray-100 pt-4">
      <button
        className="flex items-center gap-2 text-[11px] text-gray-400 hover:text-gray-600 transition-colors"
        onClick={() => setOpen((p) => !p)}
      >
        <span className="text-[9px]">{open ? "▼" : "▶"}</span>
        <span>Advanced Tools</span>
      </button>

      {open && (
        <div className="mt-4 space-y-4">
          <IdeaIntakeCard portfolioId={portfolioId} />
          <BasketSimulationCard portfolioId={portfolioId} />
          <PortfolioConstructionCard portfolioId={portfolioId} />
          <PositionSizingCard portfolioId={portfolioId} />
        </div>
      )}
    </div>
  );
}

// ─── Optimizer handoff banner ─────────────────────────────────────────────────

function OptimizerHandoffBanner({ symbols }: { symbols: string[] }) {
  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50 px-3 py-2.5 flex items-start gap-2.5">
      <span className="text-blue-500 text-sm shrink-0 mt-px">→</span>
      <div className="min-w-0">
        <p className="text-[11px] font-semibold text-blue-800">
          From Portfolio Optimizer — {symbols.length} accumulation candidate{symbols.length !== 1 ? "s" : ""}
        </p>
        <p className="text-[10px] text-blue-600 font-mono mt-0.5 truncate">
          {symbols.join(" · ")}
        </p>
      </div>
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

const PLACEHOLDER = `NVDA01\nGOOGL01\nMICRON01\nBH`;

export default function DecisionWorkspace({
  portfolioId,
  initialSymbols,
}: {
  portfolioId: number;
  initialSymbols?: string[];
}) {
  const [input, setInput] = useState(
    initialSymbols && initialSymbols.length > 0 ? initialSymbols.join("\n") : ""
  );
  const [step, setStep] = useState<WorkspaceStep>("idle");
  const [error, setError] = useState<string | null>(null);
  const [reviews, setReviews] = useState<IdeaReview[] | null>(null);
  const [portfolioCtx, setPortfolioCtx] = useState<IdeaReviewPortfolioContext | null>(null);
  const [construction, setConstruction] = useState<PortfolioConstructionResult | null>(null);
  const [sizing, setSizing] = useState<PositionSizingResult | null>(null);
  const [riskBudget, setRiskBudget] = useState<RiskBudgetResult | null>(null);
  const [timingResults, setTimingResults] = useState<StockTimingResult[] | null>(null);
  const [executionPlan, setExecutionPlan] = useState<ExecutionPlanResult | null>(null);

  const handleAnalyze = useCallback(async () => {
    const symbols = parseSymbols(input);
    if (symbols.length === 0) return;
    if (symbols.length > 10) {
      setError("Maximum 10 symbols per analysis");
      return;
    }

    setError(null);
    setReviews(null);
    setPortfolioCtx(null);
    setConstruction(null);
    setSizing(null);
    setRiskBudget(null);
    setTimingResults(null);
    setExecutionPlan(null);

    try {
      // Step 1 — Committee review
      setStep("reviewing");
      const reviewRes = await reviewIdeas(portfolioId, symbols);
      if (reviewRes.error) throw new Error(reviewRes.error);
      setReviews(reviewRes.reviews);
      setPortfolioCtx(reviewRes.portfolio_context);

      // Step 2 — Timing intelligence
      setStep("timing");
      const timingRes = await scoreTimingIntelligence(symbols);
      const allTiming: StockTimingResult[] = Array.isArray(timingRes) ? timingRes : [];
      setTimingResults(allTiming);

      // Derive gate results client-side
      const eligibleSymbols = allTiming
        .filter((r) => applyGate(r) !== "EXCLUDED")
        .map((r) => r.symbol);

      const timingScoresMap: Record<string, number> = {};
      allTiming.forEach((r) => { timingScoresMap[r.symbol] = r.timing_score; });

      if (eligibleSymbols.length === 0) {
        // All symbols excluded — skip allocation steps
        setStep("done");
        return;
      }

      // Step 3 — Portfolio impact (eligible symbols only)
      setStep("constructing");
      const constructionRes = await suggestAllocation(portfolioId, eligibleSymbols);
      if (constructionRes.error) throw new Error(constructionRes.error);
      setConstruction(constructionRes);

      // Step 4 — Position sizing with timing multipliers
      setStep("sizing");
      const sizingRes = await suggestPositionSizes(portfolioId, eligibleSymbols, timingScoresMap);
      if (sizingRes.error) throw new Error(sizingRes.error);
      setSizing(sizingRes);

      // Step 5 — Risk budget allocation (target portfolio weights)
      setStep("allocating");
      const budgetRes = await calculateRiskBudget(portfolioId, eligibleSymbols);
      if (!budgetRes.error) setRiskBudget(budgetRes);

      // Step 6 — Execution plan (funding sources + buy actions)
      setStep("planning");
      const planRes = await buildExecutionPlan(
        portfolioId,
        eligibleSymbols,
        sizingRes.suggestions,
        timingScoresMap,
      );
      // Non-fatal: plan errors don't block the rest of the output
      if (!planRes.error) setExecutionPlan(planRes);

      setStep("done");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
      setStep("idle");
    }
  }, [input, portfolioId]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        handleAnalyze();
      }
    },
    [handleAnalyze],
  );

  const handleClear = useCallback(() => {
    setStep("idle");
    setReviews(null);
    setPortfolioCtx(null);
    setConstruction(null);
    setSizing(null);
    setRiskBudget(null);
    setTimingResults(null);
    setExecutionPlan(null);
    setError(null);
  }, []);

  const isLoading = step !== "idle" && step !== "done";
  const isDone = step === "done";
  const symbolCount = parseSymbols(input).length;
  const allExcluded = isDone && timingResults !== null && timingResults.every((r) => applyGate(r) === "EXCLUDED");

  return (
    <div className="rounded-2xl border-2 border-gray-900 bg-white p-6 space-y-5">
      {/* Header */}
      <div>
        <h3 className="text-sm font-bold text-gray-900">Decision Workspace</h3>
        <p className="text-xs text-gray-400 mt-0.5">
          Committee review · timing gate · portfolio impact · timing-adjusted allocation · execution plan
        </p>
      </div>

      {/* Optimizer handoff banner */}
      {initialSymbols && initialSymbols.length > 0 && (
        <OptimizerHandoffBanner symbols={initialSymbols} />
      )}

      {/* Input */}
      <div className="space-y-2">
        <textarea
          className="w-full h-28 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm font-mono
                     text-gray-800 placeholder:text-gray-300 focus:outline-none focus:ring-2
                     focus:ring-gray-900 resize-none"
          placeholder={PLACEHOLDER}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          spellCheck={false}
        />
        <div className="flex items-center gap-3">
          <p className="text-[10px] text-gray-400 flex-1">
            {symbolCount > 0
              ? `${symbolCount} symbol${symbolCount !== 1 ? "s" : ""} · committee → timing → basket → impact → allocation → plan → decision`
              : "Ctrl+Enter to analyze"}
          </p>
          {isDone && (
            <button
              onClick={handleClear}
              className="text-[10px] text-gray-400 hover:text-gray-600 transition-colors px-2 py-1"
            >
              Clear
            </button>
          )}
          <button
            onClick={handleAnalyze}
            disabled={isLoading || symbolCount === 0}
            className="flex items-center gap-1.5 rounded-lg bg-gray-900 px-5 py-2 text-xs font-semibold
                       text-white transition hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <span className="inline-block h-3 w-3 rounded-full border-2 border-white border-t-transparent animate-spin" />
                Analyzing…
              </>
            ) : (
              "Analyze Ideas"
            )}
          </button>
        </div>
      </div>

      {/* Progress (loading) */}
      {isLoading && (
        <div className="flex justify-center py-3">
          <ProgressStrip step={step} />
        </div>
      )}

      {/* Progress (done — compact summary) */}
      {isDone && (
        <div className="flex justify-start">
          <ProgressStrip step={step} />
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          {error}
        </div>
      )}

      {/* Results */}
      {isDone && reviews && timingResults && (
        <div className="space-y-6 border-t border-gray-100 pt-5">
          <CommitteeSummary reviews={reviews} ctx={portfolioCtx} />
          <div className="border-t border-gray-100" />
          <TimingIntelligence results={timingResults} />
          <div className="border-t border-gray-100" />
          <SelectedBasket timingResults={timingResults} />

          {allExcluded ? (
            <div className="rounded-lg border border-red-100 bg-red-50 px-4 py-3 text-[11px] text-red-700">
              All symbols excluded by timing gate — no allocation calculated. Improve timing conditions before deploying capital.
            </div>
          ) : (
            construction && sizing && (
              <>
                <div className="border-t border-gray-100" />
                <PortfolioImpact sim={construction.simulation} />
                <div className="border-t border-gray-100" />
                <SuggestedAllocation sizing={sizing} />
                {riskBudget && (
                  <>
                    <div className="border-t border-gray-100" />
                    <RiskBudgetSection result={riskBudget} />
                  </>
                )}
                {executionPlan && (
                  <>
                    <div className="border-t border-gray-100" />
                    <ExecutionPlanSection plan={executionPlan} />
                  </>
                )}
                <div className="border-t border-gray-100" />
                <FinalDecision
                  construction={construction}
                  sizing={sizing}
                  timingResults={timingResults}
                />
              </>
            )
          )}
        </div>
      )}

      {/* Advanced Tools */}
      <AdvancedTools portfolioId={portfolioId} />
    </div>
  );
}
