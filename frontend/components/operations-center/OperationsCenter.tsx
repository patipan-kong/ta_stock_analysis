"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  getOperationsStatus,
  runOptimizer,
  type OperationsCenterStatus,
  type OperationsMode,
} from "@/lib/api";
import ModeToggle from "./ModeToggle";
import MujiDashboard from "./muji/MujiDashboard";
import QuantDashboard from "./quant/QuantDashboard";
import OperationsTimeline from "./quant/OperationsTimeline";

const MODE_STORAGE_KEY = "operations_mode";
const STATUS_REFRESH_INTERVAL = 60_000; // 60 seconds

export default function OperationsCenter({
  portfolioId,
  initialSymbols,
}: {
  portfolioId: number;
  initialSymbols?: string[];
}) {
  const [mode, setModeState] = useState<OperationsMode>("MUJI");
  const [status, setStatus] = useState<OperationsCenterStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [optimizing, setOptimizing] = useState(false);
  const [optimizeError, setOptimizeError] = useState<string | null>(null);
  const fetchingRef = useRef(false);

  // Restore persisted mode (localStorage is browser-only — read after mount).
  // If the user arrived via optimizer handoff, always open in QUANT mode.
  useEffect(() => {
    if (initialSymbols && initialSymbols.length > 0) {
      setModeState("QUANT");
      return;
    }
    const saved = localStorage.getItem(MODE_STORAGE_KEY);
    if (saved === "MUJI" || saved === "QUANT") setModeState(saved);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const setMode = useCallback((m: OperationsMode) => {
    setModeState(m);
    localStorage.setItem(MODE_STORAGE_KEY, m);
  }, []);

  const refetch = useCallback(async () => {
    if (fetchingRef.current) return;
    fetchingRef.current = true;
    try {
      const s = await getOperationsStatus(portfolioId);
      setStatus(s);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load status");
    } finally {
      fetchingRef.current = false;
      setLoading(false);
    }
  }, [portfolioId]);

  // Initial load + 60s background refresh.
  useEffect(() => {
    setLoading(true);
    setStatus(null);
    refetch();
    const id = setInterval(refetch, STATUS_REFRESH_INTERVAL);
    return () => clearInterval(id);
  }, [refetch]);

  // Command-center entry point: invokes the SAME optimizer pipeline as the
  // Optimizer page (POST /analyze/optimizer). Analysis only — no execution.
  // On completion the unified status (recommendation + consensus + stations)
  // is refetched so the dashboard updates without a page reload.
  const handleRunOptimizer = useCallback(async () => {
    if (optimizing) return;
    setOptimizing(true);
    setOptimizeError(null);
    try {
      await runOptimizer(portfolioId);
      await refetch();
    } catch (e) {
      setOptimizeError(e instanceof Error ? e.message : "Optimizer failed");
    } finally {
      setOptimizing(false);
    }
  }, [optimizing, portfolioId, refetch]);

  return (
    <div className="space-y-5">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-xl font-bold text-gray-900">
            {mode === "MUJI" ? "ภาพรวมพอร์ตของคุณ" : "ศูนย์บัญชาการ AI"}
          </h1>
          {status?.portfolio_name && (
            <p className="text-xs text-gray-500 mt-0.5">{status.portfolio_name}</p>
          )}
        </div>
        <div className="flex items-center gap-3 flex-wrap">
          {/* Phase 4C.2A — AI tools consolidated under Ops Center; legacy routes stay reachable here */}
          <div className="flex items-center gap-3 text-[11px] font-semibold">
            <Link href="/optimizer" className="text-blue-600 hover:underline whitespace-nowrap">
              Optimizer →
            </Link>
            <Link href="/portfolio-intelligence" className="text-blue-600 hover:underline whitespace-nowrap">
              Portfolio Intelligence →
            </Link>
          </div>
          <ModeToggle mode={mode} onChange={setMode} />
        </div>
      </div>

      {loading && (
        <div className="rounded-2xl border-2 border-gray-200 bg-white p-8 text-center text-sm text-gray-400 animate-pulse">
          {mode === "MUJI" ? "กำลังโหลดข้อมูล…" : "Loading operations status…"}
        </div>
      )}

      {!loading && error && (
        <div className="rounded-2xl border-2 border-red-200 bg-red-50 p-5 text-sm text-red-700">
          {mode === "MUJI" ? "ไม่สามารถโหลดข้อมูลได้ ลองรีเฟรชหน้าอีกครั้ง" : `Failed to load: ${error}`}
        </div>
      )}

      {/* Live staged progress while an optimizer run is in flight (real backend stages) */}
      {optimizing && <OperationsTimeline portfolioId={portfolioId} active={optimizing} />}

      {optimizeError && (
        <div className="rounded-2xl border-2 border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {mode === "MUJI"
            ? "การวิเคราะห์ไม่สำเร็จ ลองใหม่อีกครั้ง"
            : `Optimizer run failed: ${optimizeError}`}
        </div>
      )}

      {!loading && status && (
        mode === "MUJI" ? (
          <MujiDashboard
            status={status}
            portfolioId={portfolioId}
            onGoalSaved={refetch}
            optimizing={optimizing}
            onRunOptimizer={handleRunOptimizer}
          />
        ) : (
          <QuantDashboard
            portfolioId={portfolioId}
            status={status}
            optimizing={optimizing}
            onRunOptimizer={handleRunOptimizer}
            initialSymbols={initialSymbols}
          />
        )
      )}
    </div>
  );
}
