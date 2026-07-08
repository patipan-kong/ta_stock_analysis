"use client";

// UX clarification pass (Three Portfolios rolling-window transparency) —
// translates raw comparable-history days into the same pill-badge idiom as
// MaturityChip/SampleSizeChip, so users read "how much history backs this
// chart" without parsing a day count themselves.

function classify(days: number): { label: string; icon: string; classes: string } {
  if (days < 14) return { label: "Very Early", icon: "\u{1F534}", classes: "bg-red-50 text-red-700 border-red-200" };
  if (days < 30) return { label: "Early", icon: "\u{1F7E0}", classes: "bg-orange-50 text-orange-700 border-orange-200" };
  if (days < 90) return { label: "Developing", icon: "\u{1F7E1}", classes: "bg-amber-50 text-amber-700 border-amber-200" };
  return { label: "Established", icon: "\u{1F7E2}", classes: "bg-green-50 text-green-700 border-green-200" };
}

export default function EvidenceBadge({ days }: { days: number }) {
  const { label, icon, classes } = classify(days);
  return (
    <span
      className={`inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded-full border whitespace-nowrap ${classes}`}
      title="Longer history generally leads to more reliable comparisons."
    >
      {icon} {label}
    </span>
  );
}
