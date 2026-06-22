"use client";

import { useState, useCallback } from "react";
import {
  reviewIdeas,
  suggestAllocation,
  suggestPositionSizes,
  type IdeaReview,
  type IdeaReviewPortfolioContext,
  type PortfolioConstructionResult,
  type PositionSizingResult,
  type BasketSimulationResult,
} from "@/lib/api";
import IdeaIntakeCard from "../idea-intake/IdeaIntakeCard";
import BasketSimulationCard from "../basket-simulation/BasketSimulationCard";
import PortfolioConstructionCard from "../portfolio-construction/PortfolioConstructionCard";
import PositionSizingCard from "../position-sizing/PositionSizingCard";

// ─── Types ────────────────────────────────────────────────────────────────────

type WorkspaceStep = "idle" | "reviewing" | "constructing" | "sizing" | "done";

// ─── Colour maps ──────────────────────────────────────────────────────────────

const DECISION_STYLE: Record<string, string> = {
  APPROVE: "bg-emerald-100 text-emerald-800 border-emerald-200",
  WATCH:   "bg-blue-100 text-blue-800 border-blue-200",
  REVIEW:  "bg-amber-100 text-amber-800 border-amber-200",
  DECLINE: "bg-red-100 text-red-800 border-red-200",
};

const SIGNAL_STYLE: Record<string, string> = {
  ACCUMULATE: "text-emerald-700",
  BUY:        "text-emerald-600",
  WATCH:      "text-blue-600",
  HOLD:       "text-gray-500",
  REDUCE:     "text-amber-700",
  SELL:       "text-red-700",
};

const STATUS_BORDER: Record<string, string> = {
  PASS:    "border-emerald-200 bg-emerald-50 text-emerald-800",
  WARNING: "border-amber-200 bg-amber-50 text-amber-800",
  FAIL:    "border-red-200 bg-red-50 text-red-800",
};

const STATUS_DOT: Record<string, string> = {
  PASS:    "bg-emerald-500",
  WARNING: "bg-amber-500",
  FAIL:    "bg-red-500",
};

// ─── Helpers ──────────────────────────────────────────────────────────────────

const STATUS_RANK: Record<string, number> = { PASS: 2, WARNING: 1, FAIL: 0 };

function worstStatus(a: string, b: string): string {
  return (STATUS_RANK[a] ?? 2) <= (STATUS_RANK[b] ?? 2) ? a : b;
}

function parseSymbols(raw: string): string[] {
  return raw
    .split(/[\n,\s]+/)
    .map((s) => s.trim().toUpperCase())
    .filter(Boolean);
}

// ─── Progress strip ───────────────────────────────────────────────────────────

const STAGES = [
  { key: "reviewing",    label: "Committee" },
  { key: "constructing", label: "Impact" },
  { key: "sizing",       label: "Position Sizing" },
];
const STAGE_ORDER: WorkspaceStep[] = ["reviewing", "constructing", "sizing", "done"];

function ProgressStrip({ step }: { step: WorkspaceStep }) {
  const currentIdx = STAGE_ORDER.indexOf(step);
  return (
    <div className="flex items-center gap-1">
      {STAGES.map((stage, i) => {
        const done = currentIdx > i;
        const active = !done && currentIdx === i;
        return (
          <div key={stage.key} className="flex items-center gap-1">
            {i > 0 && (
              <div className={`h-px w-5 shrink-0 ${done ? "bg-emerald-300" : "bg-gray-200"}`} />
            )}
            <div
              className={`flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-semibold whitespace-nowrap ${
                done
                  ? "bg-emerald-100 text-emerald-800"
                  : active
                  ? "bg-gray-900 text-white"
                  : "bg-gray-100 text-gray-400"
              }`}
            >
              {done && <span>✓</span>}
              {active && (
                <span className="inline-block h-2 w-2 rounded-full border-2 border-white border-t-transparent animate-spin" />
              )}
              <span>{stage.label}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ─── Section 1: Committee Summary ────────────────────────────────────────────

function CommitteeSummary({
  reviews,
  ctx,
}: {
  reviews: IdeaReview[];
  ctx: IdeaReviewPortfolioContext | null;
}) {
  const noData = reviews.filter((r) => !r.data_available);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <h4 className="text-[11px] font-bold text-gray-500 uppercase tracking-wide">
          1 · Committee
        </h4>
        {ctx && (
          <span className="text-[10px] text-gray-400 font-mono">
            {ctx.persona}
            {ctx.regime ? ` · ${ctx.regime}` : ""}
            {ctx.emergency_active ? " · EMERGENCY ACTIVE" : ""}
          </span>
        )}
      </div>

      {noData.length > 0 && (
        <div className="rounded-lg border border-orange-200 bg-orange-50 px-3 py-2 text-[11px] text-orange-700">
          ⚠ No analysis data for:{" "}
          <span className="font-mono font-semibold">
            {noData.map((r) => r.symbol).join(", ")}
          </span>{" "}
          — run Stock Analysis first
        </div>
      )}

      <div className="rounded-xl border border-gray-200 overflow-hidden">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-100">
              <th className="px-3 py-2 text-left text-[10px] font-semibold text-gray-500 uppercase tracking-wide">
                Symbol
              </th>
              <th className="px-3 py-2 text-left text-[10px] font-semibold text-gray-500 uppercase tracking-wide">
                Decision
              </th>
              <th className="px-3 py-2 text-left text-[10px] font-semibold text-gray-500 uppercase tracking-wide">
                Signal
              </th>
              <th className="px-3 py-2 text-right text-[10px] font-semibold text-gray-500 uppercase tracking-wide">
                Fit
              </th>
              <th className="px-3 py-2 text-left text-[10px] font-semibold text-gray-500 uppercase tracking-wide">
                Priority
              </th>
            </tr>
          </thead>
          <tbody>
            {reviews.map((r, i) => (
              <tr
                key={r.symbol}
                className={`border-b border-gray-50 last:border-0 ${
                  i % 2 === 0 ? "bg-white" : "bg-gray-50/30"
                }`}
              >
                <td className="px-3 py-2.5 font-mono font-semibold text-gray-800 text-xs">
                  {r.symbol}
                </td>
                <td className="px-3 py-2.5">
                  <span
                    className={`rounded-full px-2 py-0.5 text-[9px] font-bold border ${
                      DECISION_STYLE[r.committee_decision] ??
                      "bg-gray-100 text-gray-600 border-gray-200"
                    }`}
                  >
                    {r.committee_decision}
                  </span>
                </td>
                <td
                  className={`px-3 py-2.5 text-[11px] font-semibold ${
                    r.existing_signal
                      ? (SIGNAL_STYLE[r.existing_signal] ?? "text-gray-500")
                      : "text-gray-300"
                  }`}
                >
                  {r.existing_signal ?? "—"}
                </td>
                <td className="px-3 py-2.5 text-right font-mono text-gray-600 text-[11px]">
                  {r.data_available ? `${r.strategic_fit_score.toFixed(0)}/10` : "—"}
                </td>
                <td className="px-3 py-2.5">
                  <span
                    className={`text-[10px] font-semibold ${
                      r.portfolio_priority === "HIGH"
                        ? "text-emerald-600"
                        : r.portfolio_priority === "MEDIUM"
                        ? "text-blue-600"
                        : "text-gray-400"
                    }`}
                  >
                    {r.portfolio_priority}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Section 2: Portfolio Impact ──────────────────────────────────────────────

function PortfolioImpact({ sim }: { sim: BasketSimulationResult }) {
  const moved = sim.impacts.filter((im) => Math.abs(im.delta_pct) > 0.01);

  return (
    <div className="space-y-3">
      <h4 className="text-[11px] font-bold text-gray-500 uppercase tracking-wide">
        2 · Portfolio Impact
      </h4>

      {/* Cash bar */}
      <div className="rounded-xl border border-gray-200 bg-gray-50 px-4 py-3 flex items-center justify-between">
        <span className="text-xs text-gray-500">Cash</span>
        <div className="flex items-center gap-2 font-mono text-sm">
          <span className="text-gray-400">{sim.cash_before_pct.toFixed(1)}%</span>
          <span className="text-gray-300">→</span>
          <span
            className={`font-bold ${
              sim.cash_after_pct < 5 ? "text-amber-700" : "text-gray-800"
            }`}
          >
            {sim.cash_after_pct.toFixed(1)}%
          </span>
          {sim.cash_after_pct < 5 && (
            <span className="text-[9px] font-bold text-amber-600">LOW</span>
          )}
        </div>
      </div>

      {/* Sector bars */}
      {moved.length > 0 && (
        <div className="space-y-2.5">
          {moved.map((impact) => {
            const fillPct = Math.min(
              100,
              impact.sector_limit_pct > 0
                ? (impact.after_pct / impact.sector_limit_pct) * 100
                : 0,
            );
            const isFail = impact.status === "FAIL";
            const isWarn = impact.status === "WARNING";
            return (
              <div key={impact.sector} className="space-y-1">
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-gray-600">{impact.sector}</span>
                  <div className="flex items-center gap-1.5 font-mono">
                    <span className="text-gray-400">{impact.before_pct.toFixed(1)}%</span>
                    <span className="text-gray-300">→</span>
                    <span
                      className={`font-bold ${
                        isFail
                          ? "text-red-700"
                          : isWarn
                          ? "text-amber-700"
                          : "text-gray-800"
                      }`}
                    >
                      {impact.after_pct.toFixed(1)}%
                    </span>
                    {isFail && (
                      <span className="text-[9px] font-bold text-red-600">BREACH</span>
                    )}
                    {isWarn && (
                      <span className="text-[9px] font-bold text-amber-600">NEAR LIMIT</span>
                    )}
                  </div>
                </div>
                <div className="h-1.5 rounded-full bg-gray-100">
                  <div
                    className={`h-1.5 rounded-full transition-all ${
                      isFail ? "bg-red-400" : isWarn ? "bg-amber-400" : "bg-blue-400"
                    }`}
                    style={{ width: `${fillPct}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Warnings */}
      {sim.warnings.length > 0 && (
        <div className="space-y-1">
          {sim.warnings.map((w, i) => (
            <p key={i} className="text-[11px] text-amber-700 flex items-start gap-1.5">
              <span className="shrink-0">⚠</span>
              <span>{w}</span>
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Section 3: Suggested Allocation ─────────────────────────────────────────

function SuggestedAllocation({ sizing }: { sizing: PositionSizingResult }) {
  const maxPct = Math.max(...sizing.suggestions.map((s) => s.suggested_pct), 0.01);

  return (
    <div className="space-y-3">
      <h4 className="text-[11px] font-bold text-gray-500 uppercase tracking-wide">
        3 · Suggested Allocation
      </h4>

      {sizing.suggestions.length === 0 ? (
        <p className="text-xs text-gray-400 italic">No positions to size.</p>
      ) : (
        <div className="space-y-3">
          {sizing.suggestions.map((s) => (
            <div key={s.symbol} className="space-y-1">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="font-mono font-semibold text-gray-800 text-xs">
                    {s.symbol}
                  </span>
                  <span
                    className={`text-[9px] font-semibold ${
                      SIGNAL_STYLE[s.signal] ?? "text-gray-400"
                    }`}
                  >
                    {s.signal}
                  </span>
                </div>
                <span className="font-mono font-bold text-emerald-700 text-sm">
                  {s.suggested_pct.toFixed(2)}%
                </span>
              </div>
              <div className="h-2 rounded-full bg-gray-100">
                <div
                  className="h-2 rounded-full bg-emerald-400"
                  style={{ width: `${(s.suggested_pct / maxPct) * 100}%` }}
                />
              </div>
            </div>
          ))}

          <div className="border-t border-gray-200 pt-2 flex items-center justify-between text-xs font-semibold text-gray-700">
            <span>Total</span>
            <span className="font-mono">{sizing.total_allocated_pct.toFixed(2)}%</span>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Section 4: Final Decision ────────────────────────────────────────────────

function FinalDecision({
  construction,
  sizing,
}: {
  construction: PortfolioConstructionResult;
  sizing: PositionSizingResult;
}) {
  const overall = worstStatus(construction.overall_status, sizing.status);
  const cashAfter = Math.max(
    0,
    construction.simulation.cash_before_pct - sizing.total_allocated_pct,
  );
  const reasonings = [...construction.reasoning, ...sizing.reasoning];

  return (
    <div className="space-y-3">
      <h4 className="text-[11px] font-bold text-gray-500 uppercase tracking-wide">
        4 · Final Decision
      </h4>

      <div className={`rounded-xl border-2 p-5 space-y-5 ${STATUS_BORDER[overall]}`}>
        {/* Status */}
        <div className="flex items-center gap-2.5">
          <div
            className={`h-3 w-3 rounded-full shrink-0 ${STATUS_DOT[overall]}`}
          />
          <span className="text-sm font-bold uppercase tracking-wide">{overall}</span>
        </div>

        {/* Numbers */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <p className="text-[10px] opacity-60 uppercase tracking-wide mb-1">
              Recommended Deployment
            </p>
            <p className="text-2xl font-bold font-mono">
              {sizing.total_allocated_pct.toFixed(2)}%
            </p>
          </div>
          <div>
            <p className="text-[10px] opacity-60 uppercase tracking-wide mb-1">
              Expected Cash Remaining
            </p>
            <p className="text-2xl font-bold font-mono">{cashAfter.toFixed(1)}%</p>
          </div>
        </div>

        {/* Reasoning */}
        {reasonings.length > 0 && (
          <div className="space-y-1 border-t border-current border-opacity-10 pt-3">
            {reasonings.map((line, i) => (
              <p key={i} className="text-[11px] opacity-75 leading-relaxed">
                · {line}
              </p>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Advanced Tools accordion ─────────────────────────────────────────────────

function AdvancedTools({ portfolioId }: { portfolioId: number }) {
  const [open, setOpen] = useState(false);

  return (
    <div className="border-t border-gray-100 pt-4">
      <button
        className="flex items-center gap-2 text-[11px] text-gray-400 hover:text-gray-600 transition-colors"
        onClick={() => setOpen((p) => !p)}
      >
        <span className="text-[9px]">{open ? "▼" : "▶"}</span>
        <span>Advanced Tools</span>
      </button>

      {open && (
        <div className="mt-4 space-y-4">
          <IdeaIntakeCard portfolioId={portfolioId} />
          <BasketSimulationCard portfolioId={portfolioId} />
          <PortfolioConstructionCard portfolioId={portfolioId} />
          <PositionSizingCard portfolioId={portfolioId} />
        </div>
      )}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

const PLACEHOLDER = `NVDA01\nGOOGL01\nMICRON01\nBH`;

export default function DecisionWorkspace({
  portfolioId,
}: {
  portfolioId: number;
}) {
  const [input, setInput] = useState("");
  const [step, setStep] = useState<WorkspaceStep>("idle");
  const [error, setError] = useState<string | null>(null);
  const [reviews, setReviews] = useState<IdeaReview[] | null>(null);
  const [portfolioCtx, setPortfolioCtx] = useState<IdeaReviewPortfolioContext | null>(null);
  const [construction, setConstruction] = useState<PortfolioConstructionResult | null>(null);
  const [sizing, setSizing] = useState<PositionSizingResult | null>(null);

  const handleAnalyze = useCallback(async () => {
    const symbols = parseSymbols(input);
    if (symbols.length === 0) return;
    if (symbols.length > 10) {
      setError("Maximum 10 symbols per analysis");
      return;
    }

    setError(null);
    setReviews(null);
    setPortfolioCtx(null);
    setConstruction(null);
    setSizing(null);

    try {
      setStep("reviewing");
      const reviewRes = await reviewIdeas(portfolioId, symbols);
      if (reviewRes.error) throw new Error(reviewRes.error);
      setReviews(reviewRes.reviews);
      setPortfolioCtx(reviewRes.portfolio_context);

      setStep("constructing");
      const constructionRes = await suggestAllocation(portfolioId, symbols);
      if (constructionRes.error) throw new Error(constructionRes.error);
      setConstruction(constructionRes);

      setStep("sizing");
      const sizingRes = await suggestPositionSizes(portfolioId, symbols);
      if (sizingRes.error) throw new Error(sizingRes.error);
      setSizing(sizingRes);

      setStep("done");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
      setStep("idle");
    }
  }, [input, portfolioId]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        handleAnalyze();
      }
    },
    [handleAnalyze],
  );

  const handleClear = useCallback(() => {
    setStep("idle");
    setReviews(null);
    setPortfolioCtx(null);
    setConstruction(null);
    setSizing(null);
    setError(null);
  }, []);

  const isLoading = step !== "idle" && step !== "done";
  const isDone = step === "done";
  const symbolCount = parseSymbols(input).length;

  return (
    <div className="rounded-2xl border-2 border-gray-900 bg-white p-6 space-y-5">
      {/* Header */}
      <div>
        <h3 className="text-sm font-bold text-gray-900">Decision Workspace</h3>
        <p className="text-xs text-gray-400 mt-0.5">
          Enter symbols once — committee review, portfolio impact, and position sizing in one click
        </p>
      </div>

      {/* Input */}
      <div className="space-y-2">
        <textarea
          className="w-full h-28 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm font-mono
                     text-gray-800 placeholder:text-gray-300 focus:outline-none focus:ring-2
                     focus:ring-gray-900 resize-none"
          placeholder={PLACEHOLDER}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          spellCheck={false}
        />
        <div className="flex items-center gap-3">
          <p className="text-[10px] text-gray-400 flex-1">
            {symbolCount > 0
              ? `${symbolCount} symbol${symbolCount !== 1 ? "s" : ""} · committee → impact → sizing → decision`
              : "Ctrl+Enter to analyze"}
          </p>
          {isDone && (
            <button
              onClick={handleClear}
              className="text-[10px] text-gray-400 hover:text-gray-600 transition-colors px-2 py-1"
            >
              Clear
            </button>
          )}
          <button
            onClick={handleAnalyze}
            disabled={isLoading || symbolCount === 0}
            className="flex items-center gap-1.5 rounded-lg bg-gray-900 px-5 py-2 text-xs font-semibold
                       text-white transition hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <>
                <span className="inline-block h-3 w-3 rounded-full border-2 border-white border-t-transparent animate-spin" />
                Analyzing…
              </>
            ) : (
              "Analyze Ideas"
            )}
          </button>
        </div>
      </div>

      {/* Progress (loading) */}
      {isLoading && (
        <div className="flex justify-center py-3">
          <ProgressStrip step={step} />
        </div>
      )}

      {/* Progress (done — compact summary) */}
      {isDone && (
        <div className="flex justify-start">
          <ProgressStrip step={step} />
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700">
          {error}
        </div>
      )}

      {/* Results */}
      {isDone && reviews && construction && sizing && (
        <div className="space-y-6 border-t border-gray-100 pt-5">
          <CommitteeSummary reviews={reviews} ctx={portfolioCtx} />
          <div className="border-t border-gray-100" />
          <PortfolioImpact sim={construction.simulation} />
          <div className="border-t border-gray-100" />
          <SuggestedAllocation sizing={sizing} />
          <div className="border-t border-gray-100" />
          <FinalDecision construction={construction} sizing={sizing} />
        </div>
      )}

      {/* Advanced Tools */}
      <AdvancedTools portfolioId={portfolioId} />
    </div>
  );
}
