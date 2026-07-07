"use client";

// AI Evaluation M4 — dense sortable-ready table chrome shared by S2 (and S4/S6
// in later milestones). Tabular figures, right-aligned numerics, row → detail.
// Loading skeleton matches final geometry (EXECUTION_INTELLIGENCE_UX.md §8).

import { ReactNode, KeyboardEvent } from "react";

function handleActivateKey<T>(onRowClick: ((row: T) => void) | undefined, row: T) {
  if (!onRowClick) return undefined;
  return (e: KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onRowClick(row);
    }
  };
}

export interface EvidenceColumn<T> {
  key: string;
  header: string;
  align?: "left" | "right";
  render: (row: T) => ReactNode;
}

export default function EvidenceLedger<T>({
  columns,
  rows,
  rowKey,
  onRowClick,
  loading,
  emptyMessage,
}: {
  columns: EvidenceColumn<T>[];
  rows: T[];
  rowKey: (row: T) => string | number;
  onRowClick?: (row: T) => void;
  loading?: boolean;
  emptyMessage?: string;
}) {
  if (loading) {
    return (
      <div className="space-y-1.5">
        {Array.from({ length: 8 }).map((_, i) => (
          <div key={i} className="h-9 animate-pulse bg-gray-100 rounded" />
        ))}
      </div>
    );
  }
  if (rows.length === 0) {
    return <p className="text-sm text-gray-400 py-6 text-center">{emptyMessage ?? "No rows yet."}</p>;
  }
  return (
    <>
      {/* Tablet+: dense table, unchanged. */}
      <div className="hidden sm:block overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-gray-500 border-b">
              {columns.map((c) => (
                <th key={c.key} className={`py-2 px-3 font-medium whitespace-nowrap ${c.align === "right" ? "text-right" : ""}`}>
                  {c.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr
                key={rowKey(row)}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
                onKeyDown={handleActivateKey(onRowClick, row)}
                tabIndex={onRowClick ? 0 : undefined}
                className={`border-b last:border-0 hover:bg-gray-50 ${onRowClick ? "cursor-pointer focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-300" : ""}`}
              >
                {columns.map((c) => (
                  <td key={c.key} className={`py-2 px-3 align-top ${c.align === "right" ? "text-right" : ""}`}>
                    {c.render(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Mobile: stacked cards, one per row (UX §9 — ledgers become
          stacked cards; tap = navigate, no page-level horizontal scroll).
          Every column renders as a label:value line in the same order and
          from the same render() the desktop table uses — a generic
          card shape rather than a bespoke per-screen 3-line layout, so no
          column is ever silently dropped on mobile. */}
      <div className="sm:hidden divide-y divide-gray-100">
        {rows.map((row) => (
          <div
            key={rowKey(row)}
            onClick={onRowClick ? () => onRowClick(row) : undefined}
            onKeyDown={handleActivateKey(onRowClick, row)}
            role={onRowClick ? "button" : undefined}
            tabIndex={onRowClick ? 0 : undefined}
            className={`py-3 px-1 space-y-1.5 ${onRowClick ? "cursor-pointer active:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-300" : ""}`}
          >
            {columns.map((c) => (
              <div key={c.key} className="flex items-start justify-between gap-3 text-sm">
                <span className="text-xs text-gray-400 shrink-0 pt-0.5 whitespace-nowrap">{c.header}</span>
                <span className={`min-w-0 ${c.align === "right" ? "text-right" : "text-left"}`}>{c.render(row)}</span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </>
  );
}
