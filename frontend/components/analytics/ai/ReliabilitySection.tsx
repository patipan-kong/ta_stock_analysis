"use client";

import type { AiReliabilitySummary } from "@/lib/api";
import { fmtPct01, fallbackHealth, type HealthLevel } from "@/lib/ai-analytics-transformers";
import { ReliabilityMetricCard } from "./shared";

// Extensibility: this array is the single place new reliability signals get wired
// in (stop_reason, thinking_mode, cache_hit, retry_count, ...). Until the backend
// records them, add an entry with value: null — it renders as N/A automatically.
function buildMetrics(r: AiReliabilitySummary) {
  return [
    {
      label: "Fallback Rate",
      value: fmtPct01(r.fallback_rate),
      level: fallbackHealth(r.fallback_rate),
      sub: "Share of optimizer calls that hit the global fallback model",
    },
    {
      label: "Success Rate",
      value: fmtPct01(r.success_rate),
      level: "unknown" as HealthLevel,
      sub: "Not tracked yet — only completed calls are recorded today",
    },
    {
      label: "JSON Parse Success",
      value: fmtPct01(r.json_parse_success_rate),
      level: "unknown" as HealthLevel,
      sub: "Not tracked yet",
    },
    {
      label: "API Errors",
      value: fmtPct01(r.api_error_rate),
      level: "unknown" as HealthLevel,
      sub: "Not tracked yet",
    },
    {
      label: "Timeouts",
      value: fmtPct01(r.timeout_rate),
      level: "unknown" as HealthLevel,
      sub: "Not tracked yet",
    },
    {
      label: "Max Token Stops",
      value: fmtPct01(r.max_token_stop_rate),
      level: "unknown" as HealthLevel,
      sub: "Not tracked yet",
    },
    {
      label: "Stop Reason",
      value: "N/A",
      level: "unknown" as HealthLevel,
      sub: "Future metric",
    },
    {
      label: "Thinking Mode",
      value: "N/A",
      level: "unknown" as HealthLevel,
      sub: "Future metric",
    },
  ];
}

export default function ReliabilitySection({ reliability }: { reliability: AiReliabilitySummary }) {
  const metrics = buildMetrics(reliability);
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
        {metrics.map((m) => (
          <ReliabilityMetricCard key={m.label} label={m.label} value={m.value} level={m.level} sub={m.sub} />
        ))}
      </div>
      <p className="text-xs text-gray-300">
        UserUsage currently only records calls that completed successfully, so error/timeout/parse-failure rates
        aren&apos;t derivable from existing data — they&apos;ll switch from N/A to live values once tracked.
      </p>
    </div>
  );
}
