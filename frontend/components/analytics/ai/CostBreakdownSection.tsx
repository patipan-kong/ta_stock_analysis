"use client";

import { useMemo, useState } from "react";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";
import type { AiDailyUsageRow } from "@/lib/api";
import {
  type Granularity,
  GRANULARITY_OPTIONS,
  type BreakdownDim,
  BREAKDOWN_OPTIONS,
  groupDailyByBucketAndDim,
  bucketLabel,
  fmtUsd,
} from "@/lib/ai-analytics-transformers";

const PALETTE = ["#2563eb", "#f97316", "#16a34a", "#a855f7", "#0891b2", "#e11d48"];
const OTHER_COLOR = "#9ca3af";

function seriesColor(key: string, i: number): string {
  if (key === "Other") return OTHER_COLOR;
  return PALETTE[i % PALETTE.length];
}

export default function CostBreakdownSection({ daily }: { daily: AiDailyUsageRow[] }) {
  const [granularity, setGranularity] = useState<Granularity>("daily");
  const [dim, setDim] = useState<BreakdownDim>("model");

  const { data, seriesKeys } = useMemo(
    () => groupDailyByBucketAndDim(daily, granularity, dim, "cost_usd"),
    [daily, granularity, dim],
  );

  if (!daily.length) {
    return <p className="text-sm text-gray-400">No cost data yet.</p>;
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-0.5 bg-gray-100 rounded-lg p-0.5 w-fit">
          {GRANULARITY_OPTIONS.map((g) => (
            <button
              key={g}
              onClick={() => setGranularity(g)}
              className={`px-2.5 py-1 text-xs font-medium rounded-md capitalize transition-colors ${
                granularity === g ? "bg-white text-blue-700 shadow-sm" : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {g}
            </button>
          ))}
        </div>
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-xs text-gray-500 font-medium mr-1">Break down by:</span>
          {BREAKDOWN_OPTIONS.map((o) => (
            <button
              key={o.key}
              onClick={() => setDim(o.key)}
              className={`text-xs px-3 py-1 rounded-full border transition-colors ${
                dim === o.key
                  ? "bg-gray-800 text-white border-gray-800"
                  : "bg-white text-gray-600 border-gray-300 hover:border-gray-500"
              }`}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>

      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} margin={{ top: 8, right: 20, left: 4, bottom: 4 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            dataKey="bucket"
            tickFormatter={(v: string) => bucketLabel(v, granularity)}
            tick={{ fontSize: 11, fill: "#9ca3af" }}
            tickLine={false}
            axisLine={false}
          />
          <YAxis
            tickFormatter={(v: number) => `$${v.toFixed(2)}`}
            tick={{ fontSize: 11, fill: "#9ca3af" }}
            tickLine={false}
            axisLine={false}
            width={56}
          />
          <Tooltip
            formatter={(v) => fmtUsd(Number(v))}
            labelFormatter={(v) => bucketLabel(String(v), granularity)}
          />
          <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
          {seriesKeys.map((k, i) => (
            <Bar key={k} dataKey={k} stackId="cost" fill={seriesColor(k, i)} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
