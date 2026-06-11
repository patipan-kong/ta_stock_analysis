"use client";

import type { OperationsCenterStatus } from "@/lib/api";
import AgentStationGrid from "./AgentStationGrid";
import MarketStatusCard from "./MarketStatusCard";
import ConsensusRoomCard from "./ConsensusRoomCard";
import PolicyEnvelopeCard from "./PolicyEnvelopeCard";

const fmtBaht = (v: number) =>
  `฿${v.toLocaleString("th-TH", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export default function QuantDashboard({
  status,
  optimizing,
  onRunOptimizer,
}: {
  status: OperationsCenterStatus;
  optimizing: boolean;
  onRunOptimizer: () => void;
}) {
  const s = status.portfolio_summary;
  const change = s.daily_return_pct;

  return (
    <div className="space-y-4">
      {/* Compact NAV strip */}
      <div className="rounded-xl border-2 border-gray-900 bg-gray-900 text-gray-100 px-5 py-3 font-mono text-sm flex flex-wrap items-center gap-x-6 gap-y-1">
        <span>
          NAV{" "}
          <span className="font-bold text-white">
            {s.portfolio_value != null ? fmtBaht(s.portfolio_value) : "—"}
          </span>
        </span>
        <span>
          1D{" "}
          <span
            className={`font-bold ${
              change == null ? "text-gray-400" : change >= 0 ? "text-emerald-400" : "text-red-400"
            }`}
          >
            {change != null ? `${change >= 0 ? "+" : ""}${change.toFixed(2)}%` : "—"}
          </span>
        </span>
        {s.days_since_last_rebalance != null && (
          <span>
            ปรับพอร์ตล่าสุด{" "}
            <span className="font-bold text-white">{s.days_since_last_rebalance} วันที่แล้ว</span>
          </span>
        )}
        {s.snapshot_date && (
          <span className="text-gray-400">ข้อมูล ณ {s.snapshot_date}</span>
        )}
      </div>

      <AgentStationGrid agentHealth={status.agent_health} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <MarketStatusCard market={status.market} snapshotDate={s.snapshot_date} />
        <ConsensusRoomCard
          optimizer={status.optimizer}
          optimizing={optimizing}
          onRunOptimizer={onRunOptimizer}
          daysSinceRebalance={s.days_since_last_rebalance}
        />
      </div>

      <PolicyEnvelopeCard policy={status.policy} />
    </div>
  );
}
