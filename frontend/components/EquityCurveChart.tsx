"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { PortfolioSnapshotRow } from "@/lib/api";

// ─── Event marker types (reserved for future use) ─────────────────────────────
export type ChartEventType = "rebalance" | "deposit" | "withdrawal" | "approved";

export interface ChartEvent {
  date: string;         // "YYYY-MM-DD"
  type: ChartEventType;
  label?: string;
}

interface Props {
  snapshots: PortfolioSnapshotRow[];
  events?: ChartEvent[]; // future: render as ReferenceLine vertical markers
}

interface ChartPoint {
  date: string;          // raw "YYYY-MM-DD" — kept for tooltip full-date formatting
  totalValue: number;
  equityValue: number;
  cash: number;
  dailyReturnPct: number | null;
  drawdownPct: number;
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

function formatValue(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(2)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
  return v.toFixed(2);
}

// ─── Tooltip ──────────────────────────────────────────────────────────────────

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: Array<{ name: string; value: number; color: string; payload: ChartPoint }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  const pt = payload[0].payload;
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-3 shadow-lg text-xs min-w-[180px] space-y-1">
      <p className="font-semibold text-gray-700 mb-2">{fullDate(label ?? "")}</p>
      {payload.map((p) => (
        <div key={p.name} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full shrink-0" style={{ background: p.color }} />
          <span className="text-gray-600">{p.name}:</span>
          <span className="font-medium text-gray-800 ml-auto">{formatValue(p.value)}</span>
        </div>
      ))}
      <div className="pt-1.5 border-t border-gray-100 space-y-0.5">
        {pt.dailyReturnPct != null && (
          <div className="flex justify-between">
            <span className="text-gray-500">Daily Return</span>
            <span
              className={`font-semibold tabular-nums ${
                pt.dailyReturnPct >= 0 ? "text-green-600" : "text-red-500"
              }`}
            >
              {pt.dailyReturnPct >= 0 ? "+" : ""}
              {pt.dailyReturnPct.toFixed(2)}%
            </span>
          </div>
        )}
        <div className="flex justify-between">
          <span className="text-gray-500">Drawdown</span>
          <span
            className={`font-semibold tabular-nums ${
              pt.drawdownPct < -0.01 ? "text-red-500" : "text-gray-400"
            }`}
          >
            {pt.drawdownPct.toFixed(2)}%
          </span>
        </div>
      </div>
    </div>
  );
}

// ─── Component ────────────────────────────────────────────────────────────────

export default function EquityCurveChart({ snapshots, events: _events = [] }: Props) {
  const spanDays =
    snapshots.length >= 2
      ? Math.round(
          (new Date(snapshots[snapshots.length - 1].snapshot_date).getTime() -
            new Date(snapshots[0].snapshot_date).getTime()) /
            86_400_000
        )
      : 0;

  const formatX = pickXFormatter(spanDays);

  let peak = snapshots[0]?.total_value ?? 0;
  const data: ChartPoint[] = snapshots.map((s) => {
    if (s.total_value > peak) peak = s.total_value;
    return {
      date: s.snapshot_date,
      totalValue: s.total_value,
      equityValue: s.total_value - s.cash_balance,
      cash: s.cash_balance,
      dailyReturnPct: s.daily_return_pct,
      drawdownPct: peak > 0 ? ((s.total_value - peak) / peak) * 100 : 0,
    };
  });

  return (
    <ResponsiveContainer width="100%" height={288}>
      <AreaChart data={data} margin={{ top: 4, right: 8, left: 8, bottom: 0 }}>
        <defs>
          <linearGradient id="gradTotal" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.25} />
            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
          </linearGradient>
          <linearGradient id="gradEquity" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%" stopColor="#10b981" stopOpacity={0.2} />
            <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
        <XAxis
          dataKey="date"
          tickFormatter={formatX}
          tick={{ fontSize: 11, fill: "#6b7280" }}
          tickLine={false}
          axisLine={false}
          minTickGap={spanDays < 90 ? 28 : 40}
        />
        <YAxis
          tickFormatter={formatValue}
          tick={{ fontSize: 11, fill: "#6b7280" }}
          tickLine={false}
          axisLine={false}
          width={56}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12, paddingTop: 8 }} />
        <Area
          type="monotone"
          dataKey="totalValue"
          name="Total Value"
          stroke="#3b82f6"
          strokeWidth={2}
          fill="url(#gradTotal)"
          dot={false}
        />
        <Area
          type="monotone"
          dataKey="equityValue"
          name="Equity"
          stroke="#10b981"
          strokeWidth={1.5}
          fill="url(#gradEquity)"
          dot={false}
          strokeDasharray="4 2"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
