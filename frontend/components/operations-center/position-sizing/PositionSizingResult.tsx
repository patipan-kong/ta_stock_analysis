"use client";

import type { PositionSizingResult, PositionSuggestion } from "@/lib/api";

const STATUS_COLOR: Record<string, string> = {
  PASS:    "text-emerald-700 bg-emerald-50 border-emerald-200",
  WARNING: "text-amber-700 bg-amber-50 border-amber-200",
  FAIL:    "text-red-700 bg-red-50 border-red-200",
};

const STATUS_DOT: Record<string, string> = {
  PASS:    "bg-emerald-500",
  WARNING: "bg-amber-500",
  FAIL:    "bg-red-500",
};

const SIGNAL_COLOR: Record<string, string> = {
  ACCUMULATE: "text-emerald-700 bg-emerald-50 border-emerald-200",
  BUY:        "text-emerald-600 bg-emerald-50 border-emerald-200",
  WATCH:      "text-blue-600 bg-blue-50 border-blue-200",
  HOLD:       "text-gray-600 bg-gray-50 border-gray-200",
  REDUCE:     "text-amber-700 bg-amber-50 border-amber-200",
  SELL:       "text-red-700 bg-red-50 border-red-200",
};

function ScoreBar({ label, value, max }: { label: string; value: number; max: number }) {
  const pct = max > 0 ? Math.min(100, (value / max) * 100) : 0;
  return (
    <div className="flex items-center gap-2">
      <span className="w-24 text-[10px] text-gray-500 shrink-0">{label}</span>
      <div className="flex-1 h-1 rounded-full bg-gray-100">
        <div className="h-1 rounded-full bg-blue-400" style={{ width: `${pct}%` }} />
      </div>
      <span className="w-8 text-right text-[10px] font-mono text-gray-600">{value.toFixed(1)}</span>
    </div>
  );
}

function SuggestionRow({
  s,
  rank,
  maxScore,
}: {
  s: PositionSuggestion;
  rank: number;
  maxScore: number;
}) {
  const [expanded, setExpanded] = useState(false);
  const pctOfMax = maxScore > 0 ? (s.position_score / maxScore) * 100 : 0;

  return (
    <>
      <tr
        className={`cursor-pointer hover:bg-gray-50 transition-colors ${rank % 2 === 0 ? "bg-white" : "bg-gray-50/40"}`}
        onClick={() => setExpanded((p) => !p)}
      >
        <td className="px-4 py-2.5 font-mono font-semibold text-gray-800 text-xs">
          {s.symbol}
        </td>
        <td className="px-4 py-2.5">
          <span
            className={`rounded-full px-1.5 py-0.5 text-[9px] font-bold border ${SIGNAL_COLOR[s.signal] ?? "text-gray-600 bg-gray-50 border-gray-200"}`}
          >
            {s.signal}
          </span>
        </td>
        <td className="px-4 py-2.5">
          <div className="flex items-center gap-1.5">
            <div className="flex-1 h-1 rounded-full bg-gray-100 max-w-[60px]">
              <div
                className="h-1 rounded-full bg-indigo-400"
                style={{ width: `${pctOfMax}%` }}
              />
            </div>
            <span className="text-[11px] font-mono text-gray-700">{s.position_score.toFixed(1)}</span>
          </div>
        </td>
        <td className="px-4 py-2.5 text-right font-mono font-bold text-emerald-700 text-sm">
          {s.suggested_pct.toFixed(2)}%
        </td>
        <td className="px-4 py-2.5 text-gray-300 text-[10px] select-none">
          {expanded ? "▲" : "▼"}
        </td>
      </tr>
      {expanded && (
        <tr className="bg-indigo-50/30">
          <td colSpan={5} className="px-4 pb-3 pt-1">
            <div className="space-y-1.5 pl-1">
              <ScoreBar label="Signal"     value={s.breakdown.signal_points}     max={5} />
              <ScoreBar label="Confidence" value={s.breakdown.confidence_points} max={5} />
              <ScoreBar label="Fit"        value={s.breakdown.fit_points}        max={5} />
              <ScoreBar label="Priority"   value={s.breakdown.priority_points}   max={3} />
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

import { useState } from "react";

export default function PositionSizingResultView({
  result,
}: {
  result: PositionSizingResult;
}) {
  const overallColor = STATUS_COLOR[result.status];
  const maxScore = Math.max(...result.suggestions.map((s) => s.position_score), 0);

  return (
    <div className="space-y-4">
      {/* Status banner */}
      <div className={`rounded-xl border px-4 py-3 flex items-center gap-3 ${overallColor}`}>
        <span className={`h-2.5 w-2.5 rounded-full shrink-0 ${STATUS_DOT[result.status]}`} />
        <div className="flex-1 min-w-0">
          <p className="text-xs font-bold uppercase tracking-wide">{result.status}</p>
          <p className="text-[10px] opacity-75 mt-0.5">
            {result.suggestions.length} symbol{result.suggestions.length !== 1 ? "s" : ""}&nbsp;·&nbsp;
            {result.total_allocated_pct.toFixed(2)}% allocated&nbsp;·&nbsp;
            {result.deployable_cash_pct.toFixed(1)}% deployable
          </p>
        </div>
      </div>

      {/* Suggestions table */}
      {result.suggestions.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="px-4 py-2 text-left font-semibold text-gray-500 uppercase tracking-wide text-[10px]">Symbol</th>
                <th className="px-4 py-2 text-left font-semibold text-gray-500 uppercase tracking-wide text-[10px]">Signal</th>
                <th className="px-4 py-2 text-left font-semibold text-gray-500 uppercase tracking-wide text-[10px]">Score</th>
                <th className="px-4 py-2 text-right font-semibold text-gray-500 uppercase tracking-wide text-[10px]">Size</th>
                <th className="px-4 py-2 w-4" />
              </tr>
            </thead>
            <tbody>
              {result.suggestions.map((s, i) => (
                <SuggestionRow key={s.symbol} s={s} rank={i} maxScore={maxScore} />
              ))}
              <tr className="border-t border-gray-200 bg-gray-50">
                <td colSpan={3} className="px-4 py-2 font-semibold text-gray-600 text-xs">
                  Total
                </td>
                <td className="px-4 py-2 text-right font-mono font-bold text-gray-800 text-xs">
                  {result.total_allocated_pct.toFixed(2)}%
                </td>
                <td />
              </tr>
            </tbody>
          </table>
          <p className="px-4 py-1.5 text-[10px] text-gray-400 border-t border-gray-100">
            Click any row to see score breakdown
          </p>
        </div>
      )}

      {/* Reasoning */}
      {result.reasoning.length > 0 && (
        <div className="space-y-1.5">
          {result.reasoning.map((line, i) => (
            <div
              key={i}
              className={`rounded-lg border px-3 py-2 flex items-start gap-2 ${
                result.status === "FAIL"
                  ? "border-red-200 bg-red-50"
                  : result.status === "WARNING"
                  ? "border-amber-200 bg-amber-50"
                  : "border-emerald-200 bg-emerald-50"
              }`}
            >
              <span
                className={`text-xs mt-px shrink-0 ${
                  result.status === "FAIL"
                    ? "text-red-500"
                    : result.status === "WARNING"
                    ? "text-amber-500"
                    : "text-emerald-600"
                }`}
              >
                {result.status === "FAIL" ? "✕" : result.status === "WARNING" ? "⚠" : "✓"}
              </span>
              <p
                className={`text-[11px] leading-relaxed ${
                  result.status === "FAIL"
                    ? "text-red-800"
                    : result.status === "WARNING"
                    ? "text-amber-800"
                    : "text-emerald-800"
                }`}
              >
                {line}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
