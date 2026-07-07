"use client";

// AI Evaluation M4 — Hub sub-navigation (EXECUTION_INTELLIGENCE_UX.md §2.2).
// Six segments, Scorecard default. System Telemetry is a header link, not a
// 7th segment (Planning Decision P1) — it is operational AI telemetry, a
// different concern than investment evaluation.

import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { label: "สรุปผลงาน", href: "/ai-analytics" },
  { label: "คำแนะนำ", href: "/ai-analytics/recommendations" },
  { label: "การตัดสินใจ", href: "/ai-analytics/execution" },
  { label: "คน vs AI", href: "/ai-analytics/human-vs-ai" },
  { label: "พอร์ตเปรียบเทียบ", href: "/ai-analytics/portfolios" },
  { label: "ที่มาผลตอบแทน", href: "/ai-analytics/attribution" },
];

export default function EvaluationTabs() {
  const pathname = usePathname();

  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-3">
      {/* Mobile: one row, horizontally scrollable (the one permitted
          horizontal scroll, per UX §9) rather than wrapping six Thai
          labels into a squished multi-row pill. Desktop: unchanged. */}
      <div className="-mx-4 px-4 sm:mx-0 sm:px-0 overflow-x-auto">
        <div className="inline-flex items-center gap-1 rounded-xl bg-gray-100 p-1 w-max">
          {TABS.map(({ label, href }) => {
            const active = href === "/ai-analytics" ? pathname === "/ai-analytics" : pathname.startsWith(href);
            return (
              <Link
                key={href}
                href={href}
                className={`px-3.5 py-1.5 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
                  active ? "bg-white text-blue-700 shadow-sm" : "text-gray-500 hover:text-gray-800"
                }`}
              >
                {label}
              </Link>
            );
          })}
        </div>
      </div>
      <Link
        href="/ai-analytics/system"
        className="text-xs font-medium text-gray-400 hover:text-blue-600 transition-colors whitespace-nowrap shrink-0"
      >
        System Telemetry →
      </Link>
    </div>
  );
}
