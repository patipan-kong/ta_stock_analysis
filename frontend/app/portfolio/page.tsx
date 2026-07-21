"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import PortfolioTable from "@/components/PortfolioTable";
import PortfolioTabs from "@/components/PortfolioTabs";
import PortfolioSummary from "@/components/PortfolioSummary";
import { usePortfolio } from "@/lib/PortfolioContext";
import WorkspaceScopeSwitcher from "@/components/WorkspaceScopeSwitcher";
import AnalyzeAllButton from "@/components/AnalyzeAllButton";
import TransactionModal from "@/components/TransactionModal";
import type { TransactionMode } from "@/components/TransactionModal";
import {
  getHoldings, removeHolding, analyzeSymbol, updateSwapPermission,
  getPortfolioPrices, getSectorBreakdown,
  buyTransaction, sellTransaction, depositTransaction, withdrawTransaction,
  initialPositionTransaction, dividendTransaction,
  isUnresolvedPortfolioError,
} from "@/lib/api";
import type {
  PortfolioItem, AnalyzeAllResult, SectorBreakdown,
  BuyPayload, SellPayload, DepositPayload, WithdrawPayload,
  InitialPositionPayload, DividendPayload, TransactionResult,
} from "@/lib/api";

const PortfolioPieChart = dynamic(
  () => import("@/components/PortfolioPieChart"),
  { ssr: false, loading: () => <div className="h-[280px] animate-pulse bg-gray-100 rounded-xl" /> }
);

const SectorPieChart = dynamic(
  () => import("@/components/SectorPieChart"),
  { ssr: false, loading: () => <div className="h-[280px] animate-pulse bg-gray-100 rounded-xl" /> }
);

const PRICE_REFRESH_INTERVAL = 60_000;

function useSecondsAgo(since: Date | null): number {
  const [secs, setSecs] = useState(0);
  useEffect(() => {
    if (!since) { setSecs(0); return; }
    setSecs(Math.floor((Date.now() - since.getTime()) / 1000));
    const id = setInterval(
      () => setSecs(Math.floor((Date.now() - since.getTime()) / 1000)),
      1000
    );
    return () => clearInterval(id);
  }, [since]);
  return secs;
}

// ─── Toast ────────────────────────────────────────────────────────────────────

function Toast({ message, kind, onDone }: { message: string; kind: "success" | "error"; onDone: () => void }) {
  useEffect(() => {
    const t = setTimeout(onDone, 3500);
    return () => clearTimeout(t);
  }, [onDone]);
  return (
    <div
      className={`fixed bottom-6 right-6 z-[100] px-4 py-3 rounded-xl shadow-lg text-sm font-medium text-white max-w-xs ${kind === "success" ? "bg-green-700" : "bg-red-700"}`}
    >
      {message}
    </div>
  );
}

// ─── Modal state ──────────────────────────────────────────────────────────────

interface ModalState {
  mode: TransactionMode;
  symbol?: string;
  currentPrice?: number | null;
  maxShares?: number;
}

export default function PortfolioPage() {
  const { portfolios, currentSelection, createPortfolio, deletePortfolio, refreshPortfolios, reportUnresolvedPortfolio, loading: ctxLoading } = usePortfolio();

  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [confirmDelete, setConfirmDelete] = useState(false);

  const activePortfolio = portfolios.find((p) => p.id === currentSelection);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    const name = newName.trim();
    if (!name) return;
    // M36.1 WP4A F02 — creation and selection are separate interaction
    // boundaries. The new portfolio is exposed through the list only;
    // Current Selection (NONE or a prior valid selection) is untouched
    // until a human explicitly selects it via WorkspaceScopeSwitcher.
    await createPortfolio(name);
    setNewName("");
    setCreating(false);
  }

  async function handleDelete() {
    if (currentSelection == null) return;
    await deletePortfolio(currentSelection);
    setConfirmDelete(false);
  }

  const [items, setItems] = useState<PortfolioItem[]>([]);
  const [cashBalance, setCashBalance] = useState(0);
  const [loading, setLoading] = useState(false);
  const [pricesLoading, setPricesLoading] = useState(false);

  // Import flow
  const [showImport, setShowImport] = useState(false);

  // Price refresh
  const [sectorBreakdown, setSectorBreakdown] = useState<SectorBreakdown | null>(null);
  const [refreshingPrices, setRefreshingPrices] = useState(false);
  const [priceRefreshAt, setPriceRefreshAt] = useState<Date | null>(null);
  const secondsAgo = useSecondsAgo(priceRefreshAt);
  const activeIdRef = useRef<number | null>(null);
  const refreshingRef = useRef(false);

  // Toast
  const [toast, setToast] = useState<{ message: string; kind: "success" | "error" } | null>(null);

  // Active transaction modal
  const [modal, setModal] = useState<ModalState | null>(null);

  // Shared helper — patches price fields (including upside_pct) onto items list
  function applyPrices(prev: PortfolioItem[], prices: Awaited<ReturnType<typeof getPortfolioPrices>>) {
    return prev.map((item) => {
      const p = prices.find((x) => x.symbol === item.symbol);
      return p
        ? { ...item, current_price: p.current_price, previous_close: p.previous_close, change_percent: p.change_percent,
            last_updated: p.last_updated, upside_pct: p.upside_pct ?? item.upside_pct }
        : item;
    });
  }

  const refreshPrices = useCallback(async (pid: number) => {
    if (refreshingRef.current) return;
    refreshingRef.current = true;
    setRefreshingPrices(true);
    try {
      const prices = await getPortfolioPrices(pid);
      // M36.1 WP4C F04 — discard a manually-triggered refresh's response if
      // Current Selection has since moved away from the portfolio it was
      // issued for.
      if (activeIdRef.current !== pid) return;
      setItems((prev) => applyPrices(prev, prices));
      setPriceRefreshAt(new Date());
    } catch {
      // silent
    } finally {
      refreshingRef.current = false;
      setRefreshingPrices(false);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function refreshHoldings(pid: number) {
    const [updated, breakdown] = await Promise.all([
      getHoldings(pid),
      getSectorBreakdown(pid).catch(() => null),
    ]);
    // M36.1 WP4C F04 — discard this response if Current Selection has since
    // moved away from the portfolio the transaction/refresh was issued for.
    if (activeIdRef.current !== pid) return;
    setItems(updated);
    if (breakdown) setSectorBreakdown(breakdown);
    // Fetch prices in background — non-blocking
    getPortfolioPrices(pid)
      .then((prices) => {
        if (activeIdRef.current !== pid) return;
        setItems((prev) => applyPrices(prev, prices));
        setPriceRefreshAt(new Date());
      })
      .catch(() => {});
  }

  // Initial load — Phase 1: holdings from DB (< 500 ms), Phase 2: prices in background
  useEffect(() => {
    if (currentSelection == null) {
      // M36.1 WP4A F04 — Current Selection is NONE: synchronously clear
      // portfolio-bound state and invalidate the request identity so any
      // still-in-flight response for the previous portfolio is dropped by
      // the activeIdRef checks below instead of repopulating the page.
      activeIdRef.current = null;
      setItems([]);
      setSectorBreakdown(null);
      setCashBalance(0);
      setPriceRefreshAt(null);
      setLoading(false);
      setPricesLoading(false);
      return;
    }
    activeIdRef.current = currentSelection;
    setLoading(true);
    setPricesLoading(false);
    setItems([]);
    setSectorBreakdown(null);
    setPriceRefreshAt(null);
    const cash = activePortfolio?.cash_balance ?? 0;
    setCashBalance(cash);

    const pid = currentSelection;
    getHoldings(pid)
      .then((data) => {
        if (activeIdRef.current !== pid) return;
        setItems(data);
        setLoading(false);

        // Phase 2: prices + sector breakdown concurrently (non-blocking)
        setPricesLoading(true);
        const pricesP = getPortfolioPrices(pid)
          .then((prices) => {
            if (activeIdRef.current !== pid) return;
            setItems((prev) => applyPrices(prev, prices));
            setPriceRefreshAt(new Date());
          })
          .catch(() => {});
        const sectorP = getSectorBreakdown(pid)
          .then((bd) => { if (activeIdRef.current === pid) setSectorBreakdown(bd); })
          .catch(() => {});
        Promise.all([pricesP, sectorP]).finally(() => {
          if (activeIdRef.current === pid) setPricesLoading(false);
        });
      })
      .catch((e) => {
        setLoading(false);
        // M36.1 WP4A F03 — bounded unresolved-response recovery: only an
        // authoritative "Portfolio not found" for the currently-selected
        // portfolio triggers re-resolution. A generic fetch failure never
        // clears Current Selection.
        if (isUnresolvedPortfolioError(e)) reportUnresolvedPortfolio(pid);
      });
  }, [currentSelection]); // eslint-disable-line react-hooks/exhaustive-deps

  // Sync cash from context
  useEffect(() => {
    if (activePortfolio) setCashBalance(activePortfolio.cash_balance ?? 0);
  }, [activePortfolio]);

  // Auto-refresh prices every 60s
  useEffect(() => {
    if (currentSelection == null) return;
    const id = setInterval(async () => {
      const pid = activeIdRef.current;
      if (pid == null || refreshingRef.current) return;
      refreshingRef.current = true;
      setRefreshingPrices(true);
      try {
        const prices = await getPortfolioPrices(pid);
        // M36.1 WP4C F04 — the interval captures pid from activeIdRef at
        // fire time, but Current Selection can still move during the await;
        // re-check before writing so a slow response for the old portfolio
        // never patches prices onto the now-different portfolio's items.
        if (activeIdRef.current !== pid) return;
        setItems((prev) => applyPrices(prev, prices));
        setPriceRefreshAt(new Date());
      } catch { /* silent */ } finally {
        refreshingRef.current = false;
        setRefreshingPrices(false);
      }
    }, PRICE_REFRESH_INTERVAL);
    return () => clearInterval(id);
  }, [currentSelection]); // eslint-disable-line react-hooks/exhaustive-deps

  // ─── Transaction handlers ──────────────────────────────────────────────────

  async function handleTransactionConfirm(
    payload: BuyPayload | SellPayload | DepositPayload | WithdrawPayload | InitialPositionPayload | DividendPayload
  ): Promise<TransactionResult> {
    if (currentSelection == null) throw new Error("No active portfolio");
    if (!modal) throw new Error("No active modal");

    let result: TransactionResult;
    switch (modal.mode) {
      case "buy":
        result = await buyTransaction(currentSelection, payload as BuyPayload);
        break;
      case "sell":
        result = await sellTransaction(currentSelection, payload as SellPayload);
        break;
      case "deposit":
        result = await depositTransaction(currentSelection, payload as DepositPayload);
        break;
      case "withdraw":
        result = await withdrawTransaction(currentSelection, payload as WithdrawPayload);
        break;
      case "initial_position":
        result = await initialPositionTransaction(currentSelection, payload as InitialPositionPayload);
        break;
      case "dividend":
        result = await dividendTransaction(currentSelection, payload as DividendPayload);
        break;
    }

    await refreshHoldings(currentSelection);
    await refreshPortfolios();
    if (result.cash_balance != null) setCashBalance(result.cash_balance);

    return result;
  }

  function handleModalClose() {
    setModal(null);
    setShowImport(false);
  }

  async function handleRemove(sym: string) {
    if (currentSelection == null) return;
    await removeHolding(currentSelection, sym);
    setItems((prev) => prev.filter((i) => i.symbol !== sym));
  }

  async function handleToggleSwap(sym: string, allow_swap: boolean) {
    if (currentSelection == null) return;
    await updateSwapPermission(currentSelection, sym, allow_swap);
    setItems((prev) => prev.map((i) => i.symbol === sym ? { ...i, allow_swap } : i));
  }

  function handleAnalyzeAllComplete(result: AnalyzeAllResult) {
    setItems((prev) =>
      prev.map((item) => {
        const r = result.results.find((x) => x.symbol === item.symbol);
        if (!r?.summary || "error" in r.summary) return item;
        const s = r.summary as { signal?: string; confidence?: string; analyzed_at?: string | null };
        return {
          ...item,
          latest_signal: (s.signal ?? item.latest_signal) as PortfolioItem["latest_signal"],
          signal_confidence: (s.confidence ?? item.signal_confidence) as PortfolioItem["signal_confidence"],
          analyzed_at: s.analyzed_at ?? item.analyzed_at,
        };
      })
    );
  }

  async function handleReanalyze(sym: string) {
    const result = await analyzeSymbol(sym);
    const summary = result.summary as { signal?: string; confidence?: string };
    setItems((prev) =>
      prev.map((i) =>
        i.symbol === sym
          ? {
              ...i,
              latest_signal: (summary.signal ?? null) as PortfolioItem["latest_signal"],
              signal_confidence: (summary.confidence ?? null) as PortfolioItem["signal_confidence"],
              analyzed_at: new Date().toISOString(),
            }
          : i
      )
    );
  }

  const hasData = items.length > 0;
  const isLoading = ctxLoading || loading;
  const staleCount = items.filter((i) => {
    if (!i.analyzed_at) return true;
    return (Date.now() - new Date(i.analyzed_at).getTime()) / 60000 > 60;
  }).length;

  const priceLabel = (() => {
    if (refreshingPrices) return "Refreshing…";
    if (!priceRefreshAt) return null;
    if (secondsAgo < 60) return `Updated ${secondsAgo}s ago`;
    return `Updated ${Math.floor(secondsAgo / 60)}m ago`;
  })();

  return (
    <div className="space-y-6">
      {/* ── Portfolio hub tabs (Phase 4C.2A) ── */}
      <PortfolioTabs />

      {/* ── Portfolio selector row ── */}
      <div className="flex items-center gap-2 flex-wrap">
        {creating ? (
          <form onSubmit={handleCreate} className="flex items-center gap-1.5">
            <input
              autoFocus
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              placeholder="Portfolio name"
              className="text-sm border rounded px-2.5 py-1.5 w-40"
            />
            <button type="submit" className="text-xs bg-blue-600 text-white px-3 py-1.5 rounded hover:bg-blue-700">
              Save
            </button>
            <button
              type="button"
              onClick={() => { setCreating(false); setNewName(""); }}
              className="text-xs text-gray-400 hover:text-gray-600 px-1"
            >
              ✕
            </button>
          </form>
        ) : confirmDelete ? (
          <div className="flex items-center gap-2 text-sm">
            <span className="text-gray-500">Delete &quot;{activePortfolio?.name}&quot;?</span>
            <button onClick={handleDelete} className="text-xs bg-red-600 text-white px-2.5 py-1 rounded hover:bg-red-700">
              Yes
            </button>
            <button onClick={() => setConfirmDelete(false)} className="text-xs text-gray-400 hover:text-gray-600">
              Cancel
            </button>
          </div>
        ) : (
          <>
            <WorkspaceScopeSwitcher variant="select" noneLabel="No portfolio selected" />
            <button
              onClick={() => setCreating(true)}
              className="text-sm border rounded px-2.5 py-1.5 hover:bg-gray-50 text-gray-600"
            >
              + New
            </button>
            {portfolios.length > 1 && (
              <button
                onClick={() => setConfirmDelete(true)}
                className="text-sm border border-red-200 rounded px-2.5 py-1.5 hover:bg-red-50 text-red-400"
              >
                Delete
              </button>
            )}
          </>
        )}
      </div>

      {/* ── Header + action buttons ── */}
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">Portfolio</h1>
          {currentSelection != null && (
            <Link
              href={`/portfolio/${currentSelection}/factors`}
              className="flex items-center gap-1.5 text-xs font-semibold text-purple-700 bg-purple-50 hover:bg-purple-100 border border-purple-200 rounded-lg px-3 py-1.5 transition-colors"
            >
              <span>◈</span> DNA Analysis
            </Link>
          )}
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          {hasData && currentSelection != null && (
            <AnalyzeAllButton
              type="portfolio"
              portfolioId={currentSelection}
              staleCount={staleCount}
              totalCount={items.length}
              onComplete={handleAnalyzeAllComplete}
            />
          )}
          {hasData && (
            <div className="flex items-center gap-2 text-xs text-gray-400">
              {priceLabel && <span>{priceLabel}</span>}
              <button
                onClick={() => currentSelection != null && refreshPrices(currentSelection)}
                disabled={refreshingPrices || currentSelection == null}
                className="flex items-center gap-1 text-blue-500 hover:text-blue-700 disabled:opacity-40 border border-blue-200 rounded px-2.5 py-1 hover:bg-blue-50 transition-colors"
              >
                <span className={refreshingPrices ? "animate-spin inline-block" : ""}>↻</span>
                Refresh Prices
              </button>
            </div>
          )}
        </div>
      </div>

      {/* ── Transaction action buttons ── */}
      <div className="flex flex-wrap gap-2">
        <button
          disabled={currentSelection == null}
          onClick={() => setModal({ mode: "buy" })}
          className="px-4 py-1.5 rounded text-sm font-semibold text-white bg-[#27500A] hover:bg-[#1d3c07] disabled:opacity-40 transition-colors"
        >
          Buy
        </button>
        <button
          disabled={currentSelection == null || items.length === 0}
          onClick={() => {
            // If only one holding, pre-select it; otherwise let user pick in modal
            if (items.length === 1) {
              setModal({ mode: "sell", symbol: items[0].symbol, currentPrice: items[0].current_price, maxShares: items[0].shares });
            } else {
              setModal({ mode: "sell" });
            }
          }}
          className="px-4 py-1.5 rounded text-sm font-semibold text-white bg-[#854F0B] hover:bg-[#6b3f09] disabled:opacity-40 transition-colors"
        >
          Sell
        </button>
        <button
          disabled={currentSelection == null}
          onClick={() => setModal({ mode: "deposit" })}
          className="px-4 py-1.5 rounded text-sm font-semibold text-white bg-[#0C447C] hover:bg-[#093560] disabled:opacity-40 transition-colors"
        >
          Deposit
        </button>
        <button
          disabled={currentSelection == null}
          onClick={() => setModal({ mode: "withdraw" })}
          className="px-4 py-1.5 rounded text-sm font-semibold text-white bg-[#791F1F] hover:bg-[#611919] disabled:opacity-40 transition-colors"
        >
          Withdraw
        </button>
        <button
          disabled={currentSelection == null}
          onClick={() => setModal({ mode: "dividend" })}
          className="px-4 py-1.5 rounded text-sm font-semibold text-white bg-[#0F6E56] hover:bg-[#0b5844] disabled:opacity-40 transition-colors"
        >
          💰 Dividend
        </button>
        <button
          disabled={currentSelection == null}
          onClick={() => setShowImport((v) => !v)}
          className="px-4 py-1.5 rounded text-sm font-semibold text-gray-600 border border-gray-300 hover:bg-gray-50 disabled:opacity-40 transition-colors"
        >
          {showImport ? "Cancel Import" : "Import Existing"}
        </button>
      </div>

      {/* ── Import Existing Portfolio ── */}
      {showImport && currentSelection != null && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 space-y-3">
          <div>
            <p className="text-sm font-semibold text-amber-800">Import Existing Portfolio</p>
            <p className="text-xs text-amber-600 mt-0.5">
              Records existing holdings as INITIAL_POSITION transactions. Does not affect cash balance.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setModal({ mode: "initial_position" })}
              className="px-3 py-1.5 rounded text-sm font-semibold text-white bg-[#444441] hover:bg-[#333330] transition-colors"
            >
              Import Position
            </button>
            <button
              onClick={() => setModal({ mode: "deposit" })}
              className="px-3 py-1.5 rounded text-sm font-semibold text-white bg-[#0C447C] hover:bg-[#093560] transition-colors"
            >
              Set Starting Cash
            </button>
          </div>
          <p className="text-xs text-amber-500">
            Tip: Import all your positions first, then set your starting cash balance with &quot;Set Starting Cash&quot;.
          </p>
        </div>
      )}

      {isLoading ? (
        <p className="text-sm text-gray-400">Loading…</p>
      ) : (
        <>
          <PortfolioSummary items={items} cashBalance={cashBalance} pricesLoading={pricesLoading} />

          {/* Cash Balance display (read-only; modified via Deposit / Withdraw) */}
          <div className="bg-white border rounded-xl p-4 shadow-sm flex items-center gap-4">
            <div className="flex-1">
              <p className="text-xs text-gray-400 mb-0.5">Cash Balance</p>
              <p className={`text-xl font-bold ${cashBalance < 0 ? "text-red-600" : "text-gray-800"}`}>
                {cashBalance.toLocaleString("th-TH", { minimumFractionDigits: 2 })}
              </p>
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setModal({ mode: "deposit" })}
                className="text-xs text-blue-600 hover:text-blue-800 border border-blue-200 rounded px-3 py-1 hover:bg-blue-50 transition-colors"
              >
                + Deposit
              </button>
              <button
                onClick={() => setModal({ mode: "withdraw" })}
                className="text-xs text-red-500 hover:text-red-700 border border-red-200 rounded px-3 py-1 hover:bg-red-50 transition-colors"
              >
                − Withdraw
              </button>
            </div>
          </div>

          <PortfolioTable
            rows={items}
            onRemove={handleRemove}
            onReanalyze={handleReanalyze}
            onToggleSwap={handleToggleSwap}
            pricesLoading={pricesLoading}
            onBuy={(item) =>
              setModal({
                mode: "buy",
                symbol: item.symbol,
                currentPrice: item.current_price,
              })
            }
            onSell={(item) =>
              setModal({
                mode: "sell",
                symbol: item.symbol,
                currentPrice: item.current_price,
                maxShares: item.shares,
              })
            }
          />

          {hasData && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-white border rounded-xl p-4 shadow-sm">
                <h2 className="text-sm font-semibold text-gray-600 mb-2">Portfolio Allocation</h2>
                <PortfolioPieChart items={items} cashBalance={cashBalance} />
              </div>
              <div className="bg-white border rounded-xl p-4 shadow-sm">
                <h2 className="text-sm font-semibold text-gray-600 mb-2">Sector Allocation</h2>
                {sectorBreakdown
                  ? <SectorPieChart breakdown={sectorBreakdown} />
                  : <div className="h-[220px] animate-pulse bg-gray-100 rounded-xl" />}
              </div>
            </div>
          )}
        </>
      )}

      {/* ── Transaction Modal ── */}
      {modal != null && (
        <TransactionModal
          mode={modal.mode}
          symbol={modal.symbol}
          currentPrice={modal.currentPrice}
          maxShares={modal.maxShares}
          onConfirm={handleTransactionConfirm}
          onClose={handleModalClose}
        />
      )}

      {/* ── Toast notification ── */}
      {toast && (
        <Toast
          message={toast.message}
          kind={toast.kind}
          onDone={() => setToast(null)}
        />
      )}
    </div>
  );
}
