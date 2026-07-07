"use client";

// AI Evaluation M4 — reuses the existing decision vocabulary from
// DecisionActionPanel (frontend/app/optimizer/page.tsx) so the same words
// render end-to-end, plus EXPIRED (P4 — system-generated terminal state for
// undecided recommendations, not present in the optimizer page's own enum).

const DECISION_BADGE: Record<string, string> = {
  APPROVED: "bg-green-100 text-green-800 border-green-200",
  REJECTED: "bg-red-100 text-red-800 border-red-200",
  MANUAL_OVERRIDE: "bg-gray-100 text-gray-700 border-gray-200",
  PARTIAL_EXECUTION: "bg-amber-100 text-amber-800 border-amber-200",
  EXPIRED: "bg-gray-50 text-gray-400 border-gray-200",
};

const DECISION_LABEL: Record<string, string> = {
  APPROVED: "Approved",
  REJECTED: "Rejected",
  MANUAL_OVERRIDE: "Override",
  PARTIAL_EXECUTION: "Partial",
  EXPIRED: "Expired",
};

export default function DecisionStatusBadge({ decision }: { decision: string | null | undefined }) {
  if (!decision) {
    return (
      <span className="text-xs font-medium px-2 py-0.5 rounded-full border bg-gray-50 text-gray-400 border-gray-200 whitespace-nowrap">
        no decision
      </span>
    );
  }
  const cls = DECISION_BADGE[decision] ?? "bg-gray-100 text-gray-700 border-gray-200";
  const label = DECISION_LABEL[decision] ?? decision;
  return (
    <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border whitespace-nowrap ${cls}`}>
      {label}
    </span>
  );
}
