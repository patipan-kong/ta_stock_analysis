"use client";

import { useState, useMemo } from "react";
import Link from "next/link";
import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  getSortedRowModel,
  useReactTable,
  type SortingState,
  type Column,
} from "@tanstack/react-table";
import SignalBadge from "./SignalBadge";
import type { PortfolioItem } from "@/lib/api";

const TZ = "Asia/Bangkok";

function formatDate(iso: string | null): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return (
    d.toLocaleDateString("th-TH", { day: "2-digit", month: "short", year: "2-digit", timeZone: TZ }) +
    " " +
    d.toLocaleTimeString("th-TH", { hour: "2-digit", minute: "2-digit", timeZone: TZ })
  );
}

function ChangeCell({ value }: { value: number | null }) {
  if (value == null) return <span className="text-gray-400">—</span>;
  const cls = value > 0 ? "text-green-600 font-medium" : value < 0 ? "text-red-600 font-medium" : "text-gray-500";
  return <span className={cls}>{value > 0 ? "+" : ""}{value.toFixed(2)}%</span>;
}

function PLCell({ value }: { value: number | null }) {
  if (value == null) return <span className="text-gray-400">—</span>;
  const cls = value > 0 ? "text-green-600 font-medium" : value < 0 ? "text-red-600 font-medium" : "text-gray-500";
  const sign = value > 0 ? "+" : "";
  const abs = Math.abs(value);
  const formatted = abs >= 1000
    ? Math.round(value).toLocaleString()
    : value.toFixed(2);
  return <span className={cls}>{sign}{formatted}</span>;
}

function PLPctCell({ value }: { value: number | null }) {
  if (value == null) return <span className="text-gray-400">—</span>;
  const cls = value > 0 ? "text-green-600 font-medium" : value < 0 ? "text-red-600 font-medium" : "text-gray-500";
  return <span className={cls}>{value > 0 ? "+" : ""}{value.toFixed(2)}%</span>;
}

function freshnessColor(analyzedAt: string | null): string {
  if (!analyzedAt) return "bg-red-400";
  const ageMins = (Date.now() - new Date(analyzedAt).getTime()) / 60000;
  if (ageMins <= 60) return "bg-green-400";
  if (ageMins <= 180) return "bg-yellow-400";
  return "bg-red-400";
}

function freshnessTitle(analyzedAt: string | null): string {
  if (!analyzedAt) return "Never analyzed";
  const ageMins = (Date.now() - new Date(analyzedAt).getTime()) / 60000;
  if (ageMins <= 60) return "Fresh (< 1h)";
  if (ageMins <= 180) return "1–3 hours ago";
  return "Stale (> 3h)";
}

function SortIcon({ column }: { column: Column<PortfolioItem, unknown> }) {
  if (!column.getCanSort()) return null;
  const sorted = column.getIsSorted();
  return (
    <span className="ml-1 inline-block w-3 text-center select-none">
      {sorted === "asc" ? "↑" : sorted === "desc" ? "↓" : <span className="text-gray-300">↕</span>}
    </span>
  );
}

const SORT_OPTIONS = [
  { label: "Default", value: "" },
  { label: "Symbol A→Z", value: "symbol:asc" },
  { label: "Symbol Z→A", value: "symbol:desc" },
  { label: "Price ↑", value: "current_price:asc" },
  { label: "Price ↓", value: "current_price:desc" },
  { label: "Market Value ↑", value: "market_value:asc" },
  { label: "Market Value ↓", value: "market_value:desc" },
  { label: "Change% ↑", value: "change_percent:asc" },
  { label: "Change% ↓", value: "change_percent:desc" },
  { label: "P/L ↑", value: "pl_amount:asc" },
  { label: "P/L ↓", value: "pl_amount:desc" },
  { label: "P/L% ↑", value: "pl_pct:asc" },
  { label: "P/L% ↓", value: "pl_pct:desc" },
  { label: "Signal", value: "latest_signal:asc" },
  { label: "Recently Analyzed", value: "analyzed_at:desc" },
];

const columnHelper = createColumnHelper<PortfolioItem>();

export default function PortfolioTable({
  rows,
  onRemove,
  onReanalyze,
  onToggleSwap,
}: {
  rows: PortfolioItem[];
  onRemove: (symbol: string) => Promise<void>;
  onReanalyze: (symbol: string) => Promise<void>;
  onToggleSwap: (symbol: string, allow_swap: boolean) => Promise<void>;
}) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [busy, setBusy] = useState<Record<string, "remove" | "reanalyze" | "toggle" | null>>({});

  function setBusyFor(sym: string, state: "remove" | "reanalyze" | "toggle" | null) {
    setBusy((prev) => ({ ...prev, [sym]: state }));
  }

  async function handleRemove(symbol: string) {
    setBusyFor(symbol, "remove");
    try { await onRemove(symbol); } finally { setBusyFor(symbol, null); }
  }

  async function handleReanalyze(symbol: string) {
    setBusyFor(symbol, "reanalyze");
    try { await onReanalyze(symbol); } finally { setBusyFor(symbol, null); }
  }

  async function handleToggleSwap(symbol: string, allow_swap: boolean) {
    setBusyFor(symbol, "toggle");
    try { await onToggleSwap(symbol, allow_swap); } finally { setBusyFor(symbol, null); }
  }

  const columns = useMemo(
    () => [
      columnHelper.accessor("symbol", {
        header: "Symbol",
        sortingFn: "alphanumeric",
        cell: ({ getValue }) => {
          const sym = getValue();
          return (
            <Link href={`/stock/${encodeURIComponent(sym)}`} className="text-blue-600 hover:underline font-medium">
              {sym.replace(".BK", "")}
            </Link>
          );
        },
      }),
      columnHelper.accessor("shares", { header: "Shares", sortingFn: "basic" }),
      columnHelper.accessor("avg_cost", {
        header: "Avg Cost", sortingFn: "basic",
        cell: ({ getValue }) => getValue().toFixed(2),
      }),
      columnHelper.accessor(
        (row) => row.avg_cost * row.shares,
        {
          id: "cost",
          header: "Cost",
          sortingFn: "basic",
          cell: ({ getValue }) => {
            const v = getValue() as number;
            return <span className="text-gray-700">{v >= 1000 ? Math.round(v).toLocaleString() : v.toFixed(2)}</span>;
          },
        }
      ),
      columnHelper.accessor("current_price", {
        header: "Price", sortingFn: "basic",
        cell: ({ getValue }) => { const v = getValue(); return v != null ? v.toFixed(2) : "—"; },
      }),
      columnHelper.accessor(
        (row) => row.current_price != null ? row.current_price * row.shares : null,
        {
          id: "market_value",
          header: "Mkt Value",
          sortingFn: "basic",
          cell: ({ getValue }) => {
            const v = getValue() as number | null;
            if (v == null) return <span className="text-gray-400">—</span>;
            return <span className="text-gray-700 font-medium">{v >= 1000 ? Math.round(v).toLocaleString() : v.toFixed(2)}</span>;
          },
        }
      ),
      columnHelper.accessor("change_percent", {
        header: "Day%", sortingFn: "basic",
        cell: ({ getValue }) => <ChangeCell value={getValue()} />,
      }),
      columnHelper.accessor(
        (row) => row.current_price != null && row.avg_cost !== 0
          ? ((row.current_price - row.avg_cost) / row.avg_cost) * 100
          : null,
        {
          id: "pl_pct",
          header: "%P/L",
          sortingFn: "basic",
          cell: ({ getValue }) => <PLPctCell value={getValue() as number | null} />,
        }
      ),
      columnHelper.accessor(
        (row) => row.current_price != null ? (row.current_price - row.avg_cost) * row.shares : null,
        {
          id: "pl_amount",
          header: "P/L",
          sortingFn: "basic",
          cell: ({ getValue }) => <PLCell value={getValue() as number | null} />,
        }
      ),
      
      columnHelper.accessor("latest_signal", {
        header: "Signal", sortingFn: "alphanumeric",
        cell: ({ getValue }) => {
          const v = getValue();
          return v ? <SignalBadge signal={v} /> : <span className="text-gray-400">—</span>;
        },
      }),
      columnHelper.accessor("analyzed_at", {
        header: "Analyzed", sortingFn: "datetime",
        cell: ({ getValue, row }) => {
          const at = getValue();
          const sym = row.original.symbol;
          return (
            <span className="flex items-center gap-1.5 text-xs text-gray-400 whitespace-nowrap">
              <Link href={`/stock/${encodeURIComponent(sym)}`}>
                <span
                  className={`inline-block w-2 h-2 rounded-full ${freshnessColor(at)} hover:scale-125 transition-transform`}
                  title={freshnessTitle(at)}
                />
              </Link>
              {formatDate(at)}
            </span>
          );
        },
      }),
      columnHelper.display({
        id: "actions",
        header: "",
        cell: ({ row }) => {
          const sym = row.original.symbol;
          const state = busy[sym];
          return (
            <div className="flex gap-2 whitespace-nowrap items-center">
              <button
                onClick={() => handleToggleSwap(sym, !row.original.allow_swap)}
                disabled={!!state}
                title={row.original.allow_swap ? "Unlocked — can be swapped" : "Locked — won't be swapped"}
                className="text-base leading-none disabled:opacity-40 hover:scale-110 transition-transform"
              >
                {state === "toggle" ? "…" : row.original.allow_swap ? "🔓" : "🔒"}
              </button>
              <button onClick={() => handleReanalyze(sym)} disabled={!!state}
                className="text-blue-500 hover:text-blue-700 text-xs disabled:opacity-40">
                {state === "reanalyze" ? "…" : "Re-analyze"}
              </button>
              <button onClick={() => handleRemove(sym)} disabled={!!state}
                className="text-red-500 hover:text-red-700 text-xs disabled:opacity-40">
                {state === "remove" ? "…" : "Remove"}
              </button>
            </div>
          );
        },
      }),
    ],
    [busy]
  );

  const table = useReactTable({
    data: rows,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    sortDescFirst: false,
  });

  const sortedRows = table.getRowModel().rows;

  if (rows.length === 0) {
    return <p className="text-gray-500 text-sm">No stocks in this portfolio.</p>;
  }

  return (
    <>
      {/* ── Mobile card view (< md) ── */}
      <div className="md:hidden space-y-3">
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-500 shrink-0">Sort by</label>
          <select
            className="text-sm border rounded px-2 py-1 flex-1 bg-white"
            value={sorting.length ? `${sorting[0].id}:${sorting[0].desc ? "desc" : "asc"}` : ""}
            onChange={(e) => {
              const val = e.target.value;
              if (!val) { setSorting([]); return; }
              const [id, dir] = val.split(":");
              setSorting([{ id, desc: dir === "desc" }]);
            }}
          >
            {SORT_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>

        {sortedRows.map((row) => {
          const item = row.original;
          const sym = item.symbol;
          const state = busy[sym];
          const pl = item.current_price != null ? (item.current_price - item.avg_cost) * item.shares : null;
          const plPct = item.current_price != null && item.avg_cost !== 0
            ? ((item.current_price - item.avg_cost) / item.avg_cost) * 100
            : null;
          return (
            <div key={sym} className="bg-white border rounded-xl p-4 shadow-sm space-y-2">
              <div className="flex items-center justify-between">
                <Link href={`/stock/${encodeURIComponent(sym)}`} className="text-base font-bold text-blue-600 hover:underline">
                  {sym.replace(".BK", "")}
                  {sym.endsWith(".BK") && <span className="ml-1 text-xs text-gray-400">.BK</span>}
                </Link>
                {item.latest_signal
                  ? <SignalBadge signal={item.latest_signal} />
                  : <span className="text-xs text-gray-400">No signal</span>}
              </div>
              <div className="flex items-center gap-4 text-sm">
                <span className="font-semibold text-gray-800">
                  {item.current_price != null ? item.current_price.toFixed(2) : "—"}
                </span>
                <ChangeCell value={item.change_percent} />
                <span className="text-gray-400 text-xs ml-auto">{item.shares} shares</span>
              </div>
              <div className="flex items-center gap-4 text-sm">
                <div className="flex flex-col">
                  <span className="text-xs text-gray-400">P/L</span>
                  <PLCell value={pl} />
                </div>
                <div className="flex flex-col">
                  <span className="text-xs text-gray-400">%P/L</span>
                  <PLPctCell value={plPct} />
                </div>
              </div>
              <div className="flex items-center gap-4 text-xs text-gray-500">
                <span>Cost: <span className="text-gray-700 font-medium">
                  {(() => { const v = item.avg_cost * item.shares; return v >= 1000 ? Math.round(v).toLocaleString() : v.toFixed(2); })()}
                </span></span>
                <span>Mkt Value: <span className="text-gray-700 font-medium">
                  {item.current_price != null
                    ? (() => { const v = item.current_price * item.shares; return v >= 1000 ? Math.round(v).toLocaleString() : v.toFixed(2); })()
                    : "—"}
                </span></span>
              </div>
              <div className="flex items-center justify-between text-xs text-gray-400">
                <span>Avg cost: <span className="text-gray-600">{item.avg_cost.toFixed(2)}</span></span>
                <span className="flex items-center gap-1.5">
                  <Link href={`/stock/${encodeURIComponent(sym)}`}>
                    <span
                      className={`inline-block w-2 h-2 rounded-full ${freshnessColor(item.analyzed_at)} hover:scale-125 transition-transform`}
                      title={freshnessTitle(item.analyzed_at)}
                    />
                  </Link>
                  {formatDate(item.analyzed_at)}
                </span>
              </div>
              <div className="flex gap-3 pt-1 border-t border-gray-100 items-center">
                <button
                  onClick={() => handleToggleSwap(sym, !item.allow_swap)}
                  disabled={!!state}
                  title={item.allow_swap ? "Unlocked — can be swapped" : "Locked — won't be swapped"}
                  className="text-base leading-none disabled:opacity-40"
                >
                  {state === "toggle" ? "…" : item.allow_swap ? "🔓" : "🔒"}
                </button>
                <button onClick={() => handleReanalyze(sym)} disabled={!!state}
                  className="text-blue-500 hover:text-blue-700 text-sm font-medium disabled:opacity-40">
                  {state === "reanalyze" ? "Analyzing…" : "Re-analyze"}
                </button>
                <button onClick={() => handleRemove(sym)} disabled={!!state}
                  className="text-red-500 hover:text-red-700 text-sm disabled:opacity-40 ml-auto">
                  {state === "remove" ? "Removing…" : "Remove"}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* ── Desktop table (≥ md) ── */}
      <div className="hidden md:block overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            {table.getHeaderGroups().map((hg) => (
              <tr key={hg.id} className="border-b text-left text-gray-500">
                {hg.headers.map((header) => (
                  <th key={header.id}
                    className={`py-2 pr-4 font-medium whitespace-nowrap ${header.column.getCanSort() ? "cursor-pointer hover:text-gray-800 select-none" : ""}`}
                    onClick={header.column.getToggleSortingHandler()}>
                    {flexRender(header.column.columnDef.header, header.getContext())}
                    <SortIcon column={header.column} />
                  </th>
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {sortedRows.map((row) => (
              <tr key={row.id} className="border-b hover:bg-gray-50">
                {row.getVisibleCells().map((cell) => (
                  <td key={cell.id} className="py-2 pr-4">
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
