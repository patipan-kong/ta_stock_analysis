"use client";

import { useEffect, useMemo, useState } from "react";
import { usePortfolio } from "@/lib/PortfolioContext";
import {
  getAIvsHumanTimeline,
  getAttributionSummary,
  getConfidenceCalibrationV2,
  getCalibrationHistory,
  getRegimeAttribution,
  getDecisionMemoryTimeline,
  type AIvsHumanTimeline,
  type AttributionSummaryResponse,
  type EnhancedCalibrationDetail,
  type CalibrationHistoryEntry,
  type RegimeAttributionResponse,
  type DecisionMemoryEntry,
} from "@/lib/api";
import DecisionMemoryTimeline from "@/components/DecisionMemoryTimeline";
import ShadowPortfolioPanel from "@/components/ShadowPortfolioPanel";

function fmtPct(v: number | null | undefined): string {
  if (v == null) return "-";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(2)}%`;
}

function pctClass(v: number | null | undefined, invert = false): string {
  if (v == null) return "text-gray-500";
  const positive = invert ? v < 0 : v > 0;
  if (positive) return "text-green-700";
  if (v === 0) return "text-gray-500";
  return "text-red-600";
}

function verdictLabel(delta: number | null | undefined): "AI Winning" | "Human Winning" | "Neutral" {
  if (delta == null) return "Neutral";
  if (delta > 0.25) return "AI Winning";
  if (delta < -0.25) return "Human Winning";
  return "Neutral";
}

function verdictClass(verdict: "AI Winning" | "Human Winning" | "Neutral"): string {
  if (verdict === "AI Winning") return "bg-amber-50 text-amber-800 border-amber-200";
  if (verdict === "Human Winning") return "bg-green-50 text-green-800 border-green-200";
  return "bg-gray-50 text-gray-700 border-gray-200";
}

function EmptyPanel({ title, body }: { title: string; body: string }) {
  return (
    <section className="bg-white border border-gray-200 rounded-xl p-5">
      <h2 className="text-sm font-semibold text-gray-800">{title}</h2>
      <p className="text-xs text-gray-400 mt-2">{body}</p>
    </section>
  );
}

function HumanVsAIComparisonCard({
  attribution,
}: {
  attribution: AttributionSummaryResponse | null;
}) {
  const cur = attribution?.current;
  const humanReturn = cur?.actual.return_pct ?? null;
  const aiReturn = cur?.ai_model_shadow?.return_pct ?? null;
  const deltaAlpha = aiReturn != null && humanReturn != null ? aiReturn - humanReturn : null;
  const regret = cur?.regret_score ?? null;
  const avoidedDrawdown = cur?.avoided_drawdown_pct ?? null;
  const verdict = verdictLabel(deltaAlpha);

  return (
    <section className="bg-white border border-gray-200 rounded-xl p-5">
      <h2 className="text-sm font-semibold text-gray-800">Human vs AI Comparison</h2>
      <p className="text-xs text-gray-400 mt-0.5">Execution quality against model-perfect baseline</p>

      {!cur ? (
        <p className="text-xs text-gray-400 mt-3">Not enough data yet. Approve decisions to build comparison history.</p>
      ) : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mt-4">
            <div>
              <p className="text-xs text-gray-500">Human Return</p>
              <p className={`text-sm font-semibold ${pctClass(humanReturn)}`}>{fmtPct(humanReturn)}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">AI Model Return</p>
              <p className={`text-sm font-semibold ${pctClass(aiReturn)}`}>{fmtPct(aiReturn)}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Delta Alpha</p>
              <p className={`text-sm font-semibold ${pctClass(deltaAlpha)}`}>{fmtPct(deltaAlpha)}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Regret Score</p>
              <p className={`text-sm font-semibold ${pctClass(regret)}`}>{fmtPct(regret)}</p>
            </div>
            <div>
              <p className="text-xs text-gray-500">Avoided Drawdown</p>
              <p className={`text-sm font-semibold ${pctClass(avoidedDrawdown)}`}>{fmtPct(avoidedDrawdown)}</p>
            </div>
          </div>

          <div className="mt-4">
            <span className={`inline-flex px-2.5 py-1 rounded-full border text-xs font-medium ${verdictClass(verdict)}`}>
              {verdict}
            </span>
          </div>
        </>
      )}
    </section>
  );
}

function RegretAnalysisCard({
  timeline,
  decisions,
}: {
  timeline: AIvsHumanTimeline | null;
  decisions: DecisionMemoryEntry[];
}) {
  const metrics = useMemo(() => {
    const points = timeline?.timeline ?? [];
    let missedUpside = 0;
    let avoidedLosses = 0;
    for (const p of points) {
      if (p.return_delta == null) continue;
      if (p.return_delta > 0) missedUpside += p.return_delta;
      if (p.return_delta < 0) avoidedLosses += Math.abs(p.return_delta);
    }

    const rejectedCount = decisions.filter((d) => d.decision === "REJECTED").length;
    const successfulOverrides = points.filter((p) => {
      if (p.ai_better !== false) return false;
      const decision = decisions.find((d) => d.decision_id === p.decision_id);
      return decision?.decision === "MANUAL_OVERRIDE" || decision?.decision === "PARTIAL_EXECUTION";
    }).length;

    return {
      missedUpside,
      avoidedLosses,
      rejectedCount,
      successfulOverrides,
    };
  }, [timeline, decisions]);

  return (
    <section className="bg-white border border-gray-200 rounded-xl p-5">
      <h2 className="text-sm font-semibold text-gray-800">Regret Analysis</h2>
      <p className="text-xs text-gray-400 mt-0.5">Where discretionary decisions helped or hurt</p>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
        <div>
          <p className="text-xs text-gray-500">Missed Upside</p>
          <p className="text-sm font-semibold text-red-600">{fmtPct(metrics.missedUpside)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Avoided Losses</p>
          <p className="text-sm font-semibold text-green-700">{fmtPct(metrics.avoidedLosses)}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Rejected Recommendations</p>
          <p className="text-sm font-semibold text-gray-800">{metrics.rejectedCount}</p>
        </div>
        <div>
          <p className="text-xs text-gray-500">Successful Overrides</p>
          <p className="text-sm font-semibold text-gray-800">{metrics.successfulOverrides}</p>
        </div>
      </div>
    </section>
  );
}

function ConfidenceCalibrationCard({
  calibration,
  history,
}: {
  calibration: EnhancedCalibrationDetail | null;
  history: CalibrationHistoryEntry[];
}) {
  const buckets = calibration?.signal_accuracy?.buckets ?? {};
  const trend = [...history]
    .reverse()
    .map((h) => h.calibration_score)
    .filter((v): v is number => v != null)
    .slice(-20);

  return (
    <section className="bg-white border border-gray-200 rounded-xl p-5">
      <h2 className="text-sm font-semibold text-gray-800">Confidence Calibration</h2>
      <p className="text-xs text-gray-400 mt-0.5">HIGH, MEDIUM, LOW confidence accuracy with rolling trend</p>

      {!calibration ? (
        <p className="text-xs text-gray-400 mt-3">Calibration history is still building.</p>
      ) : (
        <>
          <div className="space-y-2 mt-4">
            {Object.entries(buckets).map(([key, bucket]) => (
              <div key={key} className="flex items-center gap-2 text-xs">
                <span className="w-16 text-gray-600 font-medium">{key}</span>
                <div className="flex-1 h-2 rounded-full bg-gray-100 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      (bucket.accuracy_pct ?? 0) >= 60
                        ? "bg-green-500"
                        : (bucket.accuracy_pct ?? 0) >= 50
                        ? "bg-blue-500"
                        : "bg-amber-500"
                    }`}
                    style={{ width: `${Math.max(0, Math.min(100, bucket.accuracy_pct ?? 0))}%` }}
                  />
                </div>
                <span className="w-14 text-right text-gray-700">{fmtPct(bucket.accuracy_pct)}</span>
              </div>
            ))}
          </div>

          <div className="mt-4 border-t pt-3">
            <p className="text-xs text-gray-500 mb-1.5">Rolling Calibration Trend</p>
            {trend.length === 0 ? (
              <p className="text-xs text-gray-400">No trend points yet.</p>
            ) : (
              <div className="flex items-end gap-1 h-14">
                {trend.map((v, idx) => (
                  <div
                    key={`${idx}-${v}`}
                    className="flex-1 bg-blue-500/70 rounded-sm"
                    style={{ height: `${Math.max(6, Math.min(100, v))}%` }}
                    title={`Score ${v.toFixed(1)}`}
                  />
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </section>
  );
}

function RegimePerformanceCard({ regime }: { regime: RegimeAttributionResponse | null }) {
  const entries = regime ? Object.values(regime.regimes ?? {}) : [];

  return (
    <section className="bg-white border border-gray-200 rounded-xl p-5">
      <h2 className="text-sm font-semibold text-gray-800">Regime Performance</h2>
      <p className="text-xs text-gray-400 mt-0.5">How performance changed across market states</p>

      {entries.length === 0 ? (
        <p className="text-xs text-gray-400 mt-3">No regime overlap data yet.</p>
      ) : (
        <div className="mt-3 space-y-2">
          {entries
            .sort((a, b) => b.avg_daily_return_pct - a.avg_daily_return_pct)
            .map((r) => (
              <div key={r.regime} className="flex items-center justify-between text-xs">
                <span className="text-gray-700">{r.label}</span>
                <div className="flex items-center gap-3">
                  <span className="text-gray-400">{r.trading_days}d</span>
                  <span className={`font-semibold ${pctClass(r.avg_daily_return_pct)}`}>
                    {fmtPct(r.avg_daily_return_pct)}/day
                  </span>
                </div>
              </div>
            ))}
        </div>
      )}
    </section>
  );
}

export default function PortfolioIntelligencePage() {
  const { portfolios, activeId } = usePortfolio();
  const [timeline, setTimeline] = useState<AIvsHumanTimeline | null>(null);
  const [attribution, setAttribution] = useState<AttributionSummaryResponse | null>(null);
  const [calibration, setCalibration] = useState<EnhancedCalibrationDetail | null>(null);
  const [calibrationHistory, setCalibrationHistory] = useState<CalibrationHistoryEntry[]>([]);
  const [regime, setRegime] = useState<RegimeAttributionResponse | null>(null);
  const [decisions, setDecisions] = useState<DecisionMemoryEntry[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!activeId) return;

    let active = true;
    setLoading(true);
    Promise.all([
      getAIvsHumanTimeline(activeId, 180, 50),
      getAttributionSummary(activeId, 30),
      getConfidenceCalibrationV2(activeId, 30, false),
      getCalibrationHistory(activeId, 30),
      getRegimeAttribution(activeId, 120),
      getDecisionMemoryTimeline(activeId, 50),
    ])
      .then(([ai, attr, cal, calHist, reg, dec]) => {
        if (!active) return;
        setTimeline(ai);
        setAttribution(attr);
        setCalibration(cal.calibration);
        setCalibrationHistory(calHist);
        setRegime(reg);
        setDecisions(dec);
      })
      .catch(() => {
        if (!active) return;
        setTimeline(null);
        setAttribution(null);
        setCalibration(null);
        setCalibrationHistory([]);
        setRegime(null);
        setDecisions([]);
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });

    const onDecision = () => {
      Promise.all([
        getAIvsHumanTimeline(activeId, 180, 50),
        getAttributionSummary(activeId, 30),
        getDecisionMemoryTimeline(activeId, 50),
      ])
        .then(([ai, attr, dec]) => {
          setTimeline(ai);
          setAttribution(attr);
          setDecisions(dec);
        })
        .catch(() => {
          setTimeline(null);
          setAttribution(null);
          setDecisions([]);
        });
    };

    window.addEventListener("execution-decision-recorded", onDecision);
    return () => {
      active = false;
      window.removeEventListener("execution-decision-recorded", onDecision);
    };
  }, [activeId]);

  if (!activeId) {
    return (
      <div className="space-y-5">
        <h1 className="text-xl font-semibold text-gray-900">Portfolio Intelligence</h1>
        <EmptyPanel
          title="No Portfolio Selected"
          body="Select a portfolio from the navigation bar to view execution intelligence."
        />
      </div>
    );
  }

  const portfolioName = portfolios.find((p) => p.id === activeId)?.name ?? "Portfolio";

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">Portfolio Intelligence</h1>
        <p className="text-xs text-gray-500 mt-0.5">
          Decision Memory System for {portfolioName}.
          {loading ? " Refreshing intelligence..." : ""}
        </p>
      </div>

      <DecisionMemoryTimeline portfolioId={activeId} limit={20} />
      <ShadowPortfolioPanel portfolioId={activeId} />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <HumanVsAIComparisonCard attribution={attribution} />
        <RegretAnalysisCard timeline={timeline} decisions={decisions} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <ConfidenceCalibrationCard calibration={calibration} history={calibrationHistory} />
        <RegimePerformanceCard regime={regime} />
      </div>
    </div>
  );
}
