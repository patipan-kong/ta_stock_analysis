"use client";

// AI Evaluation M4 — S1 AI Scorecard (`/ai-analytics`).
// Renders backend/services/evaluation/scorecard.py::compute_scorecard() verbatim.
// This page performs zero metric computation — every number, grade, and
// sentence comes from GET /analytics/evaluation/scorecard.

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { usePortfolio } from "@/lib/PortfolioContext";
import { getEvaluationScorecard, type EvaluationScorecard } from "@/lib/api";
import VerdictSentence from "@/components/evaluation/VerdictSentence";
import LensGradeChip from "@/components/evaluation/LensGradeChip";
import SampleSizeChip from "@/components/evaluation/SampleSizeChip";
import AsOfStamp from "@/components/evaluation/AsOfStamp";
import GapAnnotation from "@/components/evaluation/GapAnnotation";
import EvaluationColdStart from "@/components/evaluation/EvaluationColdStart";

const PERIODS = [
  { label: "7D", days: 7 },
  { label: "30D", days: 30 },
  { label: "90D", days: 90 },
  { label: "180D", days: 180 },
  { label: "1Y", days: 365 },
  { label: "All", days: 3650 },
];

function pct(n: number | null | undefined, decimals = 1): string {
  if (n == null) return "—";
  return `${n >= 0 ? "+" : ""}${n.toFixed(decimals)}%`;
}
function pnlTone(n: number | null | undefined): string {
  if (n == null) return "text-gray-400";
  return n >= 0 ? "text-green-700" : "text-red-600";
}

function LensCardShell({ title, question, right, children }: { title: string; question: string; right?: React.ReactNode; children: React.ReactNode }) {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 flex flex-col gap-2.5">
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wide">{title}</h3>
          <p className="text-xs text-gray-400 mt-0.5">{question}</p>
        </div>
        {right}
      </div>
      {children}
    </div>
  );
}

function Stat({ label, value, valueClass, sub }: { label: string; value: string; valueClass?: string; sub?: string }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-gray-500">{label}</span>
      <span className={`font-semibold tabular-nums ${valueClass ?? "text-gray-800"}`}>
        {value}
        {sub && <span className="block text-xs font-normal text-gray-400 text-right">{sub}</span>}
      </span>
    </div>
  );
}

export default function ScorecardPage() {
  const { activeId } = usePortfolio();
  const portfolioId = activeId ?? 0;

  const [periodDays, setPeriodDays] = useState(90);
  const [data, setData] = useState<EvaluationScorecard | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    if (!portfolioId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await getEvaluationScorecard(portfolioId, periodDays);
      setData(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load scorecard");
    } finally {
      setLoading(false);
    }
  }, [portfolioId, periodDays]);

  useEffect(() => {
    load();
  }, [load]);

  if (!portfolioId) {
    return <p className="text-sm text-gray-400 py-10 text-center">Select a portfolio to view its AI Scorecard.</p>;
  }

  return (
    <div className="space-y-5">
      {/* Row 0 — context bar */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900">AI Scorecard</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            Belief, Execution, and Outcome quality — graded independently, never one number.
          </p>
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
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-40 animate-pulse bg-gray-100 rounded-xl" />
          ))}
        </div>
      )}

      {!loading && data && data.status === "cold_start" && (
        <EvaluationColdStart
          title="ยังไม่มีคำแนะนำให้ประเมิน"
          message="จะเริ่มประเมินได้หลังจากรันคำแนะนำครั้งแรกจากหน้า Optimizer — Belief, Execution และ Outcome จะปรากฏที่นี่ตามลำดับที่ข้อมูลพร้อม"
        />
      )}

      {!loading && data && data.status !== "cold_start" && (
        <>
          {/* Row 1 — verdict strip */}
          <div className="bg-white border border-gray-200 rounded-xl p-4 flex flex-col md:flex-row md:items-center gap-3 md:gap-6">
            <VerdictSentence verdict={data.verdict} className="flex-1" />
            <div className="flex items-center gap-2 flex-wrap">
              <LensGradeChip grade={data.belief.grade} label="Belief" />
              <LensGradeChip grade={data.execution.grade} label="Execution" />
              <span
                className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 border border-gray-200 whitespace-nowrap"
                title="Outcome quality is read through Belief and Execution, never alone (OPTIMIZER_PHILOSOPHY.md §12)."
              >
                Outcome {data.outcome.status === "ok" ? "✓" : data.outcome.status === "insufficient_evidence" ? "หลักฐานยังไม่พอ" : "◐ กำลังรอเกรด"}
              </span>
            </div>
          </div>

          {/* Row 2 — three lenses */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <LensCardShell title="Belief Quality" question="Were the ideas good?" right={<SampleSizeChip n={data.belief.n_graded} />}>
              <Stat label="Rec accuracy" value={pct(data.belief.hit_rate_pct)} valueClass={pnlTone(data.belief.hit_rate_pct != null ? data.belief.hit_rate_pct - 50 : null)} />
              <Stat label="Avg alpha" value={pct(data.belief.avg_alpha_pct)} valueClass={pnlTone(data.belief.avg_alpha_pct)} />
              <Stat
                label="Calibration"
                value={data.belief.calibration.status === "ok" ? `${data.belief.calibration.calibration_score?.toFixed(0)}` : "unavailable"}
                sub={data.belief.calibration.status === "ok" && data.belief.calibration.consensus_strength_calibration != null ? `consensus calib. ${data.belief.calibration.consensus_strength_calibration.toFixed(0)}` : undefined}
              />
            </LensCardShell>

            <LensCardShell title="Execution Quality" question="Were the plans good?" right={<SampleSizeChip n={data.execution.n_plans} label={`n=${data.execution.n_plans} plans`} />}>
              <Stat label="Plan quality" value={data.execution.avg_plan_score != null ? `${data.execution.avg_plan_score.toFixed(0)}/100` : "—"} />
              <Stat label="Funding eff." value={data.execution.avg_funding_efficiency_pct != null ? `${data.execution.avg_funding_efficiency_pct.toFixed(0)}%` : "—"} />
              <Stat label="Necessity" value={data.execution.avg_necessity_pct != null ? `${data.execution.avg_necessity_pct.toFixed(0)}%` : "—"} />
              <div className="pt-1 border-t">
                <GapAnnotation
                  label="Implementation shortfall"
                  value={data.execution.implementation_shortfall.status === "ok" ? data.execution.implementation_shortfall.value_pct : null}
                  unavailableReason={data.execution.implementation_shortfall.status === "unavailable" ? data.execution.implementation_shortfall.reason : undefined}
                />
              </div>
            </LensCardShell>

            <LensCardShell title="Outcome Quality" question="Did it work?">
              <Stat label="You" value={pct(data.outcome.actual_return_pct)} valueClass={pnlTone(data.outcome.actual_return_pct)} />
              <Stat label="AI Portfolio" value={pct(data.outcome.ai_model_return_pct)} valueClass={pnlTone(data.outcome.ai_model_return_pct)} />
              <Stat
                label="Ideal"
                value={data.outcome.ideal_return_pct.status === "ok" ? pct(data.outcome.ideal_return_pct.value_pct) : "unavailable"}
                valueClass={data.outcome.ideal_return_pct.status === "ok" ? pnlTone(data.outcome.ideal_return_pct.value_pct) : undefined}
                sub={data.outcome.ideal_return_pct.status === "unavailable" ? data.outcome.ideal_return_pct.reason : undefined}
              />
              <Stat label="Benchmark" value={pct(data.outcome.benchmark_return_pct)} valueClass={pnlTone(data.outcome.benchmark_return_pct)} />
              <div className="pt-1 border-t">
                {data.outcome.win_rate.status === "ok" ? (
                  <Stat
                    label="Win rate"
                    value={pct(data.outcome.win_rate.hit_rate_pct, 0)}
                    sub={`${data.outcome.win_rate.ai_wins ?? 0} AI · ${data.outcome.win_rate.human_wins ?? 0} you`}
                  />
                ) : (
                  <Stat label="Win rate" value="หลักฐานยังไม่พอ" sub={`n=${data.outcome.win_rate.n}`} />
                )}
              </div>
            </LensCardShell>
          </div>

          {/* Row 3 — the three portfolios summary (point returns only; the
              full indexed hero chart + allocation/risk breakdowns live on
              the S7 Portfolios screen, "full view" link below). */}
          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wide">The Three Portfolios ({periodDays}D)</h3>
              <Link href="/ai-analytics/portfolios" className="text-xs text-blue-600 hover:underline">
                full view →
              </Link>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-3">
              <Stat
                label="Ideal"
                value={data.outcome.ideal_return_pct.status === "ok" ? pct(data.outcome.ideal_return_pct.value_pct) : "unavailable"}
                valueClass={data.outcome.ideal_return_pct.status === "ok" ? pnlTone(data.outcome.ideal_return_pct.value_pct) : undefined}
              />
              <Stat label="AI Portfolio" value={pct(data.outcome.ai_model_return_pct)} valueClass={pnlTone(data.outcome.ai_model_return_pct)} />
              <Stat label="You" value={pct(data.outcome.actual_return_pct)} valueClass={pnlTone(data.outcome.actual_return_pct)} />
              <Stat label="Benchmark" value={pct(data.outcome.benchmark_return_pct)} valueClass={pnlTone(data.outcome.benchmark_return_pct)} />
            </div>
            <GapAnnotation
              label="Gap A (Ideal − AI, implementation shortfall)"
              value={data.execution.implementation_shortfall.status === "ok" ? data.execution.implementation_shortfall.value_pct : null}
              unavailableReason={data.execution.implementation_shortfall.status === "unavailable" ? data.execution.implementation_shortfall.reason : undefined}
            />
            <p className="text-xs text-gray-400 mt-1">
              For how your own decisions compared to full AI compliance (Gap B), see{" "}
              <Link href="/ai-analytics/human-vs-ai" className="text-blue-600 hover:underline">
                Human vs AI
              </Link>
              .
            </p>
          </div>

          {/* Row 5 — evidence feed */}
          <div className="bg-white border border-gray-200 rounded-xl p-4">
            <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wide mb-3">Recent Grades</h3>
            {data.recent_grades.length === 0 ? (
              <p className="text-sm text-gray-400">No grades issued yet.</p>
            ) : (
              <ul className="divide-y divide-gray-50">
                {data.recent_grades.map((g, i) => (
                  <li key={i} className="py-2 flex items-center justify-between gap-3 text-sm">
                    <div className="min-w-0">
                      <span className="text-gray-400 text-xs mr-2">{g.graded_at?.slice(0, 10) ?? "—"}</span>
                      <span className="font-medium text-gray-700">Rec #{g.recommendation_snapshot_id}</span>
                      <span className="text-gray-400 ml-1.5">{g.grade_kind}</span>
                      {g.return_pct != null && (
                        <span className={`ml-2 font-semibold tabular-nums ${pnlTone(g.return_pct)}`}>{pct(g.return_pct)}</span>
                      )}
                      {g.benchmark_return_pct != null && (
                        <span className="text-gray-400 ml-1.5">vs {pct(g.benchmark_return_pct)}</span>
                      )}
                      {g.alpha != null && <span className="text-gray-400 ml-1.5">alpha {pct(g.alpha)}</span>}
                    </div>
                    <Link
                      href={`/ai-analytics/recommendations/${g.recommendation_snapshot_id}`}
                      className="text-xs font-semibold text-blue-600 hover:underline shrink-0"
                    >
                      Report Card →
                    </Link>
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
