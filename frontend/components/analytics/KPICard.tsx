"use client";

export interface KPICardProps {
  label: string;
  value: string;
  valueClass?: string;
  sub?: string;
  tooltip?: string;
  compact?: boolean;
}

export function KPICard({ label, value, valueClass, sub, tooltip, compact }: KPICardProps) {
  return (
    <div
      className={`bg-white border border-gray-200 rounded-xl hover:border-gray-300 transition-colors ${
        compact ? "p-3" : "p-4"
      }`}
      title={tooltip}
    >
      <p className="text-xs text-gray-500 mb-1 font-medium">{label}</p>
      <p className={`${compact ? "text-sm font-semibold leading-snug" : "text-lg font-bold"} tabular-nums ${valueClass ?? "text-gray-900"}`}>{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );
}

export function SkeletonCard() {
  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 animate-pulse">
      <div className="h-3 bg-gray-100 rounded w-20 mb-2" />
      <div className="h-6 bg-gray-200 rounded w-24" />
    </div>
  );
}
