"use client";

// AI Evaluation M4 — the single mechanism for "too early to grade" everywhere
// it appears (EXECUTION_INTELLIGENCE_UX.md §6). Two distinct states, never
// merged (per confirmed M3 design decision — see memory project_ai_evaluation_m0_m3.md):
//   - maturing: age < horizon, still counting down (days_remaining / due_date known)
//   - pending_grading: age >= horizon, but the scheduler hasn't graded it yet

export type MaturityKind = "maturing" | "pending_grading";

export default function MaturityChip({
  kind,
  daysRemaining,
  dueDate,
}: {
  kind: MaturityKind;
  daysRemaining?: number | null;
  dueDate?: string | null;
}) {
  if (kind === "pending_grading") {
    return (
      <span
        className="inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200 whitespace-nowrap"
        title="This horizon is due, but the daily grading job hasn't caught up yet."
      >
        ⏳ pending grading
      </span>
    );
  }
  return (
    <span
      className="inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-blue-50 text-blue-700 border border-blue-200 whitespace-nowrap"
      title={dueDate ? `Grades on ${dueDate}` : "Still within its holding window"}
    >
      ◐ {daysRemaining != null ? `${daysRemaining}d left` : dueDate ? `due ${dueDate}` : "maturing"}
    </span>
  );
}
