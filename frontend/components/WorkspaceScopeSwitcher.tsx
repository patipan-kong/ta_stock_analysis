"use client";

// M36.1 Phase 3 — the single Workspace-Scope interaction contract. Every
// surface that lets a human change Current Selection (M36-WP1 §9) renders
// through this component instead of duplicating switching logic. It only
// ever reads/writes PortfolioContext state — it never fetches, and it never
// selects a portfolio on its own (no default, no first-item, no recent-item).

import { useEffect, useRef, useState } from "react";
import { usePortfolio } from "@/lib/PortfolioContext";
import { resolveActiveLabel } from "@/lib/workspaceScopeSwitcher";

interface WorkspaceScopeSwitcherProps {
  /** "dropdown": button + popover menu. "list": flat inline buttons (e.g. a mobile panel). "select": native <select>. */
  variant?: "dropdown" | "list" | "select";
  /** Heading shown above the options in "dropdown" variant. */
  label?: string;
  /** Label for the explicit NONE option. */
  noneLabel?: string;
  /** When set, rendered in place of the switcher if there are zero portfolios. Omit to render nothing (matches prior no-portfolios behavior). */
  emptyLabel?: string;
  className?: string;
  buttonClassName?: string;
}

export default function WorkspaceScopeSwitcher({
  variant = "dropdown",
  label = "Select portfolio",
  noneLabel = "None selected",
  emptyLabel,
  className = "",
  buttonClassName = "",
}: WorkspaceScopeSwitcherProps) {
  const { portfolios, currentSelection, selectPortfolio, clearSelection } = usePortfolio();
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (variant !== "dropdown") return;
    function onMouseDown(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", onMouseDown);
    return () => document.removeEventListener("mousedown", onMouseDown);
  }, [variant]);

  if (portfolios.length === 0) {
    return emptyLabel ? <span className={`text-sm text-gray-400 ${className}`}>{emptyLabel}</span> : null;
  }

  if (variant === "select") {
    return (
      <select
        value={currentSelection ?? ""}
        onChange={(e) => {
          const raw = e.target.value;
          if (raw === "") {
            clearSelection();
          } else {
            selectPortfolio(parseInt(raw, 10));
          }
        }}
        className={className || "text-sm border rounded px-2.5 py-1.5 bg-white"}
      >
        <option value="">{noneLabel}</option>
        {portfolios.map((p) => (
          <option key={p.id} value={p.id}>{p.name}</option>
        ))}
      </select>
    );
  }

  const options = (
    <>
      <button
        onClick={() => { clearSelection(); setOpen(false); }}
        className={`flex items-center w-full px-4 py-2 text-sm transition-colors ${
          currentSelection === null ? "bg-blue-50 text-blue-700 font-medium" : "text-gray-500 italic hover:bg-gray-50"
        }`}
      >
        {currentSelection === null && <span className="mr-2 text-blue-500">✓</span>}
        {noneLabel}
      </button>
      {portfolios.map((p) => (
        <button
          key={p.id}
          onClick={() => { selectPortfolio(p.id); setOpen(false); }}
          className={`flex items-center w-full px-4 py-2 text-sm transition-colors ${
            p.id === currentSelection ? "bg-blue-50 text-blue-700 font-medium" : "text-gray-700 hover:bg-gray-50"
          }`}
        >
          {p.id === currentSelection && <span className="mr-2 text-blue-500">✓</span>}
          <span className="truncate">{p.name}</span>
        </button>
      ))}
    </>
  );

  if (variant === "list") {
    return <div className={className}>{options}</div>;
  }

  const activeName = resolveActiveLabel(portfolios, currentSelection, noneLabel);

  return (
    <div className={`relative ${className}`} ref={containerRef}>
      <button
        onClick={() => setOpen((o) => !o)}
        className={
          buttonClassName ||
          "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-800 transition-colors max-w-[160px]"
        }
      >
        <span className={`truncate ${currentSelection === null ? "italic text-gray-400" : ""}`}>{activeName}</span>
        <span className="text-xs text-gray-400 shrink-0">{open ? "▲" : "▼"}</span>
      </button>
      {open && (
        <div className="absolute right-0 mt-1.5 w-48 bg-white border border-gray-200 rounded-xl shadow-lg py-1.5 z-50">
          <p className="px-4 pb-1 pt-0.5 text-xs font-semibold text-gray-400 uppercase tracking-wider">{label}</p>
          {options}
        </div>
      )}
    </div>
  );
}
