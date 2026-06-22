"use client";

import { useCallback, useState } from "react";
import { simulateBasket, type BasketSimulationResult } from "@/lib/api";
import BasketSimulationResultView from "./BasketSimulationResult";

const PLACEHOLDER = `NVDA01
GOOGL01
MICRON01
BH`;

function parseSymbols(raw: string): string[] {
  return raw
    .split(/[\n,\s]+/)
    .map((s) => s.trim().toUpperCase())
    .filter(Boolean);
}

export default function BasketSimulationCard({ portfolioId }: { portfolioId: number }) {
  const [input, setInput] = useState("");
  const [allocationPct, setAllocationPct] = useState("5");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BasketSimulationResult | null>(null);

  const handleSimulate = useCallback(async () => {
    const symbols = parseSymbols(input);
    if (symbols.length === 0) return;

    const pct = parseFloat(allocationPct);
    if (isNaN(pct) || pct <= 0 || pct > 100) {
      setError("Allocation must be between 0 and 100");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await simulateBasket(portfolioId, symbols, pct);
      if ((res as BasketSimulationResult & { error?: string }).error) {
        setError((res as BasketSimulationResult & { error?: string }).error!);
      } else {
        setResult(res);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Simulation failed");
    } finally {
      setLoading(false);
    }
  }, [input, allocationPct, portfolioId]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        handleSimulate();
      }
    },
    [handleSimulate],
  );

  const symbolCount = parseSymbols(input).length;

  return (
    <div className="rounded-2xl border-2 border-gray-200 bg-white p-5 space-y-4">
      {/* Header */}
      <div>
        <h3 className="text-sm font-bold text-gray-900">Basket Simulation</h3>
        <p className="text-xs text-gray-400 mt-0.5">
          Simulate purchasing a basket of symbols — see sector and cash impact before executing
        </p>
      </div>

      {/* Input area */}
      <div className="space-y-2">
        <textarea
          className="w-full h-24 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm font-mono
                     text-gray-800 placeholder:text-gray-300 focus:outline-none focus:ring-2
                     focus:ring-blue-300 resize-none"
          placeholder={PLACEHOLDER}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
          spellCheck={false}
        />

        {/* Allocation input + button row */}
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 rounded-lg border border-gray-200 bg-gray-50 px-3 py-1.5">
            <label className="text-[10px] text-gray-500 font-medium whitespace-nowrap">
              % per position
            </label>
            <input
              type="number"
              min="0.1"
              max="100"
              step="0.5"
              value={allocationPct}
              onChange={(e) => setAllocationPct(e.target.value)}
              disabled={loading}
              className="w-14 bg-transparent text-sm font-mono font-semibold text-gray-800
                         focus:outline-none text-right"
            />
          </div>

          <div className="flex-1" />

          <p className="text-[10px] text-gray-400">
            {symbolCount > 0
              ? `${symbolCount} symbol${symbolCount !== 1 ? "s" : ""} · ${(
                  symbolCount * parseFloat(allocationPct || "0")
                ).toFixed(1)}% total`
              : "Ctrl+Enter to simulate"}
          </p>

          <button
            onClick={handleSimulate}
            disabled={loading || symbolCount === 0}
            className="flex items-center gap-1.5 rounded-lg bg-gray-900 px-4 py-1.5 text-xs font-semibold
                       text-white transition hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <span className="inline-block h-3 w-3 rounded-full border-2 border-white border-t-transparent animate-spin" />
                Simulating…
              </>
            ) : (
              "Simulate Basket"
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

      {/* Result */}
      {result !== null && !loading && (
        <BasketSimulationResultView result={result} />
      )}
    </div>
  );
}
