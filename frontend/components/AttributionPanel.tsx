"use client";

import { useState, useEffect } from "react";
import {
  getAttributionSummary,
  getHumanVsAI,
  getRegimeAttribution,
  getConfidenceCalibrationV2,
  type AttributionSummaryResponse,
  type HumanVsAIResponse,
  type RegimeAttributionResponse,
  type EnhancedCalibrationDetail,
} from "@/lib/api";

// ── Helpers ────────────────────────────────────────────────────────────────────

function pctColor(val: number | null | undefined, invert = false): string {
  if (val == null) return "text-gray-500";
  const positive = invert ? val < 0 : val > 0;
  return positive ? "text-green-700" : val === 0 ? "text-gray-500" : "text-red-600";
}

function fmt(val: number | null | undefined, decimals = 2, suffix = "%"): string {
  if (val == null) return "—";
  const sign = val > 0 ? "+" : "";
  return `${sign}${val.toFixed(decimals)}${suffix}`;
}

function fmtAbs(val: number | null | undefined, decimals = 1, suffix = "%"): string {
  if (val == null) return "—";
  return `${val.toFixed(decimals)}${suffix}`;
}

// ── Attribution Card — actual vs shadow returns ────────────────────────────────

function AttributionCard({
  portfolioId,
  windowDays,
}: {
  portfolioId: number;
  windowDays: number;
}) {
  const [data, setData] = useState<AttributionSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getAttributionSummary(portfolioId, windowDays)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [portfolioId, windowDays]);

  const cur = data?.current;

  return (
    <div className="border rounded-lg p-4 bg-white">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">
        Shadow Benchmark Comparison
        <span className="ml-2 text-xs font-normal text-gray-400">{windowDays}D window</span>
      </h3>

      {loading && <div className="text-xs text-gray-400">Loading…</div>}

      {!loading && !cur && (
        <p className="text-xs text-gray-400">
          No shadow portfolio found. Record an execution decision to start tracking.
        </p>
      )}

      {!loading && cur && (
        <>
          {/* 3-column return comparison */}
          <div className="grid grid-cols-3 gap-2 mb-3">
            <ReturnCell label="Actual" value={cur.actual.return_pct} />
            <ReturnCell
              label="Static Shadow"
              value={cur.static_shadow?.return_pct ?? null}
              dim={!cur.static_shadow}
            />
            <ReturnCell
              label="AI Model"
              value={cur.ai_model_shadow?.return_pct ?? null}
              dim={!cur.ai_model_shadow}
            />
          </div>

          {/* Key metrics row */}
          <div className="flex gap-4 text-xs border-t pt-2 mt-1">
            <MetricPill
              label="Regret score"
              value={cur.regret_score}
              tooltip="AI model return − actual return. Positive = AI would have done better."
            />
            <MetricPill
              label="Avoided drawdown"
              value={cur.avoided_drawdown_pct}
              tooltip="Static shadow max drawdown − actual max drawdown. Positive = frozen portfolio had more drawdown."
            />
            {cur.ai_outperformed != null && (
              <span
                className={`px-1.5 py-0.5 rounded text-xs font-medium ${
                  cur.ai_outperformed
                    ? "bg-amber-50 text-amber-700 border border-amber-200"
                    : "bg-green-50 text-green-700 border border-green-200"
                }`}
              >
                {cur.ai_outperformed ? "AI better" : "Human better"}
              </span>
            )}
          </div>

          {/* Interpretation */}
          <p className="text-xs text-gray-500 mt-2 leading-relaxed">{cur.interpretation}</p>
        </>
      )}
    </div>
  );
}

function ReturnCell({
  label,
  value,
  dim = false,
}: {
  label: string;
  value: number | null;
  dim?: boolean;
}) {
  return (
    <div className={`text-center ${dim ? "opacity-40" : ""}`}>
      <div className={`text-base font-semibold ${pctColor(value)}`}>{fmt(value)}</div>
      <div className="text-xs text-gray-500 mt-0.5">{label}</div>
    </div>
  );
}

function MetricPill({
  label,
  value,
  tooltip,
}: {
  label: string;
  value: number | null | undefined;
  tooltip?: string;
}) {
  return (
    <div title={tooltip} className="flex flex-col cursor-default">
      <span className={`font-semibold ${pctColor(value)}`}>{fmt(value)}</span>
      <span className="text-gray-400">{label}</span>
    </div>
  );
}

// ── Human vs AI Card ───────────────────────────────────────────────────────────

function HumanVsAICard({ portfolioId }: { portfolioId: number }) {
  const [data, setData] = useState<HumanVsAIResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getHumanVsAI(portfolioId, 90)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [portfolioId]);

  const summary = data?.summary;

  return (
    <div className="border rounded-lg p-4 bg-white">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">
        Human vs AI Decisions
        <span className="ml-2 text-xs font-normal text-gray-400">90D window</span>
      </h3>

      {loading && <div className="text-xs text-gray-400">Loading…</div>}

      {!loading && (!summary || summary.total_decisions === 0) && (
        <p className="text-xs text-gray-400">
          No execution decisions recorded yet. Use the optimizer and record a decision to begin tracking.
        </p>
      )}

      {!loading && summary && summary.total_decisions > 0 && (
        <>
          {/* Hit rate gauge */}
          <div className="flex items-center gap-3 mb-3">
            <HitRateGauge hitRate={summary.hit_rate_pct} />
            <div className="text-xs text-gray-600 flex-1">
              <span className="font-semibold text-gray-800">
                {summary.decisions_with_data}
              </span>{" "}
              of {summary.total_decisions} decisions compared
              {summary.hit_rate_pct != null && (
                <span className="block mt-0.5 text-gray-500">
                  AI wins: {summary.ai_wins} / Human wins: {summary.human_wins}
                </span>
              )}
            </div>
          </div>

          {/* Avg delta */}
          {summary.mean_return_delta != null && (
            <div className="flex gap-4 text-xs border-t pt-2">
              <div>
                <span className={`font-semibold ${pctColor(summary.mean_return_delta)}`}>
                  {fmt(summary.mean_return_delta)}
                </span>
                <span className="text-gray-400 ml-1">avg return delta</span>
              </div>
              {summary.mean_drawdown_delta != null && (
                <div>
                  <span className={`font-semibold ${pctColor(summary.mean_drawdown_delta, true)}`}>
                    {fmt(summary.mean_drawdown_delta)}
                  </span>
                  <span className="text-gray-400 ml-1">avg drawdown delta</span>
                </div>
              )}
            </div>
          )}

          {/* Verdict */}
          <p className="text-xs text-gray-500 mt-2 leading-relaxed">{summary.verdict}</p>
        </>
      )}
    </div>
  );
}

function HitRateGauge({ hitRate }: { hitRate: number | null }) {
  if (hitRate == null) {
    return (
      <div className="w-14 h-14 rounded-full border-4 border-gray-200 flex items-center justify-center">
        <span className="text-xs text-gray-400">—</span>
      </div>
    );
  }
  const color =
    hitRate >= 65 ? "border-amber-400 text-amber-700" :
    hitRate >= 50 ? "border-blue-400 text-blue-700" :
    "border-green-400 text-green-700";
  return (
    <div className={`w-14 h-14 rounded-full border-4 flex items-center justify-center flex-col ${color}`}>
      <span className="text-sm font-bold leading-tight">{hitRate.toFixed(0)}</span>
      <span className="text-xs leading-tight">%</span>
    </div>
  );
}

// ── Regime Performance Card ────────────────────────────────────────────────────

const REGIME_COLORS: Record<string, string> = {
  green:  "bg-green-100 text-green-800",
  red:    "bg-red-100 text-red-800",
  gray:   "bg-gray-100 text-gray-700",
  orange: "bg-orange-100 text-orange-800",
  blue:   "bg-blue-100 text-blue-800",
  teal:   "bg-teal-100 text-teal-800",
  amber:  "bg-amber-100 text-amber-800",
};

function RegimeCard({ portfolioId }: { portfolioId: number }) {
  const [data, setData] = useState<RegimeAttributionResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getRegimeAttribution(portfolioId, 90)
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [portfolioId]);

  const regimes = data?.regimes ?? {};
  const hasData = Object.keys(regimes).length > 0;

  return (
    <div className="border rounded-lg p-4 bg-white">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">
        Performance by Market Regime
        <span className="ml-2 text-xs font-normal text-gray-400">90D window</span>
      </h3>

      {loading && <div className="text-xs text-gray-400">Loading…</div>}

      {!loading && !hasData && (
        <p className="text-xs text-gray-400">
          {data?.status === "no_snapshot_data"
            ? "No portfolio snapshots found in the evaluation window."
            : "No regime data overlaps with portfolio snapshots yet."}
        </p>
      )}

      {!loading && hasData && (
        <>
          <div className="space-y-1.5">
            {Object.values(regimes)
              .sort((a, b) => b.avg_daily_return_pct - a.avg_daily_return_pct)
              .map((r) => {
                const colorClass = REGIME_COLORS[r.color] ?? REGIME_COLORS.gray;
                const isBest = r.regime === data?.best_regime;
                const isWorst = r.regime === data?.worst_regime;
                return (
                  <div key={r.regime} className="flex items-center gap-2">
                    <span className={`text-xs px-1.5 py-0.5 rounded font-medium whitespace-nowrap ${colorClass}`}>
                      {r.label}
                    </span>
                    <span className={`text-xs font-semibold ${pctColor(r.avg_daily_return_pct)} w-14 text-right`}>
                      {fmt(r.avg_daily_return_pct)}/d
                    </span>
                    <span className="text-xs text-gray-400">
                      {r.trading_days}d
                    </span>
                    {isBest && (
                      <span className="text-xs text-green-600 font-medium">best</span>
                    )}
                    {isWorst && (
                      <span className="text-xs text-red-500 font-medium">worst</span>
                    )}
                  </div>
                );
              })}
          </div>
          {data && (
            <p className="text-xs text-gray-400 mt-2">
              {data.matched_days} of {data.total_days} days matched to regime data
              ({data.coverage_pct}% coverage)
            </p>
          )}
        </>
      )}
    </div>
  );
}

// ── Calibration Card ───────────────────────────────────────────────────────────

function CalibrationCard({ portfolioId }: { portfolioId: number }) {
  const [data, setData] = useState<EnhancedCalibrationDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getConfidenceCalibrationV2(portfolioId, 30, false)
      .then((r) => setData(r.calibration))
      .catch(() => setData(null))
      .finally(() => setLoading(false));
  }, [portfolioId]);

  const signalAcc = data?.signal_accuracy;
  const regimeStab = data?.regime_confidence_calibration;

  return (
    <div className="border rounded-lg p-4 bg-white">
      <h3 className="text-sm font-semibold text-gray-700 mb-3">
        Confidence Calibration
        <span className="ml-2 text-xs font-normal text-gray-400">30D lookback</span>
      </h3>

      {loading && <div className="text-xs text-gray-400">Loading…</div>}

      {!loading && !data && (
        <p className="text-xs text-gray-400">No calibration data available yet.</p>
      )}

      {!loading && data && (
        <>
          <div className="grid grid-cols-2 gap-3 mb-3">
            <div>
              <div className="text-xs text-gray-500 mb-0.5">Signal Accuracy</div>
              <div className={`text-base font-semibold ${pctColor(data.consensus_strength_calibration)}`}>
                {data.consensus_strength_calibration != null
                  ? fmtAbs(data.consensus_strength_calibration)
                  : "—"}
              </div>
              <div className="text-xs text-gray-400">directional hit rate</div>
            </div>
            <div>
              <div className="text-xs text-gray-500 mb-0.5">Regime Stability</div>
              <div className={`text-base font-semibold ${pctColor(regimeStab)}`}>
                {regimeStab != null ? fmtAbs(regimeStab) : "—"}
              </div>
              <div className="text-xs text-gray-400">stable transitions</div>
            </div>
          </div>

          {/* Confidence bucket breakdown */}
          {signalAcc && typeof signalAcc === "object" && (signalAcc as { buckets?: unknown }).buckets && (
            <div className="border-t pt-2 mt-1">
              <div className="text-xs text-gray-500 mb-1">By Confidence Bucket</div>
              <div className="space-y-1">
                {Object.entries((signalAcc as { buckets: Record<string, { score_range: string; accuracy_pct: number | null; total: number }> }).buckets).map(
                  ([key, b]) => (
                    <div key={key} className="flex items-center gap-2 text-xs">
                      <span className={`w-16 font-medium ${
                        key === "HIGH" ? "text-green-700" :
                        key === "MEDIUM" ? "text-blue-700" : "text-gray-500"
                      }`}>
                        {key} ({b.score_range})
                      </span>
                      <div className="flex-1 h-1.5 bg-gray-100 rounded overflow-hidden">
                        {b.accuracy_pct != null && (
                          <div
                            className={`h-full rounded ${
                              b.accuracy_pct >= 60 ? "bg-green-500" :
                              b.accuracy_pct >= 50 ? "bg-blue-400" : "bg-red-400"
                            }`}
                            style={{ width: `${b.accuracy_pct}%` }}
                          />
                        )}
                      </div>
                      <span className="w-10 text-right text-gray-600">
                        {b.accuracy_pct != null ? fmtAbs(b.accuracy_pct) : "—"}
                      </span>
                      <span className="text-gray-400">({b.total})</span>
                    </div>
                  )
                )}
              </div>
            </div>
          )}

          {data.calibration_score != null && (
            <div className="text-xs text-gray-400 mt-2">
              Overall calibration score: {data.calibration_score.toFixed(1)}
            </div>
          )}
        </>
      )}
    </div>
  );
}

// ── Public panel component ─────────────────────────────────────────────────────

interface AttributionPanelProps {
  portfolioId: number;
  evaluationWindowDays?: number;
}

export default function AttributionPanel({
  portfolioId,
  evaluationWindowDays = 30,
}: AttributionPanelProps) {
  return (
    <div className="mt-6">
      <div className="flex items-center gap-2 mb-3">
        <h2 className="text-sm font-semibold text-gray-600 uppercase tracking-wide">
          Attribution Analytics
        </h2>
        <span className="text-xs text-gray-400 font-normal">Phase 3B.7B — Observational</span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <AttributionCard portfolioId={portfolioId} windowDays={evaluationWindowDays} />
        <HumanVsAICard portfolioId={portfolioId} />
        <RegimeCard portfolioId={portfolioId} />
        <CalibrationCard portfolioId={portfolioId} />
      </div>
    </div>
  );
}
