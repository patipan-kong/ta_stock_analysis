"use client";

// AI Evaluation M4 — every page header. Evaluation reads batch-computed
// artifacts only (daily valuation + grading at 17:45 ICT) — there are no
// streaming numbers on any evaluation screen. Stale (>24h) turns amber with
// a reason, matching the ENGINEERING_PRINCIPLES observable-degradation rule.

function isStale(asOf: string): boolean {
  const t = new Date(asOf).getTime();
  if (Number.isNaN(t)) return false;
  return Date.now() - t > 24 * 60 * 60 * 1000;
}

export default function AsOfStamp({ asOf }: { asOf: string | null | undefined }) {
  if (!asOf) return null;
  const stale = isStale(asOf);
  const d = new Date(asOf);
  const label = Number.isNaN(d.getTime())
    ? asOf
    : d.toLocaleString("th-TH", { dateStyle: "medium", timeStyle: "short" });
  return (
    <span
      className={`text-xs font-medium whitespace-nowrap ${stale ? "text-amber-600" : "text-gray-400"}`}
      title={stale ? "Data older than 24h — the daily valuation/grading job may be delayed." : "Last computed at this batch run."}
    >
      {stale && "⚠ "}
      as of {label}
    </span>
  );
}
