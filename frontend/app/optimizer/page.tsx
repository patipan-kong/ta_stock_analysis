"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import BackBreadcrumb from "@/components/BackBreadcrumb";
import { usePortfolio } from "@/lib/PortfolioContext";
import {
  runOptimizer, listOptimizerHistory, getOptimizerHistory,
  listStrategyProfiles, getPortfolioPersona, updatePortfolioPersona,
  recordDecisionBySnapshot, listExecutionDecisions,
  getDecisionMemoryTimeline, getShadowPerformanceSummary,
} from "@/lib/api";
import SignalBadge from "@/components/SignalBadge";
import AIBadge from "@/components/AIBadge";
import MarketRegimeCard from "@/components/MarketRegimeCard";
import ActivePolicyEnvelopeCard from "@/components/ActivePolicyEnvelopeCard";
import AttributionPanel from "@/components/AttributionPanel";
import OperationsTimeline from "@/components/operations-center/quant/OperationsTimeline";
import type {
  OptimizerResult, OptimizerHistoryItem, TargetAllocation, AllocationAction,
  WatchlistRanking, Layer2Result, Layer3Result, OptimizerConsensus, RiskFlag, SectorWarning,
  BlockedOpportunity, NoActionReason, SwapSuggestion, ConsensusType,
  StrategyPersona, StrategyProfile, PortfolioDNA, DriftSeverity, MarketRegime,
  ActivePolicy, ExecutionDecision, ExecutionDecisionType, DecisionMemoryEntry,
  ShadowPerformanceSummary, ExecutionRisk,
  StabilizationMeta, OptimizerStatus,
} from "@/lib/api";

const TZ = "Asia/Bangkok";

// ─── Persona config ───────────────────────────────────────────────────────────

const PERSONA_CFG: Record<StrategyPersona, { icon: string; color: string; badge: string }> = {
  BALANCED:  { icon: "⚖",  color: "text-blue-700",   badge: "bg-blue-50 border-blue-300 text-blue-800" },
  GROWTH:    { icon: "🚀", color: "text-green-700",  badge: "bg-green-50 border-green-300 text-green-800" },
  VALUE:     { icon: "💎", color: "text-purple-700", badge: "bg-purple-50 border-purple-300 text-purple-800" },
  DIVIDEND:  { icon: "💰", color: "text-amber-700",  badge: "bg-amber-50 border-amber-300 text-amber-800" },
  MOMENTUM:  { icon: "⚡", color: "text-orange-700", badge: "bg-orange-50 border-orange-300 text-orange-800" },
  PASSIVE:   { icon: "🌿", color: "text-teal-700",   badge: "bg-teal-50 border-teal-300 text-teal-800" },
};

const DRIFT_CFG: Record<DriftSeverity, { bar: string; text: string; bg: string }> = {
  LOW:      { bar: "bg-green-500",  text: "text-green-700",  bg: "bg-green-50 border-green-200" },
  MEDIUM:   { bar: "bg-blue-500",   text: "text-blue-700",   bg: "bg-blue-50 border-blue-200" },
  HIGH:     { bar: "bg-amber-500",  text: "text-amber-700",  bg: "bg-amber-50 border-amber-200" },
  CRITICAL: { bar: "bg-red-500",    text: "text-red-700",    bg: "bg-red-50 border-red-200" },
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
          const deltaText = delta >= 0.5 ? `+${delta.toFixed(0)}` : delta <= -0.5 ? `${delta.toFixed(0)}` : "~";
          const deltaColor = delta > 10 ? "text-green-600" : delta < -10 ? "text-red-500" : "text-gray-400";
          return (
            <div key={factor} className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="capitalize font-medium text-gray-600 w-20">{factor}</span>
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-gray-400">target {target.toFixed(0)}</span>
                  <span className={`font-semibold ${deltaColor}`}>{deltaText}</span>
                  <span className="font-semibold text-gray-700 w-8 text-right">{current.toFixed(0)}</span>
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
      <p className="text-xs text-gray-400">Gray marker = persona target. Bar = current portfolio.</p>
    </section>
  );
}

// ─── Style Drift Card ─────────────────────────────────────────────────────────

function StyleDriftCard({
  result,
  profiles,
}: {
  result: OptimizerResult;
  profiles: StrategyProfile[];
}) {
  const severity = (result.style_drift_severity ?? "LOW") as DriftSeverity;
  const driftScore = result.style_drift_score ?? 0;
  const alignScore = result.factor_alignment_score ?? 100;
  const urgency = result.rebalance_urgency ?? "LOW";
  const persona = result.target_persona as StrategyPersona | undefined;
  const profile = profiles.find((p) => p.id === persona);
  const cfg = DRIFT_CFG[severity] ?? DRIFT_CFG.LOW;
  const personaCfg = persona ? (PERSONA_CFG[persona] ?? PERSONA_CFG.BALANCED) : null;

  const urgencyColor: Record<string, string> = {
    LOW:      "text-green-600",
    MODERATE: "text-blue-600",
    HIGH:     "text-amber-600",
    CRITICAL: "text-red-600",
  };

  const dominant = result.factor_drift
    ? Object.entries(result.factor_drift).sort(([, a], [, b]) => Math.abs(b) - Math.abs(a)).slice(0, 2)
    : [];

  return (
    <section className={`border rounded-xl p-5 shadow-sm space-y-4 ${cfg.bg}`}>
      <div className="flex items-center gap-3 flex-wrap">
        {personaCfg && <span className={`text-lg ${personaCfg.color}`}>{personaCfg.icon}</span>}
        <div>
          <h3 className="font-semibold text-gray-800">Style Alignment</h3>
          <p className="text-xs text-gray-500 mt-0.5">
            {profile?.label ?? persona ?? "Balanced"} target vs current portfolio DNA
          </p>
        </div>
        <span className={`ml-auto text-xs font-bold px-2.5 py-1 rounded-full border ${cfg.bg} ${cfg.text}`}>
          {severity} DRIFT
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
        <div className="bg-white/70 rounded-lg p-3">
          <p className="text-xs text-gray-400 mb-0.5">Drift Score</p>
          <p className={`text-sm font-bold ${cfg.text}`}>{driftScore.toFixed(0)}<span className="text-xs font-normal text-gray-400"> / 100</span></p>
        </div>
        <div className="bg-white/70 rounded-lg p-3">
          <p className="text-xs text-gray-400 mb-0.5">Alignment</p>
          <p className="text-sm font-bold text-gray-700">{alignScore.toFixed(0)}<span className="text-xs font-normal text-gray-400"> / 100</span></p>
        </div>
        <div className="bg-white/70 rounded-lg p-3">
          <p className="text-xs text-gray-400 mb-0.5">Urgency</p>
          <p className={`text-sm font-bold ${urgencyColor[urgency] ?? ""}`}>{urgency}</p>
        </div>
        <div className="bg-white/70 rounded-lg p-3">
          <p className="text-xs text-gray-400 mb-0.5">Severity</p>
          <p className={`text-sm font-bold ${cfg.text}`}>{severity}</p>
        </div>
      </div>

      {/* Drift gauge */}
      <div className="space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <span className="text-gray-500">Alignment Score</span>
          <span className={`font-semibold ${cfg.text}`}>{alignScore.toFixed(0)} / 100</span>
        </div>
        <div className="h-2 bg-gray-100 rounded-full overflow-hidden">
          <div className={`h-full rounded-full ${cfg.bar}`} style={{ width: `${alignScore}%` }} />
        </div>
      </div>

      {/* Top misaligned factors */}
      {dominant.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-gray-500">Factor gaps (current vs target)</p>
          {dominant.map(([factor, delta]) => {
            const isOver = delta > 0;
            const barColor = FACTOR_COLORS[factor] ?? "bg-gray-400";
            const absDelta = Math.abs(delta) * 100;
            return (
              <div key={factor} className="flex items-center gap-2 text-xs">
                <span className="capitalize text-gray-600 w-20">{factor}</span>
                <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div className={`h-full ${barColor} opacity-60`} style={{ width: `${Math.min(100, absDelta * 3)}%` }} />
                </div>
                <span className={`font-semibold w-14 text-right ${isOver ? "text-green-600" : "text-red-500"}`}>
                  {isOver ? "+" : ""}{(delta * 100).toFixed(1)}pp
                </span>
              </div>
            );
          })}
        </div>
      )}
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

// ─── Action badge ─────────────────────────────────────────────────────────────

const ACTION_CLS: Record<AllocationAction, string> = {
  BUY:        "bg-green-600 text-white",
  ACCUMULATE: "bg-teal-600 text-white",
  HOLD:       "bg-gray-400 text-white",
  WATCH:      "bg-blue-500 text-white",
  REDUCE:     "bg-amber-500 text-white",
  SELL:       "bg-red-600 text-white",
};

function ActionBadge({ action }: { action: AllocationAction }) {
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${ACTION_CLS[action] ?? "bg-gray-300 text-gray-700"}`}>
      {action}
    </span>
  );
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

  const significant = allocations.filter(
    (a) => a.action !== "HOLD" || Math.abs(a.allocation_change_percent) >= 2
  );
  const hold = allocations.filter(
    (a) => a.action === "HOLD" && Math.abs(a.allocation_change_percent) < 2
  );

  return (
    <div className="space-y-3">
      {title && <p className="text-xs font-medium text-gray-500">{title}</p>}
      <div className="overflow-x-auto">
        <table className="min-w-full text-xs">
          <thead>
            <tr className="border-b text-left text-gray-400">
              <th className="pb-1.5 pr-3">Symbol</th>
              <th className="pb-1.5 pr-3">Action</th>
              <th className="pb-1.5 pr-3 text-right">Current%</th>
              <th className="pb-1.5 pr-3 text-right">Target%</th>
              <th className="pb-1.5 pr-3 text-right">Change%</th>
              {totalValue && totalValue > 0 && <th className="pb-1.5 pr-3 text-right">Est. Amount</th>}
              <th className="pb-1.5">Reason</th>
            </tr>
          </thead>
          <tbody>
            {significant.map((a) => {
              const chg = a.allocation_change_percent;
              const chgCls = chg > 0 ? "text-green-600 font-semibold" : chg < 0 ? "text-red-500 font-semibold" : "text-gray-400";
              const amt = a.estimated_amount || (totalValue ? Math.round(totalValue * Math.abs(chg) / 100) : 0);
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
                  <td className="py-1.5 pr-3"><ActionBadge action={a.action as AllocationAction} /></td>
                  <td className="py-1.5 pr-3 text-right text-gray-500">{a.current_weight.toFixed(1)}%</td>
                  <td className="py-1.5 pr-3 text-right font-medium">{a.target_weight.toFixed(1)}%</td>
                  <td className={`py-1.5 pr-3 text-right ${chgCls}`}>
                    {chg >= 0 ? "+" : ""}{chg.toFixed(1)}%
                  </td>
                  {totalValue && totalValue > 0 && (
                    <td className="py-1.5 pr-3 text-right text-gray-600">
                      {amt > 0 ? `฿${amt.toLocaleString("th-TH")}` : "—"}
                    </td>
                  )}
                  <td className="py-1.5 text-gray-500 max-w-xs truncate" title={a.reason}>{a.reason}</td>
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
    return <p className="text-sm text-gray-500">No swap proposals from Strategist.</p>;
  }
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-xs">
        <thead>
          <tr className="border-b text-left text-gray-400">
            <th className="pb-1.5 pr-3">Type</th>
            <th className="pb-1.5 pr-3">Sell</th>
            <th className="pb-1.5 pr-3">Buy</th>
            <th className="pb-1.5 pr-3 text-right">Score Δ</th>
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
                <td className="py-1.5 text-gray-500 max-w-xs truncate" title={s.reason}>{s.reason}</td>
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

const NO_ACTION_REASON_LABELS: Record<NoActionReason, string> = {
  WELL_BALANCED:       "Well Balanced",
  LOW_CONFIDENCE:      "Low Confidence",
  HIGH_DISAGREEMENT:   "High Disagreement",
  CONSTRAINT_BLOCKED:  "Constraint Blocked",
  MARKET_UNCERTAINTY:  "Market Uncertainty",
  INSUFFICIENT_EDGE:   "Insufficient Edge",
  COOLDOWN_ACTIVE:     "Cooldown Active",
};

const BLOCKED_REASON_LABELS: Record<string, string> = {
  sector_limit_exceeded: "Sector limit exceeded",
  insufficient_cash:     "Insufficient cash balance",
  portfolio_count_cap:   "Portfolio stock count cap reached",
};

function scoreZone(s: number): { label: string; fill: string; text: string } {
  if (s <= 20) return { label: "Well Balanced",       fill: "bg-green-500",  text: "text-green-700" };
  if (s <= 40) return { label: "Minor Opportunity",   fill: "bg-teal-500",   text: "text-teal-700"  };
  if (s <= 70) return { label: "Moderate Opportunity",fill: "bg-amber-400",  text: "text-amber-700" };
  return            { label: "Strong Opportunity",    fill: "bg-orange-500", text: "text-orange-600" };
}

function OpportunityScoreGauge({ score }: { score: number }) {
  const s = Math.max(0, Math.min(100, score));
  const { label, fill, text } = scoreZone(s);
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-gray-500 font-medium">Rebalance Opportunity Score</span>
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
  const score  = result.rebalance_opportunity_score ?? 0;
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
                  {b.signal && (
                    <span className={`text-xs font-semibold px-1.5 py-0.5 rounded-full shrink-0 ${ACTION_CLS[b.signal as AllocationAction] ?? "bg-gray-200 text-gray-700"}`}>
                      {b.signal}
                    </span>
                  )}
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
  REBALANCE:              { label: "Rebalance Required",    icon: "⚡", section: "bg-orange-50 border-orange-200",  badge: "bg-orange-100 border-orange-300 text-orange-800", text: "text-orange-800" },
  REBALANCE_REQUIRED:     { label: "Rebalance Required",    icon: "⚡", section: "bg-orange-50 border-orange-200",  badge: "bg-orange-100 border-orange-300 text-orange-800", text: "text-orange-800" },
  NO_ACTION:              { label: "No Action Needed",       icon: "✓",  section: "bg-green-50 border-green-200",    badge: "bg-green-100 border-green-300 text-green-800",   text: "text-green-800" },
  NO_REBALANCE_REQUIRED:  { label: "No Rebalance Required", icon: "✓",  section: "bg-green-50 border-green-200",    badge: "bg-green-100 border-green-300 text-green-800",   text: "text-green-800" },
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
            Drift Analysis — {meta.positions_within_tolerance} within tolerance, {meta.positions_needing_action} need action
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
}: {
  layer: OptimizerResult["layer1_result"];
  totalValue?: number;
}) {
  if (!layer) return null;
  const swaps: SwapSuggestion[] = layer.swap_suggestions ?? [];
  const topBuys: string[] = (layer as Record<string, unknown>).top_buys as string[] ?? [];
  const sectorFlags: string[] = (layer as Record<string, unknown>).sector_flags as string[] ?? [];
  const priority: string = (layer as Record<string, unknown>).priority as string ?? "";

  return (
    <section className="bg-white border rounded-xl p-5 shadow-sm space-y-4">
      <div className="flex items-center gap-2 flex-wrap">
        <div>
          <h3 className="font-semibold text-gray-800">🟠 {layer.name ?? "Strategist"}</h3>
          <p className="text-xs text-orange-600 mt-0.5">
            Swap Proposals{priority ? ` — priority: ${priority}` : ""}
          </p>
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

          <SwapTable swaps={swaps} />

          {topBuys.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs text-gray-400 font-medium">Top buys:</span>
              {topBuys.map((sym) => (
                <Link key={sym} href={`/stock/${encodeURIComponent(sym)}`}
                  className="text-xs font-semibold text-green-700 bg-green-50 border border-green-200 px-2 py-0.5 rounded hover:bg-green-100">
                  {sym.replace(".BK", "")}{sym.endsWith(".BK") ? <span className="text-gray-400">.BK</span> : ""}
                </Link>
              ))}
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
  const [activeTab, setActiveTab] = useState<"disagreements" | "alternatives">(
    agrees ? "alternatives" : "disagreements"
  );
  useEffect(() => {
    setActiveTab(agrees ? "alternatives" : "disagreements");
  }, [agrees]);
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
          <div className="flex items-center gap-2 border-b border-amber-200 pb-2">
            <button
              type="button"
              onClick={() => setActiveTab("disagreements")}
              className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${
                activeTab === "disagreements"
                  ? "bg-amber-200 text-amber-900"
                  : "bg-white/70 text-amber-700 hover:bg-amber-100"
              }`}
            >
              Disagreements ({disagreements.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("alternatives")}
              className={`px-3 py-1 rounded-full text-xs font-semibold transition-colors ${
                activeTab === "alternatives"
                  ? "bg-blue-200 text-blue-900"
                  : "bg-white/70 text-blue-700 hover:bg-blue-100"
              }`}
            >
              Allocation Plan ({allocations.length})
            </button>
          </div>

          {activeTab === "disagreements" && (
            <div>
              {disagreements.length === 0 ? (
                <div className="bg-white/70 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
                  No disagreement notes from Challenger.
                </div>
              ) : (
                <ul className="text-xs text-amber-700 space-y-1 list-disc list-inside">
                  {disagreements.map((d, i) => <li key={i}>{d}</li>)}
                </ul>
              )}
            </div>
          )}

          {activeTab === "alternatives" && (
            <div>
              {allocations.length === 0 ? (
                <div className="bg-white/70 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
                  {agrees ? "Challenger confirms the Strategist plan." : "No alternative allocations provided."}
                </div>
              ) : (
                <AllocationTable allocations={allocations} totalValue={totalValue} />
              )}
            </div>
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
          <span className="text-gray-500 font-medium">Consensus Strength</span>
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

      {/* Disagreement reasons */}
      {consensus.disagreement_reasons && consensus.disagreement_reasons.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">Challenger disagreements</p>
          <ul className="space-y-1">
            {consensus.disagreement_reasons.map((d, i) => (
              <li key={i} className="flex items-start gap-1.5 text-xs text-gray-700">
                <span className="mt-0.5 shrink-0 text-gray-400">•</span>
                <span>{d}</span>
              </li>
            ))}
          </ul>
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

function PortfolioMetricsBar({ result }: { result: OptimizerResult }) {
  const cash = result.cash_balance ?? 0;
  const total = result.total_value ?? 0;
  const equity = total - cash;
  const cashPct = total > 0 ? (cash / total * 100).toFixed(1) : "0.0";
  const turnover = result.portfolio_turnover_percent;
  const targetCashPct = result.target_cash_weight;

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
    </div>
  );
}

// ─── Decision Action Panel ────────────────────────────────────────────────────

const DECISION_CFG: Record<ExecutionDecisionType, { label: string; cls: string; icon: string }> = {
  APPROVED:         { label: "Approve Rebalance", icon: "✓", cls: "bg-green-600 text-white hover:bg-green-700" },
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
      });
      const ds = await listExecutionDecisions(portfolioId, undefined, 50);
      const match = ds.find((d) => d.recommendation_snapshot_id === snapshotId);
      setExisting(match ?? null);
      window.dispatchEvent(new CustomEvent("execution-decision-recorded", {
        detail: { portfolioId, snapshotId, decision: confirming },
      }));
      setConfirming(null);
      setNotes("");
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

          {(confirming === "MANUAL_OVERRIDE" || confirming === "APPROVED" || confirming === "PARTIAL_EXECUTION") && (
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Notes (optional) — e.g. partial fill, adjusted sizing…"
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
              onClick={() => { setConfirming(null); setNotes(""); setError(null); }}
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
      <ul className="divide-y divide-gray-50">
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
                  {e.override_notes && (
                    <p className="text-xs text-gray-500 italic mt-0.5">"{e.override_notes}"</p>
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

// ─── Result Panel ─────────────────────────────────────────────────────────────

function ResultPanel({ result, loading, profiles, portfolioId, onForceRebalance, forceRunning }: {
  result: OptimizerResult | null;
  loading: boolean;
  onForceRebalance?: () => void;
  forceRunning?: boolean;
  profiles: StrategyProfile[];
  portfolioId: number | null;
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

      {/* Portfolio metrics */}
      {(result.total_value !== undefined) && <PortfolioMetricsBar result={result} />}

      {/* Market Regime Indicator */}
      {result.market_regime && (
        <MarketRegimeCard regime={result.market_regime as MarketRegime} />
      )}

      {/* Active Policy Envelope (3B.4 + 3B.5 constraint comparison) */}
      {result.active_policy && (
        <ActivePolicyEnvelopeCard
          policy={result.active_policy as ActivePolicy}
          effectiveEnvelope={result.effective_envelope}
        />
      )}

      {/* Strategy Persona — DNA + Drift cards */}
      {result.current_portfolio_dna && result.target_persona && profiles.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <PortfolioDNACard
            dna={result.current_portfolio_dna}
            targetPersona={result.target_persona}
            profiles={profiles}
          />
          <StyleDriftCard result={result} profiles={profiles} />
        </div>
      )}

      {/* Stabilization layer status — shown prominently for all non-REBALANCE outcomes */}
      {result.stabilization && (
        <StabilizationCard
          meta={result.stabilization}
          onForceRebalance={onForceRebalance ?? (() => {})}
          forceRunning={forceRunning ?? false}
        />
      )}

      {/* Legacy NO_ACTION card — shown only for AI-originated NO_ACTION when no stabilization meta */}
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

      {/* 3-layer sections */}
      {result.layer1_result && <Layer1Section layer={result.layer1_result} totalValue={totalValue} />}
      {result.layer2_result && <Layer2Section layer={result.layer2_result} totalValue={totalValue} />}
      {result.layer3_result && <Layer3Section layer={result.layer3_result} />}
      {result.consensus && <ConsensusSection consensus={result.consensus} />}
      {result.sector_warnings && result.sector_warnings.length > 0 && (
        <SectorImpactSection warnings={result.sector_warnings} />
      )}

      <section>
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold">Watchlist Ranking</h3>
          {totalValue > 0 && <span className="text-xs text-gray-500">Total: ฿{totalValue.toLocaleString("th-TH")}</span>}
        </div>
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
      </section>

      {/* Decision Action — record Approve / Reject / Override */}
      {result.recommendation_snapshot_id && portfolioId && (
        <DecisionActionPanel
          snapshotId={result.recommendation_snapshot_id}
          portfolioId={portfolioId}
        />
      )}

      {/* Attribution Analytics — Phase 3B.7B */}
      {portfolioId && <AttributionPanel portfolioId={portfolioId} evaluationWindowDays={30} />}

      {/* Decision Memory Timeline */}
      {portfolioId && <DecisionMemoryTimeline portfolioId={portfolioId} />}
    </div>
  );
}

// ─── History List ─────────────────────────────────────────────────────────────

function HistoryList({
  items, selectedId, loading, onSelect,
}: {
  items: OptimizerHistoryItem[];
  selectedId: number | null;
  loading: boolean;
  onSelect: (item: OptimizerHistoryItem) => void;
}) {
  return (
    <div className="bg-white border rounded-xl p-3 shadow-sm h-fit">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide px-1 mb-2">Run History</p>
      {loading ? (
        <p className="text-xs text-gray-400 px-1 py-2">Loading…</p>
      ) : items.length === 0 ? (
        <p className="text-xs text-gray-400 px-1 py-2">No history yet.</p>
      ) : (
        <ul className="space-y-1">
          {items.map((item) => {
            const isNoAction = item.optimizer_status === "NO_ACTION";
            const score = item.rebalance_opportunity_score;
            const { fill } = score != null ? scoreZone(score) : { fill: "bg-gray-300" };
            const activeCls = selectedId === item.id
              ? isNoAction ? "bg-green-50 border border-green-200" : "bg-blue-50 border border-blue-200"
              : "hover:bg-gray-50";
            return (
              <li key={item.id}>
                <button onClick={() => onSelect(item)} className={`w-full text-left px-3 py-2.5 rounded-lg transition-colors ${activeCls}`}>
                  <div className="flex items-center gap-1.5">
                    <p className={`text-xs font-medium truncate flex-1 ${selectedId === item.id ? (isNoAction ? "text-green-800" : "text-blue-700") : "text-gray-700"}`}>
                      {formatDate(item.analyzed_at)}
                    </p>
                    <span className={`shrink-0 text-xs font-bold px-1.5 py-0.5 rounded-full ${isNoAction ? "bg-green-100 text-green-700" : "bg-blue-100 text-blue-600"}`}>
                      {isNoAction ? "✓" : "⚡"}
                    </span>
                  </div>
                  <p className="text-xs text-gray-400 mt-0.5">
                    {isNoAction
                      ? (item.no_action_reason ? NO_ACTION_REASON_LABELS[item.no_action_reason] : "No action needed")
                      : `${item.swap_count} action${item.swap_count !== 1 ? "s" : ""} suggested`}
                  </p>
                  {score != null && (
                    <div className="mt-1.5 flex items-center gap-1.5">
                      <div className="flex-1 h-1 bg-gray-100 rounded-full overflow-hidden">
                        <div className={`h-1 rounded-full ${fill}`} style={{ width: `${score}%` }} />
                      </div>
                      <span className="text-xs text-gray-400 shrink-0 w-5 text-right">{score}</span>
                    </div>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function OptimizerPage() {
  const { portfolios, activeId } = usePortfolio();
  const [selectedPortfolioId, setSelectedPortfolioId] = useState<number | null>(null);
  const [result, setResult] = useState<OptimizerResult | null>(null);
  const [history, setHistory] = useState<OptimizerHistoryItem[]>([]);
  const [selectedHistoryId, setSelectedHistoryId] = useState<number | null>(null);
  const [running, setRunning] = useState(false);
  const [forceRunning, setForceRunning] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState("");

  const [profiles, setProfiles] = useState<StrategyProfile[]>([]);
  const [persona, setPersona] = useState<StrategyPersona>("BALANCED");
  const [savingPersona, setSavingPersona] = useState(false);

  const portfolioId = selectedPortfolioId ?? activeId;

  const loadHistory = useCallback(async (pid: number) => {
    setLoadingHistory(true);
    try {
      setHistory(await listOptimizerHistory(pid));
    } finally {
      setLoadingHistory(false);
    }
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
    setResult(null);
    setSelectedHistoryId(null);
    loadHistory(portfolioId);
  }, [portfolioId, loadHistory]);

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
      await loadHistory(portfolioId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Optimizer failed");
    } finally {
      setRunning(false);
      setForceRunning(false);
    }
  }

  async function handleSelectHistory(item: OptimizerHistoryItem) {
    if (selectedHistoryId === item.id) return;
    setSelectedHistoryId(item.id);
    setLoadingDetail(true);
    setError("");
    try {
      setResult(await getOptimizerHistory(item.id));
    } catch {
      setError("Failed to load history");
    } finally {
      setLoadingDetail(false);
    }
  }

  const activePortfolio = portfolios.find((p) => p.id === portfolioId);

  return (
    <div className="space-y-6">
      <div>
        <BackBreadcrumb parent="ศูนย์บัญชาการ AI" current="Optimizer" href="/operations-center" />
        <h1 className="text-2xl font-bold mb-1">Portfolio Optimizer</h1>
        <p className="text-sm text-gray-500">
          Dynamic capital allocation — position sizing, rebalancing, cash deployment.
        </p>
      </div>

      {/* Controls */}
      <div className="bg-white border rounded-xl p-4 shadow-sm flex flex-wrap gap-4 items-end">
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

      {running && portfolioId != null && (
        <div className="max-w-xl mx-auto py-6 space-y-3">
          <OperationsTimeline portfolioId={portfolioId} active={running} />
          <p className="text-xs text-gray-400 text-center">This may take 60–180 seconds</p>
        </div>
      )}

      {!running && (
        <div className="flex flex-col lg:flex-row gap-6 items-start">
          <div className="w-full lg:w-52 shrink-0">
            <HistoryList
              items={history}
              selectedId={selectedHistoryId}
              loading={loadingHistory}
              onSelect={handleSelectHistory}
            />
          </div>
          <div className="flex-1 min-w-0">
            <ResultPanel
              result={result}
              loading={loadingDetail}
              profiles={profiles}
              portfolioId={portfolioId}
              onForceRebalance={() => handleRun(true)}
              forceRunning={forceRunning}
            />
          </div>
        </div>
      )}
    </div>
  );
}
