"use client";

// AI Evaluation M4 — 7/30/90/180D returns for one recommendation. Three
// states per cell, styled once (EXECUTION_INTELLIGENCE_UX.md §6): graded ✓
// (number, or CounterfactualValue when the plan wasn't executed), maturing ◐
// (days left), pending_grading ⏳ (due but not yet graded by the scheduler).
// Grades never restyle after issuance — this component only renders what the
// backend HorizonCell.status says, it never computes maturity itself.

import type { HorizonCell } from "@/lib/api";
import MaturityChip from "./MaturityChip";
import CounterfactualValue from "./CounterfactualValue";

const HORIZON_ORDER = ["H7", "H30", "H90", "H180"];
const HORIZON_LABEL: Record<string, string> = { H7: "7D", H30: "30D", H90: "90D", H180: "180D" };

export default function HorizonStrip({
  strip,
  isCounterfactual = false,
}: {
  strip: Record<string, HorizonCell>;
  isCounterfactual?: boolean;
}) {
  return (
    <div className="flex items-center gap-2.5 flex-wrap">
      {HORIZON_ORDER.map((key) => {
        const cell = strip[key];
        if (!cell) return null;
        return (
          <div key={key} className="flex items-center gap-1 text-xs">
            <span className="text-gray-400 font-medium">{HORIZON_LABEL[key]}</span>
            {cell.status === "graded" ? (
              isCounterfactual ? (
                <CounterfactualValue value={cell.return_pct} />
              ) : (
                <span
                  className={`font-semibold tabular-nums ${
                    (cell.return_pct ?? 0) >= 0 ? "text-green-700" : "text-red-600"
                  }`}
                >
                  {(cell.return_pct ?? 0) >= 0 ? "+" : ""}
                  {cell.return_pct?.toFixed(1)}%
                </span>
              )
            ) : cell.status === "maturing" ? (
              <MaturityChip kind="maturing" daysRemaining={cell.days_remaining} dueDate={cell.due_date} />
            ) : (
              <MaturityChip kind="pending_grading" />
            )}
          </div>
        );
      })}
    </div>
  );
}
