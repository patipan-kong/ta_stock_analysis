"use client";

import { useState, useEffect } from "react";
import { getConsensus, askWhyDisagree } from "@/lib/api";
import AIBadge from "./AIBadge";
import SignalBadge from "./SignalBadge";
import type { ConsensusResult, WhyDisagreeResult, AnalysisScores } from "@/lib/api";

const TZ = "Asia/Bangkok";

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("th-TH", { day: "2-digit", month: "short", timeZone: TZ }) +
    " " + d.toLocaleTimeString("th-TH", { hour: "2-digit", minute: "2-digit", timeZone: TZ });
}

function AgreementMeter({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 80 ? "bg-green-500" : pct >= 60 ? "bg-blue-500" : pct >= 40 ? "bg-amber-400" : "bg-red-400";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-100 rounded-full h-2 overflow-hidden">
        <div className={`h-2 rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`text-xs font-semibold w-10 text-right ${pct >= 60 ? "text-green-600" : pct >= 40 ? "text-amber-600" : "text-red-500"}`}>
        {pct}%
      </span>
    </div>
  );
}

function ScoreBar({ label, value, invert = false }: { label: string; value: number; invert?: boolean }) {
  const display = invert ? 100 - value : value;
  const color = display >= 65 ? "bg-green-400" : display <= 35 ? "bg-red-400" : "bg-amber-300";
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className="text-gray-500 w-20 shrink-0">{label}</span>
      <div className="flex-1 bg-gray-100 rounded-full h-1.5 overflow-hidden">
        <div className={`h-1.5 rounded-full ${color}`} style={{ width: `${value}%` }} />
      </div>
      <span className="w-7 text-right text-gray-600 font-medium">{value}</span>
    </div>
  );
}

function ScoresRow({ scores }: { scores: AnalysisScores }) {
  return (
    <div className="mt-1 space-y-1 pl-1">
      <ScoreBar label="Technical"    value={scores.technical_score} />
      <ScoreBar label="Fundamental"  value={scores.fundamental_score} />
      <ScoreBar label="News"         value={scores.news_sentiment} />
      <ScoreBar label="Risk"         value={scores.risk_score} invert />
    </div>
  );
}

export default function ConsensusCard({ symbol, refreshKey = 0 }: { symbol: string; refreshKey?: number }) {
  const [data, setData] = useState<ConsensusResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandScores, setExpandScores] = useState<number | null>(null);

  const [whyLoading, setWhyLoading] = useState(false);
  const [whyResult, setWhyResult] = useState<WhyDisagreeResult | null>(null);
  const [whyError, setWhyError] = useState("");

  useEffect(() => {
    setLoading(true);
    setWhyResult(null);
    setWhyError("");
    getConsensus(symbol)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [symbol, refreshKey]);

  async function handleWhyDisagree() {
    setWhyLoading(true);
    setWhyError("");
    try {
      const res = await askWhyDisagree(symbol);
      if (res.error) setWhyError(res.error);
      else setWhyResult(res);
    } catch (err) {
      setWhyError(err instanceof Error ? err.message : "Failed");
    } finally {
      setWhyLoading(false);
    }
  }

  if (loading) return null;
  if (!data || data.error || data.total_analyses === 0) return null;

  const { consensus_signal, agreement, high_disagreement, signal_counts, breakdown } = data;

  return (
    <section className="bg-white border rounded-xl p-5 shadow-sm space-y-4">
      {/* Header */}
      <div className="flex items-center gap-3 flex-wrap">
        <h2 className="text-lg font-semibold">Consensus</h2>
        <span className="text-xs text-gray-400">{data.total_analyses} analyses</span>
        <SignalBadge signal={consensus_signal} />
        {high_disagreement && (
          <span className="text-xs bg-amber-100 border border-amber-300 text-amber-700 px-2 py-0.5 rounded-full font-medium">
            ⚠ High Disagreement
          </span>
        )}
      </div>

      {/* Agreement meter + signal bar */}
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-xs text-gray-500">
          <span className="w-20 shrink-0">Agreement</span>
          <AgreementMeter value={agreement} />
        </div>
        <div className="flex gap-2 text-xs">
          {(["ACCUMULATE", "BUY", "WATCH", "HOLD", "REDUCE", "SELL"] as const).map((sig) => (
            <div key={sig} className="flex-1 text-center">
              <div className={`text-xs font-semibold ${sig === "BUY" ? "text-green-600" : sig === "SELL" ? "text-red-500" : "text-amber-600"}`}>
                {sig}
              </div>
              <div className="text-lg font-bold text-gray-700">{signal_counts[sig]} </div>
            </div>
          ))}
        </div>
      </div>

      {/* Model comparison table */}
      <div className="overflow-x-auto">
        <table className="min-w-full text-xs">
          <thead>
            <tr className="border-b text-gray-400">
              <th className="py-1.5 pr-3 text-left font-medium">Model</th>
              <th className="py-1.5 pr-3 text-left font-medium">Signal</th>
              <th className="py-1.5 pr-3 text-left font-medium">Conf</th>
              <th className="py-1.5 pr-3 text-left font-medium">Scores</th>
              <th className="py-1.5 text-left font-medium">Date</th>
            </tr>
          </thead>
          <tbody>
            {breakdown.map((item) => (
              <>
                <tr key={item.id} className="border-b hover:bg-gray-50">
                  <td className="py-1.5 pr-3">
                    <AIBadge provider={item.ai_provider} model={item.ai_model} label="" />
                  </td>
                  <td className="py-1.5 pr-3">
                    <SignalBadge signal={item.signal} />
                  </td>
                  <td className={`py-1.5 pr-3 font-medium ${item.confidence === "high" ? "text-green-600" : item.confidence === "low" ? "text-gray-400" : "text-amber-600"}`}>
                    {item.confidence}
                  </td>
                  <td className="py-1.5 pr-3">
                    {item.scores ? (
                      <button
                        onClick={() => setExpandScores(expandScores === item.id ? null : item.id)}
                        className="text-blue-400 hover:text-blue-600 underline"
                      >
                        {expandScores === item.id ? "hide" : "view"}
                      </button>
                    ) : (
                      <span className="text-gray-300">—</span>
                    )}
                  </td>
                  <td className="py-1.5 text-gray-400 whitespace-nowrap">{formatDate(item.analyzed_at)}</td>
                </tr>
                {expandScores === item.id && item.scores && (
                  <tr key={`scores-${item.id}`} className="bg-gray-50">
                    <td colSpan={5} className="px-2 py-2">
                      <ScoresRow scores={item.scores} />
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>

      {/* Why disagree button */}
      {high_disagreement && !whyResult && (
        <div>
          <button
            onClick={handleWhyDisagree}
            disabled={whyLoading}
            className="text-sm border border-amber-300 text-amber-700 rounded-lg px-3 py-1.5 hover:bg-amber-50 disabled:opacity-50 font-medium"
          >
            {whyLoading ? "Analyzing…" : "Why disagree?"}
          </button>
          {whyError && <p className="text-xs text-red-500 mt-1">{whyError}</p>}
        </div>
      )}

      {/* Why disagree result */}
      {whyResult && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-sm font-semibold text-amber-800">Disagreement Analysis</p>
            <button onClick={() => setWhyResult(null)} className="text-xs text-gray-400 hover:text-gray-600">✕</button>
          </div>
          <p className="text-sm text-gray-700">{whyResult.synthesis}</p>
          {whyResult.key_differences?.length > 0 && (
            <ul className="text-xs text-gray-600 space-y-0.5 list-disc list-inside">
              {whyResult.key_differences.map((d, i) => <li key={i}>{d}</li>)}
            </ul>
          )}
          {whyResult.most_defensible && (
            <p className="text-xs text-amber-700">
              <span className="font-medium">Most defensible: </span>{whyResult.most_defensible}
            </p>
          )}
        </div>
      )}
    </section>
  );
}
