"use client";

// AI Evaluation M6 — S7 Portfolios (`/ai-analytics/portfolios`).
// Renders GET /analytics/shadow-performance's three_portfolios verbatim
// (services/evaluation/ideal_series.py::compute_three_portfolios) — the
// hero comparison of Ideal / AI Portfolio / Your Portfolio, indexed to 100,
// with Gap A (Ideal−AI, implementation shortfall) and Gap B (AI−You, human
// deviation) each carrying a backend-composed one-line interpretation
// (services/evaluation/verdict_composer.compose_gap_interpretation).
//
// Scope note: the UX wireframe also specifies Allocation (sector
// side-by-side), Contribution (per-holding), and a full underwater Drawdown
// chart. Those require net-new per-holding/per-sector attribution
// infrastructure beyond what M6's backend scope (Ideal series + Gap A +
// attribution waterfall) produces. This page ships the hero chart, the two
// named gaps, and a compact Risk table (max drawdown / volatility per
// portfolio — already computed by ideal_series.py and attribution_engine.py)
// and defers Allocation/Contribution/underwater-Drawdown to a future
// milestone rather than fabricate them client-side.

import { useCallback, useEffect, useState } from "react";
import { usePortfolio } from "@/lib/PortfolioContext";
import { getShadowPerformanceSummary, type ShadowPerformanceSummary } from "@/lib/api";
import AsOfStamp from "@/components/evaluation/AsOfStamp";
import GapAnnotation from "@/components/evaluation/GapAnnotation";
import EvaluationColdStart from "@/components/evaluation/EvaluationColdStart";
import ThreePortfolioChart from "@/components/evaluation/ThreePortfolioChart";

const PERIODS = [
  { label: "90D", days: 90 },
  { label: "180D", days: 180 },
  { label: "1Y", days: 365 },
];

function pct(n: number | null | undefined, decimals = 1): string {
  if (n == null) return "—";
  return `${n >= 0 ? "+" : ""}${n.toFixed(decimals)}%`;
}
function pnlTone(n: number | null | undefined): string {
  if (n == null) return "text-gray-400";
  return n >= 0 ? "text-green-700" : "text-red-600";
}

export default function PortfoliosPage() {
  const { activeId } = usePortfolio();
  const portfolioId = activeId ?? 0;

  const [periodDays, setPeriodDays] = useState(90);
  const [data, setData] = useState<ShadowPerformanceSummary | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!portfolioId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await getShadowPerformanceSummary(portfolioId, periodDays);
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load Three Portfolios comparison");
    } finally {
      setLoading(false);
    }
  }, [portfolioId, periodDays]);

  useEffect(() => {
    load();
  }, [load]);

  if (!portfolioId) {
    return <p className="text-sm text-gray-400 py-10 text-center">Select a portfolio to view Portfolios.</p>;
  }

  const tp = data?.three_portfolios;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Portfolios</h1>
          <p className="text-sm text-gray-500 mt-0.5">Ideal → AI Portfolio → You — the two gaps that explain the difference.</p>
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
          {tp && <AsOfStamp asOf={tp.as_of} />}
        </div>
      </div>

      {error && <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg">{error}</div>}

      {loading && !data && (
        <div className="space-y-3">
          <div className="h-72 animate-pulse bg-gray-100 rounded-xl" />
          <div className="h-40 animate-pulse bg-gray-100 rounded-xl" />
        </div>
      )}

      {!loading && tp && tp.status === "insufficient_data" && (
        <EvaluationColdStart
          title="ยังไม่มีข้อมูลเปรียบเทียบพอร์ต"
          message="เมื่อมีคำแนะนำ AI อย่างน้อยหนึ่งครั้งและมีข้อมูลราคาสะสมเพียงพอ การเปรียบเทียบสามพอร์ตจะปรากฏที่นี่"
        />
      )}

      {!loading && tp && tp.status === "ok" && (
        <>
          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wide mb-3">
              Performance (indexed, {periodDays}D)
            </h3>
            <ThreePortfolioChart chart={tp.chart} />
            <div className="grid grid-cols-3 gap-3 mt-4 pt-3 border-t text-sm">
              <div>
                <p className="text-gray-500 text-xs">Ideal</p>
                <p className={`font-semibold tabular-nums ${pnlTone(tp.ideal.return_pct)}`}>{pct(tp.ideal.return_pct)}</p>
              </div>
              <div>
                <p className="text-gray-500 text-xs">AI Portfolio</p>
                <p className={`font-semibold tabular-nums ${pnlTone(tp.ai_portfolio.return_pct)}`}>{pct(tp.ai_portfolio.return_pct)}</p>
              </div>
              <div>
                <p className="text-gray-500 text-xs">You</p>
                <p className={`font-semibold tabular-nums ${pnlTone(tp.actual.return_pct)}`}>{pct(tp.actual.return_pct)}</p>
              </div>
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wide mb-0.5">The Two Gaps</h3>
            <p className="text-xs text-gray-400 mb-3">What explains the difference between the three portfolios.</p>
            <div className="grid sm:grid-cols-2 gap-4">
              <GapAnnotation
                label="Gap A · Ideal − AI"
                value={tp.gap_a.value}
                interpretation={tp.gap_a.interpretation?.en}
                size="lg"
              />
              <GapAnnotation
                label="Gap B · AI − You"
                value={tp.gap_b.value}
                interpretation={tp.gap_b.interpretation?.en}
                size="lg"
              />
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wide mb-3">Risk</h3>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-gray-500 border-b">
                    <th className="py-2 pr-3 font-medium"> </th>
                    <th className="py-2 px-3 font-medium text-right">Ideal</th>
                    <th className="py-2 px-3 font-medium text-right">AI Portfolio</th>
                    <th className="py-2 px-3 font-medium text-right">You</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b">
                    <td className="py-2 pr-3 text-gray-600">Max drawdown</td>
                    <td className="py-2 px-3 text-right tabular-nums text-gray-800">{pct(tp.ideal.max_drawdown_pct != null ? -tp.ideal.max_drawdown_pct : null, 1)}</td>
                    <td className="py-2 px-3 text-right tabular-nums text-gray-800">{pct(tp.ai_portfolio.max_drawdown_pct != null ? -tp.ai_portfolio.max_drawdown_pct : null, 1)}</td>
                    <td className="py-2 px-3 text-right tabular-nums text-gray-800">{pct(tp.actual.max_drawdown_pct != null ? -tp.actual.max_drawdown_pct : null, 1)}</td>
                  </tr>
                  <tr>
                    <td className="py-2 pr-3 text-gray-600">Volatility (ann.)</td>
                    <td className="py-2 px-3 text-right tabular-nums text-gray-800">{tp.ideal.annualized_volatility != null ? `${tp.ideal.annualized_volatility.toFixed(1)}%` : "—"}</td>
                    <td className="py-2 px-3 text-right tabular-nums text-gray-800">{tp.ai_portfolio.annualized_volatility != null ? `${tp.ai_portfolio.annualized_volatility.toFixed(1)}%` : "—"}</td>
                    <td className="py-2 px-3 text-right tabular-nums text-gray-800">{tp.actual.annualized_volatility != null ? `${tp.actual.annualized_volatility.toFixed(1)}%` : "—"}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p className="text-[11px] text-gray-400 mt-3 italic">
              Allocation side-by-side, per-holding contribution, and the underwater drawdown chart are deferred —
              they need per-holding/per-sector attribution beyond this milestone's Ideal-series + Gap A scope.
            </p>
          </div>
        </>
      )}
    </div>
  );
}
