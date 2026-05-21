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

interface Props {
  snapshots: PortfolioSnapshotRow[];
}

interface ChartPoint {
  date: string;
  totalValue: number;
  equityValue: number;
  cash: number;
}

function formatDate(dateStr: string): string {
  // "YYYY-MM-DD" → "MMM D"
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function formatValue(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(2)}M`;
  if (v >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
  return v.toFixed(2);
}

export default function EquityCurveChart({ snapshots }: Props) {
  const data: ChartPoint[] = snapshots.map((s) => ({
    date: formatDate(s.snapshot_date),
    totalValue: s.total_value,
    equityValue: s.total_value - s.cash_balance,
    cash: s.cash_balance,
  }));

  const CustomTooltip = ({
    active,
    payload,
    label,
  }: {
    active?: boolean;
    payload?: { name: string; value: number; color: string }[];
    label?: string;
  }) => {
    if (!active || !payload?.length) return null;
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-3 shadow text-xs space-y-1">
        <p className="font-semibold text-gray-700 mb-1">{label}</p>
        {payload.map((p) => (
          <div key={p.name} className="flex items-center gap-2">
            <span className="inline-block w-2 h-2 rounded-full" style={{ background: p.color }} />
            <span className="text-gray-600">{p.name}:</span>
            <span className="font-medium text-gray-800">{formatValue(p.value)}</span>
          </div>
        ))}
      </div>
    );
  };

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
          tick={{ fontSize: 11, fill: "#6b7280" }}
          tickLine={false}
          axisLine={false}
          interval="preserveStartEnd"
        />
        <YAxis
          tickFormatter={formatValue}
          tick={{ fontSize: 11, fill: "#6b7280" }}
          tickLine={false}
          axisLine={false}
          width={56}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          iconType="circle"
          iconSize={8}
          wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
        />
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
