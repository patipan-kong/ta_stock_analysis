"use client";

// AI Evaluation M5 — S4b Execution Detail (`/ai-analytics/execution/{id}`).
// Renders GET /analytics/evaluation/execution/{decision_id} (M3, already
// shipped) verbatim — plan-vs-actual per trade, the four deltas, and the
// §8 PARTIAL-execution warning when applicable.

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { usePortfolio } from "@/lib/PortfolioContext";
import { getExecutionDetail, type ExecutionDetail } from "@/lib/api";
import BackBreadcrumb from "@/components/BackBreadcrumb";
import DecisionStatusBadge from "@/components/evaluation/DecisionStatusBadge";
import AsOfStamp from "@/components/evaluation/AsOfStamp";

function pct(n: number | null | undefined, decimals = 1): string {
  if (n == null) return "not measurable";
  return `${n >= 0 ? "+" : ""}${n.toFixed(decimals)}%`;
}

export default function ExecutionDetailPage() {
  const params = useParams();
  const decisionId = Number(params?.id);
  const { activeId } = usePortfolio();
  const portfolioId = activeId ?? 0;

  const [data, setData] = useState<ExecutionDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!portfolioId || !decisionId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await getExecutionDetail(portfolioId, decisionId);
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load execution detail");
    } finally {
      setLoading(false);
    }
  }, [portfolioId, decisionId]);

  useEffect(() => {
    load();
  }, [load]);

  return (
    <div className="space-y-4">
      <BackBreadcrumb parent="Execution" current={`#${decisionId}`} href="/ai-analytics/execution" />

      {error && <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg">{error}</div>}

      {loading && !data && <div className="h-64 animate-pulse bg-gray-100 rounded-xl" />}

      {!loading && !data && !error && <p className="text-sm text-gray-400 py-10 text-center">Decision not found.</p>}

      {data && (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-gray-900">Decision #{data.decision_id}</h1>
              <DecisionStatusBadge decision={data.decision} />
              {data.executed_at && <span className="text-xs text-gray-400">executed {data.executed_at.slice(0, 10)}</span>}
            </div>
            <AsOfStamp asOf={data.as_of} />
          </div>

          {data.partial_warning && (
            <div className="p-3 bg-amber-50 border border-amber-200 text-amber-800 text-sm rounded-lg">
              ⚠ {data.partial_warning}
            </div>
          )}

          <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
            {data.analysis.status === "unavailable" ? (
              <p className="text-sm text-gray-400 italic">
                Execution analysis unavailable — {data.analysis.reason ?? "no linked transactions"}.
              </p>
            ) : (
              <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
                <span className="text-gray-500">
                  Execution score: <strong className="text-gray-800">{data.analysis.score != null ? data.analysis.score.toFixed(0) : "—"}</strong>
                </span>
                <span className="text-gray-500">
                  Completeness: <strong className="text-gray-800">{data.analysis.completeness_pct.toFixed(0)}%</strong>
                </span>
                <span className="text-gray-500">
                  Funding fidelity: <strong className="text-gray-800">{data.analysis.funding_fidelity_pct != null ? `${data.analysis.funding_fidelity_pct.toFixed(0)}%` : "n/a"}</strong>
                </span>
                {data.analysis.status === "partial" && <span className="text-amber-600 font-semibold">⚠ partial</span>}
              </div>
            )}

            {Object.keys(data.analysis.symbols ?? {}).length > 0 && (
              <div className="overflow-x-auto pt-2 border-t">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-xs text-gray-500 border-b">
                      <th className="py-2 px-3 font-medium">Symbol</th>
                      <th className="py-2 px-3 font-medium">Action</th>
                      <th className="py-2 px-3 font-medium text-right">Planned</th>
                      <th className="py-2 px-3 font-medium text-right">Executed</th>
                      <th className="py-2 px-3 font-medium text-right">Timing Δ</th>
                      <th className="py-2 px-3 font-medium text-right">Size Δ</th>
                      <th className="py-2 px-3 font-medium">Note</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(data.analysis.symbols).map(([sym, d]) => (
                      <tr key={sym} className="border-b last:border-0">
                        <td className="py-2 px-3 font-semibold text-gray-800">{sym.replace(".BK", "")}</td>
                        <td className="py-2 px-3 text-gray-500">{d.action}</td>
                        <td className="py-2 px-3 text-right tabular-nums text-gray-600">
                          ฿{d.planned_amount.toLocaleString("th-TH")}
                        </td>
                        <td className="py-2 px-3 text-right tabular-nums text-gray-600">
                          {d.executed_amount != null ? `฿${d.executed_amount.toLocaleString("th-TH")}` : "—"}
                        </td>
                        <td className="py-2 px-3 text-right tabular-nums text-gray-600">{pct(d.timing_delta_pct)}</td>
                        <td className="py-2 px-3 text-right tabular-nums text-gray-600">{pct(d.size_delta_pct, 0)}</td>
                        <td className="py-2 px-3 text-xs text-gray-400 italic">{d.note ?? ""}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
