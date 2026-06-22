"use client";

import { useCallback, useState } from "react";
import { suggestPositionSizes, type PositionSizingResult } from "@/lib/api";
import PositionSizingResultView from "./PositionSizingResult";

const PLACEHOLDER = `NVDA01
MICRON01
BH`;

function parseSymbols(raw: string): string[] {
  return raw
    .split(/[\n,\s]+/)
    .map((s) => s.trim().toUpperCase())
    .filter(Boolean);
}

export default function PositionSizingCard({ portfolioId }: { portfolioId: number }) {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<PositionSizingResult | null>(null);

  const handleSize = useCallback(async () => {
    const symbols = parseSymbols(input);
    if (symbols.length === 0) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await suggestPositionSizes(portfolioId, symbols);
      if ((res as PositionSizingResult & { error?: string }).error) {
        setError((res as PositionSizingResult & { error?: string }).error!);
      } else {
        setResult(res);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Sizing failed");
    } finally {
      setLoading(false);
    }
  }, [input, portfolioId]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        handleSize();
      }
    },
    [handleSize],
  );

  const symbolCount = parseSymbols(input).length;

  return (
    <div className="rounded-2xl border-2 border-gray-200 bg-white p-5 space-y-4">
      {/* Header */}
      <div>
        <h3 className="text-sm font-bold text-gray-900">Position Sizing</h3>
        <p className="text-xs text-gray-400 mt-0.5">
          Sizes each idea by signal strength, confidence, fit, and priority — proportional allocation within constraints
        </p>
      </div>

      {/* Input */}
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

        <div className="flex items-center gap-2">
          <p className="text-[10px] text-gray-400 flex-1">
            {symbolCount > 0
              ? `${symbolCount} symbol${symbolCount !== 1 ? "s" : ""} · scored by signal × confidence × fit × priority`
              : "Ctrl+Enter to size"}
          </p>

          <button
            onClick={handleSize}
            disabled={loading || symbolCount === 0}
            className="flex items-center gap-1.5 rounded-lg bg-gray-900 px-4 py-1.5 text-xs font-semibold
                       text-white transition hover:bg-gray-700 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {loading ? (
              <>
                <span className="inline-block h-3 w-3 rounded-full border-2 border-white border-t-transparent animate-spin" />
                Sizing…
              </>
            ) : (
              "Suggest Sizes"
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
      {result !== null && !loading && <PositionSizingResultView result={result} />}
    </div>
  );
}
