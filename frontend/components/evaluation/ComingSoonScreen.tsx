"use client";

// AI Evaluation M4 — lightweight placeholder for the three hub segments whose
// screens are out of scope for this milestone (Execution S4/S4b, Human vs AI
// S5 + Opportunity Cost S6, Portfolios S7, Attribution S8 — all M5/M6 per
// docs/AI_EVALUATION_IMPLEMENTATION_PLAN.md §5). No data fetching, no logic —
// this exists only so the 6-segment sub-nav required by the UX baseline
// (§2.2) has no dead links. The APIs these screens will consume (execution
// ledger) may already exist from M3; the screens themselves do not yet.

export default function ComingSoonScreen({ title, milestone, description }: { title: string; milestone: string; description: string }) {
  return (
    <div className="flex flex-col items-center justify-center text-center gap-2 py-16 px-6 bg-white border border-gray-200 rounded-xl">
      <h1 className="text-lg font-bold text-gray-800">{title}</h1>
      <p className="text-sm text-gray-500 max-w-md leading-relaxed">{description}</p>
      <span className="text-xs font-medium text-gray-400 mt-2">Ships in {milestone}</span>
    </div>
  );
}
