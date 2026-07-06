"use client";

// AI Evaluation & Execution Intelligence — Milestone M0 placeholder.
//
// This route is reserved for the Evaluation hub described in
// docs/EXECUTION_INTELLIGENCE_UX.md (Scorecard / Recommendations / Execution /
// Human vs AI / Portfolios / Attribution). It ships in Milestone M4
// (docs/AI_EVALUATION_IMPLEMENTATION_PLAN.md). Until then this is a minimal
// landing page so the existing "AI Analytics" nav entry keeps working and the
// relocated telemetry page (Planning Decision P1) stays reachable.

import Link from "next/link";

export default function AiAnalyticsLandingPage() {
  return (
    <div className="max-w-2xl mx-auto py-16 text-center space-y-4">
      <h1 className="text-xl font-bold text-gray-800">AI Analytics</h1>
      <p className="text-sm text-gray-500">
        The AI Evaluation hub (recommendation grading, execution intelligence, human-vs-AI,
        attribution) is being built in stages and will live here.
      </p>
      <div>
        <Link
          href="/ai-analytics/system"
          className="inline-flex items-center gap-1.5 text-sm font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 transition-colors rounded-lg px-4 py-2"
        >
          Go to AI System Telemetry
          <span aria-hidden>→</span>
        </Link>
      </div>
    </div>
  );
}
