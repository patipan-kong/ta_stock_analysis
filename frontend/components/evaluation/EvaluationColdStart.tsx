"use client";

// AI Evaluation M4 — Rung 0 of the cold-start ladder (EXECUTION_INTELLIGENCE_UX.md
// §7): "no recommendations yet" is a first-class narrative, never a broken-looking
// empty chart. States what will appear and gives a single CTA to the optimizer.

import Link from "next/link";

export default function EvaluationColdStart({ title, message }: { title: string; message: string }) {
  return (
    <div className="flex flex-col items-center justify-center text-center gap-3 py-14 px-6 bg-white border border-gray-200 rounded-xl">
      <p className="text-sm font-semibold text-gray-700">{title}</p>
      <p className="text-sm text-gray-500 max-w-md leading-relaxed">{message}</p>
      <Link
        href="/optimizer"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-blue-700 bg-blue-50 hover:bg-blue-100 transition-colors rounded-lg px-4 py-2"
      >
        ไปที่หน้า Optimizer
        <span aria-hidden>→</span>
      </Link>
    </div>
  );
}
