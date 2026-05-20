"use client";

import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";
import type { SectorBreakdownItem, SectorBreakdown } from "@/lib/api";
import { sectorColor } from "@/lib/sectors";

const STATUS_BADGE: Record<string, string> = {
  EXCEEDS: "text-red-600 bg-red-50 border-red-300",
  WARNING: "text-amber-600 bg-amber-50 border-amber-300",
  OK:      "",
};

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: { payload: SectorBreakdownItem }[];
}) {
  if (!active || !payload?.length) return null;
  const s = payload[0].payload;
  return (
    <div className="bg-white border border-gray-200 rounded-lg shadow-md px-3 py-2.5 text-sm max-w-[200px]">
      <p className="font-semibold text-gray-800 mb-1">{s.sector}</p>
      <p className="text-gray-500">Value: ฿{s.value.toLocaleString("th-TH", { maximumFractionDigits: 0 })}</p>
      <p className="text-gray-500">Weight: <span className="font-medium">{s.weight_pct.toFixed(1)}%</span></p>
      <p className="text-gray-400 text-xs">Limit: {s.limit_pct}%</p>
      {s.stocks.length > 0 && (
        <p className="text-gray-400 text-xs mt-1">
          {s.stocks.map((sym) => sym.replace(".BK", "")).join(", ")}
        </p>
      )}
    </div>
  );
}

function LegendRow({ item }: { item: SectorBreakdownItem }) {
  const color = sectorColor(item.sector);
  const badgeCls = STATUS_BADGE[item.status];
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="w-2.5 h-2.5 rounded-full shrink-0" style={{ backgroundColor: color }} />
      <span className="text-gray-700 font-medium truncate flex-1">{item.sector}</span>
      <span className="text-gray-600">{item.weight_pct.toFixed(1)}%</span>
      <span className="text-gray-400">/{item.limit_pct}%</span>
      {badgeCls && (
        <span className={`text-xs font-semibold px-1 py-0.5 rounded border ${badgeCls}`}>
          {item.status}
        </span>
      )}
    </div>
  );
}

export default function SectorPieChart({ breakdown }: { breakdown: SectorBreakdown }) {
  const { sectors } = breakdown;
  if (!sectors.length) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-400 text-sm">
        No sector data available
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <ResponsiveContainer width="100%" height={220}>
        <PieChart>
          <Pie
            data={sectors}
            cx="50%"
            cy="50%"
            innerRadius="40%"
            outerRadius="68%"
            paddingAngle={2}
            dataKey="weight_pct"
            nameKey="sector"
          >
            {sectors.map((s, i) => {
              const color = sectorColor(s.sector);
              const strokeColor =
                s.status === "EXCEEDS" ? "#ef4444" :
                s.status === "WARNING" ? "#f59e0b" :
                "white";
              const strokeW = s.status !== "OK" ? 2.5 : 1.5;
              return (
                <Cell
                  key={i}
                  fill={color}
                  stroke={strokeColor}
                  strokeWidth={strokeW}
                />
              );
            })}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend
            content={() => null}
          />
        </PieChart>
      </ResponsiveContainer>

      <div className="space-y-1.5 px-1">
        {sectors.map((s) => (
          <LegendRow key={s.sector} item={s} />
        ))}
      </div>
    </div>
  );
}
