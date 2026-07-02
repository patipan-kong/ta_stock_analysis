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
  rankByDim,
  bucketLabel,
  fmtInt,
} from "@/lib/ai-analytics-transformers";

const PALETTE = ["#2563eb", "#f97316", "#16a34a", "#a855f7", "#0891b2", "#e11d48"];
const OTHER_COLOR = "#9ca3af";
function seriesColor(key: string, i: number): string {
  return key === "Other" ? OTHER_COLOR : PALETTE[i % PALETTE.length];
}

type TokenField = "total_tokens" | "input_tokens" | "output_tokens";
const FIELD_OPTIONS: { key: TokenField; label: string }[] = [
  { key: "total_tokens", label: "Total Tokens" },
  { key: "input_tokens", label: "Input Tokens" },
  { key: "output_tokens", label: "Output Tokens" },
];

export default function TokenDashboardSection({ daily }: { daily: AiDailyUsageRow[] }) {
  const [granularity, setGranularity] = useState<Granularity>("daily");
  const [dim, setDim] = useState<BreakdownDim>("model");
  const [field, setField] = useState<TokenField>("total_tokens");

  const { data, seriesKeys } = useMemo(
    () => groupDailyByBucketAndDim(daily, granularity, dim, field),
    [daily, granularity, dim, field],
  );

  const largest = useMemo(() => {
    const ranked = [...rankByDim(daily, dim)].sort((a, b) => b.avg_total_tokens - a.avg_total_tokens);
    const mean = ranked.length ? ranked.reduce((s, r) => s + r.avg_total_tokens, 0) / ranked.length : 0;
    return { ranked: ranked.slice(0, 8), mean };
  }, [daily, dim]);

  if (!daily.length) {
    return <p className="text-sm text-gray-400">No token data yet.</p>;
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
          <div className="flex flex-wrap items-center gap-1.5">
            {FIELD_OPTIONS.map((o) => (
              <button
                key={o.key}
                onClick={() => setField(o.key)}
                className={`text-xs px-3 py-1 rounded-full border transition-colors ${
                  field === o.key
                    ? "bg-blue-600 text-white border-blue-600"
                    : "bg-white text-gray-600 border-gray-300 hover:border-gray-500"
                }`}
              >
                {o.label}
              </button>
            ))}
          </div>
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
        </div>
        <div className="flex flex-wrap items-center gap-1.5 mb-3">
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
        <ResponsiveContainer width="100%" height={260}>
          <BarChart data={data} margin={{ top: 8, right: 20, left: 4, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis
              dataKey="bucket"
              tickFormatter={(v: string) => bucketLabel(v, granularity)}
              tick={{ fontSize: 11, fill: "#9ca3af" }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis tickFormatter={(v: number) => fmtInt(v)} tick={{ fontSize: 11, fill: "#9ca3af" }} tickLine={false} axisLine={false} width={56} />
            <Tooltip formatter={(v) => fmtInt(Number(v))} labelFormatter={(v) => bucketLabel(String(v), granularity)} />
            <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
            {seriesKeys.map((k, i) => (
              <Bar key={k} dataKey={k} stackId="tokens" fill={seriesColor(k, i)} />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div>
        <h3 className="text-xs font-semibold text-gray-700 mb-3">
          Largest Avg Responses (by {BREAKDOWN_OPTIONS.find((o) => o.key === dim)?.label.toLowerCase()})
        </h3>
        <div className="space-y-1.5">
          {largest.ranked.map((r) => {
            const unusual = largest.mean > 0 && r.avg_total_tokens > largest.mean * 1.5;
            return (
              <div key={r.key} className="flex items-center justify-between text-sm border-b border-gray-50 py-1.5">
                <span className="text-gray-700 flex items-center gap-2">
                  {r.key}
                  {unusual && (
                    <span className="text-xs font-semibold px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-200">
                      unusually large
                    </span>
                  )}
                </span>
                <span className="flex items-center gap-3 text-gray-500">
                  <span>{r.call_count} calls</span>
                  <span className="font-semibold text-gray-800">{fmtInt(r.avg_total_tokens)} avg tokens</span>
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
