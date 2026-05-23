"use client";

import { useState } from "react";

type TabType = "scoring" | "signals" | "optimizer" | "factors" | "operations";

export default function SystemGuidePage() {
  const [activeTab, setActiveTab] = useState<TabType>("scoring");

  const tabs: { id: TabType; label: string }[] = [
    { id: "scoring", label: "Scoring System" },
    { id: "signals", label: "Signal Guide" },
    { id: "optimizer", label: "3-Layer Optimizer" },
    { id: "factors", label: "Factor Analysis" },
    { id: "operations", label: "Cache & Analytics" },
  ];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2 text-gray-900">📚 System Guide</h1>
        <p className="text-gray-600">
          Understand the logic and architecture behind your stock analysis system.
        </p>
      </div>

      {/* Tab Navigation */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-2 mb-8">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`px-4 py-3 rounded-lg font-semibold transition-all ${
              activeTab === tab.id
                ? "bg-blue-600 text-white shadow-lg"
                : "bg-white text-gray-700 hover:bg-gray-50 border border-gray-200"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <div className="bg-white rounded-lg p-8 shadow">
        {activeTab === "scoring" && <ScoringTab />}
        {activeTab === "signals" && <SignalsTab />}
        {activeTab === "optimizer" && <OptimizerTab />}
        {activeTab === "factors" && <FactorsTab />}
        {activeTab === "operations" && <OperationsTab />}
      </div>
    </div>
  );
}

function ScoringTab() {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold mb-4 text-blue-600">
          Scoring System
        </h2>
        <p className="text-gray-700 mb-6">
          The platform computes deterministic, math-first scores before any AI summary call.
          These scores become objective anchors used by the analysis and optimizer pipelines.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="bg-white rounded-lg p-6 border-l-4 border-orange-500 shadow">
          <h3 className="text-xl font-bold mb-3 text-orange-600">
            Technical Score (0-100)
          </h3>
          <ul className="space-y-2 text-sm text-gray-700">
            <li><strong>50:</strong> neutral baseline</li>
            <li><strong>&gt; 65:</strong> bullish</li>
            <li><strong>&lt; 35:</strong> bearish</li>
            <li className="pt-2 text-xs text-gray-500">
              Derived from multi-timeframe TA indicators (EMA, TEMA, ZigZag, BB, MACD, RSI).
            </li>
          </ul>
        </div>

        <div className="bg-white rounded-lg p-6 border-l-4 border-green-500 shadow">
          <h3 className="text-xl font-bold mb-3 text-green-600">
            Fundamental Score (0-100)
          </h3>
          <ul className="space-y-2 text-sm text-gray-700">
            <li><strong>50:</strong> fairly valued baseline</li>
            <li><strong>&gt; 70:</strong> relatively undervalued</li>
            <li><strong>&lt; 30:</strong> relatively overvalued</li>
            <li className="pt-2 text-xs text-gray-500">
              Uses P/E, ROE, growth, debt/equity, and related valuation factors.
            </li>
          </ul>
        </div>

        <div className="bg-white rounded-lg p-6 border-l-4 border-blue-500 shadow">
          <h3 className="text-xl font-bold mb-3 text-blue-600">
            News Sentiment (0-100)
          </h3>
          <ul className="space-y-2 text-sm text-gray-700">
            <li><strong>50:</strong> neutral sentiment</li>
            <li><strong>&gt; 65:</strong> positive narrative flow</li>
            <li><strong>&lt; 35:</strong> negative narrative flow</li>
            <li className="pt-2 text-xs text-gray-500">
              Built from recent headline flow and tone extraction.
            </li>
          </ul>
        </div>

        <div className="bg-white rounded-lg p-6 border-l-4 border-amber-500 shadow">
          <h3 className="text-xl font-bold mb-3 text-amber-600">
            Valuation Percentile Penalty
          </h3>
          <ul className="space-y-2 text-sm text-gray-700">
            <li><strong>&gt;= 92 percentile:</strong> -12 to fundamental score</li>
            <li><strong>&gt;= 80 percentile:</strong> -6 to fundamental score</li>
            <li className="pt-2 text-xs text-gray-500">
              Applied during optimizer peer comparison to reduce overpaying risk.
            </li>
          </ul>
        </div>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-800">
          <strong>Why this matters:</strong> AI summaries consume these scores as fixed inputs,
          so recommendations stay tethered to reproducible numeric evidence.
        </p>
      </div>
    </div>
  );
}

function SignalsTab() {
  const signals = [
    {
      level: "BUY",
      bg: "bg-green-50 border-green-200",
      desc: "FA strong and TA positive. Reserved for top-quality setups; TA must not be bearish.",
      when: "Deploy capital now when portfolio constraints allow.",
    },
    {
      level: "ACCUMULATE",
      bg: "bg-teal-50 border-teal-200",
      desc: "FA strong, TA not fully aligned. Better for phased entries and DCA.",
      when: "Scale in gradually instead of one-shot buying.",
    },
    {
      level: "WATCH",
      bg: "bg-blue-50 border-blue-200",
      desc: "Underlying quality exists, but setup is not ready for action.",
      when: "Wait for technical confirmation or improved entry.",
    },
    {
      level: "HOLD",
      bg: "bg-gray-100 border-gray-300",
      desc: "Mixed evidence with no high-conviction add or reduce trigger.",
      when: "Keep position unchanged.",
    },
    {
      level: "REDUCE",
      bg: "bg-amber-50 border-amber-200",
      desc: "Position looks stretched, crowded, or over-valued relative to risk.",
      when: "Trim size and protect gains.",
    },
    {
      level: "SELL",
      bg: "bg-red-50 border-red-200",
      desc: "Thesis deterioration or severe technical breakdown; exit bias is dominant.",
      when: "Close position and reallocate.",
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold mb-4 text-blue-600">
          Signal Guide (6 Levels)
        </h2>
        <p className="text-gray-700 mb-6">
          Every symbol is mapped to one of six action levels. Signals combine deterministic
          scores and model reasoning, then flow into portfolio and optimizer decisions.
        </p>
      </div>

      <div className="space-y-4">
        {signals.map((signal, idx) => (
          <div
            key={idx}
            className={`${signal.bg} border rounded-lg p-6 transition-all hover:shadow-lg shadow`}
          >
            <div className="flex items-start justify-between mb-3">
              <h3 className="text-2xl font-bold text-gray-900">
                {signal.level === "BUY" && "🟢"}
                {signal.level === "ACCUMULATE" && "🔵"}
                {signal.level === "WATCH" && "🔹"}
                {signal.level === "HOLD" && "⚪"}
                {signal.level === "REDUCE" && "🟡"}
                {signal.level === "SELL" && "🔴"}
                {" " + signal.level}
              </h3>
            </div>
            <p className="text-gray-800 mb-3">{signal.desc}</p>
            <div className="text-sm text-gray-600">
              <strong>When to act:</strong> {signal.when}
            </div>
          </div>
        ))}
      </div>

      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
        <p className="text-sm text-yellow-800">
          <strong>Golden rule:</strong> BUY is never assigned on fundamentals alone.
          Technical confirmation is required for top-conviction entries.
        </p>
      </div>
    </div>
  );
}

function OptimizerTab() {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold mb-4 text-blue-600">
          3-Layer Optimizer (Consensus Engine)
        </h2>
        <p className="text-gray-700 mb-6">
          The optimizer runs three independent AI layers plus a pure-Python consensus engine.
          This design reduces single-model bias and adds explicit risk controls.
        </p>
      </div>

      <div className="space-y-6">
        <div className="bg-purple-50 border-l-4 border-purple-500 rounded-lg p-6 border shadow">
          <h3 className="text-2xl font-bold mb-2 text-purple-700">
            Layer 1 - Strategist
          </h3>
          <p className="text-gray-700 mb-3">
            <strong>Role:</strong> proposes the primary allocation plan.
          </p>
          <ul className="text-sm text-gray-700 space-y-2">
            <li>Creates swaps, top buys, and sector flags</li>
            <li>Includes partial actions (REDUCE and ACCUMULATE), not only full swaps</li>
            <li>Evaluates sector concentration, overweight holdings, and 2-5% shift opportunities</li>
          </ul>
        </div>

        <div className="bg-indigo-50 border-l-4 border-indigo-500 rounded-lg p-6 border shadow">
          <h3 className="text-2xl font-bold mb-2 text-indigo-700">
            Layer 2 - Challenger
          </h3>
          <p className="text-gray-700 mb-3">
            <strong>Role:</strong> independent critique and alternative allocation.
          </p>
          <ul className="text-sm text-gray-700 space-y-2">
            <li>Can agree with strategist or provide disagreements</li>
            <li>Returns portfolio assessment, cash target, and full target weights</li>
            <li>Acts as the final actionable plan source for signal-history logging</li>
          </ul>
        </div>

        <div className="bg-cyan-50 border-l-4 border-cyan-500 rounded-lg p-6 border shadow">
          <h3 className="text-2xl font-bold mb-2 text-cyan-700">
            Layer 3 - Risk Auditor
          </h3>
          <p className="text-gray-700 mb-3">
            <strong>Role:</strong> concentration and downside risk audit.
          </p>
          <ul className="text-sm text-gray-700 space-y-2">
            <li>Emits LOW, MEDIUM, HIGH, or CRITICAL risk flags</li>
            <li>Can block aggressive plans when concentration risk is excessive</li>
            <li>Suggests safer alternatives for high-risk exposure clusters</li>
          </ul>
        </div>
      </div>

      <div className="bg-green-50 border border-green-200 rounded-lg p-6 shadow">
        <h3 className="text-2xl font-bold mb-2 text-green-700">
          Consensus Strength Matrix
        </h3>
        <p className="text-gray-700 mb-2">
          A pure-Python engine (no AI call) computes three scores, then classifies the run into
          one of seven types evaluated top-to-bottom — <strong>first match wins</strong>.
        </p>

        {/* Score inputs */}
        <div className="grid md:grid-cols-3 gap-3 mb-5 text-sm">
          <div className="bg-white border border-green-200 rounded p-3">
            <p className="font-semibold text-gray-800 mb-1">Strategist Alignment (0–100)</p>
            <p className="text-gray-600">Base 80 (L2 agrees) or 30 (disagrees) − 12 per disagreement ± Jaccard symbol overlap bonus</p>
          </div>
          <div className="bg-white border border-green-200 rounded p-3">
            <p className="font-semibold text-gray-800 mb-1">Risk Alignment (0–100)</p>
            <p className="text-gray-600">92 clean → 55–30 HIGH flags → 12 CRITICAL flag</p>
          </div>
          <div className="bg-white border border-green-200 rounded p-3">
            <p className="font-semibold text-gray-800 mb-1">Strength Score (0–100)</p>
            <p className="text-gray-600">65% × Strategist + 35% × Risk — the main confidence gauge shown in the UI</p>
          </div>
        </div>

        {/* Type table */}
        <div className="space-y-2 text-sm">
          {[
            {
              priority: "1",
              type: "RISK_CONFLICT",
              meaning: "L3 found a serious concentration risk — act with caution",
              trigger: "CRITICAL flag OR (risk=HIGH + ≥2 HIGH flags)",
              color: "bg-orange-100 border-orange-400 text-orange-900",
              dot: "bg-orange-500",
            },
            {
              priority: "2",
              type: "STRATEGIC_CONFLICT",
              meaning: "L1 and L2 fundamentally disagree on what to do",
              trigger: "L2 disagrees AND stratAlign < 40",
              color: "bg-red-100 border-red-400 text-red-900",
              dot: "bg-red-500",
            },
            {
              priority: "3",
              type: "NO_ACTION_CONSENSUS",
              meaning: "All three layers agree: portfolio is fine, no trade needed",
              trigger: "L2 status = NO_ACTION AND score < 40 AND no critical risk",
              color: "bg-teal-100 border-teal-400 text-teal-900",
              dot: "bg-teal-500",
            },
            {
              priority: "4",
              type: "STRONG_CONSENSUS",
              meaning: "All layers aligned — high confidence signal",
              trigger: "stratAlign ≥ 70 AND riskAlign ≥ 65",
              color: "bg-green-100 border-green-400 text-green-900",
              dot: "bg-green-500",
            },
            {
              priority: "5",
              type: "REFINED_CONSENSUS",
              meaning: "L2 agrees with L1 but adds nuance or refinement",
              trigger: "L2 agrees AND stratAlign ≥ 50",
              color: "bg-blue-100 border-blue-400 text-blue-900",
              dot: "bg-blue-500",
            },
            {
              priority: "6",
              type: "PARTIAL_CONSENSUS",
              meaning: "Moderate agreement — consider recommendations but stay alert",
              trigger: "stratAlign ≥ 35",
              color: "bg-amber-100 border-amber-400 text-amber-900",
              dot: "bg-amber-500",
            },
            {
              priority: "7",
              type: "WEAK_CONSENSUS",
              meaning: "Layers diverge — treat output as exploratory only",
              trigger: "stratAlign < 35 (fallback)",
              color: "bg-gray-100 border-gray-400 text-gray-700",
              dot: "bg-gray-400",
            },
          ].map((row) => (
            <div
              key={row.type}
              className={`${row.color} border rounded-lg p-3 flex items-start gap-3`}
            >
              <span className="font-mono font-bold text-lg w-5 shrink-0 mt-0.5">{row.priority}</span>
              <span className={`w-3 h-3 rounded-full mt-1.5 shrink-0 ${row.dot}`} />
              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-baseline gap-2 mb-0.5">
                  <span className="font-bold font-mono">{row.type}</span>
                  <span className="text-xs opacity-75">{row.meaning}</span>
                </div>
                <p className="text-xs opacity-70"><strong>Trigger:</strong> {row.trigger}</p>
              </div>
            </div>
          ))}
        </div>

        <p className="text-xs text-gray-500 mt-3">
          Risk and strategic conflicts are checked first so dangerous signals are never buried under a positive consensus label.
        </p>
      </div>

      <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
        <p className="text-sm text-orange-800">
          <strong>Performance note:</strong> one optimizer run triggers three sequential AI calls,
          so end-to-end latency can still be tens of seconds.
        </p>
      </div>
    </div>
  );
}

function FactorsTab() {
  const factors = [
    {
      name: "Growth",
      color: "border-emerald-500 bg-emerald-50",
      titleColor: "text-emerald-700",
      metrics: [
        { label: "Revenue Growth", weight: "50%" },
        { label: "Earnings Growth", weight: "50%" },
      ],
      note: "Captures top-line and bottom-line expansion velocity.",
    },
    {
      name: "Value",
      color: "border-blue-500 bg-blue-50",
      titleColor: "text-blue-700",
      metrics: [
        { label: "Inverse P/E", weight: "50%" },
        { label: "Inverse P/B", weight: "30%" },
        { label: "Inverse EV/EBITDA", weight: "20%" },
      ],
      note: "Lower multiples rank higher. Eliminates Thai SET vs US valuation bias via percentile normalization.",
    },
    {
      name: "Dividend",
      color: "border-amber-500 bg-amber-50",
      titleColor: "text-amber-700",
      metrics: [
        { label: "Dividend Yield", weight: "70%" },
        { label: "Payout Optimality", weight: "30%" },
      ],
      note: "Rewards sustainable yield — excessively high payout ratios are penalized.",
    },
    {
      name: "Momentum",
      color: "border-violet-500 bg-violet-50",
      titleColor: "text-violet-700",
      metrics: [
        { label: "30-day Return", weight: "40%" },
        { label: "90-day Return", weight: "20%" },
        { label: "MA Alignment", weight: "30%" },
        { label: "RSI (14)", weight: "10%" },
      ],
      note: "Combines price trend strength with technical confirmation signals.",
    },
    {
      name: "Quality",
      color: "border-rose-500 bg-rose-50",
      titleColor: "text-rose-700",
      metrics: [
        { label: "ROE", weight: "40%" },
        { label: "Net Margin", weight: "40%" },
        { label: "Inverse D/E (leverage)", weight: "20%" },
      ],
      note: "High-quality businesses earn well on equity and carry low financial risk.",
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold mb-4 text-blue-600">
          Factor Exposure Analysis
        </h2>
        <p className="text-gray-700 mb-2">
          The platform computes five institutional-grade factor exposures for each portfolio.
          All sub-metrics are <strong>percentile-ranked within the portfolio universe</strong> before
          aggregation — this eliminates cross-market bias between Thai SET and US valuations.
        </p>
        <p className="text-gray-600 text-sm">
          Access via <strong>Portfolio → Factor DNA</strong> or{" "}
          <code className="bg-gray-100 px-1 rounded text-xs">GET /analytics/factor-exposure?portfolio_id=X</code>.
          Results are cached for 15 minutes.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-5">
        {factors.map((f) => (
          <div key={f.name} className={`border-l-4 ${f.color} rounded-lg p-5 shadow`}>
            <h3 className={`text-xl font-bold mb-3 ${f.titleColor}`}>{f.name}</h3>
            <div className="space-y-1 mb-3">
              {f.metrics.map((m) => (
                <div key={m.label} className="flex justify-between text-sm text-gray-700">
                  <span>{m.label}</span>
                  <span className="font-mono font-semibold text-gray-500">{m.weight}</span>
                </div>
              ))}
            </div>
            <p className="text-xs text-gray-500">{f.note}</p>
          </div>
        ))}
      </div>

      <div className="bg-white border border-gray-200 rounded-lg p-6 shadow">
        <h3 className="text-xl font-bold mb-3 text-gray-800">Style Classification</h3>
        <p className="text-sm text-gray-700 mb-4">
          A portfolio is dynamically classified into one of <strong>7 single-factor</strong> or{" "}
          <strong>10 dual-factor</strong> styles — no hardcoded thresholds.
        </p>
        <div className="grid md:grid-cols-2 gap-4 text-sm text-gray-700">
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="font-semibold text-gray-900 mb-2">Single-factor style</p>
            <p>Top factor dominates by ≥ 15 points <em>and</em> scores ≥ 60.</p>
            <p className="text-xs text-gray-500 mt-1">Example: Growth 82, next factor 61 → "Growth Portfolio"</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="font-semibold text-gray-900 mb-2">Dual-factor blend</p>
            <p>Top two factors within 15 points of each other, both ≥ 50.</p>
            <p className="text-xs text-gray-500 mt-1">Example: Value 74, Quality 68 → "Value-Quality Portfolio"</p>
          </div>
        </div>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-800">
          <strong>Cross-market normalization:</strong> a Thai bank at P/E 8 and a US tech stock at P/E 30 are
          ranked relative to each other within the portfolio, so factor scores reflect portfolio composition
          rather than absolute market-level differences.
        </p>
      </div>
    </div>
  );
}

function OperationsTab() {
  const cacheStrategies = [
    {
      name: "Technical Data",
      ttl: "15 minutes",
      reason: "chart indicators and trend state change quickly",
      scope: "TA agent cache",
      color: "bg-orange-50 border-orange-200",
    },
    {
      name: "News Data",
      ttl: "1 hour",
      reason: "headline flow updates intraday",
      scope: "news agent cache",
      color: "bg-blue-50 border-blue-200",
    },
    {
      name: "Fundamental Data",
      ttl: "24 hours",
      reason: "fundamental ratios move slowly compared to price",
      scope: "fundamental agent cache",
      color: "bg-green-50 border-green-200",
    },
    {
      name: "Analysis Cache (AI Summary)",
      ttl: "12 hours",
      reason: "reduce repeated model calls while keeping signals reasonably fresh",
      scope: "signal, confidence, reasoning",
      color: "bg-purple-50 border-purple-200",
    },
    {
      name: "Analyze All Shortcut Cache",
      ttl: "60 minutes",
      reason: "batch runs skip recently analyzed symbols",
      scope: "portfolio/watchlist analyze-all endpoints",
      color: "bg-indigo-50 border-indigo-200",
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold mb-4 text-blue-600">
          Jobs, Caching, and Analytics
        </h2>
        <p className="text-gray-700 mb-6">
          This platform uses concurrent analysis workers, in-process job tracking, and
          layered caches to keep large watchlists responsive.
        </p>
      </div>

      <div className="bg-white rounded-lg p-6 border border-gray-200 shadow">
        <h3 className="text-xl font-bold mb-4 text-gray-900">Concurrent Watchlist Analysis</h3>
        <div className="space-y-2 text-sm text-gray-700">
          <p>
            <strong>POST /watchlist/analyze/all</strong> runs all stale symbols concurrently via{" "}
            <code className="bg-gray-100 px-1 rounded text-xs">asyncio.gather()</code> capped at{" "}
            <code className="bg-gray-100 px-1 rounded text-xs">Semaphore(10)</code> — ~32 s for 68 stocks.
          </p>
          <p>
            <strong>POST /watchlist/analyze/all/stream</strong> returns a{" "}
            <code className="bg-gray-100 px-1 rounded text-xs">StreamingResponse (application/x-ndjson)</code>{" "}
            emitting <code className="bg-gray-100 px-1 rounded text-xs">start → progress → complete</code> events
            as stocks finish in completion order.
          </p>
          <p>Each AI call is wrapped in a 10-second timeout. On timeout or error, a deterministic fallback
            signal is computed from TA/FA scores — the UI shows a fallback count when applicable.</p>
          <p>Fallback results are <em>not</em> written to AnalysisCache so the next run will retry the AI call.</p>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {cacheStrategies.map((strategy, idx) => (
          <div
            key={idx}
            className={`${strategy.color} border rounded-lg p-6 transition-all hover:shadow-lg shadow`}
          >
            <h3 className="text-lg font-bold mb-2 text-gray-900">
              {strategy.name}
            </h3>
            <div className="space-y-3 text-sm text-gray-700">
              <div>
                <strong className="text-gray-900">TTL:</strong> {strategy.ttl}
              </div>
              <div>
                <strong className="text-gray-900">Why:</strong> {strategy.reason}
              </div>
              <div>
                <strong className="text-gray-900">Scope:</strong> {strategy.scope}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-6 shadow">
        <h3 className="text-xl font-bold mb-3 text-emerald-700">Performance Comparison Endpoint</h3>
        <p className="text-sm text-gray-700 mb-2">
          <strong>GET /analytics/performance-comparison</strong> returns benchmark-normalized series
          (base = 100 at the first snapshot date).
        </p>
        <ul className="text-sm text-gray-700 space-y-2">
          <li>Compares portfolio curve against configurable benchmark symbols</li>
          <li>Returns flat chart-ready rows for frontend rendering</li>
          <li>Supports default benchmark pair ^SET.BK and QQQ</li>
        </ul>
      </div>

      <div className="bg-teal-50 border border-teal-200 rounded-lg p-4">
        <p className="text-sm text-teal-800">
          <strong>Operator tip:</strong> use job stream for long watchlist runs and poll endpoint for
          resilient progress tracking if the browser reconnects.
        </p>
      </div>
    </div>
  );
}
