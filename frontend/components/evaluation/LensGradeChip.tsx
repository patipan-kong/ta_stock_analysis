"use client";

// AI Evaluation M4 — Belief/Execution grade chip. Renders the backend-computed
// LetterGrade exactly as delivered; below evaluation_settings.min_n_letter_grade
// the backend already sets status to "insufficient_evidence" with letter=null —
// this component never derives a letter itself (Single Source of Truth).

import type { LetterGrade } from "@/lib/api";

const LETTER_TONE: Record<string, string> = {
  "A+": "bg-green-100 text-green-800 border-green-200",
  A: "bg-green-100 text-green-800 border-green-200",
  "A-": "bg-green-100 text-green-800 border-green-200",
  "B+": "bg-blue-100 text-blue-800 border-blue-200",
  B: "bg-blue-100 text-blue-800 border-blue-200",
  "B-": "bg-blue-100 text-blue-800 border-blue-200",
  "C+": "bg-amber-100 text-amber-800 border-amber-200",
  C: "bg-amber-100 text-amber-800 border-amber-200",
  "C-": "bg-amber-100 text-amber-800 border-amber-200",
  D: "bg-orange-100 text-orange-800 border-orange-200",
  F: "bg-red-100 text-red-800 border-red-200",
};

export default function LensGradeChip({ grade, label }: { grade: LetterGrade; label?: string }) {
  if (grade.status !== "ok" || !grade.letter) {
    return (
      <span
        className="inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full bg-gray-100 text-gray-500 border border-gray-200 whitespace-nowrap"
        title="Evidence below the minimum sample-size threshold for a letter grade — shown plainly, not apologetically."
      >
        {label ? `${label} ` : ""}
        หลักฐานยังไม่พอ (n={grade.n})
      </span>
    );
  }
  const tone = LETTER_TONE[grade.letter] ?? "bg-gray-100 text-gray-700 border-gray-200";
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-bold px-2 py-0.5 rounded-full border whitespace-nowrap ${tone}`}>
      {label ? `${label} ` : ""}
      {grade.letter} <span className="font-normal opacity-70">(n={grade.n})</span>
    </span>
  );
}
