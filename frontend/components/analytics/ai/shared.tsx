"use client";

import { PROVIDER_CLS, LAYER_CLS, LAYER_LABELS, HEALTH_CLS, type HealthLevel } from "@/lib/ai-analytics-transformers";

export function ProviderTag({ provider }: { provider: string }) {
  const cls = PROVIDER_CLS[provider] ?? "text-gray-600 bg-gray-50 border-gray-200";
  return (
    <span className={`text-xs font-semibold px-1.5 py-0.5 rounded border ${cls}`}>
      {provider.toUpperCase()}
    </span>
  );
}

export function LayerTag({ layer }: { layer: string }) {
  const cls = LAYER_CLS[layer] ?? LAYER_CLS["-"];
  const label = LAYER_LABELS[layer] ?? layer;
  return <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${cls}`}>{label}</span>;
}

export function HealthDot({ level }: { level: HealthLevel }) {
  const dot =
    level === "healthy" ? "bg-green-500" :
    level === "warning" ? "bg-amber-500" :
    level === "problem" ? "bg-red-500" :
                           "bg-gray-300";
  return <span className={`inline-block w-2 h-2 rounded-full ${dot}`} />;
}

// A single reliability metric card. `value` is a pre-formatted string (or "N/A").
// Extensibility: add a new metric to the dashboard by pushing another object with
// this shape — no layout changes required, unavailable metrics render as N/A.
export function ReliabilityMetricCard({
  label,
  value,
  level,
  sub,
}: {
  label: string;
  value: string;
  level: HealthLevel;
  sub?: string;
}) {
  const cls = HEALTH_CLS[level];
  return (
    <div className={`rounded-xl border p-4 ${level === "unknown" ? "bg-white border-gray-200" : cls}`}>
      <div className="flex items-center justify-between">
        <p className="text-xs font-medium text-gray-500">{label}</p>
        <HealthDot level={level} />
      </div>
      <p className={`text-lg font-bold mt-1 ${level === "unknown" ? "text-gray-400" : ""}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}
