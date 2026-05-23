"use client";

import type { MonthlyReturn } from "@/lib/api";
import {
  transformMonthlyReturns,
  MONTH_LABELS,
  returnCellStyle,
} from "@/lib/analytics-transformers";

function HeatCell({ value }: { value: number | null }) {
  const { bg, text } = returnCellStyle(value);
  return (
    <td
      className="text-center text-xs font-medium py-1.5 px-0.5 rounded"
      style={{ backgroundColor: bg, color: text, minWidth: "3rem" }}
    >
      {value != null ? `${value >= 0 ? "+" : ""}${value.toFixed(1)}%` : "—"}
    </td>
  );
}

interface MonthlyHeatmapProps {
  monthlyReturns: MonthlyReturn[];
}

export default function MonthlyHeatmap({ monthlyReturns }: MonthlyHeatmapProps) {
  if (!monthlyReturns.length) {
    return (
      <div className="flex items-center justify-center h-24 text-sm text-gray-400">
        No monthly return data available yet.
      </div>
    );
  }

  const rows = transformMonthlyReturns(monthlyReturns);

  return (
    <div className="overflow-x-auto">
      <table className="w-full border-separate border-spacing-x-0 border-spacing-y-1">
        <thead>
          <tr>
            <th className="text-xs text-gray-400 font-medium text-left py-1 pr-2 w-12">Year</th>
            {MONTH_LABELS.map((m) => (
              <th key={m} className="text-xs text-gray-400 font-medium text-center py-1 px-0.5">
                {m}
              </th>
            ))}
            <th className="text-xs text-gray-400 font-medium text-right py-1 pl-2 w-16">Total</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.year}>
              <td className="text-xs font-semibold text-gray-600 pr-2 py-1">{row.year}</td>
              {row.cells.map((cell) => (
                <HeatCell key={cell.month} value={cell.value} />
              ))}
              <td className="pl-2">
                <div
                  className="text-xs font-semibold text-right rounded px-1 py-1"
                  style={returnCellStyle(row.yearTotal).bg !== "#f9fafb"
                    ? { color: returnCellStyle(row.yearTotal).text, backgroundColor: returnCellStyle(row.yearTotal).bg }
                    : { color: "#6b7280" }}
                >
                  {row.yearTotal != null
                    ? `${row.yearTotal >= 0 ? "+" : ""}${row.yearTotal.toFixed(1)}%`
                    : "—"}
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Legend */}
      <div className="flex items-center gap-3 mt-3 flex-wrap">
        <span className="text-xs text-gray-400">Return scale:</span>
        {[
          { label: "<−5%",   bg: "#7f1d1d", text: "#fff" },
          { label: "−2–5%",  bg: "#dc2626", text: "#fff" },
          { label: "−2–0%",  bg: "#fecaca", text: "#991b1b" },
          { label: "0–2%",   bg: "#bbf7d0", text: "#166534" },
          { label: "2–5%",   bg: "#16a34a", text: "#fff" },
          { label: ">5%",    bg: "#14532d", text: "#fff" },
        ].map((l) => (
          <span
            key={l.label}
            className="text-xs px-2 py-0.5 rounded font-medium"
            style={{ backgroundColor: l.bg, color: l.text }}
          >
            {l.label}
          </span>
        ))}
      </div>
    </div>
  );
}
