"use client";

import { useState } from "react";
import { analyzePortfolioAll, startWatchlistAnalysisJob, streamAnalysisJob } from "@/lib/api";
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
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);

  async function handleClick() {
    if (phase !== "idle" || totalCount === 0) return;
    setPhase("running");
    setProgress(null);
    try {
      if (type === "watchlist") {
        // POST to start background job — returns immediately with job_id
        const { job_id, stale } = await startWatchlistAnalysisJob();
        setProgress({ done: 0, total: stale });

        let analyzed = 0;
        let skipped = 0;
        let fallbacks = 0;
        for await (const event of streamAnalysisJob(job_id)) {
          if (event.type === "start") {
            setProgress({ done: 0, total: event.stale });
          } else if (event.type === "progress") {
            setProgress({ done: event.done, total: event.total });
          } else if (event.type === "complete") {
            analyzed  = event.analyzed;
            skipped   = event.skipped;
            fallbacks = event.fallbacks;
          }
        }
        const fallbackNote = fallbacks > 0 ? ` (${fallbacks} fallback${fallbacks > 1 ? "s" : ""})` : "";
        setDoneMsg(`${analyzed} updated, ${skipped} from cache${fallbackNote}`);
        setPhase("done");
        onComplete({ total: totalCount, analyzed, skipped, results: [], skipped_symbols: [] });
      } else {
        const result = await analyzePortfolioAll(portfolioId!);
        setDoneMsg(`${result.analyzed} updated, ${result.skipped} from cache`);
        setPhase("done");
        onComplete(result);
      }
      setTimeout(() => { setPhase("idle"); setProgress(null); }, 3000);
    } catch {
      setPhase("idle");
      setProgress(null);
    }
  }

  if (phase === "running") {
    const label = progress
      ? `${progress.done}/${progress.total} analyzed…`
      : staleCount > 0
      ? `Analyzing (${staleCount})…`
      : "Analyzing…";
    return (
      <button disabled className="flex items-center gap-1.5 text-sm border border-blue-300 text-blue-500 rounded-lg px-3 py-1.5 opacity-80 cursor-not-allowed">
        <span className="animate-spin inline-block leading-none">⟳</span>
        {label}
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
