"use client";

import type { MujiTranslation } from "@/lib/api";

export default function MujiSummaryCard({ translation }: { translation: MujiTranslation }) {
  return (
    <div className="rounded-2xl border-2 border-gray-200 bg-white p-5 space-y-3 shadow-sm">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
        ภาพรวมวันนี้
      </p>
      <p className="text-lg font-bold text-gray-900">{translation.headline}</p>
      <ul className="space-y-2">
        {translation.summary.map((line, i) => (
          <li key={i} className="flex items-start gap-2 text-sm text-gray-700">
            <span className="mt-0.5 text-emerald-500">✓</span>
            <span>{line}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
