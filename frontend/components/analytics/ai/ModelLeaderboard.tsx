"use client";

import { useMemo, useState } from "react";
import type { AiModelLeaderboardRow } from "@/lib/api";
import { fmtMs, fmtUsd, fmtInt, fmtPct01, latencyHealth, fallbackHealth } from "@/lib/ai-analytics-transformers";
import { ProviderTag, HealthDot } from "./shared";

type SortKey =
  | "call_count"
  | "avg_latency_ms"
  | "avg_cost_usd"
  | "avg_total_tokens"
  | "fallback_rate";

const SORT_OPTIONS: { key: SortKey; label: string }[] = [
  { key: "call_count", label: "Most Used" },
  { key: "avg_latency_ms", label: "Fastest" },
  { key: "avg_cost_usd", label: "Cheapest" },
  { key: "avg_total_tokens", label: "Lowest Tokens" },
  { key: "fallback_rate", label: "Most Reliable" },
];

// Lower-is-better metrics sort ascending (nulls last); call_count sorts descending.
const ASC_KEYS = new Set<SortKey>(["avg_latency_ms", "avg_cost_usd", "avg_total_tokens", "fallback_rate"]);

export default function ModelLeaderboard({ rows }: { rows: AiModelLeaderboardRow[] }) {
  const [sortKey, setSortKey] = useState<SortKey>("call_count");

  const sorted = useMemo(() => {
    const asc = ASC_KEYS.has(sortKey);
    return [...rows].sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      if (av == null && bv == null) return 0;
      if (av == null) return 1;
      if (bv == null) return -1;
      return asc ? av - bv : bv - av;
    });
  }, [rows, sortKey]);

  if (!rows.length) {
    return <p className="text-sm text-gray-400">No AI calls recorded yet.</p>;
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-1.5">
        <span className="text-xs text-gray-500 font-medium mr-1">Rank by:</span>
        {SORT_OPTIONS.map((o) => (
          <button
            key={o.key}
            onClick={() => setSortKey(o.key)}
            className={`text-xs px-3 py-1 rounded-full border transition-colors ${
              sortKey === o.key
                ? "bg-gray-800 text-white border-gray-800"
                : "bg-white text-gray-600 border-gray-300 hover:border-gray-500"
            }`}
          >
            {o.label}
          </button>
        ))}
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b text-xs text-gray-500 text-left">
              <th className="py-2 pr-3 font-medium">Model</th>
              <th className="py-2 pr-3 font-medium text-right">Calls</th>
              <th className="py-2 pr-3 font-medium text-right">Avg Latency</th>
              <th className="py-2 pr-3 font-medium text-right">Avg Cost</th>
              <th className="py-2 pr-3 font-medium text-right">Avg Tokens</th>
              <th className="py-2 pr-3 font-medium text-right">Success Rate</th>
              <th className="py-2 pr-3 font-medium text-right">JSON Parse</th>
              <th className="py-2 pr-3 font-medium text-right">Fallback Rate</th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((row, i) => (
              <tr key={`${row.provider}-${row.model}`} className="border-b hover:bg-gray-50">
                <td className="py-2.5 pr-3">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-gray-300 w-4">{i + 1}</span>
                    <ProviderTag provider={row.provider} />
                    <span className="font-medium text-gray-800">{row.model}</span>
                  </div>
                </td>
                <td className="py-2.5 pr-3 text-right text-gray-600">{fmtInt(row.call_count)}</td>
                <td className="py-2.5 pr-3 text-right">
                  <span className="inline-flex items-center gap-1.5 font-semibold text-gray-800">
                    <HealthDot level={latencyHealth(row.avg_latency_ms)} />
                    {fmtMs(row.avg_latency_ms)}
                  </span>
                </td>
                <td className="py-2.5 pr-3 text-right font-semibold text-gray-800">{fmtUsd(row.avg_cost_usd)}</td>
                <td className="py-2.5 pr-3 text-right text-gray-600">{fmtInt(row.avg_total_tokens)}</td>
                <td className="py-2.5 pr-3 text-right text-gray-400">{fmtPct01(row.success_rate)}</td>
                <td className="py-2.5 pr-3 text-right text-gray-400">{fmtPct01(row.json_parse_success_rate)}</td>
                <td className="py-2.5 pr-3 text-right">
                  <span className="inline-flex items-center gap-1.5">
                    <HealthDot level={fallbackHealth(row.fallback_rate)} />
                    {fmtPct01(row.fallback_rate)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs text-gray-300">
        Success Rate and JSON Parse Success aren&apos;t tracked yet — they&apos;ll populate automatically once recorded.
      </p>
    </div>
  );
}
