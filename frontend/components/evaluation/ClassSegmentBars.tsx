"use client";

// AI Evaluation M5 — ClassAcceptanceBars (EXECUTION_INTELLIGENCE_UX.md §6):
// a rate segmented by trade Reason or override type. Per UX D5/S4, this is
// the only honest way to read acceptance/win-rate — never render an
// unsegmented total anywhere alongside this component.

export interface SegmentBarRow {
  label: string;
  numerator: number;
  denominator: number;
}

export default function ClassSegmentBars({
  rows,
  emptyMessage,
}: {
  rows: SegmentBarRow[];
  emptyMessage?: string;
}) {
  if (rows.length === 0) {
    return <p className="text-xs text-gray-400 italic">{emptyMessage ?? "No segmented data yet."}</p>;
  }
  return (
    <div className="space-y-2">
      {rows.map((r) => {
        const pct = r.denominator > 0 ? Math.round((r.numerator / r.denominator) * 100) : 0;
        return (
          <div key={r.label} className="flex items-center gap-3 text-xs">
            <span className="w-40 shrink-0 text-gray-600 truncate" title={r.label}>
              {r.label}
            </span>
            <div className="flex-1 h-2 rounded-full bg-gray-100 overflow-hidden">
              <div className="h-full bg-blue-500 rounded-full" style={{ width: `${pct}%` }} />
            </div>
            <span className="w-24 shrink-0 text-right text-gray-500 tabular-nums">
              {pct}% ({r.numerator}/{r.denominator})
            </span>
          </div>
        );
      })}
    </div>
  );
}
