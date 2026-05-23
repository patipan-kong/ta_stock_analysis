"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import type { PerformanceDataPoint, BenchmarkSeriesMeta } from "@/lib/api";

const SERIES_COLORS: Record<string, string> = {
  portfolio: "#2563eb",
  bm_SET:    "#d97706",
  bm_QQQ:    "#7c3aed",
  bm_SPY:    "#16a34a",
};

function pickColor(key: string, idx: number): string {
  if (SERIES_COLORS[key]) return SERIES_COLORS[key];
  const fallbacks = ["#0891b2", "#be185d", "#92400e"];
  return fallbacks[idx % fallbacks.length];
}

function formatDate(d: string): string {
  const dt = new Date(d);
  return dt.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
}

function CustomTooltip({ active, payload, label }: {
  active?: boolean;
  payload?: Array<{ color: string; name: string; value: number | null; dataKey: string }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-lg px-3 py-2.5 shadow-lg text-xs min-w-[140px]">
      <p className="text-gray-500 mb-1.5 font-medium">{label}</p>
      {payload.map((p) => {
        const delta = p.value != null ? (p.value - 100).toFixed(2) : null;
        const sign  = delta != null && parseFloat(delta) >= 0 ? "+" : "";
        return (
          <div key={p.dataKey} className="flex justify-between gap-4 mb-0.5">
            <span style={{ color: p.color }}>{p.name}</span>
            <span className="font-semibold tabular-nums text-gray-700">
              {p.value != null ? (
                <>
                  {p.value.toFixed(1)}{" "}
                  <span style={{ color: parseFloat(delta ?? "0") >= 0 ? "#16a34a" : "#dc2626" }}>
                    ({sign}{delta}%)
                  </span>
                </>
              ) : "—"}
            </span>
          </div>
        );
      })}
    </div>
  );
}

interface EquityCurveChartProps {
  data: PerformanceDataPoint[];
  series: BenchmarkSeriesMeta[];
}

export default function EquityCurveChart({ data, series }: EquityCurveChartProps) {
  if (!data.length) {
    return (
      <div className="h-72 flex items-center justify-center text-sm text-gray-400">
        No equity curve data available. Generate snapshots first.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={288}>
      <LineChart data={data} margin={{ top: 8, right: 20, left: 4, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis
          dataKey="date"
          tickFormatter={formatDate}
          tick={{ fontSize: 11, fill: "#9ca3af" }}
          tickLine={false}
          axisLine={false}
          minTickGap={40}
        />
        <YAxis
          domain={["auto", "auto"]}
          tickFormatter={(v: number) => v.toFixed(0)}
          tick={{ fontSize: 11, fill: "#9ca3af" }}
          tickLine={false}
          axisLine={false}
          width={44}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }}
          iconType="line"
          iconSize={12}
        />
        <ReferenceLine y={100} stroke="#d1d5db" strokeDasharray="4 2" />
        {series.map((s, i) => (
          <Line
            key={s.key}
            type="monotone"
            dataKey={s.key}
            name={s.label}
            stroke={pickColor(s.key, i)}
            strokeWidth={s.type === "portfolio" ? 2.5 : 1.5}
            strokeDasharray={s.type === "benchmark" ? "5 3" : undefined}
            dot={false}
            connectNulls
            activeDot={{ r: 4, strokeWidth: 0 }}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
