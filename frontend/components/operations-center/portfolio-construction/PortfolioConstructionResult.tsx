"use client";

import type { PortfolioConstructionResult, BasketImpact } from "@/lib/api";

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

const STATUS_LABEL: Record<string, string> = {
  PASS:    "PASS",
  WARNING: "WARNING",
  FAIL:    "FAIL",
};

function SectorImpactRow({ impact }: { impact: BasketImpact }) {
  const barWidth = impact.sector_limit_pct > 0
    ? Math.min(100, (impact.after_pct / impact.sector_limit_pct) * 100)
    : 0;
  const barColor =
    impact.status === "FAIL"    ? "bg-red-500"
    : impact.status === "WARNING" ? "bg-amber-500"
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
                impact.status === "FAIL"    ? "text-red-600 font-bold"
                : impact.status === "WARNING" ? "text-amber-600 font-bold"
                : "text-gray-800 font-semibold"
              }
            >
              {impact.after_pct.toFixed(1)}%
            </span>
          </span>
          <span className="text-gray-400">lim {impact.sector_limit_pct.toFixed(0)}%</span>
        </div>
      </div>
      <div className="h-1.5 w-full rounded-full bg-gray-100">
        <div
          className={`h-1.5 rounded-full transition-all ${barColor}`}
          style={{ width: `${Math.min(barWidth, 100)}%` }}
        />
      </div>
    </div>
  );
}

export default function PortfolioConstructionResultView({
  result,
}: {
  result: PortfolioConstructionResult;
}) {
  const overallColor = STATUS_COLOR[result.overall_status];
  const canExecute = result.overall_status === "PASS";

  return (
    <div className="space-y-4">
      {/* Overall status banner */}
      <div className={`rounded-xl border px-4 py-3 flex items-center gap-3 ${overallColor}`}>
        <span className={`h-2.5 w-2.5 rounded-full shrink-0 ${STATUS_DOT[result.overall_status]}`} />
        <div className="flex-1 min-w-0">
          <p className="text-xs font-bold">
            {canExecute ? "Suggested Basket" : "No Viable Allocation"}&nbsp;—&nbsp;
            <span className="uppercase">{STATUS_LABEL[result.overall_status]}</span>
          </p>
          {canExecute && (
            <p className="text-[10px] opacity-80 mt-0.5">
              {result.allocations.length} symbol{result.allocations.length !== 1 ? "s" : ""}{" "}
              · {result.recommended_allocation_pct}% per position
              · {result.total_deployment_pct.toFixed(1)}% total
            </p>
          )}
        </div>
      </div>

      {/* Suggested allocations table */}
      {canExecute && result.allocations.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white overflow-hidden">
          <table className="w-full text-xs">
            <thead>
              <tr className="border-b border-gray-100 bg-gray-50">
                <th className="px-4 py-2 text-left font-semibold text-gray-500 uppercase tracking-wide text-[10px]">
                  Symbol
                </th>
                <th className="px-4 py-2 text-right font-semibold text-gray-500 uppercase tracking-wide text-[10px]">
                  % per position
                </th>
              </tr>
            </thead>
            <tbody>
              {result.allocations.map((alloc, i) => (
                <tr
                  key={alloc.symbol}
                  className={i % 2 === 0 ? "bg-white" : "bg-gray-50/50"}
                >
                  <td className="px-4 py-2 font-mono font-semibold text-gray-800">
                    {alloc.symbol}
                  </td>
                  <td className="px-4 py-2 text-right font-mono font-bold text-emerald-700">
                    {alloc.suggested_pct.toFixed(1)}%
                  </td>
                </tr>
              ))}
              <tr className="border-t border-gray-200 bg-gray-50">
                <td className="px-4 py-2 font-semibold text-gray-600">Total</td>
                <td className="px-4 py-2 text-right font-mono font-bold text-gray-800">
                  {result.total_deployment_pct.toFixed(1)}%
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {/* Cash impact */}
      <div className="rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 space-y-1.5">
        <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">
          Cash Position
        </p>
        <div className="flex items-center gap-3 font-mono text-sm">
          <span className="text-gray-600">
            {result.simulation.cash_before_pct.toFixed(1)}%
          </span>
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

      {/* Reasoning */}
      {result.reasoning.length > 0 && (
        <div className="space-y-1.5">
          {result.reasoning.map((line, i) => (
            <div
              key={i}
              className={`rounded-lg border px-3 py-2 flex items-start gap-2 ${
                i === 0 && result.overall_status !== "PASS" && result.reasoning.length === 1
                  ? "border-red-200 bg-red-50"
                  : i === 0 && result.reasoning.length > 1
                  ? "border-amber-200 bg-amber-50"
                  : "border-emerald-200 bg-emerald-50"
              }`}
            >
              <span
                className={`text-xs mt-px shrink-0 ${
                  i === 0 && result.overall_status !== "PASS" && result.reasoning.length === 1
                    ? "text-red-500"
                    : i === 0 && result.reasoning.length > 1
                    ? "text-amber-500"
                    : "text-emerald-600"
                }`}
              >
                {i === 0 && result.reasoning.length > 1 ? "⚠" : i === 0 && result.overall_status !== "PASS" ? "✕" : "✓"}
              </span>
              <p
                className={`text-[11px] leading-relaxed ${
                  i === 0 && result.overall_status !== "PASS" && result.reasoning.length === 1
                    ? "text-red-800"
                    : i === 0 && result.reasoning.length > 1
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

      {/* Sector impacts */}
      {result.simulation.impacts.length > 0 && (
        <div className="rounded-xl border border-gray-200 bg-white px-4 py-3 space-y-3">
          <p className="text-[10px] font-semibold text-gray-500 uppercase tracking-wide">
            Sector Impact
          </p>
          {result.simulation.impacts.map((imp) => (
            <SectorImpactRow key={imp.sector} impact={imp} />
          ))}
        </div>
      )}
    </div>
  );
}
