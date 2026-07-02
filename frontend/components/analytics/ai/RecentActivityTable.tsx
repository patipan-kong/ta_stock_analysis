"use client";

import { useMemo, useState } from "react";
import type { AiRecentCall } from "@/lib/api";
import { fmtMs, fmtUsd, fmtInt, latencyHealth } from "@/lib/ai-analytics-transformers";
import { ProviderTag, LayerTag, HealthDot } from "./shared";

function FilterSelect({
  value,
  onChange,
  options,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  options: string[];
  placeholder: string;
}) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="text-xs border rounded px-2 py-1 text-gray-700 bg-white focus:outline-none focus:ring-1 focus:ring-gray-400"
    >
      <option value="">{placeholder}</option>
      {options.map((o) => (
        <option key={o} value={o}>
          {o}
        </option>
      ))}
    </select>
  );
}

export default function RecentActivityTable({ calls }: { calls: AiRecentCall[] }) {
  const [provider, setProvider] = useState("");
  const [model, setModel] = useState("");
  const [layer, setLayer] = useState("");

  const { providers, models, layers } = useMemo(() => {
    return {
      providers: Array.from(new Set(calls.map((c) => c.provider))).sort(),
      models: Array.from(new Set(calls.map((c) => c.model))).sort(),
      layers: Array.from(new Set(calls.map((c) => c.layer || "-"))).sort(),
    };
  }, [calls]);

  const filtered = useMemo(() => {
    return calls.filter(
      (c) =>
        (!provider || c.provider === provider) &&
        (!model || c.model === model) &&
        (!layer || (c.layer || "-") === layer),
    );
  }, [calls, provider, model, layer]);

  if (!calls.length) {
    return <p className="text-sm text-gray-400">No AI calls recorded yet.</p>;
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs text-gray-500 font-medium">Filter:</span>
        <FilterSelect value={provider} onChange={setProvider} options={providers} placeholder="All providers" />
        <FilterSelect value={model} onChange={setModel} options={models} placeholder="All models" />
        <FilterSelect value={layer} onChange={setLayer} options={layers} placeholder="All layers" />
        {(provider || model || layer) && (
          <button
            onClick={() => {
              setProvider("");
              setModel("");
              setLayer("");
            }}
            className="text-xs text-gray-400 hover:text-gray-600 underline"
          >
            Clear
          </button>
        )}
        <span className="text-xs text-gray-300 ml-auto">
          {filtered.length} of {calls.length} shown (most recent {calls.length})
        </span>
      </div>

      <div className="overflow-x-auto max-h-[480px] overflow-y-auto">
        <table className="min-w-full text-sm">
          <thead className="sticky top-0 bg-white">
            <tr className="border-b text-xs text-gray-500 text-left">
              <th className="py-2 pr-3 font-medium">Time</th>
              <th className="py-2 pr-3 font-medium">Provider</th>
              <th className="py-2 pr-3 font-medium">Model</th>
              <th className="py-2 pr-3 font-medium">Layer</th>
              <th className="py-2 pr-3 font-medium text-right">Latency</th>
              <th className="py-2 pr-3 font-medium text-right">Tokens</th>
              <th className="py-2 pr-3 font-medium text-right">Cost</th>
              <th className="py-2 pr-3 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((c) => (
              <tr key={c.id} className="border-b hover:bg-gray-50">
                <td className="py-2 pr-3 text-xs text-gray-500 whitespace-nowrap">
                  {c.created_at ? new Date(c.created_at).toLocaleString("th-TH") : "—"}
                </td>
                <td className="py-2 pr-3">
                  <ProviderTag provider={c.provider} />
                </td>
                <td className="py-2 pr-3 font-medium text-gray-800">{c.model}</td>
                <td className="py-2 pr-3">
                  <LayerTag layer={c.layer || "-"} />
                </td>
                <td className="py-2 pr-3 text-right">
                  <span className="inline-flex items-center gap-1.5">
                    <HealthDot level={latencyHealth(c.latency_ms)} />
                    {fmtMs(c.latency_ms)}
                  </span>
                </td>
                <td className="py-2 pr-3 text-right text-gray-600">{fmtInt(c.total_tokens)}</td>
                <td className="py-2 pr-3 text-right font-semibold text-gray-800">{fmtUsd(c.cost_usd, 6)}</td>
                <td className="py-2 pr-3">
                  <span className="text-xs font-semibold px-1.5 py-0.5 rounded bg-green-50 text-green-700 border border-green-200">
                    {c.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
