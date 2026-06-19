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

// ─── Event marker types (reserved for future use) ─────────────────────────────
export type ChartEventType = "rebalance" | "deposit" | "withdrawal" | "approved";

export interface ChartEvent {
  date: string;         // "YYYY-MM-DD"
  type: ChartEventType;
  label?: string;
}

// ─── Series colors ────────────────────────────────────────────────────────────

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

// ─── Adaptive X-axis formatter ────────────────────────────────────────────────

function pickXFormatter(spanDays: number): (d: string) => string {
  if (spanDays < 90)
    return (d) =>
      new Date(d + "T00:00:00").toLocaleDateString("en-GB", { day: "numeric", month: "short" });
  if (spanDays <= 365)
    return (d) =>
      new Date(d + "T00:00:00").toLocaleDateString("en-US", { month: "short", year: "numeric" });
  return (d) => String(new Date(d + "T00:00:00").getFullYear());
}

function fullDate(d: string): string {
  return new Date(d + "T00:00:00").toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

// ─── Tooltip ──────────────────────────────────────────────────────────────────

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{
    color: string;
    name: string;
    value: number | null;
    dataKey: string;
    payload: Record<string, unknown>;
  }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  const pt = payload[0].payload;
  const drawdown = typeof pt._drawdown === "number" ? pt._drawdown : 0;
  const dailyReturn = typeof pt._dailyReturn === "number" ? pt._dailyReturn : null;

  return (
    <div className="bg-white border border-gray-200 rounded-lg px-3 py-2.5 shadow-lg text-xs min-w-[160px]">
      <p className="text-gray-700 font-semibold mb-2">{fullDate(label ?? "")}</p>
      {payload.map((p) => {
        const delta = p.value != null ? (p.value - 100).toFixed(2) : null;
        const sign = delta != null && parseFloat(delta) >= 0 ? "+" : "";
        return (
          <div key={p.dataKey} className="flex justify-between gap-4 mb-0.5">
            <span style={{ color: p.color }}>{p.name}</span>
            <span className="font-semibold tabular-nums text-gray-700">
              {p.value != null ? (
                <>
                  {p.value.toFixed(1)}{" "}
                  <span
                    style={{ color: parseFloat(delta ?? "0") >= 0 ? "#16a34a" : "#dc2626" }}
                  >
                    ({sign}{delta}%)
                  </span>
                </>
              ) : (
                "—"
              )}
            </span>
          </div>
        );
      })}
      <div className="pt-1.5 mt-1 border-t border-gray-100 space-y-0.5">
        {dailyReturn != null && (
          <div className="flex justify-between">
            <span className="text-gray-500">Daily Return</span>
            <span
              className={`font-semibold tabular-nums ${
                dailyReturn >= 0 ? "text-green-600" : "text-red-500"
              }`}
            >
              {dailyReturn >= 0 ? "+" : ""}
              {dailyReturn.toFixed(2)}%
            </span>
          </div>
        )}
        <div className="flex justify-between">
          <span className="text-gray-500">Drawdown</span>
          <span
            className={`font-semibold tabular-nums ${
              drawdown < -0.01 ? "text-red-500" : "text-gray-400"
            }`}
          >
            {drawdown.toFixed(2)}%
          </span>
        </div>
      </div>
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

interface EquityCurveChartProps {
  data: PerformanceDataPoint[];
  series: BenchmarkSeriesMeta[];
  events?: ChartEvent[]; // future: render as ReferenceLine vertical markers
}

export default function EquityCurveChart({ data, series, events: _events = [] }: EquityCurveChartProps) {
  if (!data.length) {
    return (
      <div className="h-72 flex items-center justify-center text-sm text-gray-400">
        No equity curve data available. Generate snapshots first.
      </div>
    );
  }

  const spanDays =
    data.length >= 2
      ? Math.round(
          (new Date(data[data.length - 1].date).getTime() -
            new Date(data[0].date).getTime()) /
            86_400_000
        )
      : 0;

  const formatX = pickXFormatter(spanDays);

  // Pre-compute portfolio drawdown + daily return for tooltip enrichment.
  // The portfolio series starts at 100 (normalized). We track a running peak
  // to derive the current drawdown from the high-water mark.
  let peak = 100;
  const enriched = data.map((pt, i) => {
    const pv = pt["portfolio"] as number | null | undefined;
    if (pv != null && pv > peak) peak = pv;
    const _drawdown = peak > 0 ? ((pv ?? peak) - peak) / peak * 100 : 0;
    const prev = i > 0 ? (data[i - 1]["portfolio"] as number | null) : null;
    const _dailyReturn =
      pv != null && prev != null && prev !== 0 ? (pv - prev) / prev * 100 : null;
    return { ...pt, _drawdown, _dailyReturn };
  });

  return (
    <ResponsiveContainer width="100%" height={288}>
      <LineChart data={enriched} margin={{ top: 8, right: 20, left: 4, bottom: 4 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis
          dataKey="date"
          tickFormatter={formatX}
          tick={{ fontSize: 11, fill: "#9ca3af" }}
          tickLine={false}
          axisLine={false}
          minTickGap={spanDays < 90 ? 28 : 40}
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
