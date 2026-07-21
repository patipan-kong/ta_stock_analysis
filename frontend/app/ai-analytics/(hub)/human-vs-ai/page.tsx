"use client";

// AI Evaluation M5 — S5 Human vs AI (`/ai-analytics/human-vs-ai`).
// Renders GET /analytics/evaluation/human-vs-ai (compute_scoreboard, M5)
// verbatim. Tone rule (UX): symmetrical language always — "you beat AI" and
// "AI beat you" render identically; this page never frames itself as the
// machine keeping score against the user.

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePortfolio } from "@/lib/PortfolioContext";
import { getHumanVsAiScoreboard, isUnresolvedPortfolioError, type HumanVsAiScoreboard } from "@/lib/api";
import AsOfStamp from "@/components/evaluation/AsOfStamp";
import SampleSizeChip from "@/components/evaluation/SampleSizeChip";
import GapAnnotation from "@/components/evaluation/GapAnnotation";
import ClassSegmentBars from "@/components/evaluation/ClassSegmentBars";
import EvaluationColdStart from "@/components/evaluation/EvaluationColdStart";
import PortfolioSelectionNotice from "@/components/PortfolioSelectionNotice";

const PERIODS = [
  { label: "90D", days: 90 },
  { label: "180D", days: 180 },
  { label: "1Y", days: 365 },
  { label: "All", days: 3650 },
];

// Presentation-only synthesis of the summary numbers already rendered
// below (n_graded/you_beat_ai/ai_beat_you/net_effect_pct/by_trade_class) —
// no new metric, mirrors the frontend-composed `(${periodDays}D)` suffix
// this page already builds for the Gap annotation.
function composeLeadSentence(data: HumanVsAiScoreboard): string | null {
  const { n_graded, you_beat_ai, ai_beat_you, net_effect_pct } = data.summary;
  if (n_graded === 0) return null;

  const whoPhrase =
    you_beat_ai === ai_beat_you
      ? `You and the AI split the graded decisions evenly (${you_beat_ai}–${ai_beat_you})`
      : you_beat_ai > ai_beat_you
      ? `You came out ahead, winning ${you_beat_ai} of ${n_graded} graded decisions to the AI's ${ai_beat_you}`
      : `The AI came out ahead, winning ${ai_beat_you} of ${n_graded} graded decisions to your ${you_beat_ai}`;

  const byHowMuch =
    net_effect_pct != null
      ? `, a net ${net_effect_pct >= 0 ? "gain" : "cost"} of ${Math.abs(net_effect_pct).toFixed(1)}% versus following the AI on every call`
      : "";

  const classes = Object.entries(data.by_trade_class).filter(([, v]) => v.total > 0);
  const topClass = classes.length > 0 ? classes.reduce((a, b) => (b[1].total > a[1].total ? b : a)) : null;
  const why = topClass ? ` — most concentrated in ${topClass[0].toLowerCase()} decisions` : "";

  return `${whoPhrase}${byHowMuch}${why}.`;
}

export default function HumanVsAiPage() {
  const { currentSelection, reportUnresolvedPortfolio } = usePortfolio();
  const portfolioId = currentSelection;

  const [periodDays, setPeriodDays] = useState(90);
  const [data, setData] = useState<HumanVsAiScoreboard | null>(null);
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
      const result = await getHumanVsAiScoreboard(pid, periodDays);
      if (requestIdRef.current !== pid) return;
      setData(result);
    } catch (e) {
      if (requestIdRef.current !== pid) return;
      setError(e instanceof Error ? e.message : "Failed to load Human vs AI scoreboard");
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
    return <PortfolioSelectionNotice label="Human vs AI" />;
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
          {composeLeadSentence(data) && (
            <div className="bg-white border border-gray-200 rounded-xl p-4">
              <p className="text-sm text-gray-700 leading-relaxed">{composeLeadSentence(data)}</p>
            </div>
          )}

          <div className="bg-white border border-gray-200 rounded-xl p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wide">The Scoreboard</h3>
              <SampleSizeChip n={data.summary.n_graded} />
            </div>

            {total > 0 ? (
              <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3 text-sm">
                <span className="text-gray-600 sm:w-28">You beat AI <strong>{data.summary.you_beat_ai}</strong></span>
                <div className="flex-1 h-2.5 rounded-full bg-gray-100 overflow-hidden flex">
                  <div className="h-full bg-blue-500" style={{ width: `${youPct}%` }} />
                  <div className="h-full bg-gray-300" style={{ width: `${100 - youPct - aiPct}%` }} />
                  <div className="h-full bg-purple-400" style={{ width: `${aiPct}%` }} />
                </div>
                <span className="text-gray-600 sm:w-28 sm:text-right">AI beat you <strong>{data.summary.ai_beat_you}</strong></span>
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
