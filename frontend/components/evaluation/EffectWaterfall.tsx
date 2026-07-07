"use client";

// AI Evaluation M5 — EffectWaterfall (EXECUTION_INTELLIGENCE_UX.md §6):
// opportunity-cost / attribution decomposition. Horizontal bars sorted by
// |magnitude| (caller-sorted, e.g. by the backend already), net row pinned.
// Symmetric by construction (§12) — green rows (diverging helped) and red
// rows (diverging cost) share one scale; every value here is counterfactual
// (marked with the trailing "*", same convention as CounterfactualValue)
// since nothing in this component is realized money.

export interface WaterfallRow {
  key: string | number;
  label: string;
  value: number;
  note?: string;
  onClick?: () => void;
}

export default function EffectWaterfall({
  rows,
  net,
  netLabel = "NET",
}: {
  rows: WaterfallRow[];
  net?: number | null;
  netLabel?: string;
}) {
  const scale = Math.max(1, ...rows.map((r) => Math.abs(r.value)));
  return (
    <div className="space-y-2">
      {rows.map((r) => {
        const widthPct = Math.min(100, (Math.abs(r.value) / scale) * 100);
        const positive = r.value >= 0;
        return (
          <div
            key={r.key}
            className={`flex items-center gap-3 text-xs ${r.onClick ? "cursor-pointer" : ""}`}
            onClick={r.onClick}
          >
            <span className="w-40 shrink-0 text-gray-700 truncate" title={r.label}>
              {r.label}
            </span>
            <div className="flex-1 h-4 flex items-center bg-gray-50 rounded overflow-hidden">
              <div
                className={`h-3 rounded ${positive ? "bg-green-400" : "bg-red-400"}`}
                style={{ width: `${widthPct}%` }}
              />
            </div>
            <span
              className={`w-20 shrink-0 text-right font-semibold tabular-nums italic ${
                positive ? "text-green-700" : "text-red-600"
              }`}
              title="Counterfactual — not realized money."
            >
              {positive ? "+" : ""}
              {r.value.toFixed(1)}%*
            </span>
            {r.note && <span className="hidden lg:block text-gray-400 italic w-48 truncate" title={r.note}>{r.note}</span>}
          </div>
        );
      })}
      {net != null && (
        <div className="flex items-center gap-3 text-xs pt-2 border-t font-bold">
          <span className="w-40 shrink-0 text-gray-800">{netLabel}</span>
          <div className="flex-1" />
          <span className={`w-20 shrink-0 text-right tabular-nums italic ${net >= 0 ? "text-green-700" : "text-red-600"}`}>
            {net >= 0 ? "+" : ""}
            {net.toFixed(1)}%*
          </span>
        </div>
      )}
    </div>
  );
}
