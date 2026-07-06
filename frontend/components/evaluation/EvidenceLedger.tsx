"use client";

// AI Evaluation M4 — dense sortable-ready table chrome shared by S2 (and S4/S6
// in later milestones). Tabular figures, right-aligned numerics, row → detail.
// Loading skeleton matches final geometry (EXECUTION_INTELLIGENCE_UX.md §8).

import { ReactNode } from "react";

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
    <div className="overflow-x-auto">
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
              className={`border-b last:border-0 hover:bg-gray-50 ${onRowClick ? "cursor-pointer" : ""}`}
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
  );
}
