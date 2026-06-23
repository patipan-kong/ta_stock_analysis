"use client";

import type { ActionSummary, ActionSummaryEntry } from "@/lib/api";

// ─── Config ──────────────────────────────────────────────────────────────────

const CARDS: {
  key: keyof Omit<ActionSummary, "hold">;
  label: string;
  emptyText: string;
  theme: {
    header: string;
    badge: string;
    chip: string;
    chipText: string;
    changePos: string;
    changeNeg: string;
    border: string;
    dot: string;
  };
}[] = [
  {
    key: "sell",
    label: "SELL",
    emptyText: "No exits recommended",
    theme: {
      header: "text-red-700",
      badge: "bg-red-100 text-red-700 border-red-200",
      chip:  "bg-red-50 border-red-200 hover:bg-red-100",
      chipText: "text-red-800",
      changePos: "text-green-600",
      changeNeg: "text-red-600",
      border: "border-red-100",
      dot: "bg-red-400",
    },
  },
  {
    key: "reduce",
    label: "REDUCE",
    emptyText: "No reductions needed",
    theme: {
      header: "text-amber-700",
      badge: "bg-amber-100 text-amber-700 border-amber-200",
      chip:  "bg-amber-50 border-amber-200 hover:bg-amber-100",
      chipText: "text-amber-800",
      changePos: "text-green-600",
      changeNeg: "text-amber-600",
      border: "border-amber-100",
      dot: "bg-amber-400",
    },
  },
  {
    key: "accumulate",
    label: "ACCUMULATE",
    emptyText: "No additions suggested",
    theme: {
      header: "text-teal-700",
      badge: "bg-teal-100 text-teal-700 border-teal-200",
      chip:  "bg-teal-50 border-teal-200 hover:bg-teal-100",
      chipText: "text-teal-800",
      changePos: "text-teal-600",
      changeNeg: "text-red-500",
      border: "border-teal-100",
      dot: "bg-teal-400",
    },
  },
  {
    key: "new_position",
    label: "NEW POSITION",
    emptyText: "No new positions",
    theme: {
      header: "text-green-700",
      badge: "bg-green-100 text-green-700 border-green-200",
      chip:  "bg-green-50 border-green-200 hover:bg-green-100",
      chipText: "text-green-800",
      changePos: "text-green-600",
      changeNeg: "text-red-500",
      border: "border-green-100",
      dot: "bg-green-500",
    },
  },
];

// ─── Sub-components ───────────────────────────────────────────────────────────

function SymbolChip({
  entry,
  theme,
}: {
  entry: ActionSummaryEntry;
  theme: (typeof CARDS)[number]["theme"];
}) {
  const change = entry.allocation_change_percent;
  const changeStr = (change >= 0 ? "+" : "") + change.toFixed(1) + "%";
  const changeColor = change >= 0 ? theme.changePos : theme.changeNeg;
  const displaySym = entry.symbol.replace(".BK", "");
  const isBK = entry.symbol.endsWith(".BK");

  return (
    <div
      className={`inline-flex flex-col items-center gap-0.5 px-2.5 py-1.5 rounded-lg border cursor-default select-none transition-colors ${theme.chip}`}
    >
      <span className={`text-xs font-bold ${theme.chipText}`}>
        {displaySym}
        {isBK && <span className="text-gray-400 font-normal">.BK</span>}
      </span>
      <span className={`text-[11px] font-semibold tabular-nums ${changeColor}`}>
        {changeStr}
      </span>
      {entry.timing_score != null && (
        <span className="text-[10px] text-gray-400 tabular-nums">
          Timing {entry.timing_score.toFixed(0)}
        </span>
      )}
    </div>
  );
}

function ActionCard({
  label,
  emptyText,
  entries,
  theme,
}: {
  label: string;
  emptyText: string;
  entries: ActionSummaryEntry[];
  theme: (typeof CARDS)[number]["theme"];
}) {
  const isEmpty = entries.length === 0;

  return (
    <div className={`bg-white border ${theme.border} rounded-xl p-4 shadow-sm flex flex-col gap-3 min-h-[96px]`}>
      {/* Header */}
      <div className="flex items-center gap-2">
        <span className={`w-2 h-2 rounded-full shrink-0 ${theme.dot}`} />
        <span className={`text-xs font-bold uppercase tracking-widest ${theme.header}`}>
          {label}
        </span>
        {!isEmpty && (
          <span className={`ml-auto text-xs font-bold px-1.5 py-0.5 rounded-full border ${theme.badge}`}>
            {entries.length}
          </span>
        )}
      </div>

      {/* Chips or empty state */}
      {isEmpty ? (
        <p className="text-xs text-gray-400 italic">{emptyText}</p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {entries.map((e) => (
            <SymbolChip key={e.symbol} entry={e} theme={theme} />
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Main export ─────────────────────────────────────────────────────────────

interface Props {
  summary: ActionSummary;
}

export default function OptimizerActionSummary({ summary }: Props) {
  const totalActions =
    summary.sell.length +
    summary.reduce.length +
    summary.accumulate.length +
    summary.new_position.length;

  const allHold = totalActions === 0;

  return (
    <section className="bg-gray-50 border border-gray-200 rounded-xl p-4 shadow-sm space-y-3">
      {/* Section header */}
      <div className="flex items-center gap-3">
        <h3 className="text-sm font-bold text-gray-800 uppercase tracking-wider">
          Action Summary
        </h3>
        {allHold ? (
          <span className="text-xs font-semibold px-2 py-0.5 rounded-full border bg-green-50 border-green-200 text-green-700">
            Portfolio Balanced
          </span>
        ) : (
          <span className="text-xs font-semibold px-2 py-0.5 rounded-full border bg-blue-50 border-blue-200 text-blue-700">
            {totalActions} action{totalActions !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      {allHold ? (
        <div className="bg-green-50 border border-green-100 rounded-lg px-4 py-3 text-sm text-green-800">
          All positions are within tolerance — no changes recommended at this time.
        </div>
      ) : (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {CARDS.map((card) => (
            <ActionCard
              key={card.key}
              label={card.label}
              emptyText={card.emptyText}
              entries={summary[card.key]}
              theme={card.theme}
            />
          ))}
        </div>
      )}
    </section>
  );
}
