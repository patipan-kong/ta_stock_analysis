"use client";

import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { FactorExposureResult } from "@/lib/api";

const FACTOR_ORDER = ["growth", "value", "dividend", "momentum", "quality"] as const;
const FACTOR_DISPLAY: Record<string, string> = {
  growth:   "Growth",
  value:    "Value",
  dividend: "Dividend",
  momentum: "Momentum",
  quality:  "Quality",
};

interface TooltipPayload {
  payload?: { factor: string; score: number; label: string };
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  if (!d) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-xl shadow-lg px-3 py-2 text-xs">
      <p className="font-semibold text-gray-800 mb-0.5">{d.factor}</p>
      <p className="text-blue-600 font-bold text-base tabular-nums">{d.score.toFixed(1)}<span className="text-gray-400 font-normal">/100</span></p>
      <p className="text-gray-500 mt-0.5">{d.label}</p>
    </div>
  );
}

interface Props {
  factorExposures: FactorExposureResult["factor_exposures"];
}

export default function FactorRadarChart({ factorExposures }: Props) {
  const data = FACTOR_ORDER.map(key => ({
    factor: FACTOR_DISPLAY[key],
    score:  factorExposures[key]?.score ?? 0,
    label:  factorExposures[key]?.label ?? "Unavailable",
    fullMark: 100,
  }));

  return (
    <div className="bg-white border border-gray-100 rounded-2xl shadow-sm p-5">
      <div className="mb-4">
        <h3 className="text-sm font-bold text-gray-800">Factor Exposure Radar</h3>
        <p className="text-xs text-gray-400 mt-0.5">Percentile-ranked relative to portfolio universe · 100 = highest exposure</p>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <RadarChart cx="50%" cy="50%" outerRadius="72%" data={data}>
          <PolarGrid
            stroke="#e5e7eb"
            strokeDasharray="3 3"
          />
          <PolarAngleAxis
            dataKey="factor"
            tick={{ fill: "#374151", fontSize: 12, fontWeight: 600 }}
            tickLine={false}
          />
          <PolarRadiusAxis
            angle={90}
            domain={[0, 100]}
            tick={false}
            axisLine={false}
            tickCount={5}
          />
          {/* Reference polygon at 50 */}
          <Radar
            name="Benchmark"
            dataKey={() => 50}
            stroke="#e5e7eb"
            fill="transparent"
            strokeWidth={1}
            strokeDasharray="4 4"
            dot={false}
          />
          <Radar
            name="Portfolio"
            dataKey="score"
            stroke="#3b82f6"
            fill="#3b82f6"
            fillOpacity={0.18}
            strokeWidth={2.5}
            dot={{ r: 4, fill: "#3b82f6", stroke: "#fff", strokeWidth: 2 }}
            activeDot={{ r: 6, fill: "#3b82f6", stroke: "#fff", strokeWidth: 2 }}
          />
          <Tooltip content={<CustomTooltip />} />
        </RadarChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex items-center justify-center gap-4 mt-2 text-xs text-gray-400">
        <span className="flex items-center gap-1.5">
          <span className="w-4 h-0.5 bg-blue-500 rounded-full inline-block" />
          Portfolio
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-4 h-0.5 bg-gray-300 rounded-full inline-block border-dashed" style={{ borderTop: "1.5px dashed #d1d5db", background: "none" }} />
          50th pct. reference
        </span>
      </div>
    </div>
  );
}
