"use client";

// AI Evaluation M5 — S4 Execution Intelligence (`/ai-analytics/execution`).
// Renders GET /analytics/evaluation/execution (M3, already shipped) verbatim
// — zero metric computation. Class-segmented acceptance is the only honest
// way to read acceptance (UX D5) and is never rendered as an unsegmented total.

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { usePortfolio } from "@/lib/PortfolioContext";
import { getExecutionLedger, isUnresolvedPortfolioError, type ExecutionLedger, type ExecutionLedgerRow } from "@/lib/api";
import AsOfStamp from "@/components/evaluation/AsOfStamp";
import DecisionStatusBadge from "@/components/evaluation/DecisionStatusBadge";
import CounterfactualValue from "@/components/evaluation/CounterfactualValue";
import EvidenceLedger, { type EvidenceColumn } from "@/components/evaluation/EvidenceLedger";
import EvaluationColdStart from "@/components/evaluation/EvaluationColdStart";
import ClassSegmentBars from "@/components/evaluation/ClassSegmentBars";
import PortfolioSelectionNotice from "@/components/PortfolioSelectionNotice";

const PERIODS = [
  { label: "30D", days: 30 },
  { label: "90D", days: 90 },
  { label: "180D", days: 180 },
  { label: "1Y", days: 365 },
];

function pct(n: number | null | undefined, decimals = 1): string {
  if (n == null) return "—";
  return `${n >= 0 ? "+" : ""}${n.toFixed(decimals)}%`;
}

export default function ExecutionLedgerPage() {
  const { currentSelection, reportUnresolvedPortfolio } = usePortfolio();
  const portfolioId = currentSelection;
  const router = useRouter();

  const [periodDays, setPeriodDays] = useState(90);
  const [data, setData] = useState<ExecutionLedger | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // M36.1 WP4B F04 — captured Portfolio Identity; a response arriving after
  // Current Selection has moved to a different portfolio (or cleared to
  // NONE) is discarded instead of repopulating the page.
  const requestIdRef = useRef<number | null>(null);

  const load = useCallback(async () => {
    if (portfolioId == null) return;
    const pid = portfolioId;
    setLoading(true);
    setError(null);
    try {
      const result = await getExecutionLedger(pid, periodDays);
      if (requestIdRef.current !== pid) return;
      setData(result);
    } catch (e) {
      if (requestIdRef.current !== pid) return;
      setError(e instanceof Error ? e.message : "Failed to load execution ledger");
      if (isUnresolvedPortfolioError(e)) reportUnresolvedPortfolio(pid);
    } finally {
      if (requestIdRef.current === pid) setLoading(false);
    }
  }, [portfolioId, periodDays, reportUnresolvedPortfolio]);

  useEffect(() => {
    requestIdRef.current = portfolioId;
    if (portfolioId == null) {
      setData(null);
      setError(null);
      setLoading(false);
      return;
    }
    load();
  }, [portfolioId, load]);

  if (portfolioId == null) {
    return <PortfolioSelectionNotice label="Execution Intelligence" />;
  }

  const columns: EvidenceColumn<ExecutionLedgerRow>[] = [
    { key: "date", header: "Date", render: (r) => <span className="text-gray-500">{r.date?.slice(0, 10) ?? "—"}</span> },
    { key: "snapshot", header: "Rec", render: (r) => <span className="font-medium text-gray-700">#{r.snapshot_id}</span> },
    { key: "decision", header: "Decision", render: (r) => <DecisionStatusBadge decision={r.decision} /> },
    {
      key: "score", header: "Exec score", align: "right",
      render: (r) => <span className="tabular-nums text-gray-700">{r.execution_score != null ? r.execution_score.toFixed(0) : "—"}</span>,
    },
    {
      key: "completeness", header: "Completeness", align: "right",
      render: (r) => <span className="tabular-nums text-gray-500">{r.completeness_pct != null ? `${r.completeness_pct.toFixed(0)}%` : "—"}</span>,
    },
    {
      key: "funding", header: "Funding", align: "right",
      render: (r) => <span className="tabular-nums text-gray-500">{r.funding_fidelity_pct != null ? `${r.funding_fidelity_pct.toFixed(0)}%` : "n/a"}</span>,
    },
    {
      key: "outcome", header: "Outcome", align: "right",
      render: (r) =>
        r.outcome_delta == null ? (
          <span className="text-gray-300">—</span>
        ) : r.outcome_delta.is_counterfactual ? (
          <CounterfactualValue value={r.outcome_delta.alpha ?? r.outcome_delta.return_pct} />
        ) : (
          <span className={`font-semibold tabular-nums ${(r.outcome_delta.alpha ?? 0) >= 0 ? "text-green-700" : "text-red-600"}`}>
            {pct(r.outcome_delta.alpha ?? r.outcome_delta.return_pct)}
          </span>
        ),
    },
  ];

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Execution Intelligence</h1>
          <p className="text-sm text-gray-500 mt-0.5">Decisions and how execution compared to the plan.</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="inline-flex items-center gap-1 rounded-lg bg-gray-100 p-1">
            {PERIODS.map((p) => (
              <button
                key={p.days}
                onClick={() => setPeriodDays(p.days)}
                className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                  periodDays === p.days ? "bg-white text-blue-700 shadow-sm" : "text-gray-500 hover:text-gray-800"
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
          {data && <AsOfStamp asOf={data.as_of} />}
        </div>
      </div>

      {error && <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg">{error}</div>}

      {loading && !data && (
        <div className="space-y-3">
          <div className="h-28 animate-pulse bg-gray-100 rounded-xl" />
          <div className="h-64 animate-pulse bg-gray-100 rounded-xl" />
        </div>
      )}

      {!loading && data && data.status === "cold_start" && (
        <EvaluationColdStart
          title="ยังไม่มีการบันทึกการตัดสินใจ"
          message="เมื่อคุณอนุมัติ ปฏิเสธ หรือปรับเปลี่ยนคำแนะนำ ข้อมูลคุณภาพการดำเนินการจะปรากฏที่นี่"
        />
      )}

      {!loading && data && data.status !== "cold_start" && (
        <>
          <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
            <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
              <span className="text-gray-500">
                Decisions: <strong className="text-gray-800">{data.summary.total_decisions}</strong>
              </span>
              {Object.entries(data.summary.decision_counts).map(([k, v]) => (
                <span key={k} className="text-gray-400">
                  {k} <strong className="text-gray-600">{v}</strong>
                </span>
              ))}
            </div>

            <div>
              <p className="text-xs font-semibold text-gray-500 mb-1.5">Acceptance by trade class</p>
              <ClassSegmentBars
                rows={Object.entries(data.summary.acceptance_by_class).map(([label, v]) => ({
                  label, numerator: v.accepted, denominator: v.total,
                }))}
                emptyMessage="No classified trades in this window."
              />
              <p className="text-[11px] text-gray-400 mt-1.5 italic">{data.summary.acceptance_note}</p>
            </div>

            <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-gray-500 pt-2 border-t">
              <span>Avg execution score: <strong className="text-gray-700">{data.summary.avg_execution_score?.toFixed(0) ?? "—"}</strong></span>
              <span>Avg timing delta: <strong className="text-gray-700">{pct(data.summary.avg_timing_delta_pct)}</strong></span>
              <span>Funding fidelity: <strong className="text-gray-700">{data.summary.avg_funding_fidelity_pct != null ? `${data.summary.avg_funding_fidelity_pct.toFixed(0)}%` : "n/a"}</strong></span>
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <EvidenceLedger
              columns={columns}
              rows={data.rows}
              rowKey={(r) => r.decision_id}
              onRowClick={(r) => router.push(`/ai-analytics/execution/${r.decision_id}`)}
              emptyMessage="No decisions in this window."
            />
          </div>
        </>
      )}
    </div>
  );
}
