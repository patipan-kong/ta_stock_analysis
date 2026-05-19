"use client";

import { useState } from "react";
import { analyzePortfolioAll, analyzeWatchlistAll } from "@/lib/api";
import type { AnalyzeAllResult } from "@/lib/api";

interface Props {
  type: "portfolio" | "watchlist";
  portfolioId?: number;
  staleCount: number;
  totalCount: number;
  onComplete: (result: AnalyzeAllResult) => void;
}

export default function AnalyzeAllButton({ type, portfolioId, staleCount, totalCount, onComplete }: Props) {
  const [phase, setPhase] = useState<"idle" | "running" | "done">("idle");
  const [doneMsg, setDoneMsg] = useState("");

  async function handleClick() {
    if (phase !== "idle" || totalCount === 0) return;
    setPhase("running");
    try {
      const result = type === "portfolio"
        ? await analyzePortfolioAll(portfolioId!)
        : await analyzeWatchlistAll();
      setDoneMsg(`${result.analyzed} updated, ${result.skipped} from cache`);
      setPhase("done");
      onComplete(result);
      setTimeout(() => setPhase("idle"), 3000);
    } catch {
      setPhase("idle");
    }
  }

  if (phase === "running") {
    return (
      <button disabled className="flex items-center gap-1.5 text-sm border border-blue-300 text-blue-500 rounded-lg px-3 py-1.5 opacity-80 cursor-not-allowed">
        <span className="animate-spin inline-block leading-none">⟳</span>
        Analyzing {staleCount > 0 ? `(${staleCount})` : ""}…
      </button>
    );
  }

  if (phase === "done") {
    return (
      <button disabled className="flex items-center gap-1.5 text-sm border border-green-300 text-green-600 rounded-lg px-3 py-1.5 cursor-default">
        ✓ Done — {doneMsg}
      </button>
    );
  }

  return (
    <div className="flex items-center gap-2">
      {staleCount > 0 && (
        <span className="text-xs text-gray-400 hidden sm:block">{staleCount} need update</span>
      )}
      <button
        onClick={handleClick}
        disabled={totalCount === 0}
        className="flex items-center gap-1.5 text-sm border border-blue-300 text-blue-600 rounded-lg px-3 py-1.5 hover:bg-blue-50 disabled:opacity-40 transition-colors"
      >
        ▶ Analyze All
      </button>
    </div>
  );
}
