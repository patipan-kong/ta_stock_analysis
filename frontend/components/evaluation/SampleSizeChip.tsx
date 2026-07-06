"use client";

// AI Evaluation M4 — mandatory on every aggregate metric (EXECUTION_INTELLIGENCE_UX.md §6).

export default function SampleSizeChip({ n, label }: { n: number; label?: string }) {
  return (
    <span
      className="inline-block text-[10px] font-medium px-1.5 py-0.5 rounded-full bg-gray-100 text-gray-500 border border-gray-200 tabular-nums"
      title="Sample size — the number of graded events behind this metric."
    >
      {label ?? `n=${n}`}
    </span>
  );
}
