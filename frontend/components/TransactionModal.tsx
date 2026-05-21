"use client";

import { useState, useEffect, useRef } from "react";
import type {
  BuyPayload,
  SellPayload,
  DepositPayload,
  WithdrawPayload,
  InitialPositionPayload,
  TransactionResult,
} from "@/lib/api";

export type TransactionMode = "buy" | "sell" | "deposit" | "withdraw" | "initial_position";

type Payload = BuyPayload | SellPayload | DepositPayload | WithdrawPayload | InitialPositionPayload;

interface Props {
  mode: TransactionMode;
  /** Pre-filled symbol (required for sell; optional for buy/initial_position — user can type) */
  symbol?: string;
  /** Current price pre-filled for buy/sell */
  currentPrice?: number | null;
  /** For sell: max shares the user can sell */
  maxShares?: number;
  /** Called with the filled-out payload; parent owns the API call */
  onConfirm: (payload: Payload) => Promise<TransactionResult>;
  onClose: () => void;
}

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

const MODE_CONFIG: Record<
  TransactionMode,
  { label: string; accent: string; accentLight: string; submitLabel: string }
> = {
  buy:              { label: "Buy",              accent: "#27500A", accentLight: "#27500A20", submitLabel: "Confirm Buy"      },
  sell:             { label: "Sell",             accent: "#854F0B", accentLight: "#854F0B20", submitLabel: "Confirm Sell"     },
  deposit:          { label: "Deposit",          accent: "#0C447C", accentLight: "#0C447C20", submitLabel: "Confirm Deposit"  },
  withdraw:         { label: "Withdraw",         accent: "#791F1F", accentLight: "#791F1F20", submitLabel: "Confirm Withdraw" },
  initial_position: { label: "Import Position",  accent: "#444441", accentLight: "#44444120", submitLabel: "Import"          },
};

export default function TransactionModal({
  mode,
  symbol: symbolProp,
  currentPrice,
  maxShares,
  onConfirm,
  onClose,
}: Props) {
  const cfg = MODE_CONFIG[mode];
  const isCash = mode === "deposit" || mode === "withdraw";
  const isEquity = mode === "buy" || mode === "sell" || mode === "initial_position";
  const isImport = mode === "initial_position";

  // Symbol is user-editable for "buy" and "initial_position" if not pre-provided
  const [symbolInput, setSymbolInput] = useState(symbolProp ?? "");
  const [shares, setShares] = useState("");
  const [price, setPrice] = useState(currentPrice != null ? String(currentPrice) : "");
  const [avgCost, setAvgCost] = useState("");    // for initial_position
  const [amount, setAmount] = useState("");       // for deposit/withdraw
  const [fees, setFees] = useState("0");
  const [date, setDate] = useState(today());
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<TransactionResult | null>(null);

  const firstInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    firstInputRef.current?.focus();
  }, []);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const sharesNum = parseFloat(shares) || 0;
  const priceNum  = parseFloat(price)  || 0;
  const avgNum    = parseFloat(avgCost) || 0;
  const amountNum = parseFloat(amount)  || 0;
  const feesNum   = parseFloat(fees)    || 0;

  const total = (() => {
    if (isCash) return amountNum;
    if (isImport) return sharesNum * avgNum;
    return sharesNum * priceNum + (mode === "buy" ? feesNum : -feesNum);
  })();

  const effectiveSymbol = (symbolProp ?? symbolInput).trim().toUpperCase();

  const canSubmit = (() => {
    if (submitting || result) return false;
    if (isCash) return amountNum > 0;
    if (isImport) return effectiveSymbol.length > 0 && sharesNum > 0 && avgNum > 0;
    // buy / sell
    if (!effectiveSymbol) return false;
    if (sharesNum <= 0 || priceNum <= 0 || feesNum < 0) return false;
    if (mode === "sell" && maxShares != null && sharesNum > maxShares) return false;
    return true;
  })();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    if (!canSubmit) return;
    setSubmitting(true);
    try {
      let payload: Payload;
      const txDate = date || undefined;
      const txNotes = notes.trim() || undefined;

      if (mode === "buy") {
        payload = {
          symbol: effectiveSymbol,
          shares: sharesNum,
          price_per_share: priceNum,
          fees: feesNum,
          transaction_date: txDate,
          notes: txNotes,
        } satisfies BuyPayload;
      } else if (mode === "sell") {
        payload = {
          symbol: effectiveSymbol,
          shares: sharesNum,
          price_per_share: priceNum,
          fees: feesNum,
          transaction_date: txDate,
          notes: txNotes,
          remove_if_zero: true,
        } satisfies SellPayload;
      } else if (mode === "deposit") {
        payload = {
          amount: amountNum,
          transaction_date: txDate,
          notes: txNotes,
        } satisfies DepositPayload;
      } else if (mode === "withdraw") {
        payload = {
          amount: amountNum,
          transaction_date: txDate,
          notes: txNotes,
        } satisfies WithdrawPayload;
      } else {
        payload = {
          symbol: effectiveSymbol,
          shares: sharesNum,
          avg_cost: avgNum,
          transaction_date: txDate,
          notes: txNotes,
        } satisfies InitialPositionPayload;
      }

      const res = await onConfirm(payload);
      setResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Transaction failed");
    } finally {
      setSubmitting(false);
    }
  }

  const symbolDisplay = effectiveSymbol || "—";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-sm mx-4 overflow-hidden">
        {/* Header */}
        <div
          className="px-5 py-4 flex items-center justify-between"
          style={{ backgroundColor: cfg.accentLight, borderBottom: `2px solid ${cfg.accent}30` }}
        >
          <div>
            <span className="text-xs font-bold uppercase tracking-widest" style={{ color: cfg.accent }}>
              {cfg.label}
            </span>
            {isEquity && (
              <h2 className="text-lg font-bold text-gray-900 leading-tight">
                {symbolDisplay.replace(".BK", "")}
                {symbolDisplay.endsWith(".BK") && (
                  <span className="ml-1 text-xs font-normal text-gray-400">.BK</span>
                )}
              </h2>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors text-xl leading-none"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {/* Success state */}
        {result ? (
          <div className="p-5 space-y-4">
            <div
              className="rounded-xl p-4 text-sm space-y-1.5"
              style={{ backgroundColor: cfg.accentLight }}
            >
              <div className="flex justify-between">
                <span className="text-gray-500">Type</span>
                <span className="font-semibold" style={{ color: cfg.accent }}>{result.type}</span>
              </div>
              {result.symbol && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Symbol</span>
                  <span className="font-medium">{result.symbol}</span>
                </div>
              )}
              {result.shares != null && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Shares</span>
                  <span className="font-medium">{result.shares}</span>
                </div>
              )}
              {result.price_per_share != null && (
                <div className="flex justify-between">
                  <span className="text-gray-500">Price</span>
                  <span className="font-medium">{result.price_per_share.toFixed(4)}</span>
                </div>
              )}
              <div className="flex justify-between">
                <span className="text-gray-500">{isCash ? "Amount" : "Total"}</span>
                <span className="font-semibold">{result.total_amount.toFixed(2)}</span>
              </div>
              {result.cash_balance != null && (
                <div className="flex justify-between border-t pt-1.5 mt-1.5">
                  <span className="text-gray-500">Cash balance</span>
                  <span className="font-medium">{result.cash_balance.toFixed(2)}</span>
                </div>
              )}
              {result.realized_pnl != null && (
                <div className="flex justify-between border-t pt-1.5 mt-1.5">
                  <span className="text-gray-500">Realized P&L</span>
                  <span
                    className="font-bold"
                    style={{ color: result.realized_pnl >= 0 ? "#27500A" : "#791F1F" }}
                  >
                    {result.realized_pnl >= 0 ? "+" : ""}
                    {result.realized_pnl.toFixed(2)}
                  </span>
                </div>
              )}
              {result.holding_removed && (
                <p className="text-xs text-gray-400 pt-1">Holding removed from portfolio.</p>
              )}
              {result.holding && !result.holding_removed && (
                <div className="border-t pt-1.5 mt-1.5 text-xs text-gray-500 space-y-0.5">
                  <div className="flex justify-between">
                    <span>Remaining shares</span>
                    <span>{result.holding.shares}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Avg cost</span>
                    <span>{result.holding.avg_cost.toFixed(4)}</span>
                  </div>
                </div>
              )}
            </div>
            <button
              onClick={onClose}
              className="w-full py-2 rounded-lg text-sm font-semibold text-white transition-opacity hover:opacity-90"
              style={{ backgroundColor: cfg.accent }}
            >
              Done
            </button>
          </div>
        ) : (
          /* Form */
          <form onSubmit={handleSubmit} className="p-5 space-y-3">

            {/* Symbol input — editable only when not pre-provided */}
            {isEquity && !symbolProp && (
              <div>
                <label className="block text-xs font-semibold text-gray-500 mb-1">Symbol</label>
                <input
                  ref={firstInputRef}
                  type="text"
                  value={symbolInput}
                  onChange={(e) => setSymbolInput(e.target.value.toUpperCase())}
                  placeholder="AAPL or SCB.BK"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                  required
                />
              </div>
            )}

            {/* Cash amount field (deposit / withdraw) */}
            {isCash && (
              <div>
                <label className="block text-xs font-semibold text-gray-500 mb-1">Amount</label>
                <input
                  ref={firstInputRef}
                  type="number"
                  step="any"
                  min="0.01"
                  value={amount}
                  onChange={(e) => setAmount(e.target.value)}
                  placeholder="0.00"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                  required
                />
              </div>
            )}

            {/* Shares — buy, sell, initial_position */}
            {isEquity && (
              <div>
                <label className="block text-xs font-semibold text-gray-500 mb-1">
                  Shares
                  {mode === "sell" && maxShares != null && (
                    <span className="ml-1 font-normal text-gray-400">(max {maxShares})</span>
                  )}
                </label>
                <input
                  ref={symbolProp ? firstInputRef : undefined}
                  type="number"
                  step="any"
                  min="0"
                  value={shares}
                  onChange={(e) => setShares(e.target.value)}
                  placeholder="0"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                  required
                />
              </div>
            )}

            {/* Price per share — buy / sell */}
            {(mode === "buy" || mode === "sell") && (
              <div>
                <label className="block text-xs font-semibold text-gray-500 mb-1">Price per share</label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  value={price}
                  onChange={(e) => setPrice(e.target.value)}
                  placeholder="0.00"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                  required
                />
              </div>
            )}

            {/* Avg cost — initial_position */}
            {isImport && (
              <div>
                <label className="block text-xs font-semibold text-gray-500 mb-1">Average cost</label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  value={avgCost}
                  onChange={(e) => setAvgCost(e.target.value)}
                  placeholder="0.00"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                  required
                />
              </div>
            )}

            {/* Fees — buy / sell only */}
            {(mode === "buy" || mode === "sell") && (
              <div>
                <label className="block text-xs font-semibold text-gray-500 mb-1">Fees / commission</label>
                <input
                  type="number"
                  step="any"
                  min="0"
                  value={fees}
                  onChange={(e) => setFees(e.target.value)}
                  placeholder="0"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
                />
              </div>
            )}

            {/* Date */}
            <div>
              <label className="block text-xs font-semibold text-gray-500 mb-1">Date</label>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
              />
            </div>

            {/* Notes */}
            <div>
              <label className="block text-xs font-semibold text-gray-500 mb-1">Notes (optional)</label>
              <input
                type="text"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder={isCash ? "e.g. Monthly top-up" : "e.g. DCA entry"}
                maxLength={200}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-300"
              />
            </div>

            {/* Total preview */}
            {total > 0 && (
              <div
                className="rounded-lg px-3 py-2 text-xs flex justify-between"
                style={{ backgroundColor: cfg.accentLight }}
              >
                <span className="text-gray-500">
                  {mode === "buy"    ? "Total cost"    :
                   mode === "sell"   ? "Net proceeds"  :
                   mode === "deposit" || mode === "initial_position" ? "Amount" : "Withdrawn"}
                </span>
                <span className="font-semibold" style={{ color: cfg.accent }}>
                  {Math.abs(total).toFixed(2)}
                </span>
              </div>
            )}

            {/* Oversell warning */}
            {mode === "sell" && maxShares != null && sharesNum > maxShares && (
              <p className="text-xs text-red-500">Cannot sell more than {maxShares} shares held.</p>
            )}

            {error && <p className="text-xs text-red-500 break-words">{error}</p>}

            <div className="flex gap-2 pt-1">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 py-2 rounded-lg text-sm font-semibold text-gray-500 bg-gray-100 hover:bg-gray-200 transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!canSubmit}
                className="flex-1 py-2 rounded-lg text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-40"
                style={{ backgroundColor: cfg.accent }}
              >
                {submitting ? "…" : cfg.submitLabel}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
