"use client";

import type { FactorExposureResult } from "@/lib/api";

const FACTOR_META: Array<{
  key: keyof FactorExposureResult["factor_exposures"];
  label: string;
  color: string;
  bg: string;
  icon: string;
}> = [
  { key: "quality",  label: "Quality",  color: "#14b8a6", bg: "#f0fdfa", icon: "◆" },
  { key: "growth",   label: "Growth",   color: "#10b981", bg: "#f0fdf4", icon: "↑" },
  { key: "momentum", label: "Momentum", color: "#8b5cf6", bg: "#faf5ff", icon: "▶" },
  { key: "value",    label: "Value",    color: "#3b82f6", bg: "#eff6ff", icon: "⬟" },
  { key: "dividend", label: "Dividend", color: "#f59e0b", bg: "#fffbeb", icon: "%" },
];

const STRENGTH_CONFIG: Record<string, { cls: string; width: string }> = {
  "Strong":        { cls: "text-emerald-700 bg-emerald-50 border border-emerald-200", width: "" },
  "Moderate-High": { cls: "text-blue-700 bg-blue-50 border border-blue-200",          width: "" },
  "Moderate":      { cls: "text-amber-700 bg-amber-50 border border-amber-200",        width: "" },
  "Moderate-Low":  { cls: "text-orange-700 bg-orange-50 border border-orange-200",     width: "" },
  "Weak":          { cls: "text-red-700 bg-red-50 border border-red-200",              width: "" },
  "Unavailable":   { cls: "text-gray-500 bg-gray-50 border border-gray-200",           width: "" },
};

function FactorBar({ score, color }: { score: number | null; color: string }) {
  const pct = score ?? 0;
  return (
    <div className="flex-1 relative h-2 bg-gray-100 rounded-full overflow-hidden">
      <div
        className="absolute left-0 top-0 h-2 rounded-full transition-all duration-700"
        style={{ width: `${pct}%`, backgroundColor: color }}
      />
      {/* Midpoint marker */}
      <div className="absolute left-1/2 top-0 h-full w-px bg-gray-300 opacity-50" />
    </div>
  );
}

interface Props {
  factorExposures: FactorExposureResult["factor_exposures"];
}

export default function FactorExposureBars({ factorExposures }: Props) {
  const sorted = [...FACTOR_META].sort((a, b) => {
    const sa = factorExposures[a.key]?.score ?? -1;
    const sb = factorExposures[b.key]?.score ?? -1;
    return sb - sa;
  });

  return (
    <div className="bg-white border border-gray-100 rounded-2xl shadow-sm p-5">
      <div className="mb-5">
        <h3 className="text-sm font-bold text-gray-800">Factor Exposure Detail</h3>
        <p className="text-xs text-gray-400 mt-0.5">Portfolio-weighted exposure scores · sorted strongest → weakest</p>
      </div>

      <div className="space-y-5">
        {sorted.map(({ key, label, color, bg, icon }) => {
          const detail = factorExposures[key];
          const score  = detail?.score ?? null;
          const lbl    = detail?.label ?? "Unavailable";
          const desc   = detail?.description ?? "";
          const strengthCfg = STRENGTH_CONFIG[lbl] ?? STRENGTH_CONFIG["Unavailable"];

          return (
            <div key={key}>
              {/* Row: icon + name + bar + score */}
              <div className="flex items-center gap-3 mb-1.5">
                <div
                  className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold shrink-0"
                  style={{ backgroundColor: bg, color }}
                >
                  {icon}
                </div>
                <span className="text-sm font-semibold text-gray-800 w-20 shrink-0">{label}</span>
                <FactorBar score={score} color={color} />
                <div className="flex items-center gap-2 shrink-0">
                  <span className="text-sm font-bold tabular-nums text-gray-900 w-8 text-right">
                    {score != null ? score.toFixed(0) : "—"}
                  </span>
                  <span className={`text-[11px] font-semibold px-2 py-0.5 rounded-full whitespace-nowrap ${strengthCfg.cls}`}>
                    {lbl}
                  </span>
                </div>
              </div>
              {/* Description */}
              <p className="text-xs text-gray-500 leading-relaxed pl-10">{desc}</p>
            </div>
          );
        })}
      </div>

      {/* Scale reference */}
      <div className="mt-5 pt-4 border-t border-gray-50 flex items-center justify-between text-[11px] text-gray-400">
        <span>0 — Lowest relative exposure</span>
        <span className="mx-2 text-gray-200">|</span>
        <span>50 — Median</span>
        <span className="mx-2 text-gray-200">|</span>
        <span>100 — Highest relative exposure</span>
      </div>
    </div>
  );
}
