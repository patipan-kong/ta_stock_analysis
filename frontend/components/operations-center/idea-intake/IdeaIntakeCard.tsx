"use client";

import { useCallback, useState } from "react";
import {
  reviewIdeas,
  type IdeaReview,
  type IdeaReviewPortfolioContext,
} from "@/lib/api";
import IdeaReviewResult from "./IdeaReviewResult";

const PERSONA_LABELS: Record<string, string> = {
  BALANCED:  "Balanced",
  GROWTH:    "Growth",
  VALUE:     "Value",
  DIVIDEND:  "Dividend",
  MOMENTUM:  "Momentum",
  PASSIVE:   "Passive",
};

const PLACEHOLDER = `BH
NVDA01
GOOGL01
MICRON01`;

function parseSymbols(raw: string): string[] {
  return raw
    .split(/[\n,\s]+/)
    .map((s) => s.trim().toUpperCase())
    .filter(Boolean);
}

function PortfolioConstructionWarning({ reviews }: { reviews: IdeaReview[] }) {
  const approved = reviews.filter((r) => r.committee_decision === "APPROVE" && r.sector);

  // Group approved ideas by sector
  const bySector = approved.reduce<
    Record<string, { count: number; symbols: string[]; sector_current_pct: number; sector_limit_pct: number }>
  >((acc, r) => {
    const sec = r.sector!;
    if (!acc[sec]) {
      acc[sec] = {
        count: 0,
        symbols: [],
        sector_current_pct: r.sector_current_pct,
        sector_limit_pct: r.sector_limit_pct,
      };
    }
    acc[sec].count += 1;
    acc[sec].symbols.push(r.symbol);
    return acc;
  }, {});

  const warnings = Object.entries(bySector).filter(([, g]) => g.count >= 2);
  if (warnings.length === 0) return null;

  return (
    <div className="space-y-2">
      {warnings.map(([sector, g]) => (
        <div
          key={sector}
          className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-2.5 space-y-1.5"
        >
          <p className="text-xs font-semibold text-amber-800">
            ⚠ Portfolio Construction Warning
          </p>
          <p className="text-[11px] text-amber-700 leading-relaxed">
            <span className="font-semibold">{g.count} approved ideas</span> belong to{" "}
            <span className="font-semibold">{sector}</span> —{" "}
            {g.symbols.join(", ")}
          </p>
          <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-[10px] font-mono text-amber-700">
            <span>
              Current {sector} exposure:{" "}
              <span className="font-semibold">{g.sector_current_pct.toFixed(1)}%</span>
            </span>
            <span>
              Sector limit:{" "}
              <span className="font-semibold">{g.sector_limit_pct.toFixed(0)}%</span>
            </span>
          </div>
          <p className="text-[10px] text-amber-600 leading-relaxed">
            Executing multiple approved ideas together may significantly increase sector
            concentration. Review cumulative portfolio impact before executing all positions.
          </p>
        </div>
      ))}
    </div>
  );
}

function ContextStrip({ ctx }: { ctx: IdeaReviewPortfolioContext }) {
  const fmtDate = (iso: string | null) => {
    if (!iso) return null;
    try {
      return new Date(iso).toLocaleDateString("th-TH", {
        day: "numeric", month: "short", year: "2-digit",
      });
    } catch {
      return null;
    }
  };

  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-gray-500 font-mono">
      <span>
        Persona:{" "}
        <span className="text-gray-700 font-semibold">
          {PERSONA_LABELS[ctx.persona] ?? ctx.persona}
        </span>
      </span>
      {ctx.regime && (
        <span>
          Regime: <span className="text-gray-700 font-semibold">{ctx.regime}</span>
        </span>
      )}
      {ctx.emergency_active && (
        <span className="text-red-600 font-semibold">EMERGENCY ACTIVE</span>
      )}
      {ctx.last_optimizer_run_at && (
        <span>
          Last optimizer run:{" "}
          <span className="text-gray-700">{fmtDate(ctx.last_optimizer_run_at)}</span>
        </span>
      )}
    </div>
  );
}

export default function IdeaIntakeCard({ portfolioId }: { portfolioId: number }) {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reviews, setReviews] = useState<IdeaReview[] | null>(null);
  const [ctx, setCtx] = useState<IdeaReviewPortfolioContext | null>(null);

  const handleReview = useCallback(async () => {
    const symbols = parseSymbols(input);
    if (symbols.length === 0) return;
    if (symbols.length > 10) {
      setError("Maximum 10 symbols per review");
      return;
    }
    setLoading(true);
    setError(null);
    setReviews(null);
    setCtx(null);
    try {
      const res = await reviewIdeas(portfolioId, symbols);
      if (res.error) {
        setError(res.error);
      } else {
        setReviews(res.reviews);
        setCtx(res.portfolio_context);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Review failed");
    } finally {
      setLoading(false);
    }
  }, [input, portfolioId]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        handleReview();
      }
    },
    [handleReview],
  );

  const symbolCount = parseSymbols(input).length;

  return (
    <div className="rounded-2xl border-2 border-gray-200 bg-white p-5 space-y-4">
      {/* Header */}
      <div>
        <h3 className="text-sm font-bold text-gray-900">Today&apos;s Investment Ideas</h3>
        <p className="text-xs text-gray-400 mt-0.5">
          Enter symbols (one per line or comma-separated) — the AI Committee evaluates each against your portfolio
        </p>
      </div>

      {/* Input area */}
      <div className="space-y-2">
        <textarea
          className="w-full h-28 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm font-mono
                     text-gray-800 placeholder:text-gray-300 focus:outline-none focus:ring-2
                     focus:ring-blue-300 resize-none"
          placeholder={PLACEHOLDER}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
          spellCheck={false}
        />
        <div className="flex items-center justify-between gap-3">
          <p className="text-[10px] text-gray-400">
            {symbolCount > 0
              ? `${symbolCount} symbol${symbolCount > 1 ? "s" : ""} detected · Ctrl+Enter to review`
              : "Ctrl+Enter to review"}
          </p>
          <button
            onClick={handleReview}
            disabled={loading || symbolCount === 0}
            className="flex items-center gap-1.5 rounded-lg bg-gray-900 px-4 py-1.5 text-xs font-semibold
                       text-white transition hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <span className="inline-block h-3 w-3 rounded-full border-2 border-white border-t-transparent animate-spin" />
                Reviewing…
              </>
            ) : (
              "Review With AI Committee"
            )}
          </button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          {error}
        </div>
      )}

      {/* Results */}
      {reviews !== null && !loading && (
        <div className="space-y-3">
          {ctx && <ContextStrip ctx={ctx} />}
          <PortfolioConstructionWarning reviews={reviews} />

          {reviews.length === 0 ? (
            <p className="text-xs text-gray-400 italic">No symbols to review</p>
          ) : (
            <>
              {/* Top-level banner when one or more symbols lack analysis data */}
              {(() => {
                const missingCount = reviews.filter((r) => !r.data_available).length;
                if (missingCount === 0) return null;
                const symbols = reviews
                  .filter((r) => !r.data_available)
                  .map((r) => r.symbol)
                  .join(", ");
                return (
                  <div className="rounded-lg border border-orange-300 bg-orange-50 px-3 py-2.5 space-y-1">
                    <p className="text-xs font-semibold text-orange-800">
                      ⚠ AI Committee ยังไม่มีข้อมูลวิเคราะห์สำหรับ {missingCount} หุ้น
                    </p>
                    <p className="text-[11px] text-orange-700 font-mono">{symbols}</p>
                    <p className="text-[10px] text-orange-600 leading-relaxed">
                      กรุณาไปที่หน้า Stock Analysis เพื่อรันการวิเคราะห์ก่อน
                      แล้วกลับมา Review ใหม่อีกครั้ง
                    </p>
                  </div>
                );
              })()}

              <div className="grid grid-cols-1 gap-3">
                {reviews.map((r) => (
                  <IdeaReviewResult key={r.symbol} review={r} />
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
