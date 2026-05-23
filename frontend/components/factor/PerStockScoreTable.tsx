"use client";

import { useState } from "react";
import { sectorColor } from "@/lib/sectors";
import type { PerStockFactorScore } from "@/lib/api";

type SortKey = "weight" | "growth" | "value" | "dividend" | "momentum" | "quality" | "data_coverage";

const FACTORS: Array<{ key: SortKey; label: string; color: string }> = [
  { key: "quality",  label: "Quality",  color: "#14b8a6" },
  { key: "growth",   label: "Growth",   color: "#10b981" },
  { key: "momentum", label: "Momentum", color: "#8b5cf6" },
  { key: "value",    label: "Value",    color: "#3b82f6" },
  { key: "dividend", label: "Dividend", color: "#f59e0b" },
];

function ScoreCell({ score, color }: { score: number | null; color: string }) {
  if (score == null) {
    return (
      <div className="flex justify-center">
        <span className="text-[11px] text-gray-300 font-medium">—</span>
      </div>
    );
  }
  const intensity = score / 100;
  const bg = `${color}${Math.round(intensity * 0.25 * 255).toString(16).padStart(2, "0")}`;
  const textColor = score >= 65 ? color : score >= 40 ? "#6b7280" : "#9ca3af";

  return (
    <div
      className="flex items-center justify-center rounded-md px-1 py-0.5 min-w-[36px]"
      style={{ backgroundColor: bg }}
    >
      <span className="text-xs font-bold tabular-nums" style={{ color: textColor }}>
        {score.toFixed(0)}
      </span>
    </div>
  );
}

function CoverageBar({ pct }: { pct: number }) {
  const color = pct >= 80 ? "#10b981" : pct >= 50 ? "#f59e0b" : "#ef4444";
  return (
    <div className="flex items-center gap-1.5">
      <div className="w-12 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className="h-1.5 rounded-full" style={{ width: `${pct}%`, backgroundColor: color }} />
      </div>
      <span className="text-[11px] font-medium tabular-nums" style={{ color }}>{pct.toFixed(0)}%</span>
    </div>
  );
}

interface Props {
  stocks: PerStockFactorScore[];
}

export default function PerStockScoreTable({ stocks }: Props) {
  const [sortKey, setSortKey]   = useState<SortKey>("weight");
  const [sortAsc, setSortAsc]   = useState(false);
  const [expanded, setExpanded] = useState(false);

  if (stocks.length === 0) return null;

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortAsc(a => !a);
    } else {
      setSortKey(key);
      setSortAsc(false);
    }
  }

  const sorted = [...stocks].sort((a, b) => {
    let va: number, vb: number;
    if (sortKey === "weight") {
      va = a.weight;
      vb = b.weight;
    } else if (sortKey === "data_coverage") {
      va = a.data_coverage;
      vb = b.data_coverage;
    } else {
      va = a.scores[sortKey as keyof typeof a.scores] ?? -1;
      vb = b.scores[sortKey as keyof typeof b.scores] ?? -1;
    }
    return sortAsc ? va - vb : vb - va;
  });

  const visible = expanded ? sorted : sorted.slice(0, 8);

  function SortIcon({ k }: { k: SortKey }) {
    if (sortKey !== k) return <span className="text-gray-300 ml-0.5">↕</span>;
    return <span className="text-blue-500 ml-0.5">{sortAsc ? "↑" : "↓"}</span>;
  }

  function ColHeader({ k, label, color }: { k: SortKey; label: string; color?: string }) {
    return (
      <th
        className="px-3 py-2.5 text-center cursor-pointer select-none hover:bg-gray-100 transition-colors"
        onClick={() => toggleSort(k)}
      >
        <span
          className="text-[11px] font-bold uppercase tracking-wide"
          style={{ color: color ?? "#6b7280" }}
        >
          {label}<SortIcon k={k} />
        </span>
      </th>
    );
  }

  return (
    <div className="bg-white border border-gray-100 rounded-2xl shadow-sm overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-50 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-bold text-gray-800">Per-Stock Factor Breakdown</h3>
          <p className="text-xs text-gray-400 mt-0.5">Click column headers to sort</p>
        </div>
        <span className="text-xs text-gray-400 bg-gray-50 border border-gray-100 px-2.5 py-1 rounded-full">
          {stocks.length} holdings
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50/80">
              <th className="px-4 py-2.5 text-left">
                <span className="text-[11px] font-bold uppercase tracking-wide text-gray-500">Symbol</span>
              </th>
              <th className="px-3 py-2.5 text-left">
                <span className="text-[11px] font-bold uppercase tracking-wide text-gray-500">Sector</span>
              </th>
              <ColHeader k="weight"        label="Weight"   />
              <ColHeader k="quality"       label="Quality"  color="#14b8a6" />
              <ColHeader k="growth"        label="Growth"   color="#10b981" />
              <ColHeader k="momentum"      label="Mom."     color="#8b5cf6" />
              <ColHeader k="value"         label="Value"    color="#3b82f6" />
              <ColHeader k="dividend"      label="Div."     color="#f59e0b" />
              <ColHeader k="data_coverage" label="Coverage" />
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {visible.map((s, i) => {
              const secCol = sectorColor(s.sector);
              return (
                <tr
                  key={s.symbol}
                  className={`hover:bg-gray-50/60 transition-colors ${i % 2 === 0 ? "" : "bg-gray-50/30"}`}
                >
                  {/* Symbol */}
                  <td className="px-4 py-2.5">
                    <span className="text-sm font-bold text-gray-900">{s.symbol}</span>
                  </td>
                  {/* Sector */}
                  <td className="px-3 py-2.5">
                    <span
                      className="text-[11px] font-semibold px-2 py-0.5 rounded-md"
                      style={{
                        color: secCol,
                        backgroundColor: `${secCol}18`,
                        border: `1px solid ${secCol}30`,
                      }}
                    >
                      {s.sector ?? "Other"}
                    </span>
                  </td>
                  {/* Weight */}
                  <td className="px-3 py-2.5 text-center">
                    <span className="text-xs font-bold text-gray-700 tabular-nums">{s.weight.toFixed(1)}%</span>
                  </td>
                  {/* Factor scores */}
                  {FACTORS.map(f => (
                    <td key={f.key} className="px-3 py-2.5">
                      <ScoreCell score={s.scores[f.key as keyof typeof s.scores] ?? null} color={f.color} />
                    </td>
                  ))}
                  {/* Data coverage */}
                  <td className="px-3 py-2.5">
                    <CoverageBar pct={s.data_coverage} />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Show more / less */}
      {stocks.length > 8 && (
        <div className="px-5 py-3 border-t border-gray-50 text-center">
          <button
            onClick={() => setExpanded(e => !e)}
            className="text-xs font-semibold text-blue-600 hover:text-blue-700 transition-colors"
          >
            {expanded ? `Show fewer` : `Show all ${stocks.length} holdings`}
          </button>
        </div>
      )}
    </div>
  );
}
