"use client";

// UX clarification pass (Three Portfolios rolling-window transparency).
// Makes the selected lookback window and the portfolio's actual comparable
// history two explicitly separate facts, so a newer portfolio never reads
// as "the SET return is wrong" when it's really "90 days were requested but
// only N have happened yet." No new numbers are computed server-side here —
// comparisonStart/comparableDays are derived client-side from the same
// `chart` array the page already renders (see portfolios/page.tsx).

import EvidenceBadge from "./EvidenceBadge";

function Stat({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <p className="text-gray-400 text-[11px] uppercase tracking-wide">{label}</p>
      <p className={`font-semibold text-gray-800 mt-0.5 ${mono ? "tabular-nums" : ""}`}>{value}</p>
    </div>
  );
}

export default function ComparisonWindowCard({
  periodLabel,
  comparisonStart,
  comparisonEnd,
  comparableDays,
  periodDays,
  benchmarkLabel = "SET Index",
}: {
  periodLabel: string;
  comparisonStart: string | null;
  comparisonEnd: string | null;
  comparableDays: number;
  periodDays: number;
  benchmarkLabel?: string;
}) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4">
      <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wide mb-3">Comparison Window</h3>
      <div className="flex flex-wrap gap-x-8 gap-y-3 text-sm">
        <Stat label="Period selected" value={periodLabel} />
        <Stat
          label="Actual comparison"
          value={`${comparisonStart ?? "—"} → ${comparisonEnd ?? "—"}`}
          mono
        />
        <Stat label="Comparable history" value={`${comparableDays} / ${periodDays} days`} mono />
        <div>
          <p className="text-gray-400 text-[11px] uppercase tracking-wide">Evidence</p>
          <div className="mt-1">
            <EvidenceBadge days={comparableDays} />
          </div>
        </div>
        <Stat label="Benchmark" value={benchmarkLabel} />
      </div>
      {comparableDays > 0 && comparableDays < periodDays && (
        <p className="text-[11px] text-gray-400 mt-3 pt-3 border-t">
          Comparable history starts from your portfolio's first available day — the selected period reaches back further than your portfolio does.
        </p>
      )}
    </div>
  );
}
