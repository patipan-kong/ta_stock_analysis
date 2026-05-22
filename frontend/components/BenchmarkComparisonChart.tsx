"use client";

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
import type { PerformanceComparisonResult, BenchmarkSeriesMeta } from "@/lib/api";

interface Props {
  comparison: PerformanceComparisonResult;
}

// Fixed palette: portfolio always blue; each benchmark gets a distinct colour.
const PALETTE: Record<string, string> = {
  portfolio:  "#3b82f6",
  bm_SET_BK: "#f59e0b",  // ^SET.BK — Thai SET Composite Index (price)
  bm_SET:    "#f59e0b",  // ^SET    — SET Total Return Index (legacy)
  bm_QQQ:   "#8b5cf6",
  bm_SPY:   "#10b981",
  bm_GSPC:  "#ef4444",
};
const FALLBACK_COLORS = ["#f59e0b", "#8b5cf6", "#10b981", "#ef4444", "#06b6d4", "#ec4899"];

function seriesColor(key: string, idx: number): string {
  return PALETTE[key] ?? FALLBACK_COLORS[idx % FALLBACK_COLORS.length];
}

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
              <span
                className="inline-block w-2 h-2 rounded-full flex-shrink-0"
                style={{ background: p.color }}
              />
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

export default function BenchmarkComparisonChart({ comparison }: Props) {
  const { series, data } = comparison;

  // Recharts needs string date labels on the x-axis
  const chartData = data.map((row) => ({
    ...row,
    _label: formatDate(row.date),
  }));

  return (
    <ResponsiveContainer width="100%" height={288}>
      <LineChart data={chartData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis
          dataKey="_label"
          tick={{ fontSize: 11, fill: "#6b7280" }}
          tickLine={false}
          axisLine={false}
          interval="preserveStartEnd"
        />
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
        {/* Baseline at 100 — drawn before Lines so it sits behind them */}
        <ReferenceLine
          y={100}
          stroke="#e5e7eb"
          strokeDasharray="4 3"
          strokeWidth={1}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          iconType="circle"
          iconSize={8}
          wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
        />
        {series.map((s: BenchmarkSeriesMeta, idx: number) => (
          <Line
            key={s.key}
            type="monotone"
            dataKey={s.key}
            name={s.label}
            stroke={seriesColor(s.key, idx)}
            strokeWidth={s.type === "portfolio" ? 2.5 : 1.75}
            dot={{ r: 3, strokeWidth: 0 }}
            activeDot={{ r: 5 }}
            connectNulls={false}
            strokeDasharray={s.type === "benchmark" ? "5 3" : undefined}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
