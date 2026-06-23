"use client";

import { useState } from "react";
import type { OperationsCenterStatus } from "@/lib/api";
import AgentStationGrid from "./AgentStationGrid";
import MarketStatusCard from "./MarketStatusCard";
import ConsensusRoomCard from "./ConsensusRoomCard";
import PolicyEnvelopeCard from "./PolicyEnvelopeCard";
import LatestCommitteeDecisionCard from "./LatestCommitteeDecisionCard";
import DecisionWorkspace from "../decision-workspace/DecisionWorkspace";

const fmtBaht = (v: number) =>
  `฿${v.toLocaleString("th-TH", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function CollapsiblePanel({
  title,
  summary,
  children,
}: {
  title: string;
  summary?: string;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <button
        className="w-full flex items-center justify-between gap-3 px-4 py-3 text-left hover:bg-gray-50 transition-colors"
        onClick={() => setOpen((v) => !v)}
      >
        <div className="flex items-center gap-2 min-w-0">
          <span className="text-sm font-medium text-gray-800">{title}</span>
          {summary && (
            <span className="text-xs text-gray-400 truncate">{summary}</span>
          )}
        </div>
        <span className="text-xs text-gray-400 shrink-0">
          {open ? "Hide" : "Show Details"}
        </span>
      </button>
      {open && <div className="px-4 pb-4">{children}</div>}
    </div>
  );
}

export default function QuantDashboard({
  portfolioId,
  status,
  optimizing,
  onRunOptimizer,
  initialSymbols,
}: {
  portfolioId: number;
  status: OperationsCenterStatus;
  optimizing: boolean;
  onRunOptimizer: () => void;
  initialSymbols?: string[];
}) {
  const s = status.portfolio_summary;
  const change = s.daily_return_pct;

  const marketSummary = status.market.regime?.replace(/_/g, " ") ?? undefined;
  const consensusSummary = status.optimizer.consensus_status?.replace(/_/g, " ") ?? undefined;

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

      <LatestCommitteeDecisionCard portfolioId={portfolioId} />

      <DecisionWorkspace portfolioId={portfolioId} initialSymbols={initialSymbols} />

      <CollapsiblePanel title="Market Context" summary={marketSummary}>
        <MarketStatusCard market={status.market} snapshotDate={s.snapshot_date} />
      </CollapsiblePanel>

      <CollapsiblePanel title="Committee Discussion" summary={consensusSummary}>
        <ConsensusRoomCard
          portfolioId={portfolioId}
          optimizer={status.optimizer}
          optimizing={optimizing}
          onRunOptimizer={onRunOptimizer}
          daysSinceRebalance={s.days_since_last_rebalance}
        />
      </CollapsiblePanel>

      <PolicyEnvelopeCard policy={status.policy} />
    </div>
  );
}
