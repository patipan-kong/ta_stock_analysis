"use client";

// AI Evaluation M6 — S8 Attribution (`/ai-analytics/attribution`).
// Renders GET /analytics/attribution-summary's `waterfall` field verbatim
// (services/analytics/attribution_engine.compute_attribution_waterfall) plus
// the existing regime-attribution endpoint for the By Regime tab.
//
// Scope note: the leading sentence is a deterministic template
// (verdict_composer.compose_attribution_verdict) naming the single dominant
// effect, not the UX mock's multi-clause narrative — ranking/narrating
// several causes in prose crosses from templating into generation, which
// the M6 instructions forbid ("no AI-generated narratives"). By Sector
// shows the BHB stub's honest unavailable note (no per-sector benchmark
// data yet) rather than fabricated numbers; By Holding is similarly honest
// about not having per-holding attribution in this milestone's scope.

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { usePortfolio } from "@/lib/PortfolioContext";
import {
  getAttributionSummary,
  getRegimeAttribution,
  isUnresolvedPortfolioError,
  type AttributionSummaryResponse,
  type RegimeAttributionResponse,
} from "@/lib/api";
import AsOfStamp from "@/components/evaluation/AsOfStamp";
import EffectWaterfall, { type WaterfallRow } from "@/components/evaluation/EffectWaterfall";
import EvaluationColdStart from "@/components/evaluation/EvaluationColdStart";
import PortfolioSelectionNotice from "@/components/PortfolioSelectionNotice";

const PERIODS = [
  { label: "30D", days: 30 },
  { label: "90D", days: 90 },
  { label: "180D", days: 180 },
];

type Tab = "sector" | "regime" | "holding";

export default function AttributionPage() {
  const { currentSelection, reportUnresolvedPortfolio } = usePortfolio();
  const portfolioId = currentSelection;
  const router = useRouter();

  const [periodDays, setPeriodDays] = useState(90);
  const [data, setData] = useState<AttributionSummaryResponse | null>(null);
  const [regime, setRegime] = useState<RegimeAttributionResponse | null>(null);
  const [tab, setTab] = useState<Tab>("sector");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // M36.1 WP4A F04 — captures the Portfolio Identity a request was issued
  // for; a response arriving after Current Selection has moved to a
  // different portfolio (or cleared to NONE) is discarded.
  const requestIdRef = useRef<number | null>(null);

  const load = useCallback(async () => {
    if (portfolioId == null) return;
    const pid = portfolioId;
    setLoading(true);
    setError(null);
    try {
      const [summary, regimeResult] = await Promise.all([
        getAttributionSummary(pid, periodDays),
        getRegimeAttribution(pid, periodDays),
      ]);
      if (requestIdRef.current !== pid) return;
      setData(summary);
      setRegime(regimeResult);
    } catch (e) {
      if (requestIdRef.current !== pid) return;
      setError(e instanceof Error ? e.message : "Failed to load Attribution");
      if (isUnresolvedPortfolioError(e)) reportUnresolvedPortfolio(pid);
    } finally {
      if (requestIdRef.current === pid) setLoading(false);
    }
  }, [portfolioId, periodDays, reportUnresolvedPortfolio]);

  useEffect(() => {
    requestIdRef.current = portfolioId;
    if (portfolioId == null) {
      setData(null);
      setRegime(null);
      setError(null);
      setLoading(false);
      return;
    }
    load();
  }, [portfolioId, load]);

  if (portfolioId == null) {
    return <PortfolioSelectionNotice label="Attribution" />;
  }

  const wf = data?.waterfall;

  const rows: WaterfallRow[] = (wf?.effects ?? [])
    .filter((e) => e.value != null)
    .map((e): WaterfallRow => ({ key: e.key, label: e.label, value: e.value as number, note: e.note }));
  if (wf?.residual_pct != null) {
    rows.push({ key: "residual", label: "Residual (unexplained)", value: wf.residual_pct, note: wf.residual_note ?? undefined });
  }
  const netTotal =
    wf && wf.actual_return_pct != null && wf.benchmark_return_pct != null
      ? Math.round((wf.actual_return_pct - wf.benchmark_return_pct) * 100) / 100
      : null;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Attribution</h1>
          <p className="text-sm text-gray-500 mt-0.5">Why your return happened.</p>
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
          {wf && <AsOfStamp asOf={wf.as_of} />}
        </div>
      </div>

      {error && <div className="p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg">{error}</div>}

      {loading && !data && (
        <div className="space-y-3">
          <div className="h-16 animate-pulse bg-gray-100 rounded-xl" />
          <div className="h-56 animate-pulse bg-gray-100 rounded-xl" />
        </div>
      )}

      {!loading && wf && wf.status === "insufficient_data" && (
        <EvaluationColdStart
          title="ยังไม่มีข้อมูลเพียงพอสำหรับวิเคราะห์ที่มาผลตอบแทน"
          message="เมื่อมีข้อมูลผลตอบแทนจริงและพอร์ต AI เปรียบเทียบเพียงพอ การวิเคราะห์นี้จะปรากฏที่นี่"
        />
      )}

      {!loading && wf && wf.status === "ok" && (
        <>
          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <p className="text-sm text-gray-700 leading-relaxed">{wf.verdict?.en}</p>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wide mb-1">
              Waterfall — Benchmark ({wf.benchmark_return_pct?.toFixed(1)}%) → You ({wf.actual_return_pct?.toFixed(1)}%)
            </h3>
            <p className="text-[11px] text-gray-400 mb-3">Realized effects — already reflected in your actual return, not hypothetical.</p>
            <EffectWaterfall rows={rows} net={netTotal} netLabel="Total (You − Benchmark)" variant="realized" />
          </div>

          <div className="bg-white border border-gray-200 rounded-xl">
            <div className="flex items-center gap-1 p-2 border-b">
              {([
                ["sector", "By Sector"],
                ["regime", "By Regime"],
                ["holding", "By Holding"],
              ] as [Tab, string][]).map(([key, label]) => (
                <button
                  key={key}
                  onClick={() => setTab(key)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                    tab === key ? "bg-blue-50 text-blue-700" : "text-gray-500 hover:text-gray-800"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
            <div className="p-4">
              {tab === "sector" && (
                <p className="text-sm text-gray-400 italic">
                  {data?.waterfall.effects.find((e) => e.key === "selection_allocation")?.note ??
                    "Per-sector BHB decomposition requires per-sector benchmark data — not yet available."}
                </p>
              )}
              {tab === "regime" && (
                <div className="overflow-x-auto">
                  {!regime || regime.status !== "ok" || Object.keys(regime.regimes).length === 0 ? (
                    <p className="text-sm text-gray-400 italic">No regime overlap data for this window yet.</p>
                  ) : (
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-xs text-gray-500 border-b">
                          <th className="py-2 pr-3 font-medium">Regime</th>
                          <th className="py-2 px-3 font-medium text-right">Trading days</th>
                          <th className="py-2 px-3 font-medium text-right">Avg daily</th>
                          <th className="py-2 px-3 font-medium text-right">Total return</th>
                        </tr>
                      </thead>
                      <tbody>
                        {Object.values(regime.regimes).map((r) => (
                          <tr key={r.regime} className="border-b last:border-0">
                            <td className="py-2 pr-3 font-medium text-gray-700">{r.label}</td>
                            <td className="py-2 px-3 text-right tabular-nums text-gray-600">{r.trading_days}</td>
                            <td className="py-2 px-3 text-right tabular-nums text-gray-600">{r.avg_daily_return_pct.toFixed(2)}%</td>
                            <td className={`py-2 px-3 text-right tabular-nums font-semibold ${r.total_return_pct >= 0 ? "text-green-700" : "text-red-600"}`}>
                              {r.total_return_pct >= 0 ? "+" : ""}{r.total_return_pct.toFixed(2)}%
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              )}
              {tab === "holding" && (
                <p className="text-sm text-gray-400 italic">
                  Per-holding contribution requires per-symbol counterfactual tracking not yet built — see the
                  Portfolios screen for the aggregate Ideal / AI / You comparison instead.
                </p>
              )}
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-3">
            <button onClick={() => router.push("/ai-analytics/portfolios")} className="text-xs font-medium text-blue-600 hover:underline">
              → See the full Three Portfolios comparison
            </button>
          </div>
        </>
      )}
    </div>
  );
}
