"use client";

import { useState, useEffect, useCallback } from "react";
import Link from "next/link";
import { usePortfolio } from "@/lib/PortfolioContext";
import {
  runOptimizer, listOptimizerHistory, getOptimizerHistory,
} from "@/lib/api";
import SignalBadge from "@/components/SignalBadge";
import AIBadge from "@/components/AIBadge";
import type {
  OptimizerResult, OptimizerHistoryItem, SwapSuggestion, WatchlistRanking,
  Layer2Result, Layer3Result, OptimizerConsensus, RiskFlag, SectorWarning,
} from "@/lib/api";

const TZ = "Asia/Bangkok";

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


// ─── Swap Card ────────────────────────────────────────────────────────────────

function SwapCard({ s }: { s: SwapSuggestion }) {
  if (s.type === "SELL") {
    const sym = s.sell_symbol ?? "";
    return (
      <div className="bg-red-50 border-2 border-red-300 rounded-xl p-4 shadow-sm">
        <div className="flex items-center gap-2 mb-3">
          <span className="text-xs bg-red-600 text-white px-2 py-0.5 rounded-full font-semibold">🚨 SELL SIGNAL</span>
          <span className="text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full">{s.sector}</span>
        </div>
        <div className="flex items-center gap-2 mb-2">
          <SignalBadge signal="SELL" />
          <p className="text-base font-bold text-gray-800">{sym.replace(".BK", "")}</p>
          {sym.endsWith(".BK") && <span className="text-xs text-gray-400">.BK</span>}
        </div>
        <p className="text-xs text-gray-600">{s.reason}</p>
      </div>
    );
  }

  const sellSym = s.sell_symbol ?? "";
  const buySym  = s.buy_symbol  ?? "";
  const deltaCls = s.score_improvement >= 0
    ? "bg-green-100 text-green-700"
    : "bg-red-100 text-red-700";
  return (
    <div className="bg-blue-50 border-2 border-blue-200 rounded-xl p-4 shadow-sm">
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <span className="inline-block text-xs bg-blue-600 text-white px-2 py-0.5 rounded-full font-semibold">
          🔁 SWAP PLAN
        </span>
        <span className="inline-block text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full">
          {s.sector}
        </span>
        {s.score_improvement !== 0 && (
          <span className={`inline-block text-xs px-2 py-0.5 rounded-full font-semibold ${deltaCls}`}>
            Δ {s.score_improvement >= 0 ? "+" : ""}{s.score_improvement.toFixed(1)}
          </span>
        )}
      </div>
      <div className="flex items-center gap-3 mb-3">
        {sellSym && (
          <div className="flex-1 text-center">
            <SignalBadge signal="SELL" />
            <p className="text-base font-bold text-gray-800 mt-1">{sellSym.replace(".BK", "")}</p>
            {sellSym.endsWith(".BK") && <span className="text-xs text-gray-400">.BK</span>}
          </div>
        )}
        <div className="flex flex-col items-center gap-0.5 shrink-0 text-gray-400">
          <span className="text-xl">{sellSym ? "→" : "＋"}</span>
          {s.score_improvement !== 0 && (
            <span className={`text-xs font-semibold ${s.score_improvement >= 0 ? "text-green-600" : "text-red-600"}`}>
              {s.score_improvement >= 0 ? "+" : ""}{s.score_improvement.toFixed(1)}
            </span>
          )}
        </div>
        {buySym && (
          <div className="flex-1 text-center">
            <SignalBadge signal="BUY" />
            <p className="text-base font-bold text-gray-800 mt-1">{buySym.replace(".BK", "")}</p>
            {buySym.endsWith(".BK") && <span className="text-xs text-gray-400">.BK</span>}
          </div>
        )}
      </div>
      <p className="text-xs text-gray-500">{s.reason}</p>
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
  item, budget, riskMap,
}: {
  item: WatchlistRanking;
  budget: number;
  riskMap: Record<string, string>;
}) {
  const display = item.symbol.replace(".BK", "");
  const thb = budget > 0 ? Math.round(budget * item.suggested_allocation_pct / 100) : null;
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

// ─── Layer sections ───────────────────────────────────────────────────────────

function l1Direction(priority?: string): string {
  if (priority === "growth")    return "Aggressive Growth";
  if (priority === "balanced")  return "Balanced Allocation";
  if (priority === "defensive") return "Defensive Positioning";
  return "Strategic Allocation";
}

function l2Direction(agrees?: boolean): string {
  if (agrees === true)  return "Confirms Strategist";
  if (agrees === false) return "Conservative Rotation";
  return "Independent Review";
}

function l3Direction(riskLevel?: string, saferChoice?: string): string {
  if (saferChoice === "neither")     return "Caution — Review Manually";
  if (riskLevel   === "high")        return "Defensive";
  if (riskLevel   === "low")         return "Low Risk Confirmed";
  return "Moderate Risk Profile";
}

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

function Layer1Section({
  layer,
  suggestions,
}: {
  layer: OptimizerResult["layer1_result"];
  suggestions: SwapSuggestion[];
}) {
  if (!layer) return null;
  const strategistSuggestions = suggestions.slice(0, 4);
  return (
    <section className="bg-white border rounded-xl p-5 shadow-sm space-y-3">
      <div className="flex items-center gap-2 flex-wrap">
        <div>
          <h3 className="font-semibold text-gray-800">🟠 {layer.name ?? "Strategist"}</h3>
          <p className="text-xs text-orange-600 mt-0.5">{l1Direction(layer.priority)}</p>
        </div>
        <AIBadge provider={layer.provider} model={layer.model} label="" />
      </div>
      {layer.error ? (
        <p className="text-xs text-red-500">{layer.error}</p>
      ) : (
        <>
          {layer.reasoning && <p className="text-sm text-gray-700">{layer.reasoning}</p>}
          {layer.portfolio_assessment && !layer.reasoning && (
            <p className="text-sm text-gray-700">{layer.portfolio_assessment}</p>
          )}

          <div>
            <div className="flex items-center justify-between mb-2">
              <p className="text-xs font-medium text-gray-500">Strategist Swap Suggestions</p>
              <p className="text-xs text-gray-400">{strategistSuggestions.length} cards</p>
            </div>
            {strategistSuggestions.length === 0 ? (
              <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-sm text-green-700">
                No swaps recommended by Strategist.
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {strategistSuggestions.map((s, i) => <SwapCard key={i} s={s} />)}
              </div>
            )}
          </div>
        </>
      )}
    </section>
  );
}

function Layer2Section({
  layer,
}: {
  layer: Layer2Result | null | undefined;
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
  const challengerSuggestions = (layer.alternative_suggestions ?? []).slice(0, 5);
  return (
    <section className={`border rounded-xl p-5 shadow-sm space-y-3 ${agrees ? "bg-green-50 border-green-200" : "bg-amber-50 border-amber-200"}`}>
      <div className="flex items-center gap-2 flex-wrap">
        <div>
          <h3 className="font-semibold text-gray-800">🔵 {layer.name ?? "Challenger"}</h3>
          <p className="text-xs text-blue-600 mt-0.5">{l2Direction(layer.agrees_with_layer1)}</p>
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
              Alternatives ({challengerSuggestions.length})
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
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs font-medium text-gray-500">Challenger Alternative Suggestions</p>
                <p className="text-xs text-gray-400">{challengerSuggestions.length} cards</p>
              </div>
              {challengerSuggestions.length === 0 ? (
                <div className="bg-white/70 border border-amber-200 rounded-xl p-4 text-sm text-amber-800">
                  Challenger has no alternative swap suggestions.
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {challengerSuggestions.map((s, i) => <SwapCard key={i} s={s} />)}
                </div>
              )}
            </div>
          )}

          {agrees && <p className="text-sm text-green-700">Challenger confirms the Strategist&apos;s proposal.</p>}
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
          <p className="text-xs text-purple-600 mt-0.5">{l3Direction(layer.final_risk_level, layer.safer_choice)}</p>
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
          Before/after applying proposed swaps. Bars show % of sector limit used.
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
                  <span className="text-xs text-gray-400 w-10 text-right shrink-0">
                    {w.current_pct.toFixed(1)}%
                  </span>
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
                <span className={`text-xs font-semibold px-1.5 py-0.5 rounded border ${statusCls}`}>
                  {w.status}
                </span>
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
          <span className="inline-block w-4 h-1.5 bg-green-500 rounded" /> After swaps
        </span>
        <span className="flex items-center gap-1.5 text-amber-500">
          <span className="inline-block w-0 h-3 border-l-2 border-dashed border-amber-400" /> 80% threshold
        </span>
      </p>
    </section>
  );
}

const CONF_COLOR: Record<string, string> = {
  high: "text-green-600", medium: "text-amber-600", low: "text-red-500",
};
const RISK_COLOR: Record<string, string> = {
  low: "text-green-600", medium: "text-amber-600", high: "text-red-600",
};

function ConsensusSection({ consensus }: { consensus: OptimizerConsensus }) {
  return (
    <section className="bg-white border-2 border-blue-200 rounded-xl p-5 shadow-sm space-y-3">
      <h3 className="font-semibold text-gray-800">Consensus Engine</h3>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs text-gray-500 mb-1">L1 vs L2</p>
          <p className={`text-sm font-semibold ${consensus.agrees ? "text-green-600" : "text-amber-600"}`}>
            {consensus.agrees ? "✓ Agree" : "⚠ Disagree"}
          </p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs text-gray-500 mb-1">Risk Level</p>
          <p className={`text-sm font-semibold ${RISK_COLOR[consensus.final_risk_level] ?? ""}`}>
            {consensus.final_risk_level.toUpperCase()}
          </p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs text-gray-500 mb-1">Confidence</p>
          <p className={`text-sm font-semibold ${CONF_COLOR[consensus.confidence] ?? ""}`}>
            {consensus.confidence.toUpperCase()}
          </p>
        </div>
        <div className="bg-gray-50 rounded-lg p-3">
          <p className="text-xs text-gray-500 mb-1">Follow</p>
          <p className="text-sm font-semibold text-gray-700">
            {consensus.recommended === "layer1" ? "Strategist" : consensus.recommended === "layer2" ? "Challenger" : "Neither"}
          </p>
        </div>
      </div>
      {consensus.recommended_action && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg px-4 py-3">
          <p className="text-xs font-medium text-blue-700 mb-0.5">Recommended action</p>
          <p className="text-sm text-blue-900">{consensus.recommended_action}</p>
        </div>
      )}
    </section>
  );
}

// ─── Result Panel ─────────────────────────────────────────────────────────────

function ResultPanel({ result, budget, loading }: { result: OptimizerResult | null; budget: number; loading: boolean }) {
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

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4 flex-wrap">
        <p className="text-xs text-gray-400">Analyzed: {formatDate(result.analyzed_at)}</p>
        <span className="text-xs text-gray-400">Portfolio: {result.portfolio_count ?? "?"}/12 stocks</span>
        {result.max_reached && (
          <span className="text-xs bg-amber-100 text-amber-700 border border-amber-200 px-2 py-0.5 rounded-full font-medium">
            ⚠ AT LIMIT — only SWAPs suggested
          </span>
        )}
      </div>

      <section className="bg-white border rounded-xl p-3 shadow-sm">
        <div className="flex items-center gap-2 flex-wrap text-xs">
          <span className="text-gray-500 font-medium">Card Legend:</span>
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-red-50 text-red-700 border border-red-200">
            🚨 SELL SIGNAL
          </span>
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
            🔁 SWAP PLAN
          </span>
          <span className="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-green-50 text-green-700 border border-green-200">
            Δ positive = expected improvement
          </span>
        </div>
      </section>

      {/* Single-model header (shown when no layer data) */}
      {!result.layer1_result && (
        <section className="bg-white border rounded-xl p-5 shadow-sm">
          <div className="flex items-center gap-3 mb-2">
            <h3 className="font-semibold">Portfolio Assessment — {result.portfolio_name}</h3>
            <AIBadge
              provider={result.ai_provider ?? ""}
              model={result.ai_model ?? ""}
              label="optimized by"
            />
          </div>
          <p className="text-sm text-gray-800 mb-1">{result.portfolio_assessment}</p>
          <p className="text-xs text-gray-500">{result.optimization_notes}</p>
        </section>
      )}

      {/* 3-layer sections */}
      {result.layer1_result && <Layer1Section layer={result.layer1_result} suggestions={result.swap_suggestions} />}
      {result.layer2_result && <Layer2Section layer={result.layer2_result} />}
      {result.layer3_result && <Layer3Section layer={result.layer3_result} />}
      {result.consensus && <ConsensusSection consensus={result.consensus} />}
      {result.sector_warnings && result.sector_warnings.length > 0 && (
        <SectorImpactSection warnings={result.sector_warnings} />
      )}

      {(() => {
        // Build per-symbol risk map from Layer 3 risk_flags (highest severity wins)
        const severityOrder: Record<string, number> = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
        const riskMap: Record<string, string> = {};
        for (const flag of result.layer3_result?.risk_flags ?? []) {
          const key = flag.severity?.toUpperCase();
          const cur = riskMap[flag.symbol];
          if (!cur || (severityOrder[key] ?? 99) < (severityOrder[cur] ?? 99)) {
            riskMap[flag.symbol] = key;
          }
        }
        return (
          <section>
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-semibold">Watchlist Ranking</h3>
              {budget > 0 && <span className="text-xs text-gray-500">Budget: ฿{budget.toLocaleString("th-TH")}</span>}
            </div>
            <div className="bg-white border rounded-xl overflow-x-auto shadow-sm">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-xs text-gray-500">
                    <th className="py-2 pl-4 pr-3">#</th>
                    <th className="py-2 pr-3">Symbol</th>
                    <th className="py-2 pr-3">Signal</th>
                    <th className="py-2 pr-3">Score</th>
                    <th className="py-2 pr-3 hidden sm:table-cell">Sector</th>
                    <th className="py-2 pr-3">Alloc%</th>
                    {budget > 0 && <th className="py-2 pr-3">THB</th>}
                    <th className="py-2 pr-3">Upside</th>
                    <th className="py-2 pr-3">Risk</th>
                    <th className="py-2 hidden lg:table-cell">Reasoning</th>
                  </tr>
                </thead>
                <tbody>
                  {result.watchlist_ranking.map((item) => (
                    <RankingRow key={item.symbol} item={item} budget={budget} riskMap={riskMap} />
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        );
      })()}
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
          {items.map((item) => (
            <li key={item.id}>
              <button
                onClick={() => onSelect(item)}
                className={`w-full text-left px-3 py-2.5 rounded-lg transition-colors text-sm ${
                  selectedId === item.id ? "bg-blue-50 border border-blue-200" : "hover:bg-gray-50"
                }`}
              >
                <p className={`text-xs font-medium ${selectedId === item.id ? "text-blue-700" : "text-gray-700"}`}>
                  {formatDate(item.analyzed_at)}
                </p>
                <p className="text-xs text-gray-400 mt-0.5">
                  {item.swap_count} swap{item.swap_count !== 1 ? "s" : ""} suggested
                </p>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function OptimizerPage() {
  const { portfolios, activeId } = usePortfolio();
  const [selectedPortfolioId, setSelectedPortfolioId] = useState<number | null>(null);
  const [budget, setBudget] = useState("");
  const [result, setResult] = useState<OptimizerResult | null>(null);
  const [history, setHistory] = useState<OptimizerHistoryItem[]>([]);
  const [selectedHistoryId, setSelectedHistoryId] = useState<number | null>(null);
  const [running, setRunning] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState("");


  const portfolioId = selectedPortfolioId ?? activeId;

  const loadHistory = useCallback(async (pid: number) => {
    setLoadingHistory(true);
    try {
      setHistory(await listOptimizerHistory(pid));
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  useEffect(() => {
    if (portfolioId == null) return;
    setResult(null);
    setSelectedHistoryId(null);
    loadHistory(portfolioId);
  }, [portfolioId, loadHistory]);

  async function handleRun() {
    if (portfolioId == null) return;
    setRunning(true);
    setError("");
    try {
      const data = await runOptimizer(portfolioId);
      setResult(data);
      setSelectedHistoryId(data.history_id ?? null);
      await loadHistory(portfolioId);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Optimizer failed");
    } finally {
      setRunning(false);
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

  const budgetNum = parseFloat(budget) || 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold mb-1">Portfolio Optimizer</h1>
        <p className="text-sm text-gray-500">
          Compare your portfolio vs watchlist — find swap opportunities and rank candidates.
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

        <div>
          <label className="block text-xs text-gray-500 mb-1">Budget (THB, optional)</label>
          <input
            type="number" min="0" step="1000"
            value={budget}
            onChange={(e) => setBudget(e.target.value)}
            placeholder="e.g. 500000"
            className="border rounded px-3 py-1.5 text-sm w-40"
          />
        </div>

        <button
          onClick={handleRun}
          disabled={running || portfolioId == null}
          className="bg-blue-600 text-white px-5 py-1.5 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2 self-end"
        >
          {running && <Spinner />}
          {running ? "Optimizing…" : "Run Optimizer"}
        </button>
        {error && <p className="text-red-500 text-xs self-center">{error}</p>}
      </div>

      {running && (
        <div className="text-center py-10 text-gray-400 text-sm space-y-3">
          <Spinner size="lg" />
          <p className="mt-2 font-medium">Running 3-layer analysis…</p>
          <div className="flex items-center justify-center gap-2 text-xs">
            <span className="bg-orange-100 text-orange-700 px-2 py-0.5 rounded font-semibold">L1 Strategist</span>
            <span>→</span>
            <span className="bg-blue-100 text-blue-700 px-2 py-0.5 rounded font-semibold">L2 Challenger</span>
            <span>→</span>
            <span className="bg-purple-100 text-purple-700 px-2 py-0.5 rounded font-semibold">L3 Risk Auditor</span>
          </div>
          <p className="text-xs text-gray-400">This may take 60–180 seconds</p>
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
            <ResultPanel result={result} budget={budgetNum} loading={loadingDetail} />
          </div>
        </div>
      )}
    </div>
  );
}
