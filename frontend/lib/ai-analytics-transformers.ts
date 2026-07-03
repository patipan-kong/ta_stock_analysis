import type { AiDailyUsageRow } from "@/lib/api";

// ─── Shared enums ──────────────────────────────────────────────────────────────

export type Granularity = "daily" | "weekly" | "monthly";
export const GRANULARITY_OPTIONS: Granularity[] = ["daily", "weekly", "monthly"];

export type BreakdownDim = "provider" | "model" | "layer" | "operation";
export const BREAKDOWN_OPTIONS: { key: BreakdownDim; label: string }[] = [
  { key: "provider", label: "Provider" },
  { key: "model", label: "Model" },
  { key: "layer", label: "Layer" },
  { key: "operation", label: "Operation" },
];

// ─── Bucket key helpers ─────────────────────────────────────────────────────────

function isoWeekStart(dayStr: string): string {
  const d = new Date(dayStr + "T00:00:00Z");
  const dow = (d.getUTCDay() + 6) % 7; // Mon=0..Sun=6
  d.setUTCDate(d.getUTCDate() - dow);
  return d.toISOString().slice(0, 10);
}

export function bucketKey(day: string, granularity: Granularity): string {
  if (granularity === "daily") return day;
  if (granularity === "weekly") return isoWeekStart(day);
  return day.slice(0, 7); // YYYY-MM
}

// ─── Grouped time series (stacked bar / multi-line): top N series + "Other" ──

export interface GroupedSeriesResult {
  data: Array<Record<string, string | number>>;
  seriesKeys: string[];
}

export function groupDailyByBucketAndDim(
  rows: AiDailyUsageRow[],
  granularity: Granularity,
  dim: BreakdownDim,
  valueField: "cost_usd" | "total_tokens" | "input_tokens" | "output_tokens" | "call_count",
  topN = 6,
): GroupedSeriesResult {
  const totalsByKey: Record<string, number> = {};
  const buckets: Record<string, Record<string, number>> = {};

  for (const r of rows) {
    const b = bucketKey(r.day, granularity);
    const k = r[dim] || "-";
    const v = r[valueField] ?? 0;
    totalsByKey[k] = (totalsByKey[k] ?? 0) + v;
    if (!buckets[b]) buckets[b] = {};
    buckets[b][k] = (buckets[b][k] ?? 0) + v;
  }

  const topKeys = Object.entries(totalsByKey)
    .sort((a, b) => b[1] - a[1])
    .slice(0, topN)
    .map(([k]) => k);
  const hasOther = Object.keys(totalsByKey).length > topKeys.length;
  const seriesKeys = hasOther ? [...topKeys, "Other"] : topKeys;

  const data = Object.keys(buckets)
    .sort()
    .map((b) => {
      const row: Record<string, string | number> = { bucket: b };
      for (const k of seriesKeys) row[k] = 0;
      for (const [k, v] of Object.entries(buckets[b])) {
        const target = topKeys.includes(k) ? k : "Other";
        row[target] = (row[target] as number) + v;
      }
      return row;
    });

  return { data, seriesKeys };
}

// ─── Latency trend (call-count-weighted avg/p95 per bucket) ───────────────────

export interface LatencyTrendPoint {
  bucket: string;
  avg_latency_ms: number;
  p95_latency_ms: number;
}

export function buildLatencyTrend(rows: AiDailyUsageRow[], granularity: Granularity): LatencyTrendPoint[] {
  const buckets: Record<string, { avgWeighted: number; p95Weighted: number; calls: number }> = {};
  for (const r of rows) {
    if (r.avg_latency_ms == null) continue;
    const b = bucketKey(r.day, granularity);
    if (!buckets[b]) buckets[b] = { avgWeighted: 0, p95Weighted: 0, calls: 0 };
    buckets[b].avgWeighted += r.avg_latency_ms * r.call_count;
    buckets[b].p95Weighted += (r.p95_latency_ms ?? r.avg_latency_ms) * r.call_count;
    buckets[b].calls += r.call_count;
  }
  return Object.keys(buckets)
    .sort()
    .map((b) => ({
      bucket: b,
      avg_latency_ms: Math.round(buckets[b].avgWeighted / buckets[b].calls),
      p95_latency_ms: Math.round(buckets[b].p95Weighted / buckets[b].calls),
    }));
}

// ─── Latency/token ranking by a single breakdown dimension (for "slowest models" /
// "largest responses" callouts — call-count-weighted, not a naive average of averages) ─

export interface DimRankRow {
  key: string;
  avg_latency_ms: number | null;
  avg_total_tokens: number;
  call_count: number;
}

export function rankByDim(rows: AiDailyUsageRow[], dim: BreakdownDim): DimRankRow[] {
  const groups: Record<string, { latWeighted: number; latCalls: number; tokens: number; calls: number }> = {};
  for (const r of rows) {
    const k = r[dim] || "-";
    if (!groups[k]) groups[k] = { latWeighted: 0, latCalls: 0, tokens: 0, calls: 0 };
    if (r.avg_latency_ms != null) {
      groups[k].latWeighted += r.avg_latency_ms * r.call_count;
      groups[k].latCalls += r.call_count;
    }
    groups[k].tokens += r.total_tokens;
    groups[k].calls += r.call_count;
  }
  return Object.entries(groups)
    .map(([key, g]) => ({
      key,
      avg_latency_ms: g.latCalls ? Math.round(g.latWeighted / g.latCalls) : null,
      avg_total_tokens: g.calls ? Math.round(g.tokens / g.calls) : 0,
      call_count: g.calls,
    }))
    .sort((a, b) => (b.avg_latency_ms ?? 0) - (a.avg_latency_ms ?? 0));
}

// ─── Provider / layer visual conventions (shared across the AI Analytics dashboard) ─

export const PROVIDER_CLS: Record<string, string> = {
  anthropic: "text-orange-700 bg-orange-50 border-orange-200",
  openai: "text-green-700  bg-green-50  border-green-200",
  gemini: "text-blue-700   bg-blue-50   border-blue-200",
  deepseek: "text-purple-700 bg-purple-50 border-purple-200",
  zhipu: "text-gray-600   bg-gray-50   border-gray-200",
  groq: "text-yellow-700 bg-yellow-50 border-yellow-200",
};

export const LAYER_LABELS: Record<string, string> = {
  layer1: "L1 Strategist",
  layer2: "L2 Challenger",
  layer3: "L3 Risk Auditor",
  fallback: "Fallback",
  "-": "—",
};

export const LAYER_ORDER = ["layer1", "layer2", "layer3", "fallback"];

export const LAYER_CLS: Record<string, string> = {
  layer1: "bg-orange-100 text-orange-700",
  layer2: "bg-blue-100 text-blue-700",
  layer3: "bg-purple-100 text-purple-700",
  fallback: "bg-red-100 text-red-700",
  "-": "bg-gray-100 text-gray-500",
};

// ─── Health color convention: green (healthy) / amber (warning) / red (problem) ─

export type HealthLevel = "healthy" | "warning" | "problem" | "unknown";

export const HEALTH_CLS: Record<HealthLevel, string> = {
  healthy: "text-green-700 bg-green-50 border-green-200",
  warning: "text-amber-700 bg-amber-50 border-amber-200",
  problem: "text-red-700 bg-red-50 border-red-200",
  unknown: "text-gray-500 bg-gray-50 border-gray-200",
};

// Thresholds are calibrated for LLM call latency (typically 3-70s for reasoning
// models), not generic HTTP APIs — a straight <1s/<3s split would paint almost
// every call red and defeat the point of the color coding.
export function latencyHealth(ms: number | null | undefined): HealthLevel {
  if (ms == null) return "unknown";
  if (ms < 8000) return "healthy";
  if (ms < 20000) return "warning";
  return "problem";
}

export function fallbackHealth(rate: number | null | undefined): HealthLevel {
  if (rate == null) return "unknown";
  if (rate < 0.05) return "healthy";
  if (rate < 0.2) return "warning";
  return "problem";
}

// ─── System Health — shared thresholds for every health card ────────────────
// Single home for level logic so every System Health card (AI providers,
// optimizer pipeline, policy engine, market data, portfolio engine,
// background jobs) reads the same green/amber/red/gray model.

export function ageHealth(minutes: number | null | undefined): HealthLevel {
  if (minutes == null) return "unknown";
  if (minutes < 30) return "healthy";
  if (minutes < 240) return "warning"; // < 4 hours
  return "problem";
}

export function booleanHealth(ok: boolean | null | undefined): HealthLevel {
  if (ok == null) return "unknown";
  return ok ? "healthy" : "problem";
}

export function invertedBooleanHealth(bad: boolean | null | undefined): HealthLevel {
  if (bad == null) return "unknown";
  return bad ? "problem" : "healthy";
}

export function schedulerRunHealth(status: string | null | undefined): HealthLevel {
  if (status === "completed") return "healthy";
  if (status === "running") return "healthy";
  if (status === "partial_failure") return "warning";
  if (status === "failed") return "problem";
  return "unknown";
}

export function policyEngineHealth(status: string | null | undefined): HealthLevel {
  if (status === "ACTIVE") return "healthy";
  if (status === "DISABLED_FALLBACK") return "problem";
  return "unknown";
}

// ─── Formatters ─────────────────────────────────────────────────────────────────

export function fmtMs(v: number | null | undefined): string {
  if (v == null) return "—";
  return v >= 1000 ? `${(v / 1000).toFixed(1)}s` : `${v}ms`;
}

export function fmtUsd(n: number | null | undefined, decimals = 4): string {
  if (n == null) return "—";
  return `$${n.toFixed(decimals)}`;
}

export function fmtInt(n: number | null | undefined): string {
  if (n == null) return "—";
  return n.toLocaleString("en-US");
}

export function fmtPct01(n: number | null | undefined): string {
  if (n == null) return "N/A";
  return `${(n * 100).toFixed(1)}%`;
}

export function fmtAgeMinutes(minutes: number | null | undefined): string {
  if (minutes == null) return "Unknown";
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${Math.round(minutes)} min ago`;
  if (minutes < 60 * 24) return `${(minutes / 60).toFixed(1)} hr ago`;
  return `${(minutes / 60 / 24).toFixed(1)} days ago`;
}

export function fmtTimestamp(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("en-US", {
    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
  });
}

export function bucketLabel(bucket: string, granularity: Granularity): string {
  if (granularity === "monthly") {
    const [y, m] = bucket.split("-").map(Number);
    return new Date(y, m - 1, 1).toLocaleDateString("en-US", { year: "2-digit", month: "short" });
  }
  const d = new Date(bucket + "T00:00:00Z");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}
