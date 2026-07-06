"use client";

// AI Evaluation M4 — the ONLY way a hypothetical (not-realized) return may
// render anywhere in the Evaluation hub (EXECUTION_INTELLIGENCE_UX.md §6, D7).
// Muted color + asterisk + tooltip so real and hypothetical money are never
// visually confusable.

export default function CounterfactualValue({
  value,
  suffix = "%",
  decimals = 1,
  className = "",
}: {
  value: number | null | undefined;
  suffix?: string;
  decimals?: number;
  className?: string;
}) {
  if (value == null) return <span className="text-gray-300">—</span>;
  const sign = value >= 0 ? "+" : "";
  return (
    <span
      className={`text-gray-400 italic tabular-nums ${className}`}
      title="Counterfactual — not realized money. This is what the frozen shadow would have returned; the plan was not executed."
    >
      {sign}
      {value.toFixed(decimals)}
      {suffix}*
    </span>
  );
}
