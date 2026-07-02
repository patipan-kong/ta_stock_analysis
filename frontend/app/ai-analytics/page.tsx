"use client";

import { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { getAiAnalytics, type AiAnalytics } from "@/lib/api";
import { KPICard } from "@/components/analytics/KPICard";
import { fmtMs, fmtUsd, fmtInt, fmtPct01, fallbackHealth } from "@/lib/ai-analytics-transformers";

import ModelLeaderboard from "@/components/analytics/ai/ModelLeaderboard";
import LayerHeatmap from "@/components/analytics/ai/LayerHeatmap";
import ReliabilitySection from "@/components/analytics/ai/ReliabilitySection";
import CostReportSection from "@/components/analytics/ai/CostReportSection";
import RecentActivityTable from "@/components/analytics/ai/RecentActivityTable";

const CostBreakdownSection = dynamic(() => import("@/components/analytics/ai/CostBreakdownSection"), {
  ssr: false,
  loading: () => <div className="h-72 animate-pulse bg-gray-100 rounded-xl" />,
});
const LatencyDashboardSection = dynamic(() => import("@/components/analytics/ai/LatencyDashboardSection"), {
  ssr: false,
  loading: () => <div className="h-72 animate-pulse bg-gray-100 rounded-xl" />,
});
const TokenDashboardSection = dynamic(() => import("@/components/analytics/ai/TokenDashboardSection"), {
  ssr: false,
  loading: () => <div className="h-72 animate-pulse bg-gray-100 rounded-xl" />,
});

// ─── Section wrapper (matches app/analytics/page.tsx convention) ──────────────

function Section({
  id,
  title,
  subtitle,
  children,
}: {
  id: string;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <div id={id} className="bg-white border border-gray-200 rounded-xl overflow-hidden scroll-mt-20">
      <div className="px-5 py-4 border-b border-gray-100">
        <h2 className="text-sm font-semibold text-gray-800">{title}</h2>
        {subtitle && <p className="text-xs text-gray-400 mt-0.5">{subtitle}</p>}
      </div>
      <div className="p-5">{children}</div>
    </div>
  );
}

const JUMP_LINKS = [
  { id: "leaderboard", label: "Leaderboard" },
  { id: "heatmap", label: "Layer Heatmap" },
  { id: "cost", label: "Cost" },
  { id: "latency", label: "Latency" },
  { id: "tokens", label: "Tokens" },
  { id: "reliability", label: "Reliability" },
  { id: "cost-report", label: "AI Cost" },
  { id: "recent", label: "Recent Activity" },
];

function todayStr() {
  return new Date().toISOString().slice(0, 10);
}
function daysAgoStr(n: number) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}
const DATE_PRESETS = [
  { label: "Today", from: () => todayStr(), to: () => todayStr() },
  { label: "7 days", from: () => daysAgoStr(6), to: () => todayStr() },
  { label: "30 days", from: () => daysAgoStr(29), to: () => todayStr() },
  { label: "All", from: () => "", to: () => "" },
];

export default function AiAnalyticsPage() {
  const [data, setData] = useState<AiAnalytics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");

  function load(from: string, to: string) {
    setLoading(true);
    getAiAnalytics(from || undefined, to || undefined)
      .then(setData)
      .catch(() => setError("Failed to load AI analytics"))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load("", "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function applyDateFilter(from: string, to: string) {
    setFromDate(from);
    setToDate(to);
    load(from, to);
  }

  if (error) return <p className="text-sm text-red-500">{error}</p>;

  const totals = data?.totals;
  const fallbackRate = data?.reliability.fallback_rate ?? null;

  return (
    <div className="space-y-5 max-w-6xl">
      {/* ── Header + global date filter ───────────────────────────────────── */}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold mb-1">AI Analytics</h1>
          <p className="text-sm text-gray-500">
            Observability for every AI call — cost, latency, tokens, and reliability across providers, models, and
            optimizer layers.
          </p>
        </div>
        <div className="bg-white border rounded-xl px-4 py-3 shadow-sm flex flex-wrap items-center gap-2">
          <span className="text-xs text-gray-500 font-medium mr-1">Period:</span>
          {DATE_PRESETS.map((preset) => {
            const pFrom = preset.from();
            const pTo = preset.to();
            const active = fromDate === pFrom && toDate === pTo;
            return (
              <button
                key={preset.label}
                onClick={() => applyDateFilter(pFrom, pTo)}
                className={`text-xs px-3 py-1 rounded-full border transition-colors ${
                  active
                    ? "bg-gray-800 text-white border-gray-800"
                    : "bg-white text-gray-600 border-gray-300 hover:border-gray-500"
                }`}
              >
                {preset.label}
              </button>
            );
          })}
          <div className="flex items-center gap-1 ml-1">
            <input
              type="date"
              value={fromDate}
              onChange={(e) => applyDateFilter(e.target.value, toDate)}
              className="text-xs border rounded px-2 py-1 text-gray-700 focus:outline-none focus:ring-1 focus:ring-gray-400"
            />
            <span className="text-xs text-gray-400">–</span>
            <input
              type="date"
              value={toDate}
              onChange={(e) => applyDateFilter(fromDate, e.target.value)}
              className="text-xs border rounded px-2 py-1 text-gray-700 focus:outline-none focus:ring-1 focus:ring-gray-400"
            />
          </div>
          {loading && <span className="text-xs text-gray-400 ml-1">Loading…</span>}
        </div>
      </div>

      {/* ── Quick jump nav ─────────────────────────────────────────────────── */}
      <div className="sticky top-0 z-10 bg-gray-50/95 backdrop-blur border-b border-gray-100 -mx-4 px-4 py-2 flex flex-wrap gap-1.5">
        {JUMP_LINKS.map((l) => (
          <a
            key={l.id}
            href={`#${l.id}`}
            className="text-xs px-2.5 py-1 rounded-full text-gray-500 hover:bg-white hover:text-gray-800 hover:shadow-sm transition-colors"
          >
            {l.label}
          </a>
        ))}
      </div>

      {/* ── Top-line KPIs ──────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <KPICard label="Total Calls" value={totals ? fmtInt(totals.call_count) : "…"} />
        <KPICard label="Total Cost" value={totals ? fmtUsd(totals.total_cost_usd) : "…"} />
        <KPICard label="Total Tokens" value={totals ? fmtInt(totals.total_tokens) : "…"} />
        <KPICard
          label="Fallback Rate"
          value={fmtPct01(fallbackRate)}
          valueClass={
            fallbackHealth(fallbackRate) === "problem"
              ? "text-red-600"
              : fallbackHealth(fallbackRate) === "warning"
                ? "text-amber-600"
                : undefined
          }
        />
      </div>

      {/* ── Section 1: Leaderboard ─────────────────────────────────────────── */}
      <Section id="leaderboard" title="AI Model Leaderboard" subtitle="Best performing models — sortable by speed, cost, tokens, and reliability">
        {data ? <ModelLeaderboard rows={data.leaderboard} /> : <div className="h-40 animate-pulse bg-gray-100 rounded-xl" />}
      </Section>

      {/* ── Section 2: Layer Heatmap ───────────────────────────────────────── */}
      <Section id="heatmap" title="Layer Heatmap" subtitle="Which model runs each optimizer layer — click a cell for detail">
        {data ? <LayerHeatmap cells={data.layer_matrix} /> : <div className="h-40 animate-pulse bg-gray-100 rounded-xl" />}
      </Section>

      {/* ── Section 3: Cost Breakdown ──────────────────────────────────────── */}
      <Section id="cost" title="Cost Breakdown" subtitle="Spend over time, attributed by provider, model, layer, or operation">
        {data ? <CostBreakdownSection daily={data.daily} /> : <div className="h-72 animate-pulse bg-gray-100 rounded-xl" />}
      </Section>

      {/* ── Section 4: Latency Dashboard ───────────────────────────────────── */}
      <Section id="latency" title="Latency Dashboard" subtitle="Average and P95 latency trend, plus the slowest models/layers">
        {data ? <LatencyDashboardSection daily={data.daily} /> : <div className="h-72 animate-pulse bg-gray-100 rounded-xl" />}
      </Section>

      {/* ── Section 5: Token Dashboard ─────────────────────────────────────── */}
      <Section id="tokens" title="Token Dashboard" subtitle="Input/output/total token volume, and unusually large responses">
        {data ? <TokenDashboardSection daily={data.daily} /> : <div className="h-72 animate-pulse bg-gray-100 rounded-xl" />}
      </Section>

      {/* ── Section 6: Reliability ─────────────────────────────────────────── */}
      <Section id="reliability" title="Reliability" subtitle="Health signals — metrics not yet tracked show N/A and light up automatically once recorded">
        {data ? <ReliabilitySection reliability={data.reliability} /> : <div className="h-40 animate-pulse bg-gray-100 rounded-xl" />}
      </Section>

      {/* ── Section 7: AI Cost (moved from the old Model Cost Report page) ──── */}
      <Section id="cost-report" title="AI Cost" subtitle="Monthly cost report — Analyze vs Optimizer, by day and by model">
        <CostReportSection />
      </Section>

      {/* ── Section 8: Recent Activity ─────────────────────────────────────── */}
      <Section id="recent" title="Recent Activity" subtitle="Latest AI calls — filterable by provider, model, and layer">
        {data ? <RecentActivityTable calls={data.recent} /> : <div className="h-40 animate-pulse bg-gray-100 rounded-xl" />}
      </Section>
    </div>
  );
}
