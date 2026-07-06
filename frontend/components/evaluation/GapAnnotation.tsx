"use client";

// AI Evaluation M4 — named Gap A / Gap B figure: value + one-line
// interpretation. Renders only backend-delivered values; when the backing
// field ships as an UnavailableField (e.g. implementation_shortfall pending
// M6's ideal_series.py), this renders the honest unavailable state rather
// than fabricating a gap from other numbers on the page.

export default function GapAnnotation({
  label,
  value,
  interpretation,
  unavailableReason,
}: {
  label: string;
  value?: number | null;
  interpretation?: string;
  unavailableReason?: string | null;
}) {
  if (unavailableReason || value == null) {
    return (
      <div className="text-xs text-gray-400">
        <span className="font-medium text-gray-500">{label}</span>{" "}
        <span className="italic">unavailable{unavailableReason ? ` — ${unavailableReason}` : ""}</span>
      </div>
    );
  }
  const sign = value >= 0 ? "+" : "";
  return (
    <div className="text-xs">
      <span className="font-medium text-gray-600">{label}</span>{" "}
      <span className={`font-bold tabular-nums ${value >= 0 ? "text-green-700" : "text-red-600"}`}>
        {sign}
        {value.toFixed(1)}%
      </span>
      {interpretation && <span className="text-gray-400 ml-1.5">{interpretation}</span>}
    </div>
  );
}
