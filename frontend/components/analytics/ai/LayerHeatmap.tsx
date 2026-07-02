"use client";

import { useMemo, useState } from "react";
import type { AiLayerMatrixCell } from "@/lib/api";
import { LAYER_ORDER, LAYER_LABELS, fmtMs, fmtUsd, fmtInt, latencyHealth } from "@/lib/ai-analytics-transformers";
import { ProviderTag } from "./shared";

function CellIcon({ level }: { level: ReturnType<typeof latencyHealth> }) {
  if (level === "healthy") return <span className="text-green-600">✅</span>;
  if (level === "warning") return <span className="text-amber-600">⚠</span>;
  if (level === "problem") return <span className="text-red-600">✗</span>;
  return <span className="text-gray-300">–</span>;
}

export default function LayerHeatmap({ cells }: { cells: AiLayerMatrixCell[] }) {
  const [selected, setSelected] = useState<AiLayerMatrixCell | null>(null);

  const { modelKeys, byModelLayer } = useMemo(() => {
    const map = new Map<string, Map<string, AiLayerMatrixCell>>();
    const models = new Set<string>();
    for (const c of cells) {
      const mk = `${c.provider}/${c.model}`;
      models.add(mk);
      if (!map.has(mk)) map.set(mk, new Map());
      // Merge multiple operations landing on the same layer label (e.g. "-" for analyze).
      const existing = map.get(mk)!.get(c.layer);
      if (existing) {
        const totalCalls = existing.call_count + c.call_count;
        map.get(mk)!.set(c.layer, {
          ...existing,
          call_count: totalCalls,
          avg_latency_ms:
            existing.avg_latency_ms != null && c.avg_latency_ms != null
              ? Math.round((existing.avg_latency_ms * existing.call_count + c.avg_latency_ms * c.call_count) / totalCalls)
              : existing.avg_latency_ms ?? c.avg_latency_ms,
          avg_cost_usd: (existing.avg_cost_usd * existing.call_count + c.avg_cost_usd * c.call_count) / totalCalls,
          avg_total_tokens: Math.round(
            (existing.avg_total_tokens * existing.call_count + c.avg_total_tokens * c.call_count) / totalCalls,
          ),
        });
      } else {
        map.get(mk)!.set(c.layer, c);
      }
    }
    return { modelKeys: Array.from(models).sort(), byModelLayer: map };
  }, [cells]);

  if (!cells.length) {
    return <p className="text-sm text-gray-400">No optimizer/analyze calls recorded yet.</p>;
  }

  const layerCols = LAYER_ORDER.filter((l) => cells.some((c) => c.layer === l));
  const cols = layerCols.length ? layerCols : ["-"];

  return (
    <div className="space-y-4">
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b text-xs text-gray-500 text-left">
              <th className="py-2 pr-3 font-medium">Model</th>
              {cols.map((l) => (
                <th key={l} className="py-2 px-3 font-medium text-center whitespace-nowrap">
                  {LAYER_LABELS[l] ?? l}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {modelKeys.map((mk) => {
              const [provider, ...rest] = mk.split("/");
              const model = rest.join("/");
              return (
                <tr key={mk} className="border-b hover:bg-gray-50">
                  <td className="py-2.5 pr-3">
                    <div className="flex items-center gap-2">
                      <ProviderTag provider={provider} />
                      <span className="font-medium text-gray-800">{model}</span>
                    </div>
                  </td>
                  {cols.map((l) => {
                    const cell = byModelLayer.get(mk)?.get(l);
                    const isSelected = selected && selected.provider === provider && selected.model === model && selected.layer === l;
                    return (
                      <td key={l} className="py-2.5 px-3 text-center">
                        {cell ? (
                          <button
                            onClick={() => setSelected(cell)}
                            className={`w-8 h-8 rounded-lg flex items-center justify-center text-base transition-colors ${
                              isSelected ? "bg-blue-100 ring-2 ring-blue-400" : "hover:bg-gray-100"
                            }`}
                            title={`${cell.call_count} calls`}
                          >
                            <CellIcon level={latencyHealth(cell.avg_latency_ms)} />
                          </button>
                        ) : (
                          <span className="text-gray-200">–</span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {selected ? (
        <div className="bg-gray-50 border rounded-xl p-4 flex flex-wrap gap-6">
          <div>
            <p className="text-xs text-gray-500">Model / Layer</p>
            <p className="text-sm font-semibold text-gray-800 mt-0.5">
              {selected.provider}/{selected.model} · {LAYER_LABELS[selected.layer] ?? selected.layer}
            </p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Avg Latency</p>
            <p className="text-sm font-semibold text-gray-800 mt-0.5">{fmtMs(selected.avg_latency_ms)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Avg Cost</p>
            <p className="text-sm font-semibold text-gray-800 mt-0.5">{fmtUsd(selected.avg_cost_usd)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Avg Tokens</p>
            <p className="text-sm font-semibold text-gray-800 mt-0.5">{fmtInt(selected.avg_total_tokens)}</p>
          </div>
          <div>
            <p className="text-xs text-gray-500">Call Count</p>
            <p className="text-sm font-semibold text-gray-800 mt-0.5">{fmtInt(selected.call_count)}</p>
          </div>
        </div>
      ) : (
        <p className="text-xs text-gray-400">Click a cell to see its latency, cost, and token detail.</p>
      )}
    </div>
  );
}
