"use client";

import { useMemo, useState } from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
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
  buildLatencyTrend,
  rankByDim,
  bucketLabel,
  fmtMs,
  latencyHealth,
} from "@/lib/ai-analytics-transformers";
import { HealthDot } from "./shared";

export default function LatencyDashboardSection({ daily }: { daily: AiDailyUsageRow[] }) {
  const [granularity, setGranularity] = useState<Granularity>("daily");
  const [dim, setDim] = useState<BreakdownDim>("model");

  const trend = useMemo(() => buildLatencyTrend(daily, granularity), [daily, granularity]);
  const ranked = useMemo(() => rankByDim(daily, dim), [daily, dim]);

  if (!daily.length) {
    return <p className="text-sm text-gray-400">No latency data yet.</p>;
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
          <h3 className="text-xs font-semibold text-gray-700">Latency Trend (avg vs P95, approx.)</h3>
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
        <ResponsiveContainer width="100%" height={240}>
          <LineChart data={trend} margin={{ top: 8, right: 20, left: 4, bottom: 4 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis
              dataKey="bucket"
              tickFormatter={(v: string) => bucketLabel(v, granularity)}
              tick={{ fontSize: 11, fill: "#9ca3af" }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis tickFormatter={(v: number) => fmtMs(v)} tick={{ fontSize: 11, fill: "#9ca3af" }} tickLine={false} axisLine={false} width={48} />
            <Tooltip formatter={(v) => fmtMs(Number(v))} labelFormatter={(v) => bucketLabel(String(v), granularity)} />
            <Legend wrapperStyle={{ fontSize: "12px", paddingTop: "10px" }} />
            <Line type="monotone" dataKey="avg_latency_ms" name="Avg" stroke="#2563eb" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="p95_latency_ms" name="P95 (approx.)" stroke="#f97316" strokeWidth={1.5} strokeDasharray="5 3" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div>
        <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
          <h3 className="text-xs font-semibold text-gray-700">Slowest {BREAKDOWN_OPTIONS.find((o) => o.key === dim)?.label}s</h3>
          <div className="flex flex-wrap items-center gap-1.5">
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
        <div className="space-y-1.5">
          {ranked.slice(0, 8).map((r) => (
            <div key={r.key} className="flex items-center justify-between text-sm border-b border-gray-50 py-1.5">
              <span className="text-gray-700">{r.key}</span>
              <span className="flex items-center gap-3 text-gray-500">
                <span>{r.call_count} calls</span>
                <span className="inline-flex items-center gap-1.5 font-semibold text-gray-800">
                  <HealthDot level={latencyHealth(r.avg_latency_ms)} />
                  {fmtMs(r.avg_latency_ms)}
                </span>
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
