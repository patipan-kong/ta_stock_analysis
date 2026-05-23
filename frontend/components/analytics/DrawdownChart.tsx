"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

function formatDate(d: string): string {
  const dt = new Date(d);
  return dt.toLocaleDateString("en-US", { month: "short", year: "2-digit" });
}

function CustomTooltip({ active, payload, label }: {
  active?: boolean;
  payload?: Array<{ value: number | null }>;
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  const v = payload[0]?.value;
  return (
    <div className="bg-white border border-gray-200 rounded-lg px-3 py-2 shadow-md text-xs">
      <p className="text-gray-500 mb-1">{label}</p>
      <p className="font-semibold text-red-600 tabular-nums">
        {v != null ? `${v.toFixed(2)}%` : "—"}
      </p>
    </div>
  );
}

interface DrawdownChartProps {
  data: Array<{ date: string; drawdown_pct: number }>;
  maxDrawdown?: number | null;
}

export default function DrawdownChart({ data, maxDrawdown }: DrawdownChartProps) {
  if (!data.length) {
    return (
      <div className="h-36 flex items-center justify-center text-sm text-gray-400">
        No drawdown data available.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={144}>
      <AreaChart data={data} margin={{ top: 4, right: 20, left: 4, bottom: 4 }}>
        <defs>
          <linearGradient id="ddGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="5%"  stopColor="#ef4444" stopOpacity={0.3} />
            <stop offset="95%" stopColor="#ef4444" stopOpacity={0.02} />
          </linearGradient>
        </defs>
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
          domain={["auto", 0]}
          tickFormatter={(v: number) => `${v.toFixed(0)}%`}
          tick={{ fontSize: 11, fill: "#9ca3af" }}
          tickLine={false}
          axisLine={false}
          width={44}
        />
        <Tooltip content={<CustomTooltip />} />
        {maxDrawdown != null && (
          <ReferenceLine
            y={maxDrawdown}
            stroke="#ef4444"
            strokeDasharray="4 2"
            label={{ value: `Max ${maxDrawdown.toFixed(1)}%`, position: "insideTopRight", fontSize: 10, fill: "#ef4444" }}
          />
        )}
        <Area
          type="monotone"
          dataKey="drawdown_pct"
          name="Drawdown"
          stroke="#ef4444"
          strokeWidth={1.5}
          fill="url(#ddGradient)"
          dot={false}
          connectNulls
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
