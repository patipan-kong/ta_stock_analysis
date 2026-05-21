"use client";

import { useEffect, useState } from "react";
import { getLatencyStats, getCostEstimate } from "@/lib/api";
import type { LatencyStats, CostEstimate, AnalysisLatencyStat, OptimizerLatencyStat, ModelCostStat } from "@/lib/api";

const PROVIDER_CLS: Record<string, string> = {
  anthropic: "text-orange-700 bg-orange-50 border-orange-200",
  openai:    "text-green-700  bg-green-50  border-green-200",
  gemini:    "text-blue-700   bg-blue-50   border-blue-200",
  deepseek:  "text-purple-700 bg-purple-50 border-purple-200",
  zhipu:     "text-gray-600   bg-gray-50   border-gray-200",
  groq:      "text-yellow-700 bg-yellow-50 border-yellow-200",
};

function ProviderTag({ provider }: { provider: string }) {
  const cls = PROVIDER_CLS[provider] ?? "text-gray-600 bg-gray-50 border-gray-200";
  return (
    <span className={`text-xs font-semibold px-1.5 py-0.5 rounded border ${cls}`}>
      {provider.toUpperCase()}
    </span>
  );
}

function LayerTag({ layer }: { layer: string }) {
  const cls =
    layer === "layer1" ? "bg-orange-100 text-orange-700" :
    layer === "layer2" ? "bg-blue-100   text-blue-700" :
                         "bg-purple-100 text-purple-700";
  const label =
    layer === "layer1" ? "L1 Strategist" :
    layer === "layer2" ? "L2 Challenger" :
                         "L3 Risk Auditor";
  return <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${cls}`}>{label}</span>;
}

function ms(v: number | null | undefined): string {
  if (v == null) return "—";
  return v >= 1000 ? `${(v / 1000).toFixed(1)}s` : `${v}ms`;
}

function fmt(v: number): string {
  return v.toLocaleString("en-US");
}

function SectionHeader({ title, subtitle }: { title: string; subtitle: string }) {
  return (
    <div className="px-5 py-4 border-b">
      <h2 className="font-semibold text-gray-800">{title}</h2>
      <p className="text-xs text-gray-500 mt-0.5">{subtitle}</p>
    </div>
  );
}

function AnalysisLatencyTable({ rows }: { rows: AnalysisLatencyStat[] }) {
  if (!rows.length) return <p className="px-5 py-4 text-sm text-gray-400">No data yet — run some analyses first.</p>;
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b text-xs text-gray-500 text-left">
            <th className="py-2 pl-5 pr-3 font-medium">Model</th>
            <th className="py-2 pr-3 font-medium text-right">Calls</th>
            <th className="py-2 pr-3 font-medium text-right">Avg</th>
            <th className="py-2 pr-3 font-medium text-right">Min</th>
            <th className="py-2 pr-3 font-medium text-right">Max</th>
            <th className="py-2 pr-3 font-medium text-right">P95</th>
            <th className="py-2 pr-5 font-medium text-right hidden sm:table-cell">Last used</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b hover:bg-gray-50">
              <td className="py-2.5 pl-5 pr-3">
                <div className="flex items-center gap-2">
                  <ProviderTag provider={row.provider} />
                  <span className="font-medium text-gray-800 text-sm">{row.model}</span>
                </div>
              </td>
              <td className="py-2.5 pr-3 text-right text-gray-600">{row.call_count}</td>
              <td className="py-2.5 pr-3 text-right font-semibold text-gray-800">{ms(row.avg_latency_ms)}</td>
              <td className="py-2.5 pr-3 text-right text-green-600">{ms(row.min_latency_ms)}</td>
              <td className="py-2.5 pr-3 text-right text-red-500">{ms(row.max_latency_ms)}</td>
              <td className="py-2.5 pr-3 text-right text-amber-600">{ms(row.p95_latency_ms)}</td>
              <td className="py-2.5 pr-5 text-right text-xs text-gray-400 hidden sm:table-cell">
                {row.last_used ? new Date(row.last_used).toLocaleDateString("th-TH") : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function OptimizerLatencyTable({ rows }: { rows: OptimizerLatencyStat[] }) {
  if (!rows.length) return <p className="px-5 py-4 text-sm text-gray-400">No data yet — run the optimizer first.</p>;
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b text-xs text-gray-500 text-left">
            <th className="py-2 pl-5 pr-3 font-medium">Model</th>
            <th className="py-2 pr-3 font-medium">Layer</th>
            <th className="py-2 pr-3 font-medium text-right">Calls</th>
            <th className="py-2 pr-5 font-medium text-right">Avg</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-b hover:bg-gray-50">
              <td className="py-2.5 pl-5 pr-3">
                <div className="flex items-center gap-2">
                  <ProviderTag provider={row.provider} />
                  <span className="font-medium text-gray-800 text-sm">{row.model}</span>
                </div>
              </td>
              <td className="py-2.5 pr-3"><LayerTag layer={row.layer} /></td>
              <td className="py-2.5 pr-3 text-right text-gray-600">{row.call_count}</td>
              <td className="py-2.5 pr-5 text-right font-semibold text-gray-800">{ms(row.avg_latency_ms)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function CostTable({ data }: { data: CostEstimate }) {
  const { by_model, total_estimated_usd } = data;
  if (!by_model.length) return <p className="px-5 py-4 text-sm text-gray-400">No data yet.</p>;
  const totalCalls = by_model.reduce((s, r) => s + r.call_count, 0);
  const totalIn    = by_model.reduce((s, r) => s + r.total_input_tokens, 0);
  const totalOut   = by_model.reduce((s, r) => s + r.total_output_tokens, 0);
  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b text-xs text-gray-500 text-left">
            <th className="py-2 pl-5 pr-3 font-medium">Model</th>
            <th className="py-2 pr-3 font-medium text-right">Calls</th>
            <th className="py-2 pr-3 font-medium text-right">Input tokens</th>
            <th className="py-2 pr-3 font-medium text-right">Output tokens</th>
            <th className="py-2 pr-5 font-medium text-right">Est. cost</th>
          </tr>
        </thead>
        <tbody>
          {by_model.map((row: ModelCostStat, i) => (
            <tr key={i} className="border-b hover:bg-gray-50">
              <td className="py-2.5 pl-5 pr-3">
                <div className="flex items-center gap-2">
                  <ProviderTag provider={row.provider} />
                  <span className="font-medium text-gray-800 text-sm">{row.model}</span>
                </div>
              </td>
              <td className="py-2.5 pr-3 text-right text-gray-600">{row.call_count}</td>
              <td className="py-2.5 pr-3 text-right text-gray-600">{fmt(row.total_input_tokens)}</td>
              <td className="py-2.5 pr-3 text-right text-gray-600">{fmt(row.total_output_tokens)}</td>
              <td className="py-2.5 pr-5 text-right font-semibold text-gray-800">
                ${row.estimated_cost_usd.toFixed(4)}
              </td>
            </tr>
          ))}
          <tr className="bg-gray-50 border-t-2 border-gray-300">
            <td className="py-2.5 pl-5 pr-3 font-semibold text-gray-700">Total</td>
            <td className="py-2.5 pr-3 text-right font-semibold text-gray-700">{totalCalls}</td>
            <td className="py-2.5 pr-3 text-right font-semibold text-gray-700">{fmt(totalIn)}</td>
            <td className="py-2.5 pr-3 text-right font-semibold text-gray-700">{fmt(totalOut)}</td>
            <td className="py-2.5 pr-5 text-right font-bold text-gray-900">${total_estimated_usd.toFixed(4)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}
function daysAgoStr(n: number) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

const DATE_PRESETS = [
  { label: "Today",   from: () => todayStr(),     to: () => todayStr() },
  { label: "7 days",  from: () => daysAgoStr(6),  to: () => todayStr() },
  { label: "30 days", from: () => daysAgoStr(29), to: () => todayStr() },
  { label: "All",     from: () => "",              to: () => "" },
];

export default function StatsPage() {
  const [latency, setLatency] = useState<LatencyStats | null>(null);
  const [cost, setCost] = useState<CostEstimate | null>(null);
  const [loading, setLoading] = useState(true);
  const [filtering, setFiltering] = useState(false);
  const [error, setError] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");

  useEffect(() => {
    Promise.all([getLatencyStats(), getCostEstimate()])
      .then(([l, c]) => { setLatency(l); setCost(c); })
      .catch(() => setError("Failed to load stats"))
      .finally(() => setLoading(false));
  }, []);

  function applyDateFilter(from: string, to: string) {
    setFromDate(from);
    setToDate(to);
    setFiltering(true);
    const f = from || undefined;
    const t = to || undefined;
    Promise.all([getLatencyStats(f, t), getCostEstimate(f, t)])
      .then(([l, c]) => { setLatency(l); setCost(c); })
      .catch(() => setError("Failed to load stats"))
      .finally(() => setFiltering(false));
  }

  if (loading) return <p className="text-sm text-gray-400">Loading…</p>;
  if (error)   return <p className="text-sm text-red-500">{error}</p>;

  const isFiltered = !!(fromDate || toDate);

  return (
    <div className="space-y-8 max-w-5xl">
      {/* Page header + global date filter */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold mb-1">AI Stats</h1>
          <p className="text-sm text-gray-500">Latency and token usage across all AI calls.</p>
        </div>
        <div className="bg-white border rounded-xl px-4 py-3 shadow-sm flex flex-wrap items-center gap-2">
          <span className="text-xs text-gray-500 font-medium mr-1">Period:</span>
          {DATE_PRESETS.map(preset => {
            const pFrom = preset.from();
            const pTo = preset.to();
            const active = fromDate === pFrom && toDate === pTo;
            return (
              <button
                key={preset.label}
                onClick={() => applyDateFilter(pFrom, pTo)}
                className={`text-xs px-3 py-1 rounded-full border transition-colors ${
                  active
                    ? "bg-gray-800 text-white border-gray-800"
                    : "bg-white text-gray-600 border-gray-300 hover:border-gray-500"
                }`}
              >
                {preset.label}
              </button>
            );
          })}
          <div className="flex items-center gap-1 ml-1">
            <input
              type="date"
              value={fromDate}
              onChange={e => applyDateFilter(e.target.value, toDate)}
              className="text-xs border rounded px-2 py-1 text-gray-700 focus:outline-none focus:ring-1 focus:ring-gray-400"
            />
            <span className="text-xs text-gray-400">–</span>
            <input
              type="date"
              value={toDate}
              onChange={e => applyDateFilter(fromDate, e.target.value)}
              className="text-xs border rounded px-2 py-1 text-gray-700 focus:outline-none focus:ring-1 focus:ring-gray-400"
            />
          </div>
          {filtering && <span className="text-xs text-gray-400 ml-1">Loading…</span>}
        </div>
      </div>

      {/* Analysis Latency */}
      <section className="bg-white border rounded-xl shadow-sm overflow-hidden">
        <SectionHeader
          title="Analysis Latency"
          subtitle="Per-call timing for single-stock analysis (summary AI call)."
        />
        <AnalysisLatencyTable rows={latency?.analysis ?? []} />
      </section>

      {/* Optimizer Latency */}
      <section className="bg-white border rounded-xl shadow-sm overflow-hidden">
        <SectionHeader
          title="Optimizer Latency"
          subtitle="Per-layer timing for 3-layer optimizer runs."
        />
        <OptimizerLatencyTable rows={latency?.optimizer ?? []} />
      </section>

      {/* Cost Estimate */}
      <section className="bg-white border rounded-xl shadow-sm overflow-hidden">
        <div className="px-5 py-4 border-b flex items-center justify-between">
          <div>
            <h2 className="font-semibold text-gray-800">Cost Estimate</h2>
            <p className="text-xs text-gray-500 mt-0.5">Based on actual token counts × pricing from ai-model.json.</p>
          </div>
          {cost && (
            <div className="text-right shrink-0">
              <p className="text-xs text-gray-500">{isFiltered ? "Filtered total" : "All-time total"}</p>
              <p className="text-xl font-bold text-gray-900">${cost.total_estimated_usd.toFixed(4)}</p>
            </div>
          )}
        </div>
        {cost ? <CostTable data={cost} /> : <p className="px-5 py-4 text-sm text-gray-400">No data.</p>}
      </section>
    </div>
  );
}
