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
    <div className="flex items-center justify-between flex-wrap gap-3">
      <div className="inline-flex items-center gap-1 rounded-xl bg-gray-100 p-1 flex-wrap">
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
      <Link
        href="/ai-analytics/system"
        className="text-xs font-medium text-gray-400 hover:text-blue-600 transition-colors whitespace-nowrap"
      >
        System Telemetry →
      </Link>
    </div>
  );
}
