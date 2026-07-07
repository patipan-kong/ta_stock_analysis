"use client";

// AI Evaluation M7 entry point (UX §2.3): "Ops Center Quant dashboard
// headline verdict tile" -> Scorecard (S1). Renders GET
// /analytics/evaluation/scorecard's verdict sentence verbatim — no
// recomputation, same source the Scorecard page itself reads.

import { useEffect, useState } from "react";
import Link from "next/link";
import { getEvaluationScorecard, type EvaluationScorecard } from "@/lib/api";
import LensGradeChip from "@/components/evaluation/LensGradeChip";

export default function EvaluationVerdictTile({ portfolioId }: { portfolioId: number }) {
  const [data, setData] = useState<EvaluationScorecard | null>(null);

  useEffect(() => {
    let cancelled = false;
    getEvaluationScorecard(portfolioId, 90)
      .then((r) => {
        if (!cancelled) setData(r);
      })
      .catch(() => {
        if (!cancelled) setData(null);
      });
    return () => {
      cancelled = true;
    };
  }, [portfolioId]);

  if (!data || data.status === "cold_start") {
    return (
      <Link
        href="/ai-analytics"
        className="block bg-white border border-gray-200 rounded-xl px-4 py-2.5 text-xs text-gray-400 hover:border-gray-300 transition-colors"
      >
        AI Evaluation: not enough history yet — view Scorecard →
      </Link>
    );
  }

  return (
    <Link
      href="/ai-analytics"
      className="flex items-center gap-3 bg-white border border-gray-200 rounded-xl px-4 py-2.5 hover:border-blue-300 transition-colors"
    >
      <p className="flex-1 min-w-0 text-xs text-gray-700 truncate" title={data.verdict.en}>
        {data.verdict.en}
      </p>
      <div className="flex items-center gap-1.5 shrink-0">
        <LensGradeChip grade={data.belief.grade} label="Belief" />
        <LensGradeChip grade={data.execution.grade} label="Execution" />
      </div>
      <span className="text-xs font-semibold text-blue-600 shrink-0">Scorecard →</span>
    </Link>
  );
}
