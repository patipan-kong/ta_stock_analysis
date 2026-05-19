import Link from "next/link";
import SignalBadge from "./SignalBadge";
import type { FullAnalysis } from "@/lib/api";

export default function StockCard({ analysis }: { analysis: FullAnalysis }) {
  const { symbol, technical, fundamental, summary } = analysis;
  const displaySymbol = symbol.replace(".BK", "");

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-3">
        <Link href={`/stock/${encodeURIComponent(symbol)}`} className="text-lg font-bold text-blue-600 hover:underline">
          {displaySymbol}
          {symbol.endsWith(".BK") && <span className="ml-1 text-xs text-gray-400">.BK</span>}
        </Link>
        {summary && "signal" in summary && !("error" in summary) && (
          <SignalBadge signal={(summary as { signal: string }).signal} />
        )}
      </div>

      <div className="grid grid-cols-2 gap-2 text-sm text-gray-600">
        {technical && "ta_score" in technical && (
          <div><span className="font-medium">TA Score:</span> {technical.ta_score}</div>
        )}
        {fundamental && "fa_score" in fundamental && (
          <div><span className="font-medium">FA Score:</span> {fundamental.fa_score}</div>
        )}
        {technical && "rsi" in technical && technical.rsi !== null && (
          <div><span className="font-medium">RSI:</span> {technical.rsi}</div>
        )}
        {fundamental && "pe_ratio" in fundamental && fundamental.pe_ratio !== null && (
          <div><span className="font-medium">P/E:</span> {fundamental.pe_ratio}</div>
        )}
      </div>

      {summary && "reasoning" in summary && (
        <p className="mt-2 text-xs text-gray-500 line-clamp-2">{(summary as { reasoning: string }).reasoning}</p>
      )}
    </div>
  );
}
