"use client";

// AI Evaluation M5 — EffectWaterfall (EXECUTION_INTELLIGENCE_UX.md §6):
// shared horizontal-bar decomposition, used by two screens whose numbers
// have different provenance:
//   - Opportunity Cost (S6): rows are hypothetical — "what would have
//     happened had you followed the AI instead" — never realized money.
//   - Attribution (S8): rows are the real, realized decomposition of your
//     actual return (fees paid, fill-price timing, override deltas) — this
//     money already happened.
// `variant` controls which convention renders: "counterfactual" (default,
// preserves S6's existing "*" + tooltip marking) or "realized" (no
// asterisk, no italic, a plain "already in your return" tooltip) so a
// hypothetical number is never visually confused with a realized one.

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
  variant = "counterfactual",
}: {
  rows: WaterfallRow[];
  net?: number | null;
  netLabel?: string;
  variant?: "counterfactual" | "realized";
}) {
  const isCounterfactual = variant === "counterfactual";
  const suffix = isCounterfactual ? "%*" : "%";
  const valueStyle = isCounterfactual ? "italic" : "";
  const title = isCounterfactual
    ? "Counterfactual — not realized money."
    : "Realized — already reflected in your actual return.";
  const scale = Math.max(1, ...rows.map((r) => Math.abs(r.value)));
  return (
    <div className="space-y-2.5 sm:space-y-2">
      {rows.map((r) => {
        const widthPct = Math.min(100, (Math.abs(r.value) / scale) * 100);
        const positive = r.value >= 0;
        return (
          <div
            key={r.key}
            className={`flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3 text-xs ${r.onClick ? "cursor-pointer rounded hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-300" : ""}`}
            onClick={r.onClick}
            role={r.onClick ? "button" : undefined}
            tabIndex={r.onClick ? 0 : undefined}
            onKeyDown={
              r.onClick
                ? (e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault();
                      r.onClick!();
                    }
                  }
                : undefined
            }
          >
            <div className="flex items-center justify-between sm:contents">
              <span className="sm:w-40 sm:shrink-0 text-gray-700 truncate" title={r.label}>
                {r.label}
              </span>
              <span
                className={`sm:hidden font-semibold tabular-nums ${valueStyle} ${positive ? "text-green-700" : "text-red-600"}`}
                title={title}
              >
                {positive ? "+" : ""}
                {r.value.toFixed(1)}{suffix}
              </span>
            </div>
            <div className="flex-1 h-4 flex items-center bg-gray-50 rounded overflow-hidden">
              <div
                className={`h-3 rounded ${positive ? "bg-green-400" : "bg-red-400"}`}
                style={{ width: `${widthPct}%` }}
              />
            </div>
            <span
              className={`hidden sm:inline w-20 shrink-0 text-right font-semibold tabular-nums ${valueStyle} ${
                positive ? "text-green-700" : "text-red-600"
              }`}
              title={title}
            >
              {positive ? "+" : ""}
              {r.value.toFixed(1)}{suffix}
            </span>
            {r.note && <span className="hidden lg:block text-gray-400 italic w-48 truncate" title={r.note}>{r.note}</span>}
          </div>
        );
      })}
      {net != null && (
        <div className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-3 text-xs pt-2 border-t font-bold">
          <div className="flex items-center justify-between sm:contents">
            <span className="sm:w-40 sm:shrink-0 text-gray-800">{netLabel}</span>
            <span className={`sm:hidden tabular-nums ${valueStyle} ${net >= 0 ? "text-green-700" : "text-red-600"}`} title={title}>
              {net >= 0 ? "+" : ""}
              {net.toFixed(1)}{suffix}
            </span>
          </div>
          <div className="flex-1" />
          <span className={`hidden sm:inline w-20 shrink-0 text-right tabular-nums ${valueStyle} ${net >= 0 ? "text-green-700" : "text-red-600"}`} title={title}>
            {net >= 0 ? "+" : ""}
            {net.toFixed(1)}{suffix}
          </span>
        </div>
      )}
    </div>
  );
}
