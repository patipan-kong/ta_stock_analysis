"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

// Phase 4C.2A — Portfolio hub secondary navigation.
// Soft consolidation only: existing routes stay as-is; this segmented control
// just groups them under one "Portfolio" entry point.
const TABS = [
  { label: "ภาพรวม",          href: "/portfolio" },
  { label: "ผลตอบแทน",        href: "/performance" },
  { label: "วิเคราะห์เชิงลึก", href: "/analytics" },
];

export default function PortfolioTabs() {
  const pathname = usePathname();

  return (
    <div className="inline-flex items-center gap-1 rounded-xl bg-gray-100 p-1">
      {TABS.map(({ label, href }) => {
        const active = pathname.startsWith(href);
        return (
          <Link
            key={href}
            href={href}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
              active
                ? "bg-white text-blue-700 shadow-sm"
                : "text-gray-500 hover:text-gray-800"
            }`}
          >
            {label}
          </Link>
        );
      })}
    </div>
  );
}
