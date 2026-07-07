"use client";

// AI Evaluation M6 — ThreePortfolioChart (EXECUTION_INTELLIGENCE_UX.md §6,
// S7 hero comparison). Ideal dashed, AI solid, You bold, benchmark dotted
// gray — indexed to 100. Renders GET /analytics/shadow-performance's
// three_portfolios.chart verbatim; no metric computed client-side.

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";
import type { ThreePortfoliosChartRow } from "@/lib/api";

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: { name: string; value: number | null; color: string; dataKey: string }[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  const visible = payload.filter((p) => p.value != null);
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-3 shadow text-xs space-y-1 min-w-[140px]">
      <p className="font-semibold text-gray-700 mb-1">{label}</p>
      {visible.map((p) => {
        const delta = p.value! - 100;
        const sign = delta >= 0 ? "+" : "";
        return (
          <div key={p.dataKey} className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-1.5">
              <span className="inline-block w-2 h-2 rounded-full flex-shrink-0" style={{ background: p.color }} />
              <span className="text-gray-600 truncate max-w-[90px]">{p.name}</span>
            </div>
            <span className="font-medium text-gray-800 tabular-nums">
              {p.value!.toFixed(2)}
              <span className={`ml-1 text-[10px] ${delta >= 0 ? "text-green-600" : "text-red-500"}`}>
                ({sign}{delta.toFixed(2)}%)
              </span>
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default function ThreePortfolioChart({ chart }: { chart: ThreePortfoliosChartRow[] }) {
  const data = chart.map((row) => ({ ...row, _label: formatDate(row.date) }));

  return (
    <ResponsiveContainer width="100%" height={288}>
      <LineChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis dataKey="_label" tick={{ fontSize: 11, fill: "#6b7280" }} tickLine={false} axisLine={false} interval="preserveStartEnd" />
        <YAxis
          tick={{ fontSize: 11, fill: "#6b7280" }}
          tickLine={false}
          axisLine={false}
          width={52}
          tickFormatter={(v: number) => v.toFixed(1)}
          domain={[
            (dataMin: number) => Math.floor(Math.min(dataMin, 98) - 1),
            (dataMax: number) => Math.ceil(Math.max(dataMax, 102) + 1),
          ]}
        />
        <ReferenceLine y={100} stroke="#e5e7eb" strokeDasharray="4 3" strokeWidth={1} />
        <Tooltip content={<CustomTooltip />} />
        <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
        <Line type="monotone" dataKey="ideal" name="Ideal" stroke="#8b5cf6" strokeWidth={1.75} strokeDasharray="5 3" dot={false} connectNulls activeDot={{ r: 4 }} />
        <Line type="monotone" dataKey="ai" name="AI Portfolio" stroke="#3b82f6" strokeWidth={2} dot={false} connectNulls activeDot={{ r: 4 }} />
        <Line type="monotone" dataKey="actual" name="You" stroke="#10b981" strokeWidth={2.75} dot={false} connectNulls activeDot={{ r: 5 }} />
        <Line type="monotone" dataKey="benchmark" name="Benchmark (SET)" stroke="#9ca3af" strokeWidth={1.5} strokeDasharray="2 2" dot={false} connectNulls activeDot={{ r: 4 }} />
      </LineChart>
    </ResponsiveContainer>
  );
}
