"use client";

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { PortfolioItem } from "@/lib/api";

const COLORS = [
  "#3b82f6", "#10b981", "#f59e0b", "#8b5cf6",
  "#ef4444", "#06b6d4", "#f97316", "#84cc16",
  "#ec4899", "#a78bfa",
];
const CASH_COLOR = "#94a3b8";

interface SliceData {
  name: string;
  value: number;
  color: string;
}

interface TooltipPayload {
  name: string;
  value: number;
}

function CustomTooltip({
  active,
  payload,
  total,
}: {
  active?: boolean;
  payload?: { payload: TooltipPayload }[];
  total: number;
}) {
  if (!active || !payload?.length) return null;
  const { name, value } = payload[0].payload;
  const pct = total > 0 ? ((value / total) * 100).toFixed(1) : "0.0";
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-md px-3 py-2 text-sm">
      <p className="font-semibold text-gray-800">{name}</p>
      <p className="text-gray-500">
        {value.toLocaleString("th-TH", { minimumFractionDigits: 2 })}
        <span className="ml-2 text-gray-400">({pct}%)</span>
      </p>
    </div>
  );
}

export default function PortfolioPieChart({
  items,
  cashBalance,
}: {
  items: PortfolioItem[];
  cashBalance: number;
}) {
  const stockSlices: SliceData[] = items
    .map((item, i) => ({
      name: item.symbol.replace(".BK", ""),
      value: parseFloat(
        (item.shares * (item.current_price ?? item.avg_cost)).toFixed(2)
      ),
      color: COLORS[i % COLORS.length],
    }))
    .filter((s) => s.value > 0);

  const data: SliceData[] =
    cashBalance > 0
      ? [...stockSlices, { name: "Cash", value: cashBalance, color: CASH_COLOR }]
      : stockSlices;

  const total = data.reduce((s, d) => s + d.value, 0);

  if (data.length === 0) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-400 text-sm">
        No data to display
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius="45%"
          outerRadius="70%"
          paddingAngle={2}
          dataKey="value"
          nameKey="name"
        >
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.color} stroke="white" strokeWidth={2} />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip total={total} />} />
        <Legend
          formatter={(value) => (
            <span className="text-xs text-gray-600">{value}</span>
          )}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
