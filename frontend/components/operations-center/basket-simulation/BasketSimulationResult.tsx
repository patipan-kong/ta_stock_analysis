"use client";

import type { BasketSimulationResult, BasketImpact } from "@/lib/api";

const STATUS_COLOR: Record<string, string> = {
  PASS:    "text-emerald-700 bg-emerald-50 border-emerald-200",
  WARNING: "text-amber-700 bg-amber-50 border-amber-200",
  FAIL:    "text-red-700 bg-red-50 border-red-200",
};

const STATUS_LABEL: Record<string, string> = {
  PASS:    "PASS",
  WARNING: "WARNING",
  FAIL:    "FAIL",
};

const STATUS_DOT: Record<string, string> = {
  PASS:    "bg-emerald-500",
  WARNING: "bg-amber-500",
  FAIL:    "bg-red-500",
};

function ImpactRow({ impact }: { impact: BasketImpact }) {
  const barWidth = Math.min(100, (impact.after_pct / impact.sector_limit_pct) * 100);
  const barColor =
    impact.status === "FAIL"
      ? "bg-red-500"
      : impact.status === "WARNING"
      ? "bg-amber-500"
      : "bg-emerald-500";

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[11px]">
        <span className="font-semibold text-gray-700">{impact.sector}</span>
        <div className="flex items-center gap-3 font-mono text-gray-500">
          <span>
            {impact.before_pct.toFixed(1)}%{" "}
            <span className="text-gray-300">→</span>{" "}
            <span
              className={
                impact.status === "FAIL"
                  ? "text-red-600 font-bold"
                  : impact.status === "WARNING"
                  ? "text-amber-600 font-bold"
                  : "text-gray-800 font-semibold"
              }
            >
              {impact.after_pct.toFixed(1)}%
            </span>
          </span>
          <span className="text-gray-400">lim {impact.sector_limit_pct.toFixed(0)}%</span>
          <span
            className={`rounded-full px-1.5 py-0.5 text-[9px] font-bold border ${STATUS_COLOR[impact.status]}`}
          >
            {STATUS_LABEL[impact.status]}
          </span>
        </div>
      </div>
      {/* Progress bar */}
      <div className="h-1.5 w-full rounded-full bg-gray-100">
        <div
          className={`h-1.5 rounded-full transition-all ${barColor}`}
          style={{ width: `${Math.min(barWidth, 100)}%` }}
        />
      </div>
    </div>
  );
}

export default function BasketSimulationResultView({
  result,
}: {
  result: BasketSimulationResult;
}) {
  const overallColor = STATUS_COLOR[result.overall_status];

  return (
    <div className="space-y-4">
      {/* Overall status banner */}
      <div className={`rounded-xl border px-4 py-3 flex items-center gap-3 ${overallColor}`}>
        <span className={`h-2.5 w-2.5 rounded-full shrink-0 ${STATUS_DOT[result.overall_status]}`} />
        <div className="flex-1 min-w-0">
          <p className="text-xs font-bold">
            Overall Status:{" "}
            <span className="uppercase">{STATUS_LABEL[result.overall_status]}</span>
          </p>
          <p className="text-[10px] opacity-80 mt-0.5">
            {result.symbols.length} symbol{result.symbols.length !== 1 ? "s" : ""} ·{" "}
            {result.allocation_pct}% per position ·{" "}
            {result.total_capital_required_pct.toFixed(1)}% total deployment
          </p>
        </div>
      </div>

      {/* Cash impact */}
      <div className="rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 space-y-1.5">
        <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">
          Cash Position
        </p>
        <div className="flex items-center gap-3 font-mono text-sm">
          <span className="text-gray-600">{result.cash_before_pct.toFixed(1)}%</span>
          <span className="text-gray-300">→</span>
          <span
            className={
              result.cash_after_pct < 0
                ? "text-red-600 font-bold"
                : result.cash_after_pct < 5
                ? "text-amber-600 font-semibold"
                : "text-gray-800 font-semibold"
            }
          >
            {result.cash_after_pct.toFixed(1)}%
          </span>
        </div>
      </div>

      {/* Sector impacts */}
      {result.impacts.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white px-4 py-3 space-y-3">
          <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">
            Sector Impact
          </p>
          {result.impacts.map((imp) => (
            <ImpactRow key={imp.sector} impact={imp} />
          ))}
        </div>
      )}

      {/* Warnings */}
      {result.warnings.length > 0 && (
        <div className="space-y-1.5">
          {result.warnings.map((w, i) => (
            <div
              key={i}
              className="rounded-lg border border-amber-200 bg-amber-50 px-3 py-2 flex items-start gap-2"
            >
              <span className="text-amber-500 text-xs mt-px shrink-0">⚠</span>
              <p className="text-[11px] text-amber-800 leading-relaxed">{w}</p>
            </div>
          ))}
        </div>
      )}

      {/* Symbol list */}
      <div className="flex flex-wrap gap-1.5">
        {result.symbols.map((sym) => (
          <span
            key={sym}
            className="rounded-md border border-gray-200 bg-gray-50 px-2 py-0.5 font-mono text-[10px] text-gray-600"
          >
            {sym}
          </span>
        ))}
      </div>
    </div>
  );
}
