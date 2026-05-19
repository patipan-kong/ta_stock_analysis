"use client";

import { useEffect, useMemo, useState } from "react";
import { getModelCostReport, type ModelCostReport } from "@/lib/api";

type TabType = "analyze" | "optimize";

function fmtUsd(n: number): string {
  return `$${n.toFixed(4)}`;
}

function fmtThb(n: number): string {
  return `฿${n.toLocaleString("th-TH", { maximumFractionDigits: 2 })}`;
}

function fmtMonth(yyyyMm: string): string {
  const [y, m] = yyyyMm.split("-").map(Number);
  return new Date(y, m - 1, 1).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
  });
}

export default function ModelCostReportPage() {
  const now = useMemo(() => new Date(), []);
  const [year, setYear] = useState<number>(now.getFullYear());
  const [month, setMonth] = useState<number>(now.getMonth() + 1);
  const [activeTab, setActiveTab] = useState<TabType>("analyze");
  const [report, setReport] = useState<ModelCostReport | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const data = await getModelCostReport(year, month);
        if (!cancelled) setReport(data);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load report");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [year, month]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Model Cost Report</h1>
        <p className="text-sm text-gray-500 mt-1">
          Estimated token usage and spend from your own AI calls (Analyze + Optimizer layers)
        </p>
      </div>

      <div className="bg-white border rounded-xl p-4 shadow-sm flex flex-wrap items-end gap-3">
        <div>
          <label className="block text-xs text-gray-500 mb-1">Year</label>
          <input
            type="number"
            className="border rounded px-3 py-2 text-sm w-28"
            value={year}
            onChange={(e) => setYear(Number(e.target.value || now.getFullYear()))}
          />
        </div>
        <div>
          <label className="block text-xs text-gray-500 mb-1">Month</label>
          <select
            className="border rounded px-3 py-2 text-sm w-36 bg-white"
            value={month}
            onChange={(e) => setMonth(Number(e.target.value))}
          >
            {Array.from({ length: 12 }).map((_, i) => (
              <option key={i + 1} value={i + 1}>
                {new Date(2000, i, 1).toLocaleDateString("en-US", { month: "long" })}
              </option>
            ))}
          </select>
        </div>
        <div className="ml-auto text-xs text-gray-400">
          Currency base: USD | FX: {report ? report.fx.usd_to_thb : "..."} THB / USD
        </div>
      </div>

      <div className="flex items-center gap-2">
        <button
          className={`px-4 py-2 rounded-lg text-sm font-semibold ${
            activeTab === "analyze" ? "bg-blue-600 text-white" : "bg-white border text-gray-700"
          }`}
          onClick={() => setActiveTab("analyze")}
        >
          Analyze Cost
        </button>
        <button
          className={`px-4 py-2 rounded-lg text-sm font-semibold ${
            activeTab === "optimize" ? "bg-blue-600 text-white" : "bg-white border text-gray-700"
          }`}
          onClick={() => setActiveTab("optimize")}
        >
          Optimizer Cost
        </button>
      </div>

      {loading && <div className="text-sm text-gray-500">Loading report...</div>}
      {error && <div className="text-sm text-red-600">{error}</div>}

      {!loading && !error && report && (
        <>
          <div className="bg-white border rounded-xl p-5 shadow-sm">
            <h2 className="text-lg font-semibold text-gray-900">
              {activeTab === "analyze" ? "Analyze Summary" : "Optimizer Summary"} - {fmtMonth(report.month)}
            </h2>
            <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
              <div className="bg-gray-50 rounded-lg p-4 border">
                <p className="text-xs text-gray-500">Month Total (USD)</p>
                <p className="text-xl font-bold text-gray-900">
                  {activeTab === "analyze"
                    ? fmtUsd(report.analyze.month_total_usd)
                    : fmtUsd(report.optimize.month_total_usd)}
                </p>
              </div>
              <div className="bg-gray-50 rounded-lg p-4 border">
                <p className="text-xs text-gray-500">Month Total (THB)</p>
                <p className="text-xl font-bold text-gray-900">
                  {activeTab === "analyze"
                    ? fmtThb(report.analyze.month_total_thb)
                    : fmtThb(report.optimize.month_total_thb)}
                </p>
              </div>
            </div>
          </div>

          {activeTab === "analyze" ? (
            <>
              <section className="bg-white border rounded-xl p-5 shadow-sm overflow-auto">
                <h3 className="font-semibold text-gray-900 mb-3">Daily Analyze Usage</h3>
                <table className="w-full text-sm min-w-[820px]">
                  <thead>
                    <tr className="text-left text-gray-500 border-b">
                      <th className="py-2">Date</th>
                      <th className="py-2">Provider</th>
                      <th className="py-2">Model</th>
                      <th className="py-2">Input</th>
                      <th className="py-2">Output</th>
                      <th className="py-2">Total Tokens</th>
                      <th className="py-2">USD</th>
                      <th className="py-2">THB</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.analyze.daily.length === 0 && (
                      <tr>
                        <td colSpan={8} className="py-4 text-gray-400">No analyze usage in this month.</td>
                      </tr>
                    )}
                    {report.analyze.daily.map((r, i) => (
                      <tr key={`${r.date}-${r.model}-${i}`} className="border-b last:border-b-0">
                        <td className="py-2">{r.date}</td>
                        <td className="py-2">{r.provider}</td>
                        <td className="py-2">{r.model}</td>
                        <td className="py-2">{r.input_tokens.toLocaleString()}</td>
                        <td className="py-2">{r.output_tokens.toLocaleString()}</td>
                        <td className="py-2">{r.total_tokens.toLocaleString()}</td>
                        <td className="py-2">{fmtUsd(r.total_cost_usd)}</td>
                        <td className="py-2">{fmtThb(r.total_cost_thb)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>

              <section className="bg-white border rounded-xl p-5 shadow-sm overflow-auto">
                <h3 className="font-semibold text-gray-900 mb-3">Analyze Monthly by Model</h3>
                <table className="w-full text-sm min-w-[760px]">
                  <thead>
                    <tr className="text-left text-gray-500 border-b">
                      <th className="py-2">Provider</th>
                      <th className="py-2">Model</th>
                      <th className="py-2">Input</th>
                      <th className="py-2">Output</th>
                      <th className="py-2">Total Tokens</th>
                      <th className="py-2">USD</th>
                      <th className="py-2">THB</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.analyze.by_model_month.length === 0 && (
                      <tr>
                        <td colSpan={7} className="py-4 text-gray-400">No data.</td>
                      </tr>
                    )}
                    {report.analyze.by_model_month.map((r, i) => (
                      <tr key={`${r.provider}-${r.model}-${i}`} className="border-b last:border-b-0">
                        <td className="py-2">{r.provider}</td>
                        <td className="py-2">{r.model}</td>
                        <td className="py-2">{r.input_tokens.toLocaleString()}</td>
                        <td className="py-2">{r.output_tokens.toLocaleString()}</td>
                        <td className="py-2">{r.total_tokens.toLocaleString()}</td>
                        <td className="py-2">{fmtUsd(r.total_cost_usd)}</td>
                        <td className="py-2">{fmtThb(r.total_cost_thb)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            </>
          ) : (
            <>
              <section className="bg-white border rounded-xl p-5 shadow-sm overflow-auto">
                <h3 className="font-semibold text-gray-900 mb-3">Daily Optimizer Usage (By Layer)</h3>
                <table className="w-full text-sm min-w-[860px]">
                  <thead>
                    <tr className="text-left text-gray-500 border-b">
                      <th className="py-2">Date</th>
                      <th className="py-2">Layer</th>
                      <th className="py-2">Provider</th>
                      <th className="py-2">Model</th>
                      <th className="py-2">Input</th>
                      <th className="py-2">Output</th>
                      <th className="py-2">Total Tokens</th>
                      <th className="py-2">USD</th>
                      <th className="py-2">THB</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.optimize.daily.length === 0 && (
                      <tr>
                        <td colSpan={9} className="py-4 text-gray-400">No optimizer usage in this month.</td>
                      </tr>
                    )}
                    {report.optimize.daily.map((r, i) => (
                      <tr key={`${r.date}-${r.layer}-${r.model}-${i}`} className="border-b last:border-b-0">
                        <td className="py-2">{r.date}</td>
                        <td className="py-2">{r.layer || "-"}</td>
                        <td className="py-2">{r.provider}</td>
                        <td className="py-2">{r.model}</td>
                        <td className="py-2">{r.input_tokens.toLocaleString()}</td>
                        <td className="py-2">{r.output_tokens.toLocaleString()}</td>
                        <td className="py-2">{r.total_tokens.toLocaleString()}</td>
                        <td className="py-2">{fmtUsd(r.total_cost_usd)}</td>
                        <td className="py-2">{fmtThb(r.total_cost_thb)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>

              <section className="bg-white border rounded-xl p-5 shadow-sm overflow-auto">
                <h3 className="font-semibold text-gray-900 mb-3">Optimizer Monthly by Model + Layer</h3>
                <table className="w-full text-sm min-w-[840px]">
                  <thead>
                    <tr className="text-left text-gray-500 border-b">
                      <th className="py-2">Layer</th>
                      <th className="py-2">Provider</th>
                      <th className="py-2">Model</th>
                      <th className="py-2">Input</th>
                      <th className="py-2">Output</th>
                      <th className="py-2">Total Tokens</th>
                      <th className="py-2">USD</th>
                      <th className="py-2">THB</th>
                    </tr>
                  </thead>
                  <tbody>
                    {report.optimize.by_model_layer_month.length === 0 && (
                      <tr>
                        <td colSpan={8} className="py-4 text-gray-400">No data.</td>
                      </tr>
                    )}
                    {report.optimize.by_model_layer_month.map((r, i) => (
                      <tr key={`${r.layer}-${r.provider}-${r.model}-${i}`} className="border-b last:border-b-0">
                        <td className="py-2">{r.layer || "-"}</td>
                        <td className="py-2">{r.provider}</td>
                        <td className="py-2">{r.model}</td>
                        <td className="py-2">{r.input_tokens.toLocaleString()}</td>
                        <td className="py-2">{r.output_tokens.toLocaleString()}</td>
                        <td className="py-2">{r.total_tokens.toLocaleString()}</td>
                        <td className="py-2">{fmtUsd(r.total_cost_usd)}</td>
                        <td className="py-2">{fmtThb(r.total_cost_thb)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </section>
            </>
          )}
        </>
      )}
    </div>
  );
}
