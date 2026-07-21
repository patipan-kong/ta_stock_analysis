"use client";

// AI Evaluation M5 — S6 Opportunity Cost (`/ai-analytics/opportunity-cost`).
// Reached from within Human vs AI (UX §2.3), not a 7th tab segment. Renders
// GET /analytics/evaluation/opportunity-cost verbatim.
//
// Scope note: the UX wireframe's headline is a generated prose sentence
// ("mostly one ignored BUY. Ignoring two SELL calls helped.") that ranks and
// narrates individual rows — composing that client-side would be frontend
// business logic (picking/ranking causes), which the M5 instructions forbid
// and no backend verdict field exists for it. This page instead renders the
// net number plainly plus the waterfall, whose per-row `note` text is itself
// backend-authored — never a client-synthesized narrative.

import { useCallback, useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import BackBreadcrumb from "@/components/BackBreadcrumb";
import { usePortfolio } from "@/lib/PortfolioContext";
import { getOpportunityCost, isUnresolvedPortfolioError, type OpportunityCostLedger } from "@/lib/api";
import AsOfStamp from "@/components/evaluation/AsOfStamp";
import EffectWaterfall from "@/components/evaluation/EffectWaterfall";
import EvaluationColdStart from "@/components/evaluation/EvaluationColdStart";
import PortfolioSelectionNotice from "@/components/PortfolioSelectionNotice";

const PERIODS = [
  { label: "30D", days: 30 },
  { label: "90D", days: 90 },
  { label: "180D", days: 180 },
  { label: "1Y", days: 365 },
];

const DIVERGENCE_LABEL: Record<string, string> = {
  REJECTED: "Ignored",
  PARTIAL_EXECUTION: "Partial exec",
  MANUAL_OVERRIDE: "Override",
  EXPIRED: "Expired (ignored)",
};

export default function OpportunityCostPage() {
  const { currentSelection, reportUnresolvedPortfolio } = usePortfolio();
  const portfolioId = currentSelection;
  const router = useRouter();

  const [periodDays, setPeriodDays] = useState(90);
  const [data, setData] = useState<OpportunityCostLedger | null>(null);
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
      const result = await getOpportunityCost(pid, periodDays);
      if (requestIdRef.current !== pid) return;
      setData(result);
    } catch (e) {
      if (requestIdRef.current !== pid) return;
      setError(e instanceof Error ? e.message : "Failed to load Opportunity Cost ledger");
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
    return <PortfolioSelectionNotice label="Opportunity Cost" />;
  }

  return (
    <div className="space-y-5">
      <BackBreadcrumb parent="Human vs AI" current="Opportunity Cost" href="/ai-analytics/human-vs-ai" />

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Opportunity Cost</h1>
          <p className="text-sm text-gray-500 mt-0.5">What every divergence from the AI's recommendation did — priced, symmetric.</p>
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
          <div className="h-20 animate-pulse bg-gray-100 rounded-xl" />
          <div className="h-56 animate-pulse bg-gray-100 rounded-xl" />
        </div>
      )}

      {!loading && data && data.status === "cold_start" && (
        <EvaluationColdStart
          title="ยังไม่มีข้อมูลต้นทุนค่าเสียโอกาส"
          message="เมื่อมีการปฏิเสธ ทำบางส่วน หรือปรับเปลี่ยนคำแนะนำ AI และผลลัพธ์ครบกำหนดประเมิน ต้นทุนค่าเสียโอกาสจะปรากฏที่นี่"
        />
      )}

      {!loading && data && data.status !== "cold_start" && (
        <>
          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <p className="text-sm text-gray-500">Net opportunity cost ({periodDays}D)</p>
            {data.net_opportunity_cost_pct == null ? (
              <p className="text-lg font-bold text-gray-400 italic mt-0.5">insufficient graded evidence yet</p>
            ) : (
              <p
                className={`text-2xl font-bold tabular-nums italic mt-0.5 ${
                  data.net_opportunity_cost_pct >= 0 ? "text-green-700" : "text-red-600"
                }`}
                title="Counterfactual — not realized money."
              >
                {data.net_opportunity_cost_pct >= 0 ? "+" : ""}
                {data.net_opportunity_cost_pct.toFixed(2)}%*
              </p>
            )}
            {data.maturing_count > 0 && (
              <p className="text-xs text-amber-600 mt-1">◐ {data.maturing_count} divergence(s) still maturing</p>
            )}
          </div>

          {data.rows.length === 0 ? (
            <div className="bg-white border border-gray-200 rounded-xl p-6 text-center">
              <p className="text-sm text-gray-600 font-medium">คุณทำตามคำแนะนำทั้งหมด</p>
              <p className="text-xs text-gray-400 mt-1">ยังไม่มีต้นทุนค่าเสียโอกาสให้วัด</p>
            </div>
          ) : (
            <div className="bg-white border border-gray-200 rounded-xl p-4">
              <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wide mb-3">Waterfall</h3>
              <EffectWaterfall
                net={data.net_opportunity_cost_pct}
                rows={data.rows
                  .filter((r) => r.status === "graded" && r.counterfactual_delta_pct != null)
                  .map((r) => ({
                    key: r.decision_id,
                    label: `${DIVERGENCE_LABEL[r.divergence_type] ?? r.divergence_type} · Rec #${r.snapshot_id}`,
                    value: r.counterfactual_delta_pct as number,
                    note: r.note,
                    onClick: () => router.push(`/ai-analytics/recommendations/${r.snapshot_id}`),
                  }))}
              />
              {data.rows.some((r) => r.status === "maturing") && (
                <div className="mt-3 pt-3 border-t space-y-1">
                  {data.rows.filter((r) => r.status === "maturing").map((r) => (
                    <p key={r.decision_id} className="text-xs text-gray-400">
                      ◐ {DIVERGENCE_LABEL[r.divergence_type] ?? r.divergence_type} · Rec #{r.snapshot_id} — {r.note}
                    </p>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wide mb-1">The System's Own Deferrals</h3>
            <p className="text-[11px] text-gray-400 mb-3">
              The honesty ledger for the deferral doctrine (OPTIMIZER_PHILOSOPHY.md §7/§9) — the Opportunity Cost metric pointed at the machine.
            </p>
            {data.system_deferrals.length === 0 ? (
              <p className="text-sm text-gray-400">No deferred trades in this window.</p>
            ) : (
              <ul className="divide-y divide-gray-50">
                {data.system_deferrals.map((d, i) => (
                  <li key={i} className="py-2 text-sm">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs text-gray-400">{d.date?.slice(0, 10) ?? "—"}</span>
                      <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-amber-50 text-amber-700 border border-amber-300">
                        {d.action}
                      </span>
                      <span className="font-semibold text-gray-800">{d.symbol.replace(".BK", "")}</span>
                      <span className="text-xs text-gray-400">{d.reason.replace(/_/g, " ").toLowerCase()}</span>
                    </div>
                    <p className="text-xs text-gray-400 italic mt-0.5">pricing unavailable — {d.counterfactual_reason}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      )}
    </div>
  );
}
