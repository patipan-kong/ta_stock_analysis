"use client";

import { useState, useEffect, useCallback, type ReactNode } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import BackBreadcrumb from "@/components/BackBreadcrumb";
import { usePortfolio } from "@/lib/PortfolioContext";
import {
  runOptimizer, listOptimizerHistory, getOptimizerHistory,
  listStrategyProfiles, getPortfolioPersona, updatePortfolioPersona,
  recordDecisionBySnapshot, listExecutionDecisions,
  getDecisionMemoryTimeline, getShadowPerformanceSummary, getOperationsStatus,
} from "@/lib/api";
import SignalBadge from "@/components/SignalBadge";
import AIBadge from "@/components/AIBadge";
import MarketRegimeCard from "@/components/MarketRegimeCard";
import ActivePolicyEnvelopeCard from "@/components/ActivePolicyEnvelopeCard";
import AttributionPanel from "@/components/AttributionPanel";
import OperationsTimeline from "@/components/operations-center/quant/OperationsTimeline";
import ExecutionPlanCard from "@/components/optimizer/ExecutionPlanCard";
import { isDeferred, NO_ACTION_REASON_LABELS } from "@/lib/executionPlan";
import PersonaMatchCard from "@/components/PersonaMatchCard";
import { ReasonCell, type ReasonFact } from "@/components/ReasonCell";
import type {
  OptimizerResult, OptimizerHistoryItem, TargetAllocation, AllocationAction,
  WatchlistRanking, Layer2Result, Layer3Result, OptimizerConsensus, RiskFlag, SectorWarning,
  BlockedOpportunity, SwapSuggestion, ConsensusType,
  StrategyPersona, StrategyProfile, PortfolioDNA, MarketRegime,
  ActivePolicy, ExecutionDecision, ExecutionDecisionType, OverrideCategoryType,
  DecisionMemoryEntry, ShadowPerformanceSummary, ExecutionRisk, OperationsCenterStatus,
  StabilizationMeta, OptimizerStatus,
} from "@/lib/api";
import { marketDataFreshnessTh, optimizerLastAnalysisBadgeTh } from "@/components/operations-center/freshness";

const TZ = "Asia/Bangkok";
const SELECTED_HISTORY_MAP_KEY = "optimizer_selected_history_map";

function readSelectedHistoryMap(): Record<string, number> {
  try {
    const raw = localStorage.getItem(SELECTED_HISTORY_MAP_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object" ? parsed as Record<string, number> : {};
  } catch {
    return {};
  }
}

function rememberSelectedHistory(portfolioId: number, historyId: number): void {
  const map = readSelectedHistoryMap();
  map[String(portfolioId)] = historyId;
  try {
    localStorage.setItem(SELECTED_HISTORY_MAP_KEY, JSON.stringify(map));
  } catch {
    // Ignore storage failures; this is a UX enhancement only.
  }
}

// ─── Persona config ───────────────────────────────────────────────────────────

const PERSONA_CFG: Record<StrategyPersona, { icon: string; color: string; badge: string }> = {
  BALANCED:  { icon: "⚖",  color: "text-blue-700",   badge: "bg-blue-50 border-blue-300 text-blue-800" },
  GROWTH:    { icon: "🚀", color: "text-green-700",  badge: "bg-green-50 border-green-300 text-green-800" },
  VALUE:     { icon: "💎", color: "text-purple-700", badge: "bg-purple-50 border-purple-300 text-purple-800" },
  DIVIDEND:  { icon: "💰", color: "text-amber-700",  badge: "bg-amber-50 border-amber-300 text-amber-800" },
  MOMENTUM:  { icon: "⚡", color: "text-orange-700", badge: "bg-orange-50 border-orange-300 text-orange-800" },
  PASSIVE:   { icon: "🌿", color: "text-teal-700",   badge: "bg-teal-50 border-teal-300 text-teal-800" },
};


const FACTOR_COLORS: Record<string, string> = {
  growth:   "bg-green-500",
  value:    "bg-purple-500",
  momentum: "bg-orange-500",
  quality:  "bg-blue-500",
  dividend: "bg-amber-500",
};

const FACTOR_ORDER = ["growth", "value", "momentum", "quality", "dividend"] as const;

// ─── Persona Selector ─────────────────────────────────────────────────────────

function PersonaSelector({
  portfolioId,
  persona,
  profiles,
  saving,
  onSave,
}: {
  portfolioId: number | null;
  persona: StrategyPersona;
  profiles: StrategyProfile[];
  saving: boolean;
  onSave: (p: StrategyPersona) => void;
}) {
  if (!portfolioId || profiles.length === 0) return null;
  const cfg = PERSONA_CFG[persona] ?? PERSONA_CFG.BALANCED;
  return (
    <div>
      <label className="block text-xs text-gray-500 mb-1">Strategy Persona</label>
      <div className="flex items-center gap-2">
        <span className={`text-base ${cfg.color}`}>{cfg.icon}</span>
        <select
          value={persona}
          disabled={saving}
          onChange={(e) => onSave(e.target.value as StrategyPersona)}
          className="border rounded px-2 py-1.5 text-sm bg-white min-w-[160px]"
        >
          {profiles.map((p) => (
            <option key={p.id} value={p.id}>{p.label}</option>
          ))}
        </select>
        {saving && <span className="text-xs text-gray-400">Saving…</span>}
      </div>
    </div>
  );
}

// ─── Portfolio DNA Card ───────────────────────────────────────────────────────

function PortfolioDNACard({
  dna,
  targetPersona,
  profiles,
}: {
  dna: PortfolioDNA;
  targetPersona: StrategyPersona;
  profiles: StrategyProfile[];
}) {
  const profile = profiles.find((p) => p.id === targetPersona);
  const cfg = PERSONA_CFG[targetPersona] ?? PERSONA_CFG.BALANCED;

  return (
    <section className="bg-white border rounded-xl p-5 shadow-sm space-y-4">
      <div className="flex items-center gap-2 flex-wrap">
        <span className={`text-lg ${cfg.color}`}>{cfg.icon}</span>
        <div>
          <h3 className="font-semibold text-gray-800">Portfolio DNA</h3>
          <p className="text-xs text-gray-500 mt-0.5">
            Current factor exposure vs {profile?.label ?? targetPersona} target
          </p>
        </div>
      </div>

      <div className="space-y-3">
        {FACTOR_ORDER.map((factor) => {
          const current = dna[factor] ?? 50;
          const target = profile ? (profile.factor_weights[factor] ?? 0) * 100 : 20;
          const barColor = FACTOR_COLORS[factor] ?? "bg-gray-400";
          const delta = current - target;
          const deviationText =
            delta >= 0.5  ? `+${delta.toFixed(0)} vs target`
            : delta <= -0.5 ? `${delta.toFixed(0)} vs target`
            : "on target";
          const deviationColor =
            delta > 10  ? "text-green-600"
            : delta < -10 ? "text-red-500"
            : "text-gray-400";
          return (
            <div key={factor} className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="capitalize font-medium text-gray-600 w-20">{factor}</span>
                <div className="flex items-center gap-3 text-xs">
                  <span className="text-gray-400">target {target.toFixed(0)}</span>
                  <span className={`font-semibold tabular-nums ${deviationColor}`}>{deviationText}</span>
                  <span className="font-bold text-gray-800 w-8 text-right tabular-nums">{current.toFixed(0)}</span>
                </div>
              </div>
              <div className="relative h-2 bg-gray-100 rounded-full overflow-visible">
                {/* target marker */}
                <div
                  className="absolute top-0 bottom-0 w-0.5 bg-gray-400 opacity-60 z-10 rounded"
                  style={{ left: `${Math.min(100, target)}%` }}
                />
                {/* current bar */}
                <div
                  className={`h-full rounded-full ${barColor} opacity-75`}
                  style={{ width: `${Math.min(100, current)}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
      <p className="text-xs text-gray-400">
        Gray marker = {profile?.label ?? "persona"} target · Bar = current portfolio · Same source as DNA Analysis page
      </p>
    </section>
  );
}


function formatDate(iso: string): string {
  const d = new Date(iso);
  return (
    d.toLocaleDateString("th-TH", { day: "2-digit", month: "short", year: "2-digit", timeZone: TZ }) +
    " " +
    d.toLocaleTimeString("th-TH", { hour: "2-digit", minute: "2-digit", timeZone: TZ })
  );
}

function formatDecisionLabel(item: OptimizerHistoryItem, detail: OptimizerResult | null): string {
  const c = detail?.consensus?.consensus_decision;
  if (c) return c.replace(/_/g, " ");
  if (item.optimizer_status === "NO_ACTION") return "NO ACTION";
  return "REBALANCE";
}

function formatRegimeLabel(detail: OptimizerResult | null): string {
  const r = detail?.market_regime?.regime;
  return r ? r.replace(/_/g, " ") : "-";
}

function getFinalConsensusScore(
  result: Pick<OptimizerResult, "final_consensus_score" | "consensus" | "rebalance_opportunity_score"> | null | undefined,
): number | null {
  if (!result) return null;
  if (typeof result.final_consensus_score === "number") return result.final_consensus_score;
  if (typeof result.consensus?.consensus_strength_score === "number") return result.consensus.consensus_strength_score;
  if (typeof result.rebalance_opportunity_score === "number") return result.rebalance_opportunity_score;
  return null;
}

function getHistoryFinalConsensusScore(item: OptimizerHistoryItem, detail: OptimizerResult | null): number | null {
  if (detail) return getFinalConsensusScore(detail);
  if (typeof item.final_consensus_score === "number") return item.final_consensus_score;
  if (typeof item.rebalance_opportunity_score === "number") return item.rebalance_opportunity_score;
  return null;
}

function daysSinceRebalanceText(days: number | null | undefined): string {
  if (days == null) return "ยังไม่มีประวัติการรีบาลานซ์";
  if (days === 0) return "รีบาลานซ์วันนี้";
  if (days === 1) return "รีบาลานซ์ล่าสุดเมื่อวานนี้";
  return `ผ่านมา ${days} วันนับจากรีบาลานซ์ครั้งล่าสุด`;
}

function scoreColor(score: number): string {
  if (score >= 2) return "text-green-600";
  if (score <= -2) return "text-red-600";
  return "text-gray-600";
}

function Spinner({ size = "sm" }: { size?: "sm" | "lg" }) {
  const cls = size === "lg"
    ? "w-8 h-8 border-4 border-blue-200 border-t-blue-600"
    : "w-3 h-3 border-2 border-white border-t-transparent";
  return <span className={`inline-block rounded-full animate-spin ${cls}`} />;
}

// ─── Execution warning badge ──────────────────────────────────────────────────

const EXEC_RISK_CLS: Record<ExecutionRisk, string> = {
  LOW:      "bg-gray-100 text-gray-500 border-gray-200",
  MEDIUM:   "bg-yellow-50 text-yellow-700 border-yellow-200",
  HIGH:     "bg-orange-50 text-orange-700 border-orange-200",
  CRITICAL: "bg-red-50 text-red-700 border-red-200",
};

function ExecutionWarningBadges({
  warnings,
  risk,
  slippage,
  capped,
}: {
  warnings: string[];
  risk: ExecutionRisk;
  slippage?: number;
  capped?: boolean;
}) {
  if (!warnings || warnings.length === 0) return null;
  const cls = EXEC_RISK_CLS[risk] ?? EXEC_RISK_CLS.MEDIUM;
  return (
    <span className="flex flex-wrap gap-1 mt-0.5">
      {warnings.map((w) => (
        <span key={w} className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${cls}`}>
          {w}
        </span>
      ))}
      {slippage != null && slippage >= 0.3 && (
        <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded border ${cls}`}>
          ~{slippage.toFixed(1)}% slip
        </span>
      )}
      {capped && (
        <span className="text-[10px] font-medium px-1.5 py-0.5 rounded border bg-purple-50 text-purple-700 border-purple-200">
          cap applied
        </span>
      )}
    </span>
  );
}

// ─── Reason context/facts builders (feed the shared ReasonCell) ──────────────
// Both tables switch to table-fixed at lg+ with narrow widths pinned on every
// other column, so Reason is the one column left unsized — it absorbs all
// remaining table width instead of sitting at a fixed max-width.
//
// `context` (collapsed line 2) and `facts` (expanded detail) are derived here
// from fields the backend already attaches by symbol lookup (ta_score, fa_score,
// pe_ratio, roe, timing_score — see _apply_score_context in agents/optimizer.py)
// rather than asked of the AI, per the "generate expanded detail from existing
// deterministic fields, not longer AI prose" rule.

function allocationReasonContext(a: TargetAllocation): string | undefined {
  if (a.action === "REDUCE") return `Trim to ${a.target_weight.toFixed(1)}%`;
  const chips: string[] = [];
  if (a.timing_score != null) chips.push(`TS${Math.round(a.timing_score)}`);
  if (a.fa_score != null) chips.push(`FA${Math.round(a.fa_score)}`);
  if (a.pe_ratio != null) chips.push(`PE${a.pe_ratio.toFixed(1)}`);
  return chips.length > 0 ? chips.join(" • ") : a.sector;
}

function allocationReasonFacts(a: TargetAllocation): ReasonFact[] {
  const facts: ReasonFact[] = [];
  if (a.timing_score != null) facts.push({ label: "Timing Score", value: a.timing_score.toFixed(0) });
  if (a.fa_score != null) facts.push({ label: "Fundamental Score", value: a.fa_score.toFixed(0) });
  if (a.ta_score != null) facts.push({ label: "Technical Score", value: a.ta_score.toFixed(0) });
  if (a.pe_ratio != null) facts.push({ label: "P/E", value: a.pe_ratio.toFixed(2) });
  if (a.roe != null) facts.push({ label: "ROE", value: `${a.roe.toFixed(1)}%` });
  if (a.sector) facts.push({ label: "Sector", value: a.sector });
  return facts;
}

function swapReasonContext(s: SwapSuggestion): string | undefined {
  const chips: string[] = [];
  if (s.timing_score != null) chips.push(`TS${Math.round(s.timing_score)}`);
  if (s.fa_score != null) chips.push(`FA${Math.round(s.fa_score)}`);
  if (s.pe_ratio != null) chips.push(`PE${s.pe_ratio.toFixed(1)}`);
  return chips.length > 0 ? chips.join(" • ") : s.sector;
}

function swapReasonFacts(s: SwapSuggestion): ReasonFact[] {
  const facts: ReasonFact[] = [];
  if (s.timing_score != null) facts.push({ label: "Timing Score", value: s.timing_score.toFixed(0) });
  if (s.fa_score != null) facts.push({ label: "Fundamental Score", value: s.fa_score.toFixed(0) });
  if (s.ta_score != null) facts.push({ label: "Technical Score", value: s.ta_score.toFixed(0) });
  if (s.pe_ratio != null) facts.push({ label: "P/E", value: s.pe_ratio.toFixed(2) });
  if (s.roe != null) facts.push({ label: "ROE", value: `${s.roe.toFixed(1)}%` });
  if (s.sector) facts.push({ label: "Sector", value: s.sector });
  return facts;
}

// ─── Allocation Table ─────────────────────────────────────────────────────────

function AllocationTable({
  allocations,
  totalValue,
  title,
}: {
  allocations: TargetAllocation[];
  totalValue?: number;
  title?: string;
}) {
  if (!allocations || allocations.length === 0) {
    return <p className="text-sm text-gray-500">No allocation changes proposed.</p>;
  }

  const ACTION_PRIORITY: Record<string, number> = { BUY: 0, ACCUMULATE: 1, WATCH: 2, HOLD: 3, REDUCE: 4, SELL: 5 };

  const significant = [...allocations.filter(
    (a) => a.action !== "HOLD" || Math.abs(a.allocation_change_percent) >= 2 || a.noise_suppressed
  )].sort((a, b) => (ACTION_PRIORITY[a.action] ?? 3) - (ACTION_PRIORITY[b.action] ?? 3));

  const hold = allocations.filter(
    (a) => a.action === "HOLD" && Math.abs(a.allocation_change_percent) < 2 && !a.noise_suppressed
  );

  // Build rows with optional "Opportunities" / "Risk Reduction" group headers
  const hasOpportunities = significant.some((a) => a.action === "BUY" || a.action === "ACCUMULATE");
  const hasReductions    = significant.some((a) => a.action === "REDUCE" || a.action === "SELL");
  const showGroups = hasOpportunities && hasReductions;

  type TableRow = { kind: "header"; label: string } | { kind: "row"; item: TargetAllocation };
  const tableRows: TableRow[] = [];
  let lastGroup: string | null = null;
  for (const a of significant) {
    const group = (a.action === "BUY" || a.action === "ACCUMULATE") ? "opportunity"
      : (a.action === "REDUCE" || a.action === "SELL") ? "reduction"
      : "other";
    if (showGroups && group !== lastGroup && (group === "opportunity" || group === "reduction")) {
      tableRows.push({ kind: "header", label: group === "opportunity" ? "Opportunities" : "Risk Reduction" });
      lastGroup = group;
    }
    tableRows.push({ kind: "row", item: a });
  }

  return (
    <div className="space-y-3">
      {title && <p className="text-xs font-medium text-gray-500">{title}</p>}
      <div className="overflow-x-auto">
        <table className="min-w-full text-xs lg:table-fixed">
          <thead>
            <tr className="border-b text-left text-gray-400">
              <th className="pb-1.5 pr-3 lg:w-32">Symbol</th>
              <th className="pb-1.5 pr-3 lg:w-24">AI Signal</th>
              <th className="pb-1.5 pr-2 text-right lg:w-12">Current%</th>
              <th className="pb-1.5 pr-2 text-right lg:w-12">Target%</th>
              <th className="pb-1.5 pr-2 text-right lg:w-14">Change%</th>
              {totalValue && totalValue > 0 && <th className="pb-1.5 pr-2 text-right lg:w-24">Cash Impact</th>}
              <th className="pb-1.5">Reason</th>
            </tr>
          </thead>
          <tbody>
            {tableRows.map((row, i) => {
              if (row.kind === "header") {
                return (
                  <tr key={`grp-${i}`}>
                    <td colSpan={totalValue && totalValue > 0 ? 7 : 6} className="pt-3 pb-0.5">
                      <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">{row.label}</span>
                    </td>
                  </tr>
                );
              }
              const a = row.item;
              const chg = a.allocation_change_percent;
              const chgCls = chg > 0 ? "text-green-600 font-semibold" : chg < 0 ? "text-red-500 font-semibold" : "text-gray-400";
              // Signed cash flow: positive = cash required (BUY/ACCUMULATE), negative = cash
              // released (REDUCE/SELL). Already computed once by the optimizer from
              // allocation_change_percent × total_value — reused as-is, not recalculated.
              const amt = a.estimated_amount;
              return (
                <tr key={a.symbol} className="border-b hover:bg-gray-50">
                  <td className="py-1.5 pr-3">
                    <div className="flex flex-col gap-0.5">
                      <Link href={`/stock/${encodeURIComponent(a.symbol)}`} className="text-blue-600 hover:underline font-medium">
                        {a.symbol.replace(".BK", "")}
                        {a.symbol.endsWith(".BK") && <span className="text-gray-400 ml-0.5">.BK</span>}
                      </Link>
                      {a.execution_warnings && a.execution_warnings.length > 0 && (
                        <ExecutionWarningBadges
                          warnings={a.execution_warnings}
                          risk={a.execution_risk ?? "LOW"}
                          slippage={a.slippage_est_pct}
                          capped={a.execution_capped}
                        />
                      )}
                    </div>
                  </td>
                  <td className="py-1.5 pr-3">
                    <div className="flex flex-col gap-0.5 items-start">
                      <SignalBadge signal={a.action} />
                      {a.within_drift_tolerance && (
                        <span
                          className="text-[10px] font-medium px-1.5 py-0.5 rounded border bg-gray-50 text-gray-500 border-gray-200"
                          title={
                            a.allocation_drift_pct != null
                              ? `${a.allocation_drift_pct.toFixed(1)}% drift — within tolerance, deferrable`
                              : "Within drift tolerance — deferrable"
                          }
                        >
                          Within tolerance
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="py-1.5 pr-2 text-right text-gray-500">{a.current_weight.toFixed(1)}%</td>
                  <td className="py-1.5 pr-2 text-right font-medium">{a.target_weight.toFixed(1)}%</td>
                  <td className={`py-1.5 pr-2 text-right ${chgCls}`}>
                    {chg >= 0 ? "+" : ""}{chg.toFixed(1)}%
                  </td>
                  {totalValue && totalValue > 0 && (
                    <td className="py-1.5 pr-2 text-right">
                      {isDeferred(a) ? (
                        <span className="text-gray-400 italic text-xs">No action today</span>
                      ) : amt === 0 ? (
                        <span className={chgCls}>—</span>
                      ) : amt > 0 ? (
                        <span className={chgCls}>฿{amt.toLocaleString("th-TH")} <span className="text-gray-400 font-normal">required</span></span>
                      ) : (
                        <span className={chgCls}>฿{Math.abs(amt).toLocaleString("th-TH")} <span className="text-gray-400 font-normal">released</span></span>
                      )}
                    </td>
                  )}
                  <ReasonCell
                    reason={a.noise_suppressed ? a.noise_reason : a.reason}
                    context={a.noise_suppressed ? undefined : allocationReasonContext(a)}
                    facts={a.noise_suppressed ? [] : allocationReasonFacts(a)}
                    italic={!!a.noise_suppressed}
                    action={a.action}
                  />
                </tr>
              );
            })}
            {hold.length > 0 && (
              <tr className="text-gray-400">
                <td colSpan={totalValue && totalValue > 0 ? 7 : 6} className="py-1.5 text-center text-xs italic">
                  + {hold.length} position{hold.length !== 1 ? "s" : ""} held unchanged
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Ranking Row ──────────────────────────────────────────────────────────────

const RISK_BADGE: Record<string, string> = {
  CRITICAL: "text-red-900 bg-red-100 border-red-400",
  HIGH:     "text-red-700 bg-red-50  border-red-300",
  MEDIUM:   "text-amber-700 bg-amber-50 border-amber-300",
  LOW:      "text-gray-600 bg-gray-50 border-gray-200",
};

function RankingRow({
  item, totalValue, riskMap,
}: {
  item: WatchlistRanking;
  totalValue: number;
  riskMap: Record<string, string>;
}) {
  const display = item.symbol.replace(".BK", "");
  const thb = totalValue > 0 ? Math.round(totalValue * item.suggested_allocation_pct / 100) : null;
  const upside = item.upside_pct;
  const riskLevel = riskMap[item.symbol];
  return (
    <tr className="border-b hover:bg-gray-50">
      <td className="py-2 pl-4 pr-3 text-center text-sm font-bold text-gray-400">{item.rank}</td>
      <td className="py-2 pr-3">
        <Link href={`/stock/${encodeURIComponent(item.symbol)}`} className="text-blue-600 hover:underline font-medium text-sm">
          {display}{item.symbol.endsWith(".BK") && <span className="ml-0.5 text-xs text-gray-400">.BK</span>}
        </Link>
      </td>
      <td className="py-2 pr-3"><SignalBadge signal={item.signal} /></td>
      <td className={`py-2 pr-3 text-sm font-semibold ${scoreColor(item.combined_score)}`}>
        {item.combined_score >= 0 ? "+" : ""}{item.combined_score.toFixed(1)}
      </td>
      <td className="py-2 pr-3 text-xs text-gray-500 hidden sm:table-cell">{item.sector}</td>
      <td className="py-2 pr-3 text-sm font-medium text-blue-700">{item.suggested_allocation_pct.toFixed(1)}%</td>
      {thb !== null && <td className="py-2 pr-3 text-sm text-gray-700">฿{thb.toLocaleString("th-TH")}</td>}
      <td className="py-2 pr-3 text-sm font-medium">
        {upside == null
          ? <span className="text-gray-400 text-xs">N/A</span>
          : <span className={upside >= 0 ? "text-green-600" : "text-red-500"}>
              {upside >= 0 ? "+" : ""}{upside.toFixed(1)}%
            </span>
        }
      </td>
      <td className="py-2 pr-3">
        {riskLevel
          ? <span className={`text-xs font-semibold px-1.5 py-0.5 rounded border ${RISK_BADGE[riskLevel] ?? RISK_BADGE.LOW}`}>{riskLevel}</span>
          : <span className="text-gray-300 text-xs">—</span>
        }
      </td>
      <td className="py-2 text-xs text-gray-400 hidden lg:table-cell">{item.reasoning}</td>
    </tr>
  );
}

// ─── Swap Table (Layer 1 output) ──────────────────────────────────────────────

const SWAP_TYPE_CLS: Record<string, string> = {
  SWAP:   "bg-blue-100 text-blue-800 border-blue-200",
  SELL:   "bg-red-100 text-red-700 border-red-200",
  REDUCE: "bg-amber-100 text-amber-800 border-amber-200",
};

function SwapTable({ swaps }: { swaps: SwapSuggestion[] }) {
  if (!swaps || swaps.length === 0) {
    return <p className="text-sm text-gray-500">No changes met the conviction bar this cycle.</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-xs lg:table-fixed">
        <thead>
          <tr className="border-b text-left text-gray-400">
            <th className="pb-1.5 pr-3 lg:w-20">Type</th>
            <th className="pb-1.5 pr-3 lg:w-24">Sell</th>
            <th className="pb-1.5 pr-3 lg:w-24">Buy</th>
            <th className="pb-1.5 pr-3 text-right lg:w-16">Score Δ</th>
            <th className="pb-1.5">Reason</th>
          </tr>
        </thead>
        <tbody>
          {swaps.map((s, i) => {
            const typeCls = SWAP_TYPE_CLS[s.type] ?? SWAP_TYPE_CLS.SWAP;
            const delta = s.score_improvement ?? 0;
            return (
              <tr key={i} className="border-b hover:bg-gray-50">
                <td className="py-1.5 pr-3">
                  <span className={`text-xs font-semibold px-2 py-0.5 rounded border ${typeCls}`}>{s.type}</span>
                </td>
                <td className="py-1.5 pr-3">
                  {s.sell_symbol
                    ? <Link href={`/stock/${encodeURIComponent(s.sell_symbol)}`} className="text-red-600 hover:underline font-medium">
                        {s.sell_symbol.replace(".BK", "")}{s.sell_symbol.endsWith(".BK") && <span className="text-gray-400 ml-0.5">.BK</span>}
                      </Link>
                    : <span className="text-gray-300">—</span>
                  }
                </td>
                <td className="py-1.5 pr-3">
                  {s.buy_symbol
                    ? <Link href={`/stock/${encodeURIComponent(s.buy_symbol)}`} className="text-green-600 hover:underline font-medium">
                        {s.buy_symbol.replace(".BK", "")}{s.buy_symbol.endsWith(".BK") && <span className="text-gray-400 ml-0.5">.BK</span>}
                      </Link>
                    : <span className="text-gray-300">—</span>
                  }
                </td>
                <td className={`py-1.5 pr-3 text-right font-semibold ${delta >= 0 ? "text-green-600" : "text-red-500"}`}>
                  {delta >= 0 ? "+" : ""}{delta.toFixed(1)}
                </td>
                <ReasonCell reason={s.reason} context={swapReasonContext(s)} facts={swapReasonFacts(s)} action={s.type} />
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

// ─── Layer sections ───────────────────────────────────────────────────────────

const RISK_CLS: Record<string, string> = {
  CRITICAL: "text-red-900   bg-red-100   border-red-500",
  HIGH:     "text-red-700   bg-red-50    border-red-300",
  MEDIUM:   "text-amber-700 bg-amber-50  border-amber-300",
  LOW:      "text-gray-600  bg-gray-50   border-gray-200",
};

const RISK_DOT: Record<string, string> = {
  CRITICAL: "bg-red-600", HIGH: "bg-red-400", MEDIUM: "bg-amber-400", LOW: "bg-gray-400",
};

const SEVERITY_ORDER: Record<string, number> = {
  CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3,
};

function RiskFlagPill({ flag }: { flag: RiskFlag }) {
  const key = flag.severity?.toUpperCase() as keyof typeof RISK_CLS;
  const cls = RISK_CLS[key] ?? RISK_CLS.LOW;
  const dot = RISK_DOT[key] ?? RISK_DOT.LOW;
  return (
    <div className={`flex items-start gap-2 border rounded-lg px-3 py-2 text-xs ${cls}`}>
      <span className={`mt-0.5 shrink-0 w-2 h-2 rounded-full ${dot}`} />
      <div>
        <span className="font-bold mr-1.5">[{key}]</span>
        <span className="font-semibold mr-1">{flag.symbol}</span>
        {flag.issue}
      </div>
    </div>
  );
}


// ─── NO_ACTION display helpers ────────────────────────────────────────────────
// NO_ACTION_REASON_LABELS moved to lib/executionPlan.ts (shared with ExecutionPlanCard).

const BLOCKED_REASON_LABELS: Record<string, string> = {
  sector_limit_exceeded: "Sector limit exceeded",
  insufficient_cash:     "Insufficient cash balance",
  portfolio_count_cap:   "Portfolio stock count cap reached",
};

function scoreZone(s: number): { label: string; fill: string; text: string } {
  if (s <= 20) return { label: "Very Low", fill: "bg-red-500", text: "text-red-700" };
  if (s <= 40) return { label: "Low", fill: "bg-amber-500", text: "text-amber-700" };
  if (s <= 70) return { label: "Moderate", fill: "bg-blue-500", text: "text-blue-700" };
  return { label: "High", fill: "bg-green-500", text: "text-green-700" };
}

function OpportunityScoreGauge({ score }: { score: number }) {
  const s = Math.max(0, Math.min(100, score));
  const { label, fill, text } = scoreZone(s);
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-gray-500 font-medium">Final Consensus Score</span>
        <span className={`font-bold text-sm ${text}`}>
          {s}<span className="text-xs font-normal text-gray-400"> / 100</span>
        </span>
      </div>
      <div className="relative h-3 bg-gray-100 rounded-full overflow-hidden">
        <div className="absolute inset-y-0 left-[20%] w-px bg-white/60 z-10" />
        <div className="absolute inset-y-0 left-[40%] w-px bg-white/60 z-10" />
        <div className="absolute inset-y-0 left-[70%] w-px bg-white/60 z-10" />
        <div className={`h-full rounded-full transition-all duration-500 ${fill}`} style={{ width: `${s}%` }} />
      </div>
      <div className="flex items-center justify-between text-xs">
        <span className="text-gray-400">0</span>
        <span className={`font-semibold ${text}`}>{label}</span>
        <span className="text-gray-400">100</span>
      </div>
    </div>
  );
}

function NoActionCard({ result }: { result: OptimizerResult }) {
  const score  = getFinalConsensusScore(result) ?? 0;
  const reason = result.no_action_reason ?? null;
  const summary = result.no_action_summary ?? null;
  const blocked: BlockedOpportunity[] = result.blocked_opportunities ?? [];

  return (
    <section className="bg-gradient-to-br from-green-50 to-teal-50 border border-green-200 rounded-xl p-6 shadow-sm space-y-5">
      {/* Header */}
      <div className="flex items-start gap-4">
        <div className="shrink-0 w-12 h-12 rounded-full bg-green-100 border-2 border-green-300 flex items-center justify-center text-xl font-bold text-green-700">
          ✓
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="text-lg font-bold text-green-900">Portfolio is Well-Balanced</h3>
            {reason && (
              <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-green-100 border border-green-300 text-green-700">
                {NO_ACTION_REASON_LABELS[reason] ?? reason}
              </span>
            )}
          </div>
          {summary && (
            <p className="text-sm text-green-800 mt-1.5 leading-relaxed">{summary}</p>
          )}
        </div>
      </div>

      {/* Score gauge */}
      <div className="bg-white/70 rounded-xl border border-green-100 px-5 py-4">
        <OpportunityScoreGauge score={score} />
      </div>

      {/* Blocked opportunities */}
      {blocked.length > 0 && (
        <div className="space-y-2">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
            Evaluated but blocked by constraints
          </p>
          <div className="space-y-1.5">
            {blocked.map((b, i) => {
              const sym = b.symbol.replace(".BK", "");
              const reasonLabel = BLOCKED_REASON_LABELS[b.reason] ?? b.reason.replace(/_/g, " ");
              return (
                <div key={i} className="flex items-center gap-2.5 bg-white/60 border border-green-100 rounded-lg px-3 py-2 flex-wrap">
                  <Link
                    href={`/stock/${encodeURIComponent(b.symbol)}`}
                    className="text-sm font-semibold text-blue-600 hover:underline shrink-0"
                  >
                    {sym}{b.symbol.endsWith(".BK") && <span className="text-xs text-gray-400 ml-0.5">.BK</span>}
                  </Link>
                  {b.signal && <SignalBadge signal={b.signal} />}
                  <span className="text-xs text-gray-500 shrink-0">—</span>
                  <span className="text-xs text-gray-600">{reasonLabel}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
}

// ─── Stabilization Status Badges ─────────────────────────────────────────────

const STABILIZATION_STATUS_CFG: Record<OptimizerStatus, {
  label: string; icon: string;
  section: string; badge: string; text: string;
}> = {
  REBALANCE:              { label: "Portfolio Drift",        icon: "⚡", section: "bg-orange-50 border-orange-200",  badge: "bg-orange-100 border-orange-300 text-orange-800", text: "text-orange-800" },
  REBALANCE_REQUIRED:     { label: "Portfolio Drift",        icon: "⚡", section: "bg-orange-50 border-orange-200",  badge: "bg-orange-100 border-orange-300 text-orange-800", text: "text-orange-800" },
  NO_ACTION:              { label: "No Action Needed",       icon: "✓",  section: "bg-green-50 border-green-200",    badge: "bg-green-100 border-green-300 text-green-800",   text: "text-green-800" },
  NO_REBALANCE_REQUIRED:  { label: "Portfolio Drift",        icon: "✓",  section: "bg-green-50 border-green-200",    badge: "bg-green-100 border-green-300 text-green-800",   text: "text-green-800" },
  OPTIMAL:                { label: "Portfolio Optimal",      icon: "✓",  section: "bg-teal-50 border-teal-200",      badge: "bg-teal-100 border-teal-300 text-teal-800",      text: "text-teal-800" },
  COOLDOWN_ACTIVE:        { label: "Cooldown Active",        icon: "⏸",  section: "bg-blue-50 border-blue-200",     badge: "bg-blue-100 border-blue-300 text-blue-800",      text: "text-blue-800" },
};

const OVERRIDE_REASON_LABELS: Record<string, string> = {
  REGIME_CHANGE:               "Market Regime Changed",
  SECTOR_CONCENTRATION_BREACH: "Sector Concentration Breach",
  SINGLE_POSITION_BREACH:      "Single Position Breach",
  RISK_POLICY_VIOLATION:       "Risk Policy Violation",
  DRAWDOWN_EVENT:              "Drawdown / Emergency Event",
  CONFIDENCE_COLLAPSE:         "Confidence Collapse",
  MANUAL_OVERRIDE:             "Manual Override Requested",
};

function StabilizationStatusBadge({ status }: { status: OptimizerStatus }) {
  const cfg = STABILIZATION_STATUS_CFG[status] ?? STABILIZATION_STATUS_CFG.REBALANCE;
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full border ${cfg.badge}`}>
      <span>{cfg.icon}</span>
      {cfg.label}
    </span>
  );
}

function StabilizationCard({
  meta,
  onForceRebalance,
  forceRunning,
}: {
  meta: StabilizationMeta;
  onForceRebalance: () => void;
  forceRunning: boolean;
}) {
  const status = meta.status as OptimizerStatus;
  const cfg = STABILIZATION_STATUS_CFG[status] ?? STABILIZATION_STATUS_CFG.REBALANCE;
  const isBlocked = status === "NO_REBALANCE_REQUIRED" || status === "OPTIMAL" || status === "COOLDOWN_ACTIVE";
  const cooldown = meta.cooldown;
  const impact = meta.minimum_impact;

  return (
    <section className={`border rounded-xl p-5 shadow-sm space-y-4 ${cfg.section}`}>
      {/* Header */}
      <div className="flex items-start gap-3 flex-wrap">
        <div className={`shrink-0 w-10 h-10 rounded-full flex items-center justify-center text-lg font-bold border-2 ${
          isBlocked ? "bg-green-100 border-green-300 text-green-700" : "bg-orange-100 border-orange-300 text-orange-700"
        }`}>
          {cfg.icon}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className={`font-bold text-base ${cfg.text}`}>{cfg.label}</h3>
            <StabilizationStatusBadge status={status} />
          </div>
          <p className="text-xs text-gray-400 mt-0.5">
            How far each position has drifted from its optimizer target, and whether that's enough to justify trading today.
          </p>
          {meta.reason && (
            <p className={`text-sm mt-1 leading-relaxed ${cfg.text} opacity-80`}>{meta.reason}</p>
          )}
        </div>
        {isBlocked && (
          <button
            onClick={onForceRebalance}
            disabled={forceRunning}
            className="shrink-0 text-xs font-medium px-3 py-1.5 rounded border border-gray-300 bg-white text-gray-600 hover:bg-gray-50 disabled:opacity-50 self-start"
          >
            {forceRunning ? "Running…" : "Force Rebalance"}
          </button>
        )}
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
        <div className="bg-white/70 rounded-lg p-3">
          <p className="text-xs text-gray-400 mb-0.5">Drift Threshold</p>
          <p className="text-sm font-bold text-gray-700">{meta.drift_threshold_pct.toFixed(0)}%</p>
        </div>
        <div className="bg-white/70 rounded-lg p-3">
          <p className="text-xs text-gray-400 mb-0.5">Within Tolerance</p>
          <p className="text-sm font-bold text-green-700">{meta.positions_within_tolerance} / {meta.positions_within_tolerance + meta.positions_needing_action}</p>
        </div>
        {impact && (
          <>
            <div className="bg-white/70 rounded-lg p-3">
              <p className="text-xs text-gray-400 mb-0.5">Est. Net Benefit</p>
              <p className={`text-sm font-bold ${impact.net_benefit_pct >= impact.threshold_pct ? "text-green-700" : "text-red-600"}`}>
                {impact.net_benefit_pct >= 0 ? "+" : ""}{impact.net_benefit_pct.toFixed(3)}%
              </p>
            </div>
            <div className="bg-white/70 rounded-lg p-3">
              <p className="text-xs text-gray-400 mb-0.5">Est. Turnover</p>
              <p className="text-sm font-bold text-gray-700">{impact.total_turnover_pct.toFixed(1)}%</p>
            </div>
          </>
        )}
      </div>

      {/* Cooldown progress */}
      {cooldown && (
        <div className="bg-white/70 rounded-lg px-4 py-3 space-y-2">
          <div className="flex items-center justify-between text-xs">
            <span className="font-medium text-gray-600">
              {cooldown.active && !cooldown.overridden
                ? `Cooldown: ${cooldown.days_remaining} / ${cooldown.cooldown_days} day(s) remaining`
                : cooldown.overridden
                ? "Cooldown bypassed"
                : cooldown.last_rebalance_at
                ? `Last rebalance ${cooldown.days_elapsed}d ago — cooldown cleared`
                : "No prior rebalance recorded"}
            </span>
            {cooldown.overridden && (
              <span className="text-amber-600 font-semibold">Override active</span>
            )}
          </div>
          {cooldown.active && !cooldown.overridden && (
            <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-400 rounded-full transition-all"
                style={{ width: `${Math.min(100, (cooldown.days_elapsed / cooldown.cooldown_days) * 100)}%` }}
              />
            </div>
          )}
          {cooldown.override_reasons.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {cooldown.override_reasons.map((r) => (
                <span key={r} className="text-[10px] font-medium px-1.5 py-0.5 rounded border bg-amber-50 border-amber-200 text-amber-700">
                  {OVERRIDE_REASON_LABELS[r] ?? r}
                </span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Impact breakdown */}
      {impact && (
        <div className="bg-white/70 rounded-lg px-4 py-3">
          <p className="text-xs font-semibold text-gray-500 mb-2">Cost-Benefit Analysis</p>
          <div className="grid grid-cols-3 gap-2 text-center text-xs">
            <div>
              <p className="text-gray-400">Expected Gain</p>
              <p className="font-bold text-green-700">+{impact.expected_improvement_pct.toFixed(3)}%</p>
            </div>
            <div>
              <p className="text-gray-400">Trading Cost</p>
              <p className="font-bold text-red-600">−{impact.estimated_cost_pct.toFixed(4)}%</p>
            </div>
            <div>
              <p className="text-gray-400">Net Benefit</p>
              <p className={`font-bold ${impact.passes_threshold ? "text-green-700" : "text-red-600"}`}>
                {impact.net_benefit_pct >= 0 ? "+" : ""}{impact.net_benefit_pct.toFixed(3)}%
                <span className="ml-1 text-gray-400 font-normal">(min {impact.threshold_pct.toFixed(2)}%)</span>
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Drift table (compact) */}
      {meta.drift_analysis.length > 0 && (
        <details className="bg-white/70 rounded-lg px-4 py-3">
          <summary className="text-xs font-semibold text-gray-500 cursor-pointer">
            Drift Analysis — {meta.positions_within_tolerance} positions within tolerance, {meta.positions_needing_action} positions exceed drift threshold
          </summary>
          <div className="mt-2 overflow-x-auto">
            <table className="min-w-full text-xs">
              <thead>
                <tr className="text-gray-400 text-left">
                  <th className="py-1 pr-4">Symbol</th>
                  <th className="py-1 pr-4">Current</th>
                  <th className="py-1 pr-4">Target</th>
                  <th className="py-1 pr-4">Drift</th>
                  <th className="py-1">Status</th>
                </tr>
              </thead>
              <tbody>
                {meta.drift_analysis.map((d) => (
                  <tr key={d.symbol} className="border-t border-gray-100">
                    <td className="py-1 pr-4 font-semibold text-gray-700">{d.symbol.replace(".BK","")}</td>
                    <td className="py-1 pr-4 text-gray-600">{d.current_weight.toFixed(1)}%</td>
                    <td className="py-1 pr-4 text-gray-600">{d.target_weight.toFixed(1)}%</td>
                    <td className="py-1 pr-4 font-medium text-gray-700">{d.allocation_drift.toFixed(1)}%</td>
                    <td className="py-1">
                      {d.within_tolerance
                        ? <span className="text-green-600 font-semibold">Within tolerance</span>
                        : <span className="text-amber-600 font-semibold">Needs action</span>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      )}
    </section>
  );
}

function Layer1Section({
  layer,
  totalValue,
}: {
  layer: OptimizerResult["layer1_result"];
  totalValue?: number;
}) {
  if (!layer) return null;
  const swaps: SwapSuggestion[] = layer.swap_suggestions ?? [];
  const topBuys: string[] = (layer as Record<string, unknown>).top_buys as string[] ?? [];
  const sectorFlags: string[] = (layer as Record<string, unknown>).sector_flags as string[] ?? [];
  const allocations: TargetAllocation[] = layer.target_allocations ?? [];

  return (
    <section className="bg-white border rounded-xl p-5 shadow-sm space-y-4">
      <div className="flex items-center gap-2 flex-wrap">
        <div>
          <h3 className="font-semibold text-gray-800">🟠 {layer.name ?? "Strategist"}</h3>
          <p className="text-xs text-orange-600 mt-0.5">Stability Review</p>
        </div>
        <AIBadge provider={layer.provider} model={layer.model} label="" />
      </div>

      {layer.error ? (
        <p className="text-xs text-red-500">{layer.error}</p>
      ) : (
        <>
          {layer.summary && (
            <div className="bg-orange-50 border border-orange-200 rounded-lg px-4 py-2">
              <p className="text-sm text-orange-900">{layer.summary}</p>
            </div>
          )}

          {(allocations.length > 0 || swaps.length > 0) && (
            <p className="text-xs text-gray-400 font-medium">
              {(allocations.length || swaps.length) === 1 ? "Recommendation" : "Recommendations"}
            </p>
          )}

          {allocations.length > 0 ? (
            <AllocationTable allocations={allocations} totalValue={totalValue} />
          ) : (
            <SwapTable swaps={swaps} />
          )}

          {allocations.length > 0 && swaps.length > 0 && (
            <details>
              <summary className="text-xs font-medium text-gray-400 cursor-pointer hover:text-gray-600 select-none">
                Swap proposals ({swaps.length})
              </summary>
              <div className="mt-2">
                <SwapTable swaps={swaps} />
              </div>
            </details>
          )}

          {topBuys.length > 0 && (
            <div>
              <p className="text-xs text-gray-400 font-medium mb-1">Top Watchlist</p>
              <div className="flex items-center gap-2 flex-wrap">
                {topBuys.map((sym) => (
                  <Link key={sym} href={`/stock/${encodeURIComponent(sym)}`}
                    className="text-xs font-semibold text-green-700 bg-green-50 border border-green-200 px-2 py-0.5 rounded hover:bg-green-100">
                    {sym.replace(".BK", "")}{sym.endsWith(".BK") ? <span className="text-gray-400">.BK</span> : ""}
                  </Link>
                ))}
              </div>
            </div>
          )}

          {sectorFlags.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs text-gray-400 font-medium">Sector flags:</span>
              {sectorFlags.map((f, i) => (
                <span key={i} className="text-xs bg-amber-50 border border-amber-200 text-amber-800 px-2 py-0.5 rounded">{f}</span>
              ))}
            </div>
          )}
        </>
      )}
    </section>
  );
}

function Layer2Section({
  layer, totalValue,
}: {
  layer: Layer2Result | null | undefined;
  totalValue?: number;
}) {
  if (!layer) return null;
  const agrees = layer.agrees_with_layer1;
  const disagreements = layer.disagreements ?? [];
  const allocations = layer.target_allocations ?? [];

  return (
    <section className={`border rounded-xl p-5 shadow-sm space-y-3 ${agrees ? "bg-green-50 border-green-200" : "bg-amber-50 border-amber-200"}`}>
      <div className="flex items-center gap-2 flex-wrap">
        <div>
          <h3 className="font-semibold text-gray-800">🔵 {layer.name ?? "Challenger"}</h3>
          <p className="text-xs text-blue-600 mt-0.5">{agrees ? "Confirms Strategist" : "Alternative Allocation"}</p>
        </div>
        <AIBadge provider={layer.provider} model={layer.model} label="" />
        <span className={`text-xs font-medium px-2 py-0.5 rounded-full border ml-auto ${agrees ? "bg-green-100 border-green-300 text-green-700" : "bg-amber-100 border-amber-300 text-amber-700"}`}>
          {agrees ? "✓ Agrees" : "⚠ Disagrees"}
        </span>
      </div>

      {!agrees && !layer.error && disagreements.length > 0 && (
        <div className="bg-yellow-50 border border-yellow-300 rounded-lg px-4 py-3 space-y-1.5">
          <p className="text-xs font-bold text-yellow-800 flex items-center gap-1.5">
            <span>⚠</span> Challenger disagrees with Strategist
          </p>
          <ul className="space-y-1">
            {disagreements.map((d, i) => (
              <li key={i} className="flex items-start gap-1.5 text-xs text-yellow-800">
                <span className="mt-0.5 shrink-0">•</span>
                <span>{d}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {layer.error ? (
        <p className="text-xs text-red-500">{layer.error}</p>
      ) : (
        <>
          {allocations.length === 0 ? (
            <div className="bg-white/70 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
              {agrees ? "Challenger confirms the Strategist plan." : "No alternative allocations provided."}
            </div>
          ) : (
            <AllocationTable allocations={allocations} totalValue={totalValue} />
          )}

          {agrees && layer.summary && (
            <p className="text-sm text-green-700">{layer.summary}</p>
          )}
        </>
      )}
    </section>
  );
}

function Layer3Section({ layer }: { layer: Layer3Result | null | undefined }) {
  if (!layer) return null;
  const flags = [...(layer.risk_flags ?? [])].sort(
    (a, b) => (SEVERITY_ORDER[a.severity?.toUpperCase()] ?? 99) - (SEVERITY_ORDER[b.severity?.toUpperCase()] ?? 99)
  );
  const risk = layer.final_risk_level ?? "medium";
  const riskColor = risk === "high" ? "text-red-600" : risk === "low" ? "text-green-600" : "text-amber-600";
  return (
    <section className="bg-white border rounded-xl p-5 shadow-sm space-y-3">
      <div className="flex items-center gap-2 flex-wrap">
        <div>
          <h3 className="font-semibold text-gray-800">🟣 {layer.name ?? "Risk Auditor"}</h3>
          <p className="text-xs text-purple-600 mt-0.5">
            {layer.safer_choice === "neither" ? "Caution — Review Manually" : risk === "high" ? "Defensive" : risk === "low" ? "Low Risk Confirmed" : "Moderate Risk Profile"}
          </p>
        </div>
        <AIBadge provider={layer.provider} model={layer.model} label="" />
        <span className={`text-xs font-semibold ml-auto ${riskColor}`}>
          Risk: {risk.toUpperCase()}
        </span>
      </div>
      {layer.error ? (
        <p className="text-xs text-red-500">{layer.error}</p>
      ) : (
        <>
          {flags.length === 0 ? (
            <p className="text-sm text-green-600">No risk flags identified.</p>
          ) : (
            <div className="space-y-1.5">
              {flags.map((f, i) => <RiskFlagPill key={i} flag={f} />)}
            </div>
          )}
          {layer.auditor_notes && (
            <p className="text-xs text-gray-500 border-t pt-2">{layer.auditor_notes}</p>
          )}
        </>
      )}
    </section>
  );
}

// ─── Sector Impact ────────────────────────────────────────────────────────────

function SectorImpactSection({ warnings }: { warnings: SectorWarning[] }) {
  const visible = warnings.filter((w) => w.current_pct > 0 || w.projected_pct > 0);
  if (visible.length === 0) return null;

  return (
    <section className="bg-white border rounded-xl p-5 shadow-sm space-y-4">
      <div>
        <h3 className="font-semibold text-gray-800">Sector Impact</h3>
        <p className="text-xs text-gray-500 mt-0.5">
          Before/after applying proposed allocation. Bars show % of sector limit used.
        </p>
      </div>
      <div className="space-y-4">
        {visible.map((w) => {
          const statusCls =
            w.status === "EXCEEDS"
              ? "text-red-600 bg-red-50 border-red-300"
              : w.status === "WARNING"
              ? "text-amber-600 bg-amber-50 border-amber-300"
              : "text-green-700 bg-green-50 border-green-200";
          const barAfterColor =
            w.status === "EXCEEDS" ? "bg-red-500" : w.status === "WARNING" ? "bg-amber-400" : "bg-green-500";
          const beforeFill = w.limit_pct > 0 ? Math.min(100, (w.current_pct / w.limit_pct) * 100) : 0;
          const afterFill  = w.limit_pct > 0 ? Math.min(100, (w.projected_pct / w.limit_pct) * 100) : 0;
          const changed = w.current_pct !== w.projected_pct;

          return (
            <div key={w.sector} className="flex items-start gap-3">
              <div className="w-24 shrink-0 pt-0.5">
                <span className="text-sm font-medium text-gray-700">{w.sector}</span>
              </div>
              <div className="flex-1 space-y-1.5">
                <div className="flex items-center gap-2">
                  <span className="text-xs text-gray-400 w-10 text-right shrink-0">{w.current_pct.toFixed(1)}%</span>
                  <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-2 bg-gray-300 rounded-full" style={{ width: `${beforeFill}%` }} />
                  </div>
                  <span className="text-xs text-gray-400 w-6 shrink-0">now</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-medium w-10 text-right shrink-0 ${changed ? "text-gray-800" : "text-gray-400"}`}>
                    {w.projected_pct.toFixed(1)}%
                  </span>
                  <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden relative">
                    <div className={`h-2 rounded-full ${barAfterColor}`} style={{ width: `${afterFill}%` }} />
                    <div className="absolute inset-y-0 border-l-2 border-dashed border-amber-400 opacity-60" style={{ left: "80%" }} />
                  </div>
                  <span className="text-xs text-gray-400 w-6 shrink-0">est</span>
                </div>
              </div>
              <div className="shrink-0 flex flex-col items-end gap-1 pt-0.5">
                <span className={`text-xs font-semibold px-1.5 py-0.5 rounded border ${statusCls}`}>{w.status}</span>
                <span className="text-xs text-gray-400">lim {w.limit_pct}%</span>
              </div>
            </div>
          );
        })}
      </div>
      <p className="text-xs text-gray-400 flex items-center gap-4">
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-4 h-1.5 bg-gray-300 rounded" /> Now
        </span>
        <span className="flex items-center gap-1.5">
          <span className="inline-block w-4 h-1.5 bg-green-500 rounded" /> After rebalance
        </span>
        <span className="flex items-center gap-1.5 text-amber-500">
          <span className="inline-block w-0 h-3 border-l-2 border-dashed border-amber-400" /> 80% threshold
        </span>
      </p>
    </section>
  );
}

const CONSENSUS_TYPE_CFG: Record<ConsensusType, {
  label: string; icon: string;
  section: string; border: string; badge: string; badgeText: string;
  bar: string; summary: string; summaryText: string;
}> = {
  STRONG_CONSENSUS:    { label: "Strong Consensus",    icon: "✓✓", section: "bg-green-50 border-green-300",   border: "border-green-300",   badge: "bg-green-100 border-green-300 text-green-800",   badgeText: "text-green-800", bar: "bg-green-500",  summary: "bg-green-100 border-green-200",   summaryText: "text-green-900" },
  REFINED_CONSENSUS:   { label: "Refined Consensus",   icon: "✓~", section: "bg-blue-50 border-blue-300",     border: "border-blue-300",    badge: "bg-blue-100 border-blue-300 text-blue-800",      badgeText: "text-blue-800",  bar: "bg-blue-500",   summary: "bg-blue-50 border-blue-200",     summaryText: "text-blue-900" },
  PARTIAL_CONSENSUS:   { label: "Partial Consensus",   icon: "~",  section: "bg-amber-50 border-amber-300",   border: "border-amber-300",   badge: "bg-amber-100 border-amber-300 text-amber-800",   badgeText: "text-amber-800", bar: "bg-amber-400",  summary: "bg-amber-50 border-amber-200",   summaryText: "text-amber-900" },
  WEAK_CONSENSUS:      { label: "Weak Consensus",      icon: "?",  section: "bg-gray-50 border-gray-300",     border: "border-gray-300",    badge: "bg-gray-100 border-gray-300 text-gray-700",      badgeText: "text-gray-700",  bar: "bg-gray-400",   summary: "bg-gray-100 border-gray-200",    summaryText: "text-gray-800" },
  RISK_CONFLICT:       { label: "Risk Conflict",       icon: "⚠",  section: "bg-orange-50 border-orange-400", border: "border-orange-400",  badge: "bg-orange-100 border-orange-400 text-orange-800",badgeText: "text-orange-800",bar: "bg-orange-500", summary: "bg-orange-50 border-orange-300", summaryText: "text-orange-900" },
  STRATEGIC_CONFLICT:  { label: "Strategic Conflict",  icon: "✗",  section: "bg-red-50 border-red-400",       border: "border-red-400",     badge: "bg-red-100 border-red-400 text-red-800",         badgeText: "text-red-800",   bar: "bg-red-500",    summary: "bg-red-50 border-red-300",       summaryText: "text-red-900" },
  NO_ACTION_CONSENSUS:    { label: "No Action Consensus",    icon: "✓",  section: "bg-teal-50 border-teal-300",  border: "border-teal-300",  badge: "bg-teal-100 border-teal-300 text-teal-800",  badgeText: "text-teal-800",  bar: "bg-teal-500",  summary: "bg-teal-50 border-teal-200",  summaryText: "text-teal-900" },
  NO_REBALANCE_CONSENSUS: { label: "No Rebalance Needed",    icon: "✓",  section: "bg-teal-50 border-teal-300",  border: "border-teal-300",  badge: "bg-teal-100 border-teal-300 text-teal-800",  badgeText: "text-teal-800",  bar: "bg-teal-500",  summary: "bg-teal-50 border-teal-200",  summaryText: "text-teal-900" },
};

const RISK_COLOR: Record<string, string> = {
  low: "text-green-600", medium: "text-amber-600", high: "text-red-600",
};
const CONF_COLOR: Record<string, string> = {
  high: "text-green-600", medium: "text-amber-600", low: "text-red-500",
};

function AlignmentBar({ label, score, barColor }: { label: string; score: number; barColor: string }) {
  const s = Math.max(0, Math.min(100, score));
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-gray-500">{label}</span>
        <span className="font-semibold text-gray-700">{s}</span>
      </div>
      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${barColor}`} style={{ width: `${s}%` }} />
      </div>
    </div>
  );
}

function ConsensusSection({ consensus }: { consensus: OptimizerConsensus }) {
  const ct = consensus.consensus_type;

  // Legacy path: old history rows without consensus_type
  if (!ct) {
    const isNoAction = consensus.consensus_decision === "NO_ACTION" || consensus.recommended === "no_action";
    const followLabel =
      consensus.recommended === "no_action" ? "Stable"
      : consensus.recommended === "layer1"  ? "Strategist"
      : consensus.recommended === "layer2"  ? "Challenger"
      : "Review";
    return (
      <section className={`border-2 rounded-xl p-5 shadow-sm space-y-3 ${isNoAction ? "bg-green-50 border-green-300" : "bg-white border-blue-200"}`}>
        <div className="flex items-center gap-2 flex-wrap">
          <h3 className="font-semibold text-gray-800">Consensus Engine</h3>
          <span className={`text-xs font-bold px-2.5 py-0.5 rounded-full border ${isNoAction ? "bg-green-100 border-green-300 text-green-700" : "bg-blue-100 border-blue-200 text-blue-700"}`}>
            {isNoAction ? "No Action" : "Rebalance"}
          </span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
          <div className="bg-white/70 rounded-lg p-3">
            <p className="text-xs text-gray-500 mb-1">L1 vs L2</p>
            <p className={`text-sm font-semibold ${consensus.agrees ? "text-green-600" : "text-amber-600"}`}>
              {consensus.agrees ? "✓ Agree" : "⚠ Disagree"}
            </p>
          </div>
          <div className="bg-white/70 rounded-lg p-3">
            <p className="text-xs text-gray-500 mb-1">Risk Level</p>
            <p className={`text-sm font-semibold ${RISK_COLOR[consensus.final_risk_level ?? "medium"] ?? ""}`}>
              {(consensus.final_risk_level ?? "medium").toUpperCase()}
            </p>
          </div>
          <div className="bg-white/70 rounded-lg p-3">
            <p className="text-xs text-gray-500 mb-1">Confidence</p>
            <p className={`text-sm font-semibold ${CONF_COLOR[consensus.confidence] ?? ""}`}>
              {consensus.confidence.toUpperCase()}
            </p>
          </div>
          <div className="bg-white/70 rounded-lg p-3">
            <p className="text-xs text-gray-500 mb-1">Decision</p>
            <p className={`text-sm font-semibold ${isNoAction ? "text-green-700" : "text-blue-700"}`}>{followLabel}</p>
          </div>
        </div>
        {consensus.recommended_action && (
          <div className={`rounded-lg px-4 py-3 ${isNoAction ? "bg-green-100 border border-green-200" : "bg-blue-50 border border-blue-200"}`}>
            <p className={`text-sm ${isNoAction ? "text-green-900" : "text-blue-900"}`}>{consensus.recommended_action}</p>
          </div>
        )}
      </section>
    );
  }

  // New path: Consensus Strength Matrix
  const cfg = CONSENSUS_TYPE_CFG[ct] ?? CONSENSUS_TYPE_CFG.WEAK_CONSENSUS;
  const strength = consensus.consensus_strength_score ?? 0;
  const stratAlign = consensus.strategist_alignment_score ?? 0;
  const riskAlign = consensus.risk_alignment_score ?? 0;
  const s = Math.max(0, Math.min(100, strength));

  const followLabel =
    consensus.recommended === "no_action" ? "Stable"
    : consensus.recommended === "layer1"  ? "Strategist"
    : consensus.recommended === "layer2"  ? "Challenger"
    : consensus.recommended === "fallback"? "Fallback"
    : "Review";

  return (
    <section className={`border-2 rounded-xl p-5 shadow-sm space-y-4 ${cfg.section}`}>
      {/* Header row */}
      <div className="flex items-center gap-3 flex-wrap">
        <h3 className="font-semibold text-gray-800">Consensus Engine</h3>
        <span className={`text-xs font-bold px-2.5 py-1 rounded-full border ${cfg.badge}`}>
          {cfg.icon} {cfg.label}
        </span>
        <span className={`text-xs font-medium ml-auto ${CONF_COLOR[consensus.confidence]}`}>
          {consensus.confidence.toUpperCase()} confidence
        </span>
      </div>

      {/* Consensus Strength gauge */}
      <div className="bg-white/70 rounded-xl border border-white/80 px-4 py-3 space-y-2">
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-500 font-medium">Final Consensus Score</span>
          <span className={`font-bold text-sm ${cfg.badgeText}`}>{s}<span className="text-xs font-normal text-gray-400"> / 100</span></span>
        </div>
        <div className="h-3 bg-gray-100 rounded-full overflow-hidden">
          <div className={`h-full rounded-full transition-all duration-500 ${cfg.bar}`} style={{ width: `${s}%` }} />
        </div>
        {/* Alignment sub-scores */}
        <div className="grid grid-cols-2 gap-3 pt-1">
          <AlignmentBar label="Strategist alignment" score={stratAlign} barColor={cfg.bar} />
          <AlignmentBar label="Risk alignment" score={riskAlign} barColor={cfg.bar} />
        </div>
      </div>

      {/* Refinement summary */}
      {consensus.refinement_summary && (
        <div className={`rounded-lg px-4 py-3 border ${cfg.summary}`}>
          <p className={`text-sm leading-relaxed ${cfg.summaryText}`}>{consensus.refinement_summary}</p>
        </div>
      )}

      {/* Committee Resolution — what the committee decided, not repeating the Challenger's reasons */}
      {consensus.disagreement_reasons && consensus.disagreement_reasons.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Committee Resolution</p>
          <p className="text-xs text-gray-600">
            Resolved {consensus.disagreement_reasons.length} disagreement{consensus.disagreement_reasons.length !== 1 ? "s" : ""}
            {consensus.recommended === "layer1" ? " — following Strategist"
             : consensus.recommended === "layer2" ? " — following Challenger"
             : consensus.recommended === "no_action" ? " — no action required"
             : ""}
          </p>
        </div>
      )}

      {/* Stats grid */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
        <div className="bg-white/60 rounded-lg p-2.5">
          <p className="text-xs text-gray-400 mb-0.5">Risk Level</p>
          <p className={`text-sm font-semibold ${RISK_COLOR[consensus.final_risk_level ?? "medium"] ?? ""}`}>
            {(consensus.final_risk_level ?? "medium").toUpperCase()}
          </p>
        </div>
        <div className="bg-white/60 rounded-lg p-2.5">
          <p className="text-xs text-gray-400 mb-0.5">Risk Flags</p>
          <p className={`text-sm font-semibold ${(consensus.risk_flag_count ?? 0) > 0 ? "text-amber-600" : "text-green-600"}`}>
            {consensus.risk_flag_count ?? 0}
          </p>
        </div>
        <div className="bg-white/60 rounded-lg p-2.5">
          <p className="text-xs text-gray-400 mb-0.5">Follow</p>
          <p className={`text-sm font-semibold ${cfg.badgeText}`}>{followLabel}</p>
        </div>
        <div className="bg-white/60 rounded-lg p-2.5">
          <p className="text-xs text-gray-400 mb-0.5">Decision</p>
          <p className={`text-sm font-semibold ${cfg.badgeText}`}>
            {consensus.consensus_decision ?? "—"}
          </p>
        </div>
      </div>

      {/* Recommended action */}
      {consensus.recommended_action && (
        <div className="border-t border-white/50 pt-3">
          <p className="text-xs font-medium text-gray-500 mb-1">Recommended action</p>
          <p className={`text-sm ${cfg.summaryText}`}>{consensus.recommended_action}</p>
        </div>
      )}
    </section>
  );
}

// ─── Portfolio Metrics Bar ────────────────────────────────────────────────────

// Sums the same `estimated_amount` field already rendered per-row in the
// rebalance table (backend-computed, signed) — pure aggregation of data
// already on hand, not a new calculation. Rows deferred by either governance
// layer (noise filter or drift-tolerance — see `isDeferred` in AllocationTable)
// are excluded so this reflects cash needed for trades actually happening
// today, not the full theoretical rebalance.
function PortfolioMetricsBar({ result }: { result: OptimizerResult }) {
  const cash = result.cash_balance ?? 0;
  const total = result.total_value ?? 0;
  const equity = total - cash;
  const cashPct = total > 0 ? (cash / total * 100).toFixed(1) : "0.0";
  const turnover = result.portfolio_turnover_percent;
  const targetCashPct = result.target_cash_weight;
  const finalConsensus = getFinalConsensusScore(result);

  return (
    <div className="bg-white border rounded-xl p-4 shadow-sm flex flex-wrap gap-4 text-sm">
      <div>
        <span className="text-xs text-gray-500">Portfolio Value</span>
        <p className="font-semibold text-gray-800">฿{total.toLocaleString("th-TH")}</p>
      </div>
      <div>
        <span className="text-xs text-gray-500">Equity</span>
        <p className="font-semibold text-gray-800">฿{equity.toLocaleString("th-TH")}</p>
      </div>
      <div>
        <span className="text-xs text-gray-500">Cash</span>
        <p className="font-semibold text-blue-700">฿{cash.toLocaleString("th-TH")} ({cashPct}%)</p>
      </div>
      {targetCashPct !== undefined && (
        <div>
          <span className="text-xs text-gray-500">Target Cash</span>
          <p className={`font-semibold ${targetCashPct > 20 ? "text-amber-600" : "text-green-600"}`}>{targetCashPct.toFixed(1)}%</p>
        </div>
      )}
      {turnover !== undefined && (
        <div>
          <span className="text-xs text-gray-500">Est. Turnover</span>
          <p className={`font-semibold ${turnover > 30 ? "text-amber-600" : "text-gray-700"}`}>{turnover.toFixed(1)}%</p>
        </div>
      )}
      {finalConsensus != null && (
        <div>
          <span className="text-xs text-gray-500">Final Consensus Score</span>
          <p className={`font-semibold ${scoreZone(finalConsensus).text}`}>{finalConsensus}/100</p>
        </div>
      )}
    </div>
  );
}

// ─── Decision Action Panel ────────────────────────────────────────────────────

const DECISION_CFG: Record<ExecutionDecisionType, { label: string; cls: string; icon: string }> = {
  APPROVED:         { label: "Approve Recommendation", icon: "✓", cls: "bg-green-600 text-white hover:bg-green-700" },
  REJECTED:         { label: "Reject Recommendation", icon: "✗", cls: "border border-red-300 text-red-700 hover:bg-red-50" },
  MANUAL_OVERRIDE:  { label: "Manual Override",  icon: "✎", cls: "border border-gray-300 text-gray-600 hover:bg-gray-50" },
  PARTIAL_EXECUTION:{ label: "Partial",          icon: "½", cls: "border border-amber-300 text-amber-700 hover:bg-amber-50" },
};

const DECISION_BADGE: Record<ExecutionDecisionType, string> = {
  APPROVED:          "bg-green-100 text-green-800 border-green-200",
  REJECTED:          "bg-red-100 text-red-800 border-red-200",
  MANUAL_OVERRIDE:   "bg-gray-100 text-gray-700 border-gray-200",
  PARTIAL_EXECUTION: "bg-amber-100 text-amber-800 border-amber-200",
};

function ShadowReturnChip({ label, value }: { label: string; value: number | null }) {
  if (value === null) return null;
  const positive = value >= 0;
  return (
    <div className="text-xs">
      <span className="text-gray-400">{label}: </span>
      <span className={`font-semibold ${positive ? "text-green-600" : "text-red-600"}`}>
        {positive ? "+" : ""}{value.toFixed(2)}%
      </span>
    </div>
  );
}

function DecisionActionPanel({
  snapshotId,
  portfolioId,
}: {
  snapshotId: number;
  portfolioId: number;
}) {
  const [existing, setExisting] = useState<ExecutionDecision | null | undefined>(undefined);
  const [confirming, setConfirming] = useState<ExecutionDecisionType | null>(null);
  const [notes, setNotes] = useState("");
  const [overrideType, setOverrideType] = useState<OverrideCategoryType | "">("");
  const [originalSymbol, setOriginalSymbol] = useState("");
  const [replacementSymbol, setReplacementSymbol] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [shadowPerf, setShadowPerf] = useState<ShadowPerformanceSummary | null>(null);

  useEffect(() => {
    listExecutionDecisions(portfolioId, undefined, 50)
      .then((ds) => {
        const match = ds.find((d) => d.recommendation_snapshot_id === snapshotId);
        setExisting(match ?? null);
      })
      .catch(() => setExisting(null));
  }, [snapshotId, portfolioId]);

  // Fetch shadow performance once we know an APPROVED decision exists
  useEffect(() => {
    if (existing?.decision === "APPROVED") {
      getShadowPerformanceSummary(portfolioId)
        .then(setShadowPerf)
        .catch(() => setShadowPerf(null));
    }
  }, [existing, portfolioId]);

  if (existing === undefined) return null; // still loading

  const handleConfirm = async () => {
    if (!confirming) return;
    setSubmitting(true);
    setError(null);
    try {
      await recordDecisionBySnapshot(snapshotId, {
        portfolio_id: portfolioId,
        recommendation_snapshot_id: snapshotId,
        decision: confirming,
        override_notes: notes.trim() || undefined,
        create_static_shadow: confirming !== "APPROVED",
        override_type: (confirming === "MANUAL_OVERRIDE" && overrideType) ? overrideType : undefined,
        original_symbol: (confirming === "MANUAL_OVERRIDE" && originalSymbol.trim()) ? originalSymbol.trim() : undefined,
        replacement_symbol: (confirming === "MANUAL_OVERRIDE" && replacementSymbol.trim()) ? replacementSymbol.trim() : undefined,
      });
      const ds = await listExecutionDecisions(portfolioId, undefined, 50);
      const match = ds.find((d) => d.recommendation_snapshot_id === snapshotId);
      setExisting(match ?? null);
      window.dispatchEvent(new CustomEvent("execution-decision-recorded", {
        detail: { portfolioId, snapshotId, decision: confirming },
      }));
      setConfirming(null);
      setNotes("");
      setOverrideType("");
      setOriginalSymbol("");
      setReplacementSymbol("");
    } catch {
      setError("Failed to record decision. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  if (existing) {
    const cfg = DECISION_CFG[existing.decision] ?? DECISION_CFG.MANUAL_OVERRIDE;
    const badgeCls = DECISION_BADGE[existing.decision] ?? DECISION_BADGE.MANUAL_OVERRIDE;
    const staticShadow = shadowPerf?.summary?.static_frozen ?? null;
    const activeShadow = shadowPerf?.summary?.active_model ?? null;
    const trackingActive = shadowPerf?.has_shadows && shadowPerf.shadows.length > 0;

    return (
      <section className="bg-white border rounded-xl p-4 shadow-sm">
        <div className="flex items-center gap-3 flex-wrap">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Decision Recorded</span>
          <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${badgeCls}`}>
            {cfg.icon} {cfg.label}
          </span>
          {existing.override_type && (
            <span className="text-xs px-2 py-0.5 rounded-full border border-gray-200 bg-gray-50 text-gray-600 font-medium">
              {existing.override_type.replace(/_/g, " ")}
            </span>
          )}
          {existing.original_symbol && (
            <span className="text-xs text-gray-500 font-mono">
              {existing.original_symbol}
              {existing.replacement_symbol && ` → ${existing.replacement_symbol}`}
            </span>
          )}
          {existing.override_notes && (
            <span className="text-xs text-gray-500 italic">"{existing.override_notes}"</span>
          )}
          <span className="text-xs text-gray-400 ml-auto">
            {new Date(existing.executed_at).toLocaleString("en-GB", { dateStyle: "short", timeStyle: "short", timeZone: TZ })}
          </span>
        </div>

        {/* Shadow tracking status */}
        {existing.decision === "APPROVED" && (
          <div className="mt-2.5 pt-2.5 border-t border-gray-100">
            {trackingActive ? (
              <div className="space-y-1.5">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="inline-flex items-center gap-1 text-xs font-medium text-teal-700 bg-teal-50 border border-teal-200 px-2 py-0.5 rounded-full">
                    <span className="w-1.5 h-1.5 rounded-full bg-teal-500 animate-pulse" />
                    Shadow Tracking Active
                  </span>
                  {shadowPerf?.summary?.tracking_since && (
                    <span className="text-xs text-gray-400">
                      since {shadowPerf.summary.tracking_since}
                    </span>
                  )}
                </div>
                {(staticShadow?.inception_return_pct !== undefined || activeShadow?.inception_return_pct !== undefined) && (
                  <div className="flex gap-4 flex-wrap">
                    <ShadowReturnChip label="Frozen" value={staticShadow?.inception_return_pct ?? null} />
                    <ShadowReturnChip label="AI Model" value={activeShadow?.inception_return_pct ?? null} />
                    {(staticShadow?.latest_alpha !== undefined || activeShadow?.latest_alpha !== undefined) && (
                      <div className="text-xs text-gray-400">
                        α {(activeShadow?.latest_alpha ?? staticShadow?.latest_alpha ?? 0) >= 0 ? "+" : ""}
                        {((activeShadow?.latest_alpha ?? staticShadow?.latest_alpha) ?? 0).toFixed(2)}% vs benchmark
                      </div>
                    )}
                  </div>
                )}
                {!staticShadow?.inception_return_pct && !activeShadow?.inception_return_pct && (
                  <p className="text-xs text-gray-400">Performance data available after first daily valuation (17:45 ICT).</p>
                )}
              </div>
            ) : (
              <p className="text-xs text-gray-400">
                Shadow portfolios are being initialized — data will appear after the next daily valuation.
              </p>
            )}
          </div>
        )}
        {existing.decision !== "APPROVED" && (
          <p className="text-xs text-gray-400 mt-1.5">
            Performance impact tracked. See Attribution panel below.
          </p>
        )}

        {/* AI Evaluation M7 entry point (UX §2.3): "Track this decision" ->
            the graded execution detail (S4b) for this exact decision. */}
        <div className="mt-2.5 pt-2.5 border-t border-gray-100">
          <Link
            href={`/ai-analytics/execution/${existing.id}`}
            className="text-xs font-semibold text-blue-600 hover:underline"
          >
            Track this decision in AI Evaluation →
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section className="bg-white border rounded-xl p-4 shadow-sm">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
        Record Execution Decision
      </p>

      {confirming ? (
        <div className="space-y-3">
          <p className="text-sm text-gray-700">
            You are recording{" "}
            <span className={`font-semibold ${confirming === "APPROVED" ? "text-green-700" : confirming === "REJECTED" ? "text-red-700" : "text-gray-700"}`}>
              {DECISION_CFG[confirming]?.label}
            </span>{" "}
            for this optimizer recommendation.
            {confirming === "APPROVED" && (
              <span className="text-gray-500"> Two shadow portfolios will be created automatically to track performance over time.</span>
            )}
          </p>

          {confirming === "MANUAL_OVERRIDE" && (
            <div className="space-y-3 border border-gray-200 rounded-lg p-3 bg-gray-50">
              {/* Override Type */}
              <div>
                <p className="text-xs font-semibold text-gray-600 mb-1.5">Override Type</p>
                <div className="flex flex-wrap gap-2">
                  {([
                    { value: "REJECT_SWAP",        label: "Reject Swap" },
                    { value: "REPLACE_SYMBOL",     label: "Replace Symbol" },
                    { value: "INCREASE_CONVICTION",label: "Increase Conviction" },
                    { value: "REDUCE_CONVICTION",  label: "Reduce Conviction" },
                    { value: "HOLD_POSITION",      label: "Hold Position" },
                    { value: "CUSTOM",             label: "Custom" },
                  ] as { value: OverrideCategoryType; label: string }[]).map(({ value, label }) => (
                    <button
                      key={value}
                      type="button"
                      onClick={() => setOverrideType(v => v === value ? "" : value)}
                      className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${
                        overrideType === value
                          ? "bg-gray-800 text-white border-gray-800"
                          : "border-gray-300 text-gray-600 hover:bg-gray-100"
                      }`}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Symbol fields */}
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide block mb-1">
                    Symbol Affected
                  </label>
                  <input
                    type="text"
                    value={originalSymbol}
                    onChange={(e) => setOriginalSymbol(e.target.value.toUpperCase())}
                    placeholder="e.g. KBANK"
                    className="w-full border border-gray-200 rounded-md px-2.5 py-1.5 text-xs font-mono bg-white focus:outline-none focus:ring-1 focus:ring-gray-400"
                  />
                </div>
                <div>
                  <label className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide block mb-1">
                    Replacement Symbol
                  </label>
                  <input
                    type="text"
                    value={replacementSymbol}
                    onChange={(e) => setReplacementSymbol(e.target.value.toUpperCase())}
                    placeholder="e.g. TOA (optional)"
                    className="w-full border border-gray-200 rounded-md px-2.5 py-1.5 text-xs font-mono bg-white focus:outline-none focus:ring-1 focus:ring-gray-400"
                  />
                </div>
              </div>
            </div>
          )}

          {(confirming === "MANUAL_OVERRIDE" || confirming === "APPROVED" || confirming === "PARTIAL_EXECUTION") && (
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder={confirming === "MANUAL_OVERRIDE" ? "Reason (required) — e.g. Higher conviction in TOA vs GUNKUL" : "Notes (optional) — e.g. partial fill, adjusted sizing…"}
              className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm resize-none focus:outline-none focus:ring-1 focus:ring-blue-400"
              rows={2}
            />
          )}

          {error && <p className="text-xs text-red-500">{error}</p>}

          <div className="flex gap-2">
            <button
              onClick={handleConfirm}
              disabled={submitting}
              className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${
                confirming === "APPROVED"
                  ? "bg-green-600 text-white hover:bg-green-700"
                  : confirming === "REJECTED"
                  ? "bg-red-600 text-white hover:bg-red-700"
                  : "bg-blue-600 text-white hover:bg-blue-700"
              } disabled:opacity-50`}
            >
              {submitting ? "Saving…" : "Confirm"}
            </button>
            <button
              onClick={() => { setConfirming(null); setNotes(""); setOverrideType(""); setOriginalSymbol(""); setReplacementSymbol(""); setError(null); }}
              className="px-4 py-2 text-sm border rounded-lg text-gray-600 hover:bg-gray-50 transition-colors"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="flex gap-2 flex-wrap items-center">
          {(["APPROVED", "REJECTED", "MANUAL_OVERRIDE"] as ExecutionDecisionType[]).map((d) => {
            const cfg = DECISION_CFG[d];
            return (
              <button
                key={d}
                onClick={() => setConfirming(d)}
                className={`px-4 py-2 text-sm font-medium rounded-lg transition-colors ${cfg.cls}`}
              >
                {cfg.icon} {cfg.label}
              </button>
            );
          })}
          <p className="text-xs text-gray-400 ml-1">
            Recording a decision activates shadow portfolio tracking.
          </p>
        </div>
      )}
    </section>
  );
}

// ─── Decision Memory Timeline ─────────────────────────────────────────────────

function DecisionMemoryTimeline({ portfolioId }: { portfolioId: number }) {
  const [entries, setEntries] = useState<DecisionMemoryEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getDecisionMemoryTimeline(portfolioId, 10)
      .then(setEntries)
      .catch(() => setEntries([]))
      .finally(() => setLoading(false));
  }, [portfolioId]);

  if (loading || entries.length === 0) return null;

  return (
    <section className="bg-white border rounded-xl shadow-sm overflow-hidden">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide px-4 py-3 border-b">
        Decision History
      </p>
      <ul className="divide-y divide-gray-50 h-80 overflow-y-auto">
        {entries.map((e) => {
          const badgeCls = DECISION_BADGE[e.decision] ?? DECISION_BADGE.MANUAL_OVERRIDE;
          const cfg = DECISION_CFG[e.decision] ?? DECISION_CFG.MANUAL_OVERRIDE;
          const shadows = e.shadows ?? [];
          const staticShadow = shadows.find((s) => s.shadow_type === "STATIC_FROZEN");
          const activeShadow = shadows.find((s) => s.shadow_type === "ACTIVE_MODEL");

          return (
            <li key={e.decision_id} className="px-4 py-3">
              <div className="flex items-start gap-3 flex-wrap">
                <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border whitespace-nowrap ${badgeCls}`}>
                  {cfg.icon} {cfg.label}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    {e.recommendation_snapshot?.persona && (
                      <span className="text-xs text-gray-500">
                        {e.recommendation_snapshot.persona}
                      </span>
                    )}
                    {e.recommendation_snapshot?.consensus?.consensus_type && (
                      <span className="text-xs bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded">
                        {e.recommendation_snapshot.consensus.consensus_type.replace(/_/g, " ")}
                      </span>
                    )}
                    {e.recommendation_snapshot?.total_portfolio_value && (
                      <span className="text-xs text-gray-400">
                        ฿{e.recommendation_snapshot.total_portfolio_value.toLocaleString("th-TH", { maximumFractionDigits: 0 })}
                      </span>
                    )}
                  </div>
                  {(e.override_type || e.original_symbol || e.override_notes) && (
                    <div className="flex flex-wrap items-center gap-1.5 mt-0.5">
                      {e.override_type && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded border border-gray-200 bg-gray-50 text-gray-500 font-medium">
                          {e.override_type.replace(/_/g, " ")}
                        </span>
                      )}
                      {e.original_symbol && (
                        <span className="text-[10px] text-gray-400 font-mono">
                          {e.original_symbol}
                          {e.replacement_symbol && ` → ${e.replacement_symbol}`}
                        </span>
                      )}
                      {e.override_notes && (
                        <span className="text-xs text-gray-500 italic">"{e.override_notes}"</span>
                      )}
                    </div>
                  )}
                </div>
                <span className="text-xs text-gray-400 whitespace-nowrap">
                  {new Date(e.executed_at).toLocaleDateString("en-GB", { dateStyle: "short", timeZone: TZ })}
                </span>
              </div>

              {(staticShadow || activeShadow) && (
                <div className="mt-2 flex gap-4 flex-wrap">
                  {staticShadow && staticShadow.inception_return_pct !== null && (
                    <div className="text-xs">
                      <span className="text-gray-400">Frozen: </span>
                      <span className={`font-semibold ${(staticShadow.inception_return_pct ?? 0) >= 0 ? "text-green-600" : "text-red-600"}`}>
                        {(staticShadow.inception_return_pct ?? 0) >= 0 ? "+" : ""}
                        {staticShadow.inception_return_pct?.toFixed(2)}%
                      </span>
                    </div>
                  )}
                  {activeShadow && activeShadow.inception_return_pct !== null && (
                    <div className="text-xs">
                      <span className="text-gray-400">AI Model: </span>
                      <span className={`font-semibold ${(activeShadow.inception_return_pct ?? 0) >= 0 ? "text-green-600" : "text-red-600"}`}>
                        {(activeShadow.inception_return_pct ?? 0) >= 0 ? "+" : ""}
                        {activeShadow.inception_return_pct?.toFixed(2)}%
                      </span>
                    </div>
                  )}
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}

// ─── Optimizer → Decision Workspace handoff ───────────────────────────────────

const POSITIVE_ACTIONS: AllocationAction[] = ["BUY", "ACCUMULATE"];

function extractAccumulationSymbols(result: OptimizerResult): string[] {
  const allocations = result.target_allocations ?? [];
  const seen = new Set<string>();
  const out: string[] = [];
  for (const a of allocations) {
    if (POSITIVE_ACTIONS.includes(a.action) && !seen.has(a.symbol)) {
      seen.add(a.symbol);
      out.push(a.symbol);
    }
  }
  return out;
}

// Deliberately styled apart from the blue "follow the AI recommendation" path
// (ExecutionPlanCard, DecisionActionPanel): dashed violet border + "Optional"
// badge signal this is a separate sandbox, not the next required step.
function SendToWorkspaceButton({
  result,
  onSend,
}: {
  result: OptimizerResult;
  onSend: (symbols: string[]) => void;
}) {
  const symbols = extractAccumulationSymbols(result);
  const hasSymbols = symbols.length > 0;

  return (
    <section className="bg-violet-50/40 border border-dashed border-violet-200 rounded-xl p-4 space-y-3">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <p className="text-sm font-semibold text-violet-900">🧪 Decision Workspace</p>
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-full bg-violet-100 border border-violet-300 text-violet-700 uppercase tracking-wide">
              Optional
            </span>
          </div>
          <p className="text-xs text-violet-700/80 mt-1 max-w-xl">
            A separate what-if sandbox for exploring alternative ideas — it does not
            modify or replace the recommendation above. Use it only if you want to
            challenge or compare against this Execution Plan.
          </p>
          <p className="text-xs text-violet-600/70 mt-1">
            {hasSymbols
              ? `${symbols.length} accumulation candidate${symbols.length !== 1 ? "s" : ""} (BUY / ACCUMULATE) available to seed the sandbox`
              : "No accumulation candidates — only reductions were suggested"}
            {" "}— allocations there are recalculated from scratch, not copied from this recommendation.
          </p>
        </div>
        <button
          onClick={() => onSend(symbols)}
          disabled={!hasSymbols}
          className="shrink-0 flex items-center gap-1.5 rounded-lg border border-violet-300 bg-white px-4 py-2 text-xs font-semibold
                     text-violet-700 transition hover:bg-violet-100 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Run What-if Analysis →
        </button>
      </div>
      {hasSymbols && (
        <div className="flex flex-wrap gap-1.5">
          {symbols.map((sym) => (
            <span
              key={sym}
              className="text-[11px] font-mono font-semibold px-2 py-0.5 rounded bg-white border border-violet-200 text-violet-700"
            >
              {sym.replace(".BK", "")}
              {sym.endsWith(".BK") && <span className="text-violet-400">.BK</span>}
            </span>
          ))}
        </div>
      )}
    </section>
  );
}

// ─── Section Label (lightweight IA grouping, no visual chrome) ───────────────

function SectionLabel({ id, children }: { id?: string; children: ReactNode }) {
  return (
    <p id={id} className="text-xs font-semibold text-gray-400 uppercase tracking-widest pt-2 scroll-mt-20">
      {children}
    </p>
  );
}

// ─── Jump Navigation (anchor pills, mirrors ai-analytics pattern) ─────────────

const JUMP_LINKS = [
  { id: "analysis",             label: "Analysis" },
  { id: "ai-recommendation",    label: "AI Recommendation" },
  { id: "execution",            label: "Execution" },
  { id: "supporting-analytics", label: "Supporting Analytics" },
];

function OptimizerJumpNav() {
  return (
    <div className="sticky top-0 z-10 -mx-1 px-1 py-2 bg-gray-50/95 backdrop-blur rounded-b-lg mb-2">
      <div className="flex flex-wrap gap-1.5">
        {JUMP_LINKS.map((l) => (
          <a
            key={l.id}
            href={`#${l.id}`}
            className="text-xs font-medium px-2.5 py-1 rounded-full border bg-white border-gray-200 text-gray-600 hover:bg-gray-100 hover:text-gray-800 transition-colors"
          >
            {l.label}
          </a>
        ))}
      </div>
    </div>
  );
}

// ─── Collapsible Section (UX.3A.5) ───────────────────────────────────────────

function CollapsibleSection({
  title,
  summary,
  defaultOpen = false,
  children,
}: {
  title: string;
  summary?: string;
  defaultOpen?: boolean;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div>
      <button
        type="button"
        className="w-full flex items-center justify-between bg-white border rounded-xl px-5 py-4 text-left shadow-sm hover:bg-gray-50 transition-colors"
        onClick={() => setOpen((o) => !o)}
      >
        <div className="min-w-0">
          <h3 className="font-semibold text-gray-800 text-sm">{title}</h3>
          {summary && <p className="text-xs text-gray-500 mt-0.5 truncate">{summary}</p>}
        </div>
        <span className="text-gray-400 text-xs ml-4 shrink-0">{open ? "▲ Hide" : "▼ Show Details"}</span>
      </button>
      {open && <div className="mt-2">{children}</div>}
    </div>
  );
}

// ─── Committee Decision Card (UX.3A.4) ────────────────────────────────────────

function CommitteeDecisionCard({
  consensus,
  allocations,
}: {
  consensus: OptimizerConsensus;
  allocations?: TargetAllocation[];
}) {
  const ct = consensus.consensus_type;
  const cfg = ct ? (CONSENSUS_TYPE_CFG[ct] ?? CONSENSUS_TYPE_CFG.WEAK_CONSENSUS) : null;
  const isDeadlock = ct === "STRATEGIC_CONFLICT" || ct === "RISK_CONFLICT";
  const isNoAction =
    consensus.consensus_decision === "NO_ACTION" ||
    consensus.recommended === "no_action" ||
    ct === "NO_ACTION_CONSENSUS" ||
    ct === "NO_REBALANCE_CONSENSUS";

  const followLabel =
    consensus.recommended === "no_action" ? "No action needed"
    : consensus.recommended === "layer1"  ? "Strategist"
    : consensus.recommended === "layer2"  ? "Challenger"
    : consensus.recommended === "fallback"? "Fallback plan"
    : "Human review required";

  const sectionCls = isDeadlock
    ? "bg-red-50 border-red-300"
    : isNoAction
    ? "bg-teal-50 border-teal-300"
    : cfg
    ? cfg.section
    : "bg-blue-50 border-blue-300";

  const keyActions = (allocations ?? [])
    .filter((a) => a.action !== "HOLD" && a.action !== "WATCH")
    .sort((a, b) => {
      const pri: Record<string, number> = { BUY: 0, ACCUMULATE: 1, REDUCE: 2, SELL: 3 };
      return (pri[a.action] ?? 9) - (pri[b.action] ?? 9);
    })
    .slice(0, 6);

  return (
    <section className={`border-2 rounded-xl p-5 shadow-sm space-y-4 ${sectionCls}`}>
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mb-1">
            Committee Decision
          </p>
          {isDeadlock ? (
            <>
              <h3 className="font-bold text-lg text-red-800">Human Review Required</h3>
              <p className="text-sm text-red-600 mt-0.5">No clear consensus between layers.</p>
            </>
          ) : (
            <>
              <h3 className="font-bold text-lg text-gray-900">
                Following: <span className={cfg?.badgeText ?? "text-gray-800"}>{followLabel}</span>
              </h3>
              <p className="text-xs text-gray-500 mt-0.5">
                The AI's final call after reconciling Strategist, Challenger, and Risk Auditor.
              </p>
            </>
          )}
        </div>
        {cfg && (
          <span className={`text-xs font-bold px-2.5 py-1 rounded-full border ${cfg.badge}`}>
            {cfg.icon} {cfg.label}
          </span>
        )}
      </div>

      <div className="flex flex-wrap gap-4">
        <div>
          <p className="text-[10px] text-gray-400 uppercase tracking-wide mb-0.5">Confidence</p>
          <p className={`text-sm font-bold ${CONF_COLOR[consensus.confidence] ?? "text-gray-700"}`}>
            {consensus.confidence.toUpperCase()}
          </p>
        </div>
        {consensus.consensus_strength_score != null && (
          <div>
            <p className="text-[10px] text-gray-400 uppercase tracking-wide mb-0.5">Score</p>
            <p className={`text-sm font-bold ${cfg?.badgeText ?? "text-gray-700"}`}>
              {consensus.consensus_strength_score}<span className="text-xs font-normal text-gray-400">/100</span>
            </p>
          </div>
        )}
        <div>
          <p className="text-[10px] text-gray-400 uppercase tracking-wide mb-0.5">Risk</p>
          <p className={`text-sm font-bold ${RISK_COLOR[consensus.final_risk_level ?? "medium"] ?? "text-gray-700"}`}>
            {(consensus.final_risk_level ?? "medium").toUpperCase()}
          </p>
        </div>
        {(consensus.risk_flag_count ?? 0) > 0 && (
          <div>
            <p className="text-[10px] text-gray-400 uppercase tracking-wide mb-0.5">Flags</p>
            <p className="text-sm font-bold text-amber-600">{consensus.risk_flag_count}</p>
          </div>
        )}
      </div>

      {keyActions.length > 0 && (
        <div>
          <p className="text-[10px] font-bold text-gray-400 uppercase tracking-wide mb-2">Actions</p>
          <div className="flex flex-wrap gap-2">
            {keyActions.map((a) => (
              <div key={a.symbol} className="flex items-center gap-1.5">
                <SignalBadge signal={a.action} />
                <Link
                  href={`/stock/${encodeURIComponent(a.symbol)}`}
                  className="text-sm font-medium text-gray-700 hover:text-blue-600 hover:underline"
                >
                  {a.symbol.replace(".BK", "")}
                </Link>
              </div>
            ))}
          </div>
        </div>
      )}

      {(consensus.refinement_summary || consensus.recommended_action) && (
        <div className={`rounded-lg px-4 py-3 border ${cfg?.summary ?? "bg-white/60 border-white/80"}`}>
          <p className={`text-sm leading-relaxed ${cfg?.summaryText ?? "text-gray-700"}`}>
            {consensus.refinement_summary ?? consensus.recommended_action}
          </p>
        </div>
      )}
    </section>
  );
}

// ─── Sector summary helper ────────────────────────────────────────────────────

function sectorImpactSummary(warnings: SectorWarning[]): string {
  const changed = warnings.filter((w) => w.current_pct !== w.projected_pct);
  if (changed.length === 0) return "No significant sector changes";
  return changed.slice(0, 3).map((w) => {
    const delta = w.projected_pct - w.current_pct;
    return `${w.sector} ${delta >= 0 ? "+" : ""}${delta.toFixed(0)}%`;
  }).join(" · ");
}

// ─── Result Panel ─────────────────────────────────────────────────────────────

function ResultPanel({ result, loading, profiles, portfolioId, onForceRebalance, forceRunning, onSendToWorkspace }: {
  result: OptimizerResult | null;
  loading: boolean;
  onForceRebalance?: () => void;
  forceRunning?: boolean;
  profiles: StrategyProfile[];
  portfolioId: number | null;
  onSendToWorkspace: (symbols: string[]) => void;
}) {
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 gap-3 text-gray-400 text-sm">
        <Spinner size="lg" />
        <p>Loading…</p>
      </div>
    );
  }
  if (!result) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-gray-400 text-sm gap-2">
        <span className="text-4xl">📊</span>
        <p>Select a run from history or click <strong>Run Optimizer</strong>.</p>
        <p className="text-xs">Make sure your watchlist has candidates.</p>
      </div>
    );
  }

  const totalValue = result.total_value ?? 0;
  const riskMap: Record<string, string> = {};
  for (const flag of result.layer3_result?.risk_flags ?? []) {
    const key = flag.severity?.toUpperCase();
    const cur = riskMap[flag.symbol];
    if (!cur || (SEVERITY_ORDER[key] ?? 99) < (SEVERITY_ORDER[cur] ?? 99)) {
      riskMap[flag.symbol] = key;
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4 flex-wrap">
        <p className="text-xs text-gray-400">Analyzed: {formatDate(result.analyzed_at)}</p>
        <span className="text-xs text-gray-400">Portfolio: {result.portfolio_count ?? "?"}/12 stocks</span>
        {result.max_reached && (
          <span className="text-xs bg-amber-100 text-amber-700 border border-amber-200 px-2 py-0.5 rounded-full font-medium">
            ⚠ AT LIMIT — only reductions/swaps suggested
          </span>
        )}
      </div>

      {/* ── Analysis ─────────────────────────────────────────────────────── */}
      <SectionLabel id="analysis">Analysis</SectionLabel>

      {(result.total_value !== undefined) && <PortfolioMetricsBar result={result} />}

      {result.current_portfolio_dna && result.target_persona && profiles.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <PortfolioDNACard
            dna={result.current_portfolio_dna}
            targetPersona={result.target_persona}
            profiles={profiles}
          />
          <PersonaMatchCard result={result} profiles={profiles} />
        </div>
      )}

      {/* ── AI Recommendation ────────────────────────────────────────────── */}
      <SectionLabel id="ai-recommendation">AI Recommendation</SectionLabel>

      {!result.stabilization && result.status === "NO_ACTION" && <NoActionCard result={result} />}

      {/* Single-model header (shown when no layer data) */}
      {!result.layer1_result && (
        <section className="bg-white border rounded-xl p-5 shadow-sm">
          <div className="flex items-center gap-3 mb-2">
            <h3 className="font-semibold">Portfolio Assessment — {result.portfolio_name}</h3>
            <AIBadge provider={result.ai_provider ?? ""} model={result.ai_model ?? ""} label="optimized by" />
          </div>
          <p className="text-sm text-gray-800 mb-1">{result.portfolio_assessment}</p>
          <p className="text-xs text-gray-500">{result.optimization_notes}</p>
          {result.target_allocations && result.target_allocations.length > 0 && (
            <div className="mt-4">
              <AllocationTable allocations={result.target_allocations} totalValue={totalValue} />
            </div>
          )}
        </section>
      )}

      {result.layer1_result && <Layer1Section layer={result.layer1_result} totalValue={totalValue} />}

      {result.layer2_result && <Layer2Section layer={result.layer2_result} totalValue={totalValue} />}

      {result.layer3_result && <Layer3Section layer={result.layer3_result} />}

      {result.consensus && (
        <div className="space-y-3">
          <CommitteeDecisionCard
            consensus={result.consensus}
            allocations={result.target_allocations}
          />
          <CollapsibleSection
            title="Full Consensus Detail"
            summary="Alignment scores, strength matrix, and committee resolution"
          >
            <ConsensusSection consensus={result.consensus} />
          </CollapsibleSection>
        </div>
      )}

      {/* ── Execution ────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <SectionLabel id="execution">Execution</SectionLabel>
        {/* AI Evaluation M7 entry point (UX §2.3): "How did this run turn
            out?" -> the full graded Report Card for this exact recommendation. */}
        {result.recommendation_snapshot_id && (
          <Link
            href={`/ai-analytics/recommendations/${result.recommendation_snapshot_id}`}
            className="text-xs font-semibold text-blue-600 hover:underline"
          >
            AI Evaluation Report Card →
          </Link>
        )}
      </div>

      {/* Primary output: what to trade today — a view derived from the
          recommendation above (action_summary classification joined with
          target_allocations amounts), not a separately stored "execution
          plan". The canonical recommendation is never mutated. */}
      <ExecutionPlanCard result={result} portfolioId={portfolioId ?? undefined} />

      {/* Act on the plan — record approve/reject/override */}
      {result.recommendation_snapshot_id && portfolioId && (
        <DecisionActionPanel
          snapshotId={result.recommendation_snapshot_id}
          portfolioId={portfolioId}
        />
      )}

      {/* Execution Analysis — explains the plan (the "why", not the "what").
          Portfolio Drift is one card within this, not the umbrella title. */}
      {result.stabilization && (
        <div className="space-y-3 pt-1">
          <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-wide">Execution Analysis</p>
          <div id="portfolio-drift" className="scroll-mt-20">
            <StabilizationCard
              meta={result.stabilization}
              onForceRebalance={onForceRebalance ?? (() => {})}
              forceRunning={forceRunning ?? false}
            />
          </div>
        </div>
      )}

      {/* Separate path, visually broken out from the plan above — see
          SendToWorkspaceButton comment for why it's styled apart. */}
      <div className="pt-2 border-t border-dashed border-gray-200">
        <SendToWorkspaceButton result={result} onSend={onSendToWorkspace} />
      </div>

      {/* ── Supporting Analytics — collapsed by default (UX.3A.5) ──────────── */}
      <div className="space-y-3">
        <SectionLabel id="supporting-analytics">Supporting Analytics</SectionLabel>

        {/* Market Regime — collapsed by default (UX.3A.3) */}
        {result.market_regime && (
          <CollapsibleSection
            title="Market Regime"
            summary={((result.market_regime as MarketRegime).regime ?? "").replace(/_/g, " ")}
          >
            <MarketRegimeCard regime={result.market_regime as MarketRegime} />
          </CollapsibleSection>
        )}

        {/* Active Policy Envelope */}
        {result.active_policy ? (
          <CollapsibleSection
            title="Active Policy Envelope"
            summary="🟢 Active — sector limits and position constraints"
          >
            <ActivePolicyEnvelopeCard
              policy={result.active_policy as ActivePolicy}
              effectiveEnvelope={result.effective_envelope}
            />
          </CollapsibleSection>
        ) : result.policy_engine_status === "DISABLED_FALLBACK" ? (
          <div className="text-xs px-3 py-2 rounded border text-red-700 bg-red-50 border-red-200">
            🔴 Policy Engine Disabled (Fallback) — this run used legacy regime-only
            constraints. Persona weighting, confidence-adjusted limits, and policy
            alignment scoring were skipped. Check backend logs for
            <span className="font-mono"> [POLICY_ENGINE]</span> errors.
          </div>
        ) : null}

        {/* Sector Impact */}
        {result.sector_warnings && result.sector_warnings.length > 0 && (
          <CollapsibleSection
            title="Sector Impact"
            summary={sectorImpactSummary(result.sector_warnings)}
          >
            <SectorImpactSection warnings={result.sector_warnings} />
          </CollapsibleSection>
        )}

        {/* Watchlist Ranking */}
        <CollapsibleSection
          title="Watchlist Ranking"
          summary={`${result.watchlist_ranking.length} candidates ranked`}
        >
          <div className="bg-white border rounded-xl overflow-x-auto overflow-y-auto max-h-[200px] shadow-sm">
            <table className="min-w-full text-sm">
              <thead className="sticky top-0 bg-white z-10">
                <tr className="border-b text-left text-xs text-gray-500">
                  <th className="py-2 pl-4 pr-3">#</th>
                  <th className="py-2 pr-3">Symbol</th>
                  <th className="py-2 pr-3">Signal</th>
                  <th className="py-2 pr-3">Score</th>
                  <th className="py-2 pr-3 hidden sm:table-cell">Sector</th>
                  <th className="py-2 pr-3">Alloc%</th>
                  {totalValue > 0 && <th className="py-2 pr-3">THB</th>}
                  <th className="py-2 pr-3">Upside</th>
                  <th className="py-2 pr-3">Risk</th>
                  <th className="py-2 hidden lg:table-cell">Reasoning</th>
                </tr>
              </thead>
              <tbody>
                {result.watchlist_ranking.map((item) => (
                  <RankingRow key={item.symbol} item={item} totalValue={totalValue} riskMap={riskMap} />
                ))}
              </tbody>
            </table>
          </div>
        </CollapsibleSection>

        {/* Attribution Analytics */}
        {portfolioId && (
          <CollapsibleSection
            title="Attribution Analytics"
            summary="Shadow benchmark, Human vs AI, Performance by regime"
          >
            <AttributionPanel portfolioId={portfolioId} evaluationWindowDays={30} />
          </CollapsibleSection>
        )}

        {/* Decision History */}
        {portfolioId && (
          <CollapsibleSection
            title="Decision History"
            summary="Past execution decisions and shadow portfolio returns"
          >
            <DecisionMemoryTimeline portfolioId={portfolioId} />
          </CollapsibleSection>
        )}
      </div>
    </div>
  );
}

// ─── Analysis History (consolidated) ─────────────────────────────────────────

function AnalysisHistory({
  items,
  details,
  loading,
  selectedId,
  onSelect,
}: {
  items: OptimizerHistoryItem[];
  details: Record<number, OptimizerResult | null>;
  loading: boolean;
  selectedId: number | null;
  onSelect: (item: OptimizerHistoryItem) => void;
}) {
  return (
    <section className="bg-white border rounded-xl p-4 shadow-sm">
      <div className="flex items-center justify-between gap-2 mb-3">
        <h2 className="text-sm font-semibold text-gray-800">Analysis History</h2>
        {items.length > 0 && (
          <span className="text-xs text-gray-400">{items.length} run{items.length !== 1 ? "s" : ""}</span>
        )}
      </div>

      {loading ? (
        <p className="text-xs text-gray-400 py-2">Loading…</p>
      ) : items.length === 0 ? (
        <p className="text-xs text-gray-400 py-2">No analysis history yet. Run the optimizer to begin.</p>
      ) : (
        <div className="overflow-y-auto" style={{ maxHeight: "320px" }}>
          <div className="flex flex-col gap-2 pr-1">
            {items.map((item) => {
              const detail = details[item.id] ?? null;
              const isActive = selectedId === item.id;
              const isNoAction = item.optimizer_status === "NO_ACTION";
              const score = getHistoryFinalConsensusScore(item, detail);
              const { fill } = score != null ? scoreZone(score) : { fill: "bg-gray-300" };

              const persona = detail?.target_persona ?? null;
              const personaLabel = detail?.persona_label ?? persona ?? null;
              const personaCfg = persona ? PERSONA_CFG[persona] : null;

              const regime = detail?.market_regime?.regime?.replace(/_/g, " ") ?? null;
              const holdingsCount = detail?.portfolio_count ?? null;

              const keySymbols = (detail?.target_allocations ?? [])
                .filter((a) => a.action !== "HOLD")
                .slice(0, 3)
                .map((a) => a.symbol.replace(".BK", ""));

              const activeCls = isActive
                ? isNoAction
                  ? "bg-green-50 border-green-200"
                  : "bg-blue-50 border-blue-200"
                : "border-transparent hover:border-gray-200 hover:bg-gray-50";

              return (
                <button
                  key={item.id}
                  onClick={() => onSelect(item)}
                  className={`w-full text-left px-3 py-2.5 rounded-lg border transition-colors ${activeCls}`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className={`text-xs font-medium ${isActive ? (isNoAction ? "text-green-800" : "text-blue-700") : "text-gray-700"}`}>
                      {formatDate(item.analyzed_at)}
                    </span>
                    <span className={`shrink-0 text-[10px] font-bold px-1.5 py-0.5 rounded-full ${isNoAction ? "bg-green-100 text-green-700" : "bg-blue-100 text-blue-600"}`}>
                      {isNoAction ? "✓" : "⚡"}
                    </span>
                  </div>

                  <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                    {personaCfg && personaLabel && (
                      <span className={`text-xs ${personaCfg.color}`}>
                        {personaCfg.icon} {personaLabel}
                      </span>
                    )}
                    {regime && (
                      <span className="text-xs text-gray-400 capitalize">{regime}</span>
                    )}
                    {holdingsCount != null && (
                      <span className="text-xs text-gray-400">{holdingsCount} holdings</span>
                    )}
                  </div>

                  {keySymbols.length > 0 && (
                    <div className="flex gap-1 flex-wrap mt-1">
                      {keySymbols.map((sym) => (
                        <span key={sym} className="text-[10px] font-medium px-1.5 py-0.5 bg-gray-100 text-gray-600 rounded">
                          {sym}
                        </span>
                      ))}
                    </div>
                  )}

                  {score != null && (
                    <div className="mt-1.5 flex items-center gap-1.5">
                      <div className="flex-1 h-1 bg-gray-100 rounded-full overflow-hidden">
                        <div className={`h-1 rounded-full ${fill}`} style={{ width: `${score}%` }} />
                      </div>
                      <span className="text-[10px] text-gray-400 tabular-nums w-5 text-right">{score}</span>
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      )}
    </section>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function OptimizerPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { portfolios, activeId } = usePortfolio();
  const [selectedPortfolioId, setSelectedPortfolioId] = useState<number | null>(null);
  const [result, setResult] = useState<OptimizerResult | null>(null);
  const [history, setHistory] = useState<OptimizerHistoryItem[]>([]);
  const [historyDetails, setHistoryDetails] = useState<Record<number, OptimizerResult | null>>({});
  const [selectedHistoryId, setSelectedHistoryId] = useState<number | null>(null);
  const [running, setRunning] = useState(false);
  const [forceRunning, setForceRunning] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState("");
  const [opsStatus, setOpsStatus] = useState<OperationsCenterStatus | null>(null);

  const [profiles, setProfiles] = useState<StrategyProfile[]>([]);
  const [persona, setPersona] = useState<StrategyPersona>("BALANCED");
  const [savingPersona, setSavingPersona] = useState(false);

  const portfolioId = selectedPortfolioId ?? activeId;

  const loadHistory = useCallback(async (pid: number): Promise<OptimizerHistoryItem[]> => {
    setLoadingHistory(true);
    try {
      const items = await listOptimizerHistory(pid);
      setHistory(items);
      return items;
    } catch {
      setHistory([]);
      return [];
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  const preloadRecentDetails = useCallback(async (items: OptimizerHistoryItem[]) => {
    const top = items.slice(0, 5).map((h) => h.id);
    const loaded = await Promise.all(
      top.map(async (id) => {
        try {
          const detail = await getOptimizerHistory(id);
          return [id, detail] as const;
        } catch {
          return [id, null] as const;
        }
      }),
    );

    setHistoryDetails((prev) => {
      const next = { ...prev };
      for (const [id, detail] of loaded) next[id] = detail;
      return next;
    });
  }, []);

  // Load strategy profiles once on mount
  useEffect(() => {
    listStrategyProfiles().then((d) => setProfiles(d.profiles)).catch(() => {});
  }, []);

  // Load portfolio persona when portfolio changes
  useEffect(() => {
    if (portfolioId == null) return;
    getPortfolioPersona(portfolioId).then((d) => setPersona(d.persona)).catch(() => {});
  }, [portfolioId]);

  useEffect(() => {
    if (portfolioId == null) return;
    getOperationsStatus(portfolioId).then(setOpsStatus).catch(() => setOpsStatus(null));
  }, [portfolioId]);

  useEffect(() => {
    void preloadRecentDetails(history);
  }, [history, preloadRecentDetails]);

  useEffect(() => {
    if (portfolioId == null) return;
    let cancelled = false;

    setResult(null);
    setSelectedHistoryId(null);

    const bootstrapLatestHistory = async () => {
      const items = await loadHistory(portfolioId);
      if (cancelled || items.length === 0) return;

      const rawHistoryId = searchParams.get("history");
      const historyFromQuery = rawHistoryId ? Number(rawHistoryId) : Number.NaN;
      const queryTarget = Number.isFinite(historyFromQuery)
        ? items.find((h) => h.id === historyFromQuery)
        : undefined;
      const target = queryTarget ?? items[0];
      if (!target) return;

      setSelectedHistoryId(target.id);
      setLoadingDetail(true);
      setError("");
      try {
        const detail = await getOptimizerHistory(target.id);
        if (!cancelled) {
          setResult(detail);
          setHistoryDetails((prev) => ({ ...prev, [target.id]: detail }));
          rememberSelectedHistory(portfolioId, target.id);
        }
      } catch {
        if (!cancelled) setError("Failed to load history");
      } finally {
        if (!cancelled) setLoadingDetail(false);
      }
    };

    bootstrapLatestHistory();

    return () => {
      cancelled = true;
    };
  }, [portfolioId, loadHistory, searchParams]);

  async function handlePersonaSave(p: StrategyPersona) {
    if (portfolioId == null) return;
    setPersona(p);
    setSavingPersona(true);
    try {
      await updatePortfolioPersona(portfolioId, p);
    } finally {
      setSavingPersona(false);
    }
  }

  async function handleRun(forceRebalance = false) {
    if (portfolioId == null) return;
    if (forceRebalance) {
      setForceRunning(true);
    } else {
      setRunning(true);
    }
    setError("");
    try {
      const data = await runOptimizer(portfolioId, undefined, undefined, forceRebalance || undefined);
      setResult(data);
      setSelectedHistoryId(data.history_id ?? null);
      if (data.history_id != null) {
        setHistoryDetails((prev) => ({ ...prev, [data.history_id as number]: data }));
        rememberSelectedHistory(portfolioId, data.history_id);
      }
      await loadHistory(portfolioId);
      getOperationsStatus(portfolioId).then(setOpsStatus).catch(() => {});
    } catch (err) {
      setError(err instanceof Error ? err.message : "Optimizer failed");
    } finally {
      setRunning(false);
      setForceRunning(false);
    }
  }

  function handleSendToWorkspace(symbols: string[]) {
    if (symbols.length === 0) return;
    const deduplicated = [...new Set(symbols)];
    router.push(`/operations-center?symbols=${deduplicated.join(",")}`);
  }

  async function handleSelectHistory(item: OptimizerHistoryItem) {
    if (selectedHistoryId === item.id) return;
    setSelectedHistoryId(item.id);
    if (portfolioId != null) {
      rememberSelectedHistory(portfolioId, item.id);
    }
    setLoadingDetail(true);
    setError("");
    try {
      const detail = await getOptimizerHistory(item.id);
      setResult(detail);
      setHistoryDetails((prev) => ({ ...prev, [item.id]: detail }));
    } catch {
      setError("Failed to load history");
    } finally {
      setLoadingDetail(false);
    }
  }

  const activePortfolio = portfolios.find((p) => p.id === portfolioId);
  const latestAnalysisAt = history[0]?.analyzed_at ?? null;
  const lastSnapshotDate = opsStatus?.portfolio_summary.snapshot_date ?? null;
  const daysSinceLastRebalance = opsStatus?.portfolio_summary.days_since_last_rebalance ?? null;
  const deepLinkedHistoryIdRaw = searchParams.get("history");
  const deepLinkedHistoryId = deepLinkedHistoryIdRaw ? Number(deepLinkedHistoryIdRaw) : Number.NaN;
  const hasDeepLinkedHistory = Number.isFinite(deepLinkedHistoryId);
  const isViewingDeepLinkedHistory = hasDeepLinkedHistory && selectedHistoryId === deepLinkedHistoryId;

  return (
    <div className="space-y-6">
      <div>
        <BackBreadcrumb parent="ศูนย์บัญชาการ AI" current="Optimizer" href="/operations-center" />
        <h1 className="text-2xl font-bold mb-1">Portfolio Optimizer</h1>
        <p className="text-sm text-gray-500">
          Dynamic capital allocation — position sizing, rebalancing, cash deployment.
        </p>
        {hasDeepLinkedHistory && (
          <p className="mt-2 inline-flex items-center rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700">
            {isViewingDeepLinkedHistory
              ? "กำลังแสดงผลการวิเคราะห์ล่าสุดจาก Ops Center"
              : "กำลังโหลดผลการวิเคราะห์ที่เลือกจาก Ops Center"}
          </p>
        )}
      </div>

      {/* Controls */}
      <div className="bg-white border rounded-xl p-4 shadow-sm space-y-4">
        <div>
          <h2 className="text-sm font-semibold text-gray-800">Control Panel</h2>
          <p className="text-xs text-gray-500 mt-0.5">Select a portfolio and strategy persona, then run a new analysis.</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <span className="inline-flex items-center rounded-full border border-blue-200 bg-blue-50 px-2.5 py-1 text-xs font-medium text-blue-700">
            {optimizerLastAnalysisBadgeTh(latestAnalysisAt)}
          </span>
          <span className="inline-flex items-center rounded-full border border-gray-200 bg-gray-50 px-2.5 py-1 text-xs font-medium text-gray-600">
            {marketDataFreshnessTh(lastSnapshotDate)}
          </span>
          <span className="inline-flex items-center rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700">
            {daysSinceRebalanceText(daysSinceLastRebalance)}
          </span>
        </div>

        <div className="flex flex-wrap gap-4 items-end">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Portfolio</label>
          <select
            value={portfolioId ?? ""}
            onChange={(e) => setSelectedPortfolioId(parseInt(e.target.value, 10))}
            className="border rounded px-3 py-1.5 text-sm bg-white"
          >
            {portfolios.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>

        <PersonaSelector
          portfolioId={portfolioId}
          persona={persona}
          profiles={profiles}
          saving={savingPersona}
          onSave={handlePersonaSave}
        />

        {activePortfolio && (
          <div>
            <span className="block text-xs text-gray-500 mb-1">Cash Balance</span>
            <span className="text-sm font-semibold text-blue-700">
              ฿{(activePortfolio.cash_balance ?? 0).toLocaleString("th-TH")}
            </span>
          </div>
        )}

        <button
          onClick={() => handleRun()}
          disabled={running || portfolioId == null}
          className="bg-blue-600 text-white px-5 py-1.5 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2 self-end"
        >
          {running && <Spinner />}
          {running ? "Optimizing…" : "Run Optimizer"}
        </button>
        {error && <p className="text-red-500 text-xs self-center">{error}</p>}
        </div>
      </div>

      {/* Mobile: Analysis History stacked (UX.3A.2) */}
      <div className="lg:hidden">
        <AnalysisHistory
          items={history}
          details={historyDetails}
          loading={loadingHistory}
          selectedId={selectedHistoryId}
          onSelect={handleSelectHistory}
        />
      </div>

      {/* Desktop: main content + Analysis History sidebar (UX.3A.2) */}
      <div className="flex gap-6 items-start">
        <div className="flex-1 min-w-0">
          {running && portfolioId != null && (
            <div className="max-w-xl mx-auto py-6 space-y-3">
              <OperationsTimeline portfolioId={portfolioId} active={running} />
              <p className="text-xs text-gray-400 text-center">This may take 60–180 seconds</p>
            </div>
          )}

          {!running && result && <OptimizerJumpNav />}

          {!running && (
            <div className={`rounded-xl transition-colors ${isViewingDeepLinkedHistory ? "ring-1 ring-blue-200 bg-blue-50/30" : ""}`}>
              <ResultPanel
                result={result}
                loading={loadingDetail}
                profiles={profiles}
                portfolioId={portfolioId}
                onForceRebalance={() => handleRun(true)}
                forceRunning={forceRunning}
                onSendToWorkspace={handleSendToWorkspace}
              />
            </div>
          )}
        </div>

        {/* Desktop sidebar: Analysis History (320px, sticky) */}
        <div className="w-80 shrink-0 hidden lg:block sticky top-4 self-start">
          <AnalysisHistory
            items={history}
            details={historyDetails}
            loading={loadingHistory}
            selectedId={selectedHistoryId}
            onSelect={handleSelectHistory}
          />
        </div>
      </div>
    </div>
  );
}
