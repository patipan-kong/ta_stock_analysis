"use client";

import { useEffect, useMemo, useState } from "react";
import {
  getShadowPerformanceSummary,
  getAttributionSummary,
  type ShadowPerformanceSummary,
  type AttributionSummaryResponse,
} from "@/lib/api";

/** Clamp to plausible return bounds — suppresses corrupted -100% values. */
function safeReturn(v: number | null | undefined): number | null {
  if (v == null) return null;
  if (v <= -99.5 || v > 999) return null;
  return v;
}

function fmtPct(v: number | null | undefined): string {
  const safe = safeReturn(v);
  if (safe == null) return "-";
  const sign = safe > 0 ? "+" : "";
  return `${sign}${safe.toFixed(2)}%`;
}

function pctClass(v: number | null | undefined): string {
  const safe = safeReturn(v);
  if (safe == null) return "text-gray-500";
  if (safe > 0) return "text-green-700";
  if (safe < 0) return "text-red-600";
  return "text-gray-500";
}

function MetricRow({ label, value, className }: { label: string; value: string; className?: string }) {
  return (
    <div className="flex items-center justify-between text-xs">
      <span className="text-gray-500">{label}</span>
      <span className={`font-semibold ${className ?? "text-gray-700"}`}>{value}</span>
    </div>
  );
}

export default function ShadowPortfolioPanel({ portfolioId }: { portfolioId: number }) {
  const [shadowSummary, setShadowSummary] = useState<ShadowPerformanceSummary | null>(null);
  const [attribution, setAttribution] = useState<AttributionSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    setLoading(true);
    Promise.all([
      getShadowPerformanceSummary(portfolioId),
      getAttributionSummary(portfolioId, 30),
    ])
      .then(([summary, attr]) => {
        if (!active) return;
        setShadowSummary(summary);
        setAttribution(attr);
      })
      .catch(() => {
        if (!active) return;
        setShadowSummary(null);
        setAttribution(null);
      })
      .finally(() => {
        if (!active) return;
        setLoading(false);
      });

    const onDecision = () => {
      Promise.all([
        getShadowPerformanceSummary(portfolioId),
        getAttributionSummary(portfolioId, 30),
      ])
        .then(([summary, attr]) => {
          setShadowSummary(summary);
          setAttribution(attr);
        })
        .catch(() => {
          setShadowSummary(null);
          setAttribution(null);
        });
    };

    window.addEventListener("execution-decision-recorded", onDecision);
    return () => {
      active = false;
      window.removeEventListener("execution-decision-recorded", onDecision);
    };
  }, [portfolioId]);

  const staticShadow = shadowSummary?.summary?.static_frozen ?? null;
  const aiModel = shadowSummary?.summary?.active_model ?? null;
  const actual = attribution?.current.actual ?? null;

  // A shadow is "tracking started" when it exists but has no valid return data yet
  // (e.g. inception_return_pct is null or corrupted, snapshot_count < 2)
  const staticIsNew =
    staticShadow != null &&
    safeReturn(staticShadow.inception_return_pct) == null &&
    (staticShadow.snapshot_count ?? 0) < 2;
  const aiIsNew =
    aiModel != null &&
    safeReturn(aiModel.inception_return_pct) == null &&
    (aiModel.snapshot_count ?? 0) < 2;

  const staticDivergence = useMemo(() => {
    const sr = safeReturn(staticShadow?.inception_return_pct);
    const ar = safeReturn(actual?.return_pct);
    if (sr == null || ar == null) return null;
    return sr - ar;
  }, [staticShadow, actual]);

  const aiDivergence = useMemo(() => {
    const air = safeReturn(aiModel?.inception_return_pct);
    const ar = safeReturn(actual?.return_pct);
    if (air == null || ar == null) return null;
    return air - ar;
  }, [aiModel, actual]);

  if (loading) {
    return (
      <section className="bg-white border border-gray-200 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-gray-800">Shadow Portfolio Tracking</h2>
        <p className="text-xs text-gray-400 mt-2">Loading shadow portfolios...</p>
      </section>
    );
  }

  if (!shadowSummary?.has_shadows) {
    return (
      <section className="bg-white border border-gray-200 rounded-xl p-5">
        <h2 className="text-sm font-semibold text-gray-800">Shadow Portfolio Tracking</h2>
        <p className="text-xs text-gray-400 mt-2">
          No active shadow portfolios yet. Record an optimizer decision to begin paper-trading lifecycle tracking.
        </p>
      </section>
    );
  }

  return (
    <section className="bg-white border border-gray-200 rounded-xl overflow-hidden">
      <div className="px-5 py-4 border-b border-gray-100">
        <h2 className="text-sm font-semibold text-gray-800">Shadow Portfolio Dashboard</h2>
        <p className="text-xs text-gray-400 mt-0.5">Counterfactual tracking for execution quality</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 p-5">
        <div className="border border-gray-200 rounded-lg p-4 bg-gray-50/50">
          <p className="text-xs uppercase tracking-wide text-gray-500">Static Shadow Portfolio</p>
          <p className="text-xs text-gray-400 mt-0.5">What if no rebalance happened?</p>
          {staticIsNew ? (
            <div className="mt-3 flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
              <span className="text-xs text-blue-600">Tracking started — first valuation at 17:45 ICT</span>
            </div>
          ) : (
            <div className="mt-3 space-y-2">
              <MetricRow
                label="Cumulative Return"
                value={fmtPct(staticShadow?.inception_return_pct)}
                className={pctClass(staticShadow?.inception_return_pct)}
              />
              <MetricRow
                label="Drawdown"
                value={fmtPct(attribution?.current.static_shadow?.max_drawdown_pct ?? null)}
                className="text-red-600"
              />
              <MetricRow
                label="Alpha"
                value={fmtPct(staticShadow?.latest_alpha)}
                className={pctClass(staticShadow?.latest_alpha)}
              />
              <MetricRow
                label="Divergence vs Actual"
                value={fmtPct(staticDivergence)}
                className={pctClass(staticDivergence)}
              />
            </div>
          )}
        </div>

        <div className="border border-gray-200 rounded-lg p-4 bg-blue-50/40">
          <p className="text-xs uppercase tracking-wide text-gray-500">AI Model Portfolio</p>
          <p className="text-xs text-gray-400 mt-0.5">
            Cumulative track record · since {aiModel?.inception_date ?? "—"}
          </p>
          {aiIsNew ? (
            <div className="mt-3 flex items-center gap-2">
              <span className="inline-block w-2 h-2 rounded-full bg-blue-400 animate-pulse" />
              <span className="text-xs text-blue-600">Tracking started — first valuation at 17:45 ICT</span>
            </div>
          ) : (
          <div className="mt-3 space-y-2">
            <MetricRow
              label="Cumulative Return"
              value={fmtPct(aiModel?.inception_return_pct)}
              className={pctClass(aiModel?.inception_return_pct)}
            />
            <MetricRow
              label="Drawdown"
              value={fmtPct(attribution?.current.ai_model_shadow?.max_drawdown_pct ?? null)}
              className="text-red-600"
            />
            <MetricRow
              label="Alpha"
              value={fmtPct(aiModel?.latest_alpha)}
              className={pctClass(aiModel?.latest_alpha)}
            />
            <MetricRow
              label="Divergence vs Actual"
              value={fmtPct(aiDivergence)}
              className={pctClass(aiDivergence)}
            />
          </div>
          )}
        </div>
      </div>
    </section>
  );
}
