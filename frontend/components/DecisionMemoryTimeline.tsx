"use client";

import { useEffect, useMemo, useState } from "react";
import {
  getDecisionMemoryTimeline,
  getAIvsHumanTimeline,
  type DecisionMemoryEntry,
  type AIvsHumanTimelineEntry,
  type ExecutionDecisionType,
} from "@/lib/api";

const DECISION_BADGE: Record<ExecutionDecisionType, string> = {
  APPROVED: "bg-green-50 text-green-700 border-green-200",
  REJECTED: "bg-red-50 text-red-700 border-red-200",
  MANUAL_OVERRIDE: "bg-gray-50 text-gray-700 border-gray-200",
  PARTIAL_EXECUTION: "bg-amber-50 text-amber-700 border-amber-200",
};

function decisionLabel(decision: ExecutionDecisionType): string {
  if (decision === "APPROVED") return "Approve Rebalance";
  if (decision === "REJECTED") return "Reject Recommendation";
  if (decision === "MANUAL_OVERRIDE") return "Manual Override";
  return "Partial Execution";
}

function fmtPct(v: number | null | undefined): string {
  if (v == null) return "-";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(2)}%`;
}

function aiVerdict(entry: AIvsHumanTimelineEntry | undefined): string {
  if (!entry || entry.ai_better == null) return "Pending";
  return entry.ai_better ? "AI Winning" : "Human Winning";
}

function verdictClass(entry: AIvsHumanTimelineEntry | undefined): string {
  if (!entry || entry.ai_better == null) return "text-gray-500";
  return entry.ai_better ? "text-amber-700" : "text-green-700";
}

export default function DecisionMemoryTimeline({
  portfolioId,
  limit = 20,
}: {
  portfolioId: number;
  limit?: number;
}) {
  const [entries, setEntries] = useState<DecisionMemoryEntry[]>([]);
  const [aiTimeline, setAiTimeline] = useState<AIvsHumanTimelineEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.all([
      getDecisionMemoryTimeline(portfolioId, limit),
      getAIvsHumanTimeline(portfolioId, 180, limit),
    ])
      .then(([timeline, ai]) => {
        if (!active) return;
        setEntries(timeline);
        setAiTimeline(ai.timeline ?? []);
      })
      .catch(() => {
        if (!active) return;
        setEntries([]);
        setAiTimeline([]);
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [portfolioId, limit]);

  const aiMap = useMemo(() => {
    const map = new Map<number, AIvsHumanTimelineEntry>();
    for (const item of aiTimeline) {
      map.set(item.decision_id, item);
    }
    return map;
  }, [aiTimeline]);

  if (loading) {
    return (
      <section className="bg-white border border-gray-200 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-gray-800">Decision Timeline</h2>
        <p className="text-xs text-gray-400 mt-2">Loading decision memory...</p>
      </section>
    );
  }

  if (entries.length === 0) {
    return (
      <section className="bg-white border border-gray-200 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-gray-800">Decision Timeline</h2>
        <p className="text-xs text-gray-400 mt-2">
          No execution decisions yet. Run optimizer and record your first decision to start memory tracking.
        </p>
      </section>
    );
  }

  return (
    <section className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100">
        <h2 className="text-sm font-semibold text-gray-800">Decision Timeline</h2>
        <p className="text-xs text-gray-400 mt-0.5">Execution lifecycle with optimizer confidence and realized outcomes</p>
      </div>
      <div className="overflow-x-auto max-h-80 overflow-y-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-50 text-xs text-gray-500">
            <tr>
              <th className="text-left py-2.5 px-4">Recommendation Date</th>
              <th className="text-left py-2.5 px-4">Decision Type</th>
              <th className="text-left py-2.5 px-4">Optimizer Confidence</th>
              <th className="text-left py-2.5 px-4">Regime</th>
              <th className="text-left py-2.5 px-4">Realized Outcome</th>
              <th className="text-left py-2.5 px-4">AI vs Human</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {entries.map((entry) => {
              const ai = aiMap.get(entry.decision_id);
              const confidence = entry.recommendation_snapshot?.consensus?.consensus_strength_score;
              const regime = entry.recommendation_snapshot?.regime?.regime ?? "-";
              const recDate = entry.recommendation_snapshot?.created_at ?? entry.executed_at;

              return (
                <tr key={entry.decision_id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-xs text-gray-600 whitespace-nowrap">
                    {new Date(recDate).toLocaleDateString("en-GB", { dateStyle: "medium" })}
                  </td>
                  <td className="px-4 py-3">
                    <span className={`inline-flex text-xs font-medium px-2 py-0.5 rounded-full border ${DECISION_BADGE[entry.decision]}`}>
                      {decisionLabel(entry.decision)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-700">
                    {confidence != null ? `${Math.round(confidence)}/100` : "-"}
                  </td>
                  <td className="px-4 py-3 text-xs text-gray-600">{regime.replace(/_/g, " ")}</td>
                  <td className="px-4 py-3 text-xs">
                    <span className={`${(ai?.actual_return_pct ?? 0) >= 0 ? "text-green-700" : "text-red-600"}`}>
                      Human {fmtPct(ai?.actual_return_pct)}
                    </span>
                    <span className="text-gray-400 mx-1">/</span>
                    <span className={`${(ai?.shadow_return_pct ?? 0) >= 0 ? "text-green-700" : "text-red-600"}`}>
                      AI {fmtPct(ai?.shadow_return_pct)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-xs font-medium">
                    <span className={verdictClass(ai)}>{aiVerdict(ai)}</span>
                    {ai?.return_delta != null && (
                      <span className="text-gray-400 ml-2">({fmtPct(ai.return_delta)} delta)</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
