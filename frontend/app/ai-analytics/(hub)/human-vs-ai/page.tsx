"use client";

// AI Evaluation M5 — S5 Human vs AI (`/ai-analytics/human-vs-ai`).
// Renders GET /analytics/evaluation/human-vs-ai (compute_scoreboard, M5)
// verbatim. Tone rule (UX): symmetrical language always — "you beat AI" and
// "AI beat you" render identically; this page never frames itself as the
// machine keeping score against the user.

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { usePortfolio } from "@/lib/PortfolioContext";
import { getHumanVsAiScoreboard, type HumanVsAiScoreboard } from "@/lib/api";
import AsOfStamp from "@/components/evaluation/AsOfStamp";
import SampleSizeChip from "@/components/evaluation/SampleSizeChip";
import GapAnnotation from "@/components/evaluation/GapAnnotation";
import ClassSegmentBars from "@/components/evaluation/ClassSegmentBars";
import EvaluationColdStart from "@/components/evaluation/EvaluationColdStart";

const PERIODS = [
  { label: "90D", days: 90 },
  { label: "180D", days: 180 },
  { label: "1Y", days: 365 },
  { label: "All", days: 3650 },
];

export default function HumanVsAiPage() {
  const { activeId } = usePortfolio();
  const portfolioId = activeId ?? 0;

  const [periodDays, setPeriodDays] = useState(90);
  const [data, setData] = useState<HumanVsAiScoreboard | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!portfolioId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await getHumanVsAiScoreboard(portfolioId, periodDays);
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load Human vs AI scoreboard");
    } finally {
      setLoading(false);
    }
  }, [portfolioId, periodDays]);

  useEffect(() => {
    load();
  }, [load]);

  if (!portfolioId) {
    return <p className="text-sm text-gray-400 py-10 text-center">Select a portfolio to view Human vs AI.</p>;
  }

  const total = data ? data.summary.you_beat_ai + data.summary.ai_beat_you + data.summary.ties : 0;
  const youPct = total > 0 && data ? Math.round((data.summary.you_beat_ai / total) * 100) : 0;
  const aiPct = total > 0 && data ? Math.round((data.summary.ai_beat_you / total) * 100) : 0;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">Human vs AI</h1>
          <p className="text-sm text-gray-500 mt-0.5">Where is each of you strong?</p>
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
          <div className="h-32 animate-pulse bg-gray-100 rounded-xl" />
          <div className="h-40 animate-pulse bg-gray-100 rounded-xl" />
        </div>
      )}

      {!loading && data && data.status === "cold_start" && (
        <EvaluationColdStart
          title="ยังไม่มีการตัดสินใจให้เปรียบเทียบ"
          message="เมื่อคุณตัดสินใจกับคำแนะนำอย่างน้อยหนึ่งครั้งและผลลัพธ์ครบกำหนดประเมิน กระดานคะแนนจะปรากฏที่นี่"
        />
      )}

      {!loading && data && data.status !== "cold_start" && (
        <>
          <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wide">The Scoreboard</h3>
              <SampleSizeChip n={data.summary.n_graded} />
            </div>

            {total > 0 ? (
              <div className="flex items-center gap-3 text-sm">
                <span className="text-gray-600 w-28">You beat AI <strong>{data.summary.you_beat_ai}</strong></span>
                <div className="flex-1 h-2.5 rounded-full bg-gray-100 overflow-hidden flex">
                  <div className="h-full bg-blue-500" style={{ width: `${youPct}%` }} />
                  <div className="h-full bg-gray-300" style={{ width: `${100 - youPct - aiPct}%` }} />
                  <div className="h-full bg-purple-400" style={{ width: `${aiPct}%` }} />
                </div>
                <span className="text-gray-600 w-28 text-right">AI beat you <strong>{data.summary.ai_beat_you}</strong></span>
              </div>
            ) : (
              <p className="text-sm text-gray-400">No graded comparisons yet in this window.</p>
            )}

            <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-gray-500">
              <span>Ties (±{data.tie_band_pct}%): <strong className="text-gray-700">{data.summary.ties}</strong></span>
              {data.summary.maturing > 0 && (
                <span className="text-amber-600">◐ {data.summary.maturing} decision(s) still maturing — scoreboard updates as they grade</span>
              )}
            </div>

            <div className="pt-2 border-t">
              <GapAnnotation
                label="Net effect of your judgment vs full compliance"
                value={data.summary.net_effect_pct}
                interpretation={data.summary.net_effect_pct != null && data.summary.n_graded > 0 ? `(${periodDays}D)` : undefined}
              />
            </div>
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wide mb-3">Where each side wins (by trade class)</h3>
            <ClassSegmentBars
              rows={Object.entries(data.by_trade_class).map(([label, v]) => ({
                label, numerator: v.human_better, denominator: v.total,
              }))}
              emptyMessage="No graded decisions with classified trades yet."
            />
            <p className="text-[11px] text-gray-400 mt-2 italic">
              Bar = share of graded decisions touching that trade class where your own outcome beat full AI compliance.
              Decision-level approximation — a multi-trade recommendation contributes to every class it contains.
            </p>
          </div>

          {Object.keys(data.by_override_type).length > 0 && (
            <div className="bg-white border border-gray-200 rounded-xl p-4">
              <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wide mb-3">Where each side wins (by override type)</h3>
              <ClassSegmentBars
                rows={Object.entries(data.by_override_type).map(([label, v]) => ({
                  label, numerator: v.human_better, denominator: v.total,
                }))}
              />
            </div>
          )}

          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <Link href="/ai-analytics/opportunity-cost" className="text-sm font-medium text-blue-600 hover:underline">
              → Opportunity Cost ledger: every ignored/modified call, priced
            </Link>
          </div>
        </>
      )}
    </div>
  );
}
