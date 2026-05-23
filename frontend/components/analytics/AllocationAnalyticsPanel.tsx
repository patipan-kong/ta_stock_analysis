"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  ReferenceLine,
} from "recharts";
import type { AllocationAnalyticsMetrics } from "@/lib/api";
import { transformSectorContribution, fmtPct, fmtNum, pnlColorClass } from "@/lib/analytics-transformers";

const CONCENTRATION_COLORS: Record<string, string> = {
  LOW:      "bg-green-100 text-green-700",
  MEDIUM:   "bg-amber-100 text-amber-700",
  HIGH:     "bg-orange-100 text-orange-700",
  CRITICAL: "bg-red-100 text-red-700",
};

function SectorBar({ color, value }: { color: string; value: number }) {
  const pct = Math.min(100, Math.abs(value) * 6); // scale contribution to bar width
  return (
    <div className="h-full rounded" style={{ width: `${pct}%`, minWidth: "2px", backgroundColor: color }} />
  );
}

interface AllocationAnalyticsPanelProps {
  metrics: AllocationAnalyticsMetrics | null;
}

export default function AllocationAnalyticsPanel({ metrics }: AllocationAnalyticsPanelProps) {
  if (!metrics) {
    return (
      <div className="flex items-center justify-center h-32 text-sm text-gray-400">
        No allocation data available.
      </div>
    );
  }

  const { sector_contribution, top_contributors, cash_utilization, concentration_risk } = metrics;

  const sectorData = transformSectorContribution(sector_contribution ?? []);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* Left column: contributors + cash + concentration */}
      <div className="space-y-5">
        {/* Concentration risk */}
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Concentration Risk</h3>
          <div className="flex items-center gap-3">
            <span
              className={`text-xs font-bold px-3 py-1 rounded-full ${
                CONCENTRATION_COLORS[concentration_risk?.hhi_label ?? "LOW"]
              }`}
            >
              {concentration_risk?.hhi_label ?? "—"}
            </span>
            <span className="text-xs text-gray-500">
              HHI {concentration_risk?.hhi != null ? fmtNum(concentration_risk.hhi, 0) : "—"}
              {" · "}Top holding {concentration_risk?.top_holding_weight_pct != null
                ? `${concentration_risk.top_holding_weight_pct.toFixed(1)}%`
                : "—"}
            </span>
          </div>
        </div>

        {/* Cash utilization */}
        <div>
          <h3 className="text-sm font-semibold text-gray-700 mb-2">Cash Utilization</h3>
          <div className="grid grid-cols-2 gap-2 text-xs">
            {[
              { label: "Current",  v: cash_utilization?.current_cash_pct },
              { label: "Average",  v: cash_utilization?.avg_cash_pct },
              { label: "Min",      v: cash_utilization?.min_cash_pct },
              { label: "Max",      v: cash_utilization?.max_cash_pct },
            ].map(({ label, v }) => (
              <div key={label} className="bg-gray-50 rounded-lg p-2.5">
                <p className="text-gray-400">{label}</p>
                <p className="font-semibold text-gray-700 tabular-nums">
                  {v != null ? `${v.toFixed(1)}%` : "—"}
                </p>
              </div>
            ))}
          </div>
        </div>

        {/* Top contributors */}
        {top_contributors?.top_contributors?.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">
              Top Contributors
              {top_contributors.snapshot_date && (
                <span className="ml-2 text-xs font-normal text-gray-400">
                  as of {top_contributors.snapshot_date}
                </span>
              )}
            </h3>
            <div className="space-y-1">
              {top_contributors.top_contributors.map((c) => (
                <div key={c.symbol} className="flex items-center justify-between py-1.5 border-b border-gray-50 last:border-0">
                  <div>
                    <span className="text-sm font-semibold text-blue-700">{c.symbol}</span>
                    <span className="ml-2 text-xs text-gray-400">{c.sector}</span>
                  </div>
                  <div className="text-right">
                    <span className={`text-sm font-semibold tabular-nums ${pnlColorClass(c.unrealized_pnl_pct)}`}>
                      {fmtPct(c.unrealized_pnl_pct)}
                    </span>
                    <p className="text-xs text-gray-400">{fmtNum(c.unrealized_pnl, 0)} THB/USD</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Worst contributors */}
        {top_contributors?.worst_contributors?.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Worst Performers</h3>
            <div className="space-y-1">
              {top_contributors.worst_contributors.map((c) => (
                <div key={c.symbol} className="flex items-center justify-between py-1.5 border-b border-gray-50 last:border-0">
                  <div>
                    <span className="text-sm font-semibold text-blue-700">{c.symbol}</span>
                    <span className="ml-2 text-xs text-gray-400">{c.sector}</span>
                  </div>
                  <div className="text-right">
                    <span className={`text-sm font-semibold tabular-nums ${pnlColorClass(c.unrealized_pnl_pct)}`}>
                      {fmtPct(c.unrealized_pnl_pct)}
                    </span>
                    <p className="text-xs text-gray-400">{fmtNum(c.market_value, 0)} THB/USD</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Right column: sector contribution chart */}
      <div>
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Sector Contribution</h3>
        {sectorData.length > 0 ? (
          <>
            <p className="text-xs text-gray-400 mb-3">Contribution to portfolio return (%) by sector</p>
            <ResponsiveContainer width="100%" height={Math.max(160, sectorData.length * 36)}>
              <BarChart
                data={sectorData}
                layout="vertical"
                margin={{ top: 4, right: 24, left: 8, bottom: 4 }}
              >
                <XAxis
                  type="number"
                  tick={{ fontSize: 11, fill: "#9ca3af" }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(v) => `${v > 0 ? "+" : ""}${v.toFixed(1)}%`}
                />
                <YAxis
                  type="category"
                  dataKey="sector"
                  tick={{ fontSize: 11, fill: "#374151" }}
                  axisLine={false}
                  tickLine={false}
                  width={90}
                />
                <Tooltip
                  formatter={(v, name) => {
                    const n = Number(v);
                    return [
                      name === "contribution_pct" ? `${n >= 0 ? "+" : ""}${n.toFixed(2)}%` : `${n.toFixed(1)}%`,
                      name === "contribution_pct" ? "Contribution" : "Avg Weight",
                    ];
                  }}
                  contentStyle={{ fontSize: 11 }}
                />
                <ReferenceLine x={0} stroke="#e5e7eb" />
                <Bar dataKey="contribution_pct" name="Contribution" radius={[0, 3, 3, 0]}>
                  {sectorData.map((d) => (
                    <Cell
                      key={d.sector}
                      fill={d.contribution_pct >= 0 ? "#2563eb" : "#dc2626"}
                      fillOpacity={0.75}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>

            {/* Avg weight table */}
            <div className="mt-4">
              <p className="text-xs text-gray-400 mb-2">Average sector weight</p>
              <div className="space-y-1.5">
                {sectorData.map((d) => (
                  <div key={d.sector} className="flex items-center gap-2">
                    <span className="text-xs text-gray-600 w-24 truncate">{d.sector}</span>
                    <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-blue-400"
                        style={{ width: `${Math.min(100, d.avg_weight_pct)}%` }}
                      />
                    </div>
                    <span className="text-xs text-gray-500 tabular-nums w-10 text-right">
                      {d.avg_weight_pct.toFixed(1)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </>
        ) : (
          <div className="flex items-center justify-center h-32 text-sm text-gray-400">
            No sector contribution data.
          </div>
        )}
      </div>
    </div>
  );
}
