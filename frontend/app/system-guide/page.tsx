"use client";

import { useState } from "react";

type TabType = "scoring" | "signals" | "optimizer" | "caching";

export default function SystemGuidePage() {
  const [activeTab, setActiveTab] = useState<TabType>("scoring");

  const tabs: { id: TabType; label: string; icon: string }[] = [
    { id: "scoring", label: "🧩 Scoring System", icon: "🧩" },
    { id: "signals", label: "🚦 Signal Guide", icon: "🚦" },
    { id: "optimizer", label: "🧠 3-Layer Optimizer", icon: "🧠" },
    { id: "caching", label: "⚡ Caching & Freshness", icon: "⚡" },
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
      <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-8">
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
        {activeTab === "caching" && <CachingTab />}
      </div>
    </div>
  );
}

function ScoringTab() {
  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold mb-4 text-blue-600">
          🧩 Scoring System
        </h2>
        <p className="text-gray-700 mb-6">
          The system uses <strong>Deterministic Scoring</strong> (mathematics-based,
          no AI) to calculate raw scores on a 0-100 scale. These scores serve as
          <strong> anchors</strong> that the AI uses to reason about investment decisions.
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        {/* Technical Score */}
        <div className="bg-white rounded-lg p-6 border-l-4 border-orange-500 shadow">
          <h3 className="text-xl font-bold mb-3 text-orange-600">
            📈 Technical Score
          </h3>
          <ul className="space-y-2 text-sm text-gray-700">
            <li>
              <strong>Midpoint:</strong> 50 (Neutral)
            </li>
            <li>
              <strong>&gt; 65:</strong> <span className="text-green-600">Bullish</span>
            </li>
            <li>
              <strong>&lt; 35:</strong> <span className="text-red-600">Bearish</span>
            </li>
            <li className="pt-2 text-xs text-gray-500">
              Based on EMA, TEMA, ZigZag pivots, BB crossovers, RSI, MACD, and price patterns.
            </li>
          </ul>
        </div>

        {/* Fundamental Score */}
        <div className="bg-white rounded-lg p-6 border-l-4 border-green-500 shadow">
          <h3 className="text-xl font-bold mb-3 text-green-600">
            💰 Fundamental Score
          </h3>
          <ul className="space-y-2 text-sm text-gray-700">
            <li>
              <strong>Midpoint:</strong> 50 (Fairly Valued)
            </li>
            <li>
              <strong>&gt; 70:</strong> <span className="text-green-600">Undervalued</span>
            </li>
            <li>
              <strong>&lt; 30:</strong> <span className="text-red-600">Overvalued</span>
            </li>
            <li className="pt-2 text-xs text-gray-500">
              Based on P/E ratio, ROE, revenue growth, and debt/equity ratio.
            </li>
          </ul>
        </div>

        {/* News Sentiment */}
        <div className="bg-white rounded-lg p-6 border-l-4 border-blue-500 shadow">
          <h3 className="text-xl font-bold mb-3 text-blue-600">
            📰 News Sentiment
          </h3>
          <ul className="space-y-2 text-sm text-gray-700">
            <li>
              <strong>Midpoint:</strong> 50 (Neutral)
            </li>
            <li>
              <strong>&gt; 65:</strong> <span className="text-green-600">Positive</span> news
            </li>
            <li>
              <strong>&lt; 35:</strong> <span className="text-red-600">Negative</span> news
            </li>
            <li className="pt-2 text-xs text-gray-500">
              Aggregated sentiment from recent news articles and market activity.
            </li>
          </ul>
        </div>

        {/* Valuation Percentile */}
        <div className="bg-white rounded-lg p-6 border-l-4 border-amber-500 shadow">
          <h3 className="text-xl font-bold mb-3 text-amber-600">
            📊 Valuation Percentile Penalty
          </h3>
          <ul className="space-y-2 text-sm text-gray-700">
            <li>
              <strong>≥ 92:</strong> <span className="text-red-600">−12 points</span> to Fundamental
            </li>
            <li>
              <strong>≥ 80:</strong> <span className="text-orange-600">−6 points</span> to Fundamental
            </li>
            <li className="pt-2 text-xs text-gray-500">
              Protects against overpaying in a sector. Adjusted during portfolio optimization.
            </li>
          </ul>
        </div>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <p className="text-sm text-blue-800">
          💡 <strong>Why Scores Matter:</strong> All three scores are calculated before
          the AI makes recommendations. This ensures the AI bases decisions on
          objective, reproducible measurements—not just subjective reasoning.
        </p>
      </div>
    </div>
  );
}

function SignalsTab() {
  const signals = [
    {
      level: "BUY",
      color: "green",
      bg: "bg-green-50 border-green-200",
      desc: "FA is strong AND TA is positive. Top-20% opportunity with valuation_percentile < 92. TA must NOT be bearish.",
      when: "Ready to deploy capital immediately.",
    },
    {
      level: "ACCUMULATE",
      color: "teal",
      bg: "bg-teal-50 border-teal-200",
      desc: "FA is strong, but TA is weak or neutral. Best for Dollar-Cost Averaging (DCA)—buy gradually over time, not all at once.",
      when: "Fundamentals are solid but technicals need work.",
    },
    {
      level: "WATCH",
      color: "blue",
      bg: "bg-blue-50 border-blue-200",
      desc: "Good fundamentals, technicals not ready. Valuation percentile < 75 and FA positive but TA neutral.",
      when: "Hold back and wait for a better entry signal or chart confirmation.",
    },
    {
      level: "HOLD",
      color: "gray",
      bg: "bg-gray-100 border-gray-300",
      desc: "Mixed or insufficient signals. No strong reason to add or reduce.",
      when: "Neither a buy nor a sell. Status quo is acceptable.",
    },
    {
      level: "REDUCE",
      color: "amber",
      bg: "bg-amber-50 border-amber-200",
      desc: "Position is overextended. TA strongly bearish on the holding OR valuation_percentile > 85.",
      when: "Begin trimming and taking profits.",
    },
    {
      level: "SELL",
      color: "red",
      bg: "bg-red-50 border-red-200",
      desc: "Exit immediately. FA is deteriorating OR TA score ≤ −3 OR major negative catalyst.",
      when: "Liquidate position to prevent further losses.",
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold mb-4 text-blue-600">
          🚦 Signal Guide (6 Levels)
        </h2>
        <p className="text-gray-700 mb-6">
          Each stock receives one of six trading signals, each with distinct
          investment guidance. The AI translates combined scores into these signals
          using strict rules.
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
          ⚠️ <strong>Golden Rule:</strong> The system NEVER assigns a BUY signal based
          on Fundamentals alone. Both FA strength AND TA confirmation are required for BUY.
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
          🧠 3-Layer Optimizer (Consensus Engine)
        </h2>
        <p className="text-gray-700 mb-6">
          Instead of relying on a single AI call, the optimizer runs three independent
          layers that check and balance each other. This multi-perspective approach
          reduces bias and improves portfolio recommendations.
        </p>
      </div>

      <div className="space-y-6">
        {/* Layer 1 */}
        <div className="bg-purple-50 border-l-4 border-purple-500 rounded-lg p-6 border shadow">
          <h3 className="text-2xl font-bold mb-2 text-purple-700">
            📋 Layer 1 — Strategist
          </h3>
          <p className="text-gray-700 mb-3">
            <strong>Primary Role:</strong> Architect of the main portfolio allocation.
          </p>
          <ul className="text-sm text-gray-700 space-y-2">
            <li>✓ Creates the foundational allocation plan</li>
            <li>✓ Proposes stock swaps (which holdings to exit, which to enter)</li>
            <li>✓ Ranks watchlist symbols by growth potential</li>
            <li>✓ Follows an <strong>Aggressive Growth</strong> strategy</li>
          </ul>
        </div>

        {/* Layer 2 */}
        <div className="bg-indigo-50 border-l-4 border-indigo-500 rounded-lg p-6 border shadow">
          <h3 className="text-2xl font-bold mb-2 text-indigo-700">
            🔍 Layer 2 — Challenger
          </h3>
          <p className="text-gray-700 mb-3">
            <strong>Primary Role:</strong> Independent reviewer and alternative strategist.
          </p>
          <ul className="text-sm text-gray-700 space-y-2">
            <li>✓ Reviews Layer 1's plan objectively</li>
            <li>✓ Searches for overlooked opportunities</li>
            <li>✓ Proposes risk-diversified alternatives</li>
            <li>✓ Either agrees with Layer 1 or suggests a different approach</li>
          </ul>
        </div>

        {/* Layer 3 */}
        <div className="bg-cyan-50 border-l-4 border-cyan-500 rounded-lg p-6 border shadow">
          <h3 className="text-2xl font-bold mb-2 text-cyan-700">
            ⚠️ Layer 3 — Risk Auditor
          </h3>
          <p className="text-gray-700 mb-3">
            <strong>Primary Role:</strong> Detect deep-level risks and concentration issues.
          </p>
          <ul className="text-sm text-gray-700 space-y-2">
            <li>✓ Flags sector concentration risks (Limit: 40% per sector)</li>
            <li>✓ Analyzes intra-sector stock correlations</li>
            <li>✓ Proposes safer alternatives or rebalancing</li>
            <li>✓ Provides risk severity ratings and remediation steps</li>
          </ul>
        </div>
      </div>

      {/* Consensus Engine */}
      <div className="bg-green-50 border border-green-200 rounded-lg p-6 shadow">
        <h3 className="text-2xl font-bold mb-2 text-green-700">
          🎯 Consensus Engine
        </h3>
        <p className="text-gray-700 mb-4">
          After all three layers submit their recommendations, a <strong>pure Python backend</strong> aggregates
          their votes and decisions:
        </p>
        <ul className="text-sm text-gray-700 space-y-2">
          <li>✓ Tallies agreement scores across layers</li>
          <li>✓ Enforces forced SELL for flagged holdings</li>
          <li>✓ Respects locked stock exclusions</li>
          <li>✓ Applies sector allocation caps (e.g., Tech ≤ 35%)</li>
          <li>✓ Ensures total allocation ≤ 100% (respects dry powder)</li>
          <li>✓ Outputs final swap recommendations and watchlist priority order</li>
        </ul>
      </div>

      <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
        <p className="text-sm text-orange-800">
          ⏱️ <strong>Performance Note:</strong> Each of the 3 layers makes one independent
          AI call. Expect the optimizer to take 30–60 seconds per full run.
        </p>
      </div>
    </div>
  );
}

function CachingTab() {
  const cacheStrategies = [
    {
      name: "Technical Data",
      ttl: "15 minutes",
      reason: "Price and chart patterns change frequently",
      scope: "EMA, TEMA, ZigZag, BB, MACD, RSI, OHLCV",
      color: "bg-orange-50 border-orange-200",
    },
    {
      name: "News Data",
      ttl: "1 hour",
      reason: "News articles arrive throughout the day",
      scope: "Recent articles, sentiment updates",
      color: "bg-blue-50 border-blue-200",
    },
    {
      name: "Fundamental Data",
      ttl: "24 hours",
      reason: "Earnings only update quarterly, ratios change slowly",
      scope: "P/E, ROE, revenue growth, debt/equity, dividends",
      color: "bg-green-50 border-green-200",
    },
    {
      name: "Analysis Cache (AI Summary)",
      ttl: "12 hours",
      reason: "AI signal should reflect latest data without constant reanalysis",
      scope: "Generated signal, reasoning, confidence",
      color: "bg-purple-50 border-purple-200",
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-3xl font-bold mb-4 text-blue-600">
          ⚡ Caching & Freshness
        </h2>
        <p className="text-gray-700 mb-6">
          The system caches data at multiple layers with different Time-To-Live (TTL)
          values. This balances responsiveness with API rate limits and computational
          efficiency. A <strong>freshness indicator</strong> (colored dot) shows you how
          recent each piece of data is.
        </p>
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

      {/* Freshness Indicator */}
      <div className="bg-white rounded-lg p-6 border border-gray-200 shadow">
        <h3 className="text-xl font-bold mb-4 text-gray-900">
          🟢 Freshness Indicator (Colored Dots)
        </h3>
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <span className="inline-flex h-4 w-4 rounded-full bg-green-500"></span>
            <span className="text-gray-700">
              <strong>Green:</strong> Data updated within the TTL (Fresh)
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="inline-flex h-4 w-4 rounded-full bg-yellow-500"></span>
            <span className="text-gray-700">
              <strong>Yellow:</strong> Data is aging, approaching stale threshold
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="inline-flex h-4 w-4 rounded-full bg-red-500"></span>
            <span className="text-gray-700">
              <strong>Red:</strong> Data is stale (exceeded TTL)
            </span>
          </div>
        </div>
      </div>

      {/* Batch Analysis */}
      <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-6 shadow">
        <h3 className="text-xl font-bold mb-3 text-indigo-700">
          📊 Batch Analysis ("Analyze All")
        </h3>
        <p className="text-gray-700 mb-3">
          The "Analyze All" button has its own 60-minute cache:
        </p>
        <ul className="text-sm text-gray-700 space-y-2">
          <li>✓ Skips symbols analyzed within the last 60 minutes</li>
          <li>✓ Only re-analyzes stale symbols</li>
          <li>✓ Reduces API calls and computation time</li>
          <li>✓ Perfect for overnight batch updates</li>
        </ul>
      </div>

      <div className="bg-teal-50 border border-teal-200 rounded-lg p-4">
        <p className="text-sm text-teal-800">
          💡 <strong>Pro Tip:</strong> If you need fresh data immediately, click
          "Analyze" on a specific stock to bypass the cache and fetch live data.
        </p>
      </div>
    </div>
  );
}
