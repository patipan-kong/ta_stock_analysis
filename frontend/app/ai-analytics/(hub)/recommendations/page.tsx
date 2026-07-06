"use client";

// AI Evaluation M4 — S2 Recommendations ledger (`/ai-analytics/recommendations`).
// Every recommendation snapshot ever made, newest first. Renders
// GET /analytics/evaluation/recommendations verbatim; the Decision/Consensus
// filters below only hide/show already-fetched rows — no value is recomputed.

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { usePortfolio } from "@/lib/PortfolioContext";
import { getRecommendationsLedger, type RecommendationLedger, type RecommendationLedgerRow } from "@/lib/api";
import EvidenceLedger, { type EvidenceColumn } from "@/components/evaluation/EvidenceLedger";
import HorizonStrip from "@/components/evaluation/HorizonStrip";
import DecisionStatusBadge from "@/components/evaluation/DecisionStatusBadge";
import CounterfactualValue from "@/components/evaluation/CounterfactualValue";
import AsOfStamp from "@/components/evaluation/AsOfStamp";
import EvaluationColdStart from "@/components/evaluation/EvaluationColdStart";

const PAGE_SIZE = 50;
const DECISION_FILTERS = ["All", "APPROVED", "REJECTED", "PARTIAL_EXECUTION", "MANUAL_OVERRIDE", "EXPIRED", "No decision"];

export default function RecommendationsLedgerPage() {
  const { activeId } = usePortfolio();
  const portfolioId = activeId ?? 0;
  const router = useRouter();

  const [offset, setOffset] = useState(0);
  const [data, setData] = useState<RecommendationLedger | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [decisionFilter, setDecisionFilter] = useState("All");
  const [consensusFilter, setConsensusFilter] = useState("All");

  const load = useCallback(async () => {
    if (!portfolioId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await getRecommendationsLedger(portfolioId, PAGE_SIZE, offset);
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load recommendations ledger");
    } finally {
      setLoading(false);
    }
  }, [portfolioId, offset]);

  useEffect(() => {
    load();
  }, [load]);

  const consensusOptions = useMemo(() => {
    const set = new Set<string>();
    (data?.rows ?? []).forEach((r) => r.consensus_type && set.add(r.consensus_type));
    return ["All", ...Array.from(set)];
  }, [data]);

  const filteredRows = useMemo(() => {
    let rows = data?.rows ?? [];
    if (decisionFilter !== "All") {
      rows = rows.filter((r) => (decisionFilter === "No decision" ? !r.decision : r.decision === decisionFilter));
    }
    if (consensusFilter !== "All") {
      rows = rows.filter((r) => r.consensus_type === consensusFilter);
    }
    return rows;
  }, [data, decisionFilter, consensusFilter]);

  const columns: EvidenceColumn<RecommendationLedgerRow>[] = [
    { key: "id", header: "#", render: (r) => <span className="font-medium text-gray-500">{r.snapshot_id}</span> },
    { key: "date", header: "Date", render: (r) => r.date?.slice(0, 10) ?? "—" },
    { key: "consensus", header: "Consensus", render: (r) => r.consensus_type ?? "—" },
    { key: "trades", header: "Trades", align: "right", render: (r) => r.trade_count },
    {
      key: "decision",
      header: "Decision",
      render: (r) => (
        <div className="flex items-center gap-1.5">
          <DecisionStatusBadge decision={r.decision} />
          {r.is_system_generated && <span className="text-[10px] text-gray-400">auto</span>}
        </div>
      ),
    },
    { key: "horizons", header: "7D / 30D / 90D / 180D", render: (r) => <HorizonStrip strip={r.horizon_strip} isCounterfactual={r.is_counterfactual} /> },
    {
      key: "alpha",
      header: "Alpha",
      align: "right",
      render: (r) =>
        r.headline_alpha == null ? (
          <span className="text-gray-300">—</span>
        ) : r.is_counterfactual ? (
          <CounterfactualValue value={r.headline_alpha} />
        ) : (
          <span className={`font-semibold tabular-nums ${r.headline_alpha >= 0 ? "text-green-700" : "text-red-600"}`}>
            {r.headline_alpha >= 0 ? "+" : ""}
            {r.headline_alpha.toFixed(1)}%
          </span>
        ),
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Recommendations</h1>
          <p className="text-sm text-gray-500 mt-0.5">Every recommendation snapshot ever made, newest first.</p>
        </div>
        {data && <AsOfStamp asOf={data.as_of} />}
      </div>

      {error && <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg">{error}</div>}

      {!loading && data && data.status === "cold_start" ? (
        <EvaluationColdStart
          title="ยังไม่มีคำแนะนำในบันทึก"
          message="รายการนี้จะเริ่มมีข้อมูลทันทีที่ Optimizer สร้างคำแนะนำครั้งแรก — รวมถึงคำแนะนำที่ระบบเลือก 'ไม่ทำอะไร' ก็จะถูกประเมินเช่นกัน"
        />
      ) : (
        <div className="bg-white border border-gray-200 rounded-xl overflow-hidden">
          <div className="flex flex-wrap items-center gap-2 px-4 py-3 border-b border-gray-100">
            <span className="text-xs text-gray-400 font-medium">Decision:</span>
            {DECISION_FILTERS.map((f) => (
              <button
                key={f}
                onClick={() => setDecisionFilter(f)}
                className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                  decisionFilter === f ? "bg-gray-800 text-white border-gray-800" : "bg-white text-gray-600 border-gray-300 hover:border-gray-500"
                }`}
              >
                {f}
              </button>
            ))}
            {consensusOptions.length > 1 && (
              <>
                <span className="text-xs text-gray-400 font-medium ml-2">Consensus:</span>
                {consensusOptions.map((c) => (
                  <button
                    key={c}
                    onClick={() => setConsensusFilter(c)}
                    className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                      consensusFilter === c ? "bg-gray-800 text-white border-gray-800" : "bg-white text-gray-600 border-gray-300 hover:border-gray-500"
                    }`}
                  >
                    {c}
                  </button>
                ))}
              </>
            )}
          </div>

          <EvidenceLedger
            columns={columns}
            rows={filteredRows}
            rowKey={(r) => r.snapshot_id}
            onRowClick={(r) => router.push(`/ai-analytics/recommendations/${r.snapshot_id}`)}
            loading={loading && !data}
            emptyMessage="No recommendations match this filter."
          />

          {data && data.total > PAGE_SIZE && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-100 text-xs text-gray-500">
              <span>
                {offset + 1}–{Math.min(offset + PAGE_SIZE, data.total)} of {data.total}
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
                  disabled={offset === 0}
                  className="px-2.5 py-1 rounded border border-gray-300 disabled:opacity-40"
                >
                  ← Prev
                </button>
                <button
                  onClick={() => setOffset((o) => o + PAGE_SIZE)}
                  disabled={offset + PAGE_SIZE >= data.total}
                  className="px-2.5 py-1 rounded border border-gray-300 disabled:opacity-40"
                >
                  Next →
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      <p className="text-xs text-gray-400">Column key: 7D/30D/90D/180D returns — ◐ maturing · ⏳ pending grading · * counterfactual (plan not executed)</p>
    </div>
  );
}
