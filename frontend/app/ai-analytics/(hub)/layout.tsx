"use client";

// AI Evaluation M4 — Hub shell. Wraps every Evaluation screen (Scorecard,
// Recommendations, Execution, Human vs AI, Portfolios, Attribution) with the
// shared segmented sub-nav. `/ai-analytics/system` (AI operational telemetry,
// Planning Decision P1) deliberately lives OUTSIDE this route group so it
// keeps its own page chrome and isn't shown inside the Evaluation tab set.

import EvaluationTabs from "@/components/evaluation/EvaluationTabs";

export default function EvaluationHubLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="max-w-6xl mx-auto px-4 py-6 space-y-5">
      <EvaluationTabs />
      {children}
    </div>
  );
}
