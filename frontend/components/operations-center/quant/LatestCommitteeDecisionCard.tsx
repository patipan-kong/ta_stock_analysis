"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  listOptimizerHistory,
  getOptimizerHistory,
  type OptimizerResult,
  type TargetAllocation,
} from "@/lib/api";

// ── Constants ─────────────────────────────────────────────────────────────────

const FOLLOWING_LABEL: Record<string, string> = {
  layer1:    "Strategist",
  layer2:    "Challenger",
  neither:   "No Clear Winner",
  no_action: "No Action",
  fallback:  "Fallback",
};

const ACTION_ORDER = ["SELL", "REDUCE", "BUY", "ACCUMULATE"];
const ACTION_STYLE: Record<string, { bg: string; text: string }> = {
  BUY:        { bg: "bg-emerald-100 border-emerald-300", text: "text-emerald-800" },
  ACCUMULATE: { bg: "bg-teal-100 border-teal-300",       text: "text-teal-800" },
  REDUCE:     { bg: "bg-amber-100 border-amber-300",     text: "text-amber-800" },
  SELL:       { bg: "bg-red-100 border-red-300",         text: "text-red-800" },
};

const CONFIDENCE_COLOR = (score: number) =>
  score >= 70 ? "text-emerald-600" : score >= 40 ? "text-amber-600" : "text-red-500";

function timeAgo(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60)    return "just now";
  if (diff < 3600)  return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function extractActions(allocations: TargetAllocation[]): TargetAllocation[] {
  return allocations
    .filter((a) => ACTION_ORDER.includes((a.action ?? "").toUpperCase()))
    .sort(
      (a, b) =>
        ACTION_ORDER.indexOf((a.action ?? "").toUpperCase()) -
        ACTION_ORDER.indexOf((b.action ?? "").toUpperCase()),
    );
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function LatestCommitteeDecisionCard({
  portfolioId,
}: {
  portfolioId: number;
}) {
  const [result, setResult] = useState<OptimizerResult | null>(null);
  const [historyId, setHistoryId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(false);

    listOptimizerHistory(portfolioId)
      .then((items) => {
        if (cancelled || items.length === 0) {
          if (!cancelled) setLoading(false);
          return;
        }
        const latest = items[0];
        setHistoryId(latest.id);
        return getOptimizerHistory(latest.id);
      })
      .then((detail) => {
        if (!cancelled && detail) setResult(detail);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [portfolioId]);

  const optimizerHref = historyId != null
    ? `/optimizer?history=${historyId}`
    : "/optimizer?view=latest";

  // ── Loading ────────────────────────────────────────────────────────────────
  if (loading) {
    return (
      <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm animate-pulse">
        <div className="h-3 w-40 bg-gray-200 rounded mb-3" />
        <div className="h-5 w-56 bg-gray-200 rounded mb-2" />
        <div className="flex gap-2">
          <div className="h-6 w-20 bg-gray-200 rounded-full" />
          <div className="h-6 w-24 bg-gray-200 rounded-full" />
          <div className="h-6 w-16 bg-gray-200 rounded-full" />
        </div>
      </div>
    );
  }

  // ── Error or no data ───────────────────────────────────────────────────────
  if (error || !result) {
    return (
      <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2">
          Latest Committee Decision
        </p>
        <p className="text-sm text-gray-500">No Committee Decision Yet</p>
        <p className="text-xs text-gray-400 mt-1">
          Run the Optimizer to generate recommendations.
        </p>
        <Link
          href="/optimizer"
          className="inline-block mt-3 text-xs font-semibold text-blue-600 hover:underline"
        >
          Open Optimizer →
        </Link>
      </div>
    );
  }

  const consensus = result.consensus;
  const allocations = result.target_allocations ?? [];
  const actionItems = extractActions(allocations);
  const displayItems = actionItems.slice(0, 3);
  const overflow = actionItems.length - displayItems.length;
  const following = consensus?.recommended
    ? (FOLLOWING_LABEL[consensus.recommended] ?? consensus.recommended)
    : null;
  const confidence = consensus?.consensus_strength_score ?? null;
  const analyzedAt = result.analyzed_at;

  return (
    <div className="rounded-2xl border border-gray-200 bg-white p-4 shadow-sm space-y-3">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-widest">
          Latest Committee Decision
        </p>
        {analyzedAt && (
          <span className="text-[11px] text-gray-400">{timeAgo(analyzedAt)}</span>
        )}
      </div>

      {/* Meta row: Following + Confidence */}
      <div className="flex items-center flex-wrap gap-x-5 gap-y-1 text-xs">
        {following && (
          <span className="text-gray-600">
            Following{" "}
            <span className="font-bold text-gray-900">{following}</span>
          </span>
        )}
        {confidence != null && (
          <span className="text-gray-600">
            Confidence{" "}
            <span className={`font-bold ${CONFIDENCE_COLOR(confidence)}`}>
              {confidence}
            </span>
          </span>
        )}
      </div>

      {/* Action pills */}
      {displayItems.length > 0 ? (
        <div className="flex flex-wrap gap-2 items-center">
          {displayItems.map((a) => {
            const action = (a.action ?? "").toUpperCase();
            const style = ACTION_STYLE[action] ?? { bg: "bg-gray-100 border-gray-300", text: "text-gray-700" };
            return (
              <span
                key={`${a.symbol}-${action}`}
                className={`inline-flex items-center gap-1 text-xs font-semibold px-2.5 py-1 rounded-full border ${style.bg} ${style.text}`}
              >
                <span className="opacity-70">{action}</span>
                <span>{a.symbol.replace(".BK", "")}</span>
              </span>
            );
          })}
          {overflow > 0 && (
            <span className="text-xs text-gray-400">+{overflow} more</span>
          )}
        </div>
      ) : (
        <p className="text-xs text-gray-400">No actionable positions</p>
      )}

      {/* Footer: run ID + link */}
      <div className="flex items-center justify-between pt-2 border-t border-gray-100 flex-wrap gap-2">
        <span className="text-[11px] text-gray-400">
          {historyId != null ? `Run #${historyId}` : ""}
          {historyId != null && analyzedAt ? " • " : ""}
          {analyzedAt
            ? new Date(analyzedAt).toLocaleString("en-GB", {
                day: "2-digit", month: "short",
                hour: "2-digit", minute: "2-digit",
              })
            : ""}
        </span>
        <Link
          href={optimizerHref}
          className="inline-flex items-center gap-1 text-xs font-semibold text-blue-600 hover:text-blue-800 hover:underline"
        >
          Open Details →
        </Link>
      </div>
    </div>
  );
}
