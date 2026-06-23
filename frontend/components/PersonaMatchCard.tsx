"use client";

import { useState } from "react";
import type { OptimizerResult, StrategyPersona, StrategyProfile } from "@/lib/api";

// ── Match category config ─────────────────────────────────────────────────────

type MatchCategory = "EXCELLENT" | "STRONG" | "GOOD" | "PARTIAL" | "POOR";

function matchCategory(score: number): MatchCategory {
  if (score >= 90) return "EXCELLENT";
  if (score >= 75) return "STRONG";
  if (score >= 60) return "GOOD";
  if (score >= 40) return "PARTIAL";
  return "POOR";
}

const MATCH_CFG: Record<MatchCategory, {
  label: string;
  badge: string;
  scoreColor: string;
  border: string;
  bg: string;
  bar: string;
}> = {
  EXCELLENT: {
    label:      "Excellent Match",
    badge:      "bg-emerald-100 border-emerald-300 text-emerald-800",
    scoreColor: "text-emerald-700",
    border:     "border-emerald-200",
    bg:         "bg-emerald-50",
    bar:        "bg-emerald-500",
  },
  STRONG: {
    label:      "Strong Match",
    badge:      "bg-green-100 border-green-300 text-green-800",
    scoreColor: "text-green-700",
    border:     "border-green-200",
    bg:         "bg-green-50",
    bar:        "bg-green-500",
  },
  GOOD: {
    label:      "Good Match",
    badge:      "bg-blue-100 border-blue-300 text-blue-800",
    scoreColor: "text-blue-700",
    border:     "border-blue-200",
    bg:         "bg-blue-50",
    bar:        "bg-blue-500",
  },
  PARTIAL: {
    label:      "Partial Match",
    badge:      "bg-amber-100 border-amber-300 text-amber-800",
    scoreColor: "text-amber-700",
    border:     "border-amber-200",
    bg:         "bg-amber-50",
    bar:        "bg-amber-500",
  },
  POOR: {
    label:      "Poor Match",
    badge:      "bg-red-100 border-red-300 text-red-800",
    scoreColor: "text-red-700",
    border:     "border-red-200",
    bg:         "bg-red-50",
    bar:        "bg-red-500",
  },
};

const PERSONA_CFG: Record<string, { icon: string; color: string }> = {
  BALANCED:  { icon: "⚖",  color: "text-blue-700"   },
  GROWTH:    { icon: "🚀", color: "text-green-700"  },
  VALUE:     { icon: "💎", color: "text-purple-700" },
  DIVIDEND:  { icon: "💰", color: "text-amber-700"  },
  MOMENTUM:  { icon: "⚡", color: "text-orange-700" },
  PASSIVE:   { icon: "🌿", color: "text-teal-700"   },
};

const FACTOR_BAR: Record<string, string> = {
  growth:   "bg-green-500",
  value:    "bg-purple-500",
  momentum: "bg-orange-500",
  quality:  "bg-blue-500",
  dividend: "bg-amber-500",
};

// ── Summary sentence builder ──────────────────────────────────────────────────

function buildSummary(
  alignScore: number,
  gaps: [string, number][],   // [factor, raw_fraction] sorted by |delta| desc
): string {
  if (alignScore >= 90) return "Your portfolio closely matches the selected strategy.";

  const top = gaps.slice(0, 2);
  if (top.length === 0) return "No significant factor differences detected.";

  const over  = top.filter(([, v]) => v > 0).map(([f]) => f);
  const under = top.filter(([, v]) => v < 0).map(([f]) => f);

  if (over.length > 0 && under.length === 0) {
    return `Portfolio has more ${over.join(" and ")} exposure than the selected strategy targets.`;
  }
  if (under.length > 0 && over.length === 0) {
    return `Portfolio has lower ${under.join(" and ")} exposure than the selected strategy targets.`;
  }
  const overStr  = over.map((f)  => f).join(" and ");
  const underStr = under.map((f) => f).join(" and ");
  return `Portfolio has more ${overStr} but lower ${underStr} exposure than the selected strategy targets.`;
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function PersonaMatchCard({
  result,
  profiles,
}: {
  result: OptimizerResult;
  profiles: StrategyProfile[];
}) {
  const [expanded, setExpanded] = useState(false);

  const alignScore = result.factor_alignment_score ?? 100;
  const persona    = result.target_persona as StrategyPersona | undefined;
  const profile    = profiles.find((p) => p.id === persona);
  const pCfg       = persona ? (PERSONA_CFG[persona] ?? PERSONA_CFG.BALANCED) : null;
  const cat        = matchCategory(alignScore);
  const cfg        = MATCH_CFG[cat];

  // Sort all gaps by absolute magnitude for summary + detail list
  const allGaps: [string, number][] = result.factor_drift
    ? Object.entries(result.factor_drift).sort(([, a], [, b]) => Math.abs(b) - Math.abs(a))
    : [];

  const top2 = allGaps.slice(0, 2);
  const summary = buildSummary(alignScore, top2);

  const personaLabel = profile?.label ?? persona ?? "Balanced";

  return (
    <section className={`border rounded-xl p-5 shadow-sm space-y-4 ${cfg.bg} ${cfg.border}`}>

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2.5">
          {pCfg && (
            <span className={`text-xl leading-none ${pCfg.color}`}>{pCfg.icon}</span>
          )}
          <div>
            <p className="text-[10px] font-bold text-gray-400 uppercase tracking-widest">
              Persona Match
            </p>
            <h3 className="font-bold text-gray-800 text-sm leading-tight">
              {personaLabel}
            </h3>
          </div>
        </div>

        <span
          className={`text-[11px] font-bold px-2.5 py-1 rounded-full border whitespace-nowrap ${cfg.badge}`}
        >
          {cfg.label}
        </span>
      </div>

      {/* ── Score ──────────────────────────────────────────────────────── */}
      <div className="flex items-end gap-2">
        <span className={`text-4xl font-black tabular-nums leading-none ${cfg.scoreColor}`}>
          {alignScore.toFixed(0)}
        </span>
        <span className="text-lg text-gray-300 font-light mb-0.5">/ 100</span>
      </div>

      {/* Progress bar */}
      <div className="h-2 bg-white/60 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${cfg.bar}`} style={{ width: `${alignScore}%` }} />
      </div>

      {/* ── One-sentence summary ───────────────────────────────────────── */}
      <p className="text-[12px] text-gray-700 leading-snug">{summary}</p>

      {/* ── Top 2 factor gaps ─────────────────────────────────────────── */}
      {top2.length > 0 && (
        <div className="space-y-2">
          <p className="text-[10px] font-semibold text-gray-400 uppercase tracking-wide">
            Main differences
          </p>
          {top2.map(([factor, delta]) => {
            const pp       = delta * 100;
            const isOver   = pp > 0;
            const barColor = FACTOR_BAR[factor] ?? "bg-gray-400";
            return (
              <div key={factor} className="flex items-center gap-2.5">
                <span className="capitalize text-xs text-gray-600 w-20 shrink-0">{factor}</span>
                <div className="flex-1 h-1.5 bg-white/60 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${barColor} opacity-70`}
                    style={{ width: `${Math.min(100, Math.abs(pp) * 2)}%` }}
                  />
                </div>
                <span
                  className={`text-[11px] font-bold tabular-nums w-14 text-right ${
                    isOver ? "text-emerald-700" : "text-red-600"
                  }`}
                >
                  {isOver ? "+" : ""}{pp.toFixed(1)}pp
                </span>
                <span className="text-[10px] text-gray-400 w-16 shrink-0">
                  {isOver ? "above target" : "below target"}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* ── Expandable detail ─────────────────────────────────────────── */}
      {allGaps.length > 0 && (
        <div>
          <button
            className="flex items-center gap-1.5 text-[11px] text-gray-400 hover:text-gray-600 transition-colors"
            onClick={() => setExpanded((p) => !p)}
          >
            <span className="text-[9px]">{expanded ? "▼" : "▶"}</span>
            <span>
              {expanded ? "Hide" : "View"} Detailed Factor Alignment
            </span>
          </button>

          {expanded && (
            <div className="mt-3 space-y-2.5">
              {allGaps.map(([factor, delta]) => {
                const pp       = delta * 100;
                const isOver   = pp > 0;
                const barColor = FACTOR_BAR[factor] ?? "bg-gray-400";
                return (
                  <div key={factor} className="space-y-0.5">
                    <div className="flex items-center justify-between text-[11px]">
                      <span className="capitalize text-gray-600">{factor}</span>
                      <span
                        className={`font-semibold tabular-nums ${
                          isOver ? "text-emerald-700" : "text-red-600"
                        }`}
                      >
                        {isOver ? "+" : ""}{pp.toFixed(1)}pp vs target
                      </span>
                    </div>
                    <div className="h-1.5 bg-white/60 rounded-full overflow-hidden">
                      <div
                        className={`h-full ${barColor} opacity-60`}
                        style={{ width: `${Math.min(100, Math.abs(pp) * 2)}%` }}
                      />
                    </div>
                  </div>
                );
              })}
              <p className="text-[10px] text-gray-400 pt-1">
                Positive = portfolio holds more of this factor than {personaLabel} targets.
                Negative = portfolio holds less.
              </p>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
