"use client";

import type { IdeaReview } from "@/lib/api";

// ─── Decision styling ─────────────────────────────────────────────────────────

const DECISION_STYLE: Record<string, { bg: string; text: string; border: string }> = {
  APPROVE:  { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-300" },
  WATCH:    { bg: "bg-blue-50",    text: "text-blue-700",    border: "border-blue-300"    },
  REVIEW:   { bg: "bg-amber-50",   text: "text-amber-700",   border: "border-amber-300"   },
  DECLINE:  { bg: "bg-red-50",     text: "text-red-700",     border: "border-red-300"     },
};

// Used when data_available == false — overrides the decision badge entirely
const NEEDS_ANALYSIS_STYLE = {
  card:   { bg: "bg-orange-50", border: "border-orange-300" },
  badge:  { bg: "bg-orange-100", text: "text-orange-700", border: "border-orange-300" },
};

const SIGNAL_STYLE: Record<string, string> = {
  ACCUMULATE: "bg-[#0F6E56] text-white",
  BUY:        "bg-[#27500A] text-white",
  WATCH:      "bg-[#0C447C] text-white",
  HOLD:       "bg-[#444441] text-white",
  REDUCE:     "bg-[#854F0B] text-white",
  SELL:       "bg-[#791F1F] text-white",
};

const ALIGNMENT_STYLE: Record<string, string> = {
  ALIGNED:       "bg-emerald-100 text-emerald-700",
  CONTRADICTING: "bg-red-100 text-red-700",
  NEUTRAL:       "bg-gray-100 text-gray-500",
};

const ALIGNMENT_LABEL: Record<string, string> = {
  ALIGNED:       "Aligned",
  CONTRADICTING: "Contradicting",
  NEUTRAL:       "Neutral",
};

const PRIORITY_STYLE: Record<string, string> = {
  HIGH:   "bg-violet-100 text-violet-700",
  MEDIUM: "bg-sky-100 text-sky-700",
  LOW:    "bg-gray-100 text-gray-500",
};

const RISK_STYLE: Record<string, string> = {
  LOW:    "text-emerald-600",
  MEDIUM: "text-amber-600",
  HIGH:   "text-red-600",
};

const POLICY_STYLE: Record<string, string> = {
  PASS:    "text-emerald-600",
  WARNING: "text-amber-600",
  FAIL:    "text-red-600",
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

function AllocationBar({
  current,
  target,
  limit,
  label,
}: {
  current: number;
  target: number | null;
  limit: number;
  label: string;
}) {
  const pct = Math.min(100, limit > 0 ? (current / limit) * 100 : 0);
  const targetPct = target != null ? Math.min(100, limit > 0 ? (target / limit) * 100 : 0) : null;
  const barColor = pct >= 80 ? "bg-red-400" : pct >= 60 ? "bg-amber-400" : "bg-emerald-400";

  return (
    <div className="space-y-0.5">
      <div className="flex justify-between text-[10px] text-gray-500 font-mono">
        <span>{label}</span>
        <span>
          {current.toFixed(1)}%
          {target != null && (
            <span className="text-blue-500 ml-1">→ {target.toFixed(1)}%</span>
          )}
          <span className="text-gray-400"> / {limit.toFixed(0)}%</span>
        </span>
      </div>
      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden relative">
        <div
          className={`h-full rounded-full ${barColor} transition-all`}
          style={{ width: `${pct}%` }}
        />
        {targetPct != null && (
          <div
            className="absolute top-0 h-full w-0.5 bg-blue-500 opacity-70"
            style={{ left: `${targetPct}%` }}
          />
        )}
      </div>
    </div>
  );
}

function FitBar({ score }: { score: number }) {
  const pct = score * 10;
  const barColor = score >= 7 ? "bg-emerald-400" : score >= 5 ? "bg-amber-400" : "bg-red-400";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${barColor} transition-all`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[10px] font-mono text-gray-600 w-8 text-right">{score}/10</span>
    </div>
  );
}

// ─── Main card ────────────────────────────────────────────────────────────────

export default function IdeaReviewResult({ review }: { review: IdeaReview }) {
  const needsAnalysis = !review.data_available;
  const cardStyle = needsAnalysis
    ? NEEDS_ANALYSIS_STYLE.card
    : (DECISION_STYLE[review.committee_decision] ?? DECISION_STYLE.WATCH);

  return (
    <div className={`rounded-xl border ${cardStyle.border} ${cardStyle.bg} p-4 space-y-3`}>
      {/* Header row */}
      <div className="flex items-start justify-between gap-2 flex-wrap">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-bold text-gray-900 text-base">{review.symbol}</span>
          {review.sector && (
            <span className="text-[10px] bg-white border border-gray-200 text-gray-500 rounded px-1.5 py-0.5">
              {review.sector}
            </span>
          )}
          {review.existing_position && (
            <span className="text-[10px] bg-white border border-gray-200 text-gray-400 rounded px-1.5 py-0.5">
              In portfolio
            </span>
          )}
        </div>
        <div className="flex items-center gap-1.5 flex-wrap">
          {/* Portfolio priority — always valid, portfolio-derived */}
          <span className={`text-[10px] font-semibold rounded px-1.5 py-0.5 ${PRIORITY_STYLE[review.portfolio_priority]}`}>
            {review.portfolio_priority} fit
          </span>
          {/* Optimizer alignment — only show when fully evaluated */}
          {!needsAnalysis && review.optimizer_alignment !== "NEUTRAL" && (
            <span className={`text-[10px] font-semibold rounded px-1.5 py-0.5 ${ALIGNMENT_STYLE[review.optimizer_alignment]}`}>
              {ALIGNMENT_LABEL[review.optimizer_alignment]}
            </span>
          )}
          {/* Committee decision badge — swapped for warning when data missing */}
          {needsAnalysis ? (
            <span
              className={`text-xs font-bold rounded px-2 py-0.5 border
                          ${NEEDS_ANALYSIS_STYLE.badge.border}
                          ${NEEDS_ANALYSIS_STYLE.badge.text}
                          ${NEEDS_ANALYSIS_STYLE.badge.bg}`}
              title="ยังไม่มีข้อมูลวิเคราะห์ — AI Committee ยังไม่สามารถประเมินได้"
            >
              ⚠ Needs Analysis
            </span>
          ) : (
            <span
              className={`text-xs font-bold rounded px-2 py-0.5 border
                          ${(DECISION_STYLE[review.committee_decision] ?? DECISION_STYLE.WATCH).border}
                          ${(DECISION_STYLE[review.committee_decision] ?? DECISION_STYLE.WATCH).text}
                          bg-white`}
            >
              {review.committee_decision}
            </span>
          )}
        </div>
      </div>

      {/* Missing-data notice — shown prominently when analysis cache absent */}
      {needsAnalysis && (
        <div className="rounded-lg border border-orange-200 bg-orange-100 px-3 py-2.5 space-y-1">
          <p className="text-xs font-semibold text-orange-800">
            ยังไม่มีข้อมูลวิเคราะห์สำหรับหุ้นตัวนี้
          </p>
          <p className="text-[11px] text-orange-700 leading-relaxed">
            กรุณารันการวิเคราะห์ก่อน เพื่อให้ AI Committee ประเมินได้อย่างครบถ้วน
          </p>
          <p className="text-[10px] text-orange-600 font-mono mt-0.5">
            ผลลัพธ์ด้านล่างอิงจากข้อมูล Portfolio เท่านั้น — ไม่รวมสัญญาณ TA/FA/News
          </p>
        </div>
      )}

      {/* Signal + fit row */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <p className="text-[10px] text-gray-500 uppercase tracking-wide">Signal</p>
          {review.existing_signal ? (
            <div className="flex items-center gap-1.5">
              <span className={`text-[10px] font-bold rounded px-1.5 py-0.5 ${SIGNAL_STYLE[review.existing_signal] ?? "bg-gray-100 text-gray-600"}`}>
                {review.existing_signal}
              </span>
              {review.signal_confidence != null && (
                <span className="text-[10px] text-gray-400">
                  {Math.round(review.signal_confidence * 100)}% conf
                </span>
              )}
            </div>
          ) : (
            <span className={`text-[10px] italic ${needsAnalysis ? "text-orange-500" : "text-gray-400"}`}>
              {needsAnalysis ? "ต้องวิเคราะห์ก่อน" : "No signal"}
            </span>
          )}
        </div>
        <div className="space-y-1">
          <p className="text-[10px] text-gray-500 uppercase tracking-wide">Strategic Fit</p>
          <FitBar score={review.strategic_fit_score} />
        </div>
      </div>

      {/* Allocation bars */}
      <div className="space-y-2">
        <AllocationBar
          current={review.current_allocation_pct}
          target={review.target_allocation_pct}
          limit={review.position_limit_pct}
          label="Position"
        />
        <AllocationBar
          current={review.sector_current_pct}
          target={null}
          limit={review.sector_limit_pct}
          label={review.sector ? `${review.sector} sector` : "Sector"}
        />
      </div>

      {/* Risk + Policy row */}
      <div className="flex gap-4 text-[10px]">
        <span>
          Risk:{" "}
          <span className={`font-semibold ${RISK_STYLE[review.risk_impact]}`}>
            {review.risk_impact}
          </span>
        </span>
        <span>
          Policy:{" "}
          <span className={`font-semibold ${POLICY_STYLE[review.policy_check]}`}>
            {review.policy_check}
          </span>
        </span>
        {!needsAnalysis && review.optimizer_action && (
          <span className="text-gray-400">
            Optimizer: <span className="font-mono">{review.optimizer_action}</span>
          </span>
        )}
      </div>

      {/* Reason — only shown for fully evaluated results */}
      {!needsAnalysis && (
        <p className="text-xs text-gray-600 leading-relaxed">{review.reason}</p>
      )}

      {/* Warnings */}
      {review.warnings.length > 0 && (
        <div className="space-y-0.5">
          {review.warnings.map((w, i) => (
            <p key={i} className="text-[10px] text-amber-700 bg-amber-50 rounded px-2 py-0.5">
              {w}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
