"use client";

import { useEffect, useRef, useState } from "react";
import { getOptimizerProgress, type OptimizerProgress } from "@/lib/api";

const POLL_INTERVAL = 1_500; // ms

/** Live staged timeline shown while an optimizer run is in flight.
 *  Polls the run-progress registry — stages reflect the REAL pipeline position. */
export default function OperationsTimeline({
  portfolioId,
  active,
}: {
  portfolioId: number;
  active: boolean;
}) {
  const [progress, setProgress] = useState<OptimizerProgress | null>(null);
  const fetchingRef = useRef(false);

  useEffect(() => {
    if (!active) {
      setProgress(null);
      return;
    }
    const poll = async () => {
      if (fetchingRef.current) return;
      fetchingRef.current = true;
      try {
        const p = await getOptimizerProgress(portfolioId);
        setProgress(p);
      } catch {
        /* silent — keep last known state */
      } finally {
        fetchingRef.current = false;
      }
    };
    poll();
    const id = setInterval(poll, POLL_INTERVAL);
    return () => clearInterval(id);
  }, [active, portfolioId]);

  const stages = progress?.stages ?? [];

  return (
    <div className="rounded-2xl border-2 border-gray-200 bg-white p-6 space-y-4 shadow-sm">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
          AI Operations Center — กำลังวิเคราะห์พอร์ต
        </p>
        <span className="font-mono text-[10px] font-bold text-blue-600 border border-blue-200 bg-blue-50 px-2 py-0.5 rounded-full animate-pulse">
          RUNNING
        </span>
      </div>

      {stages.length === 0 ? (
        // Race at run start (registry not yet populated) — indeterminate bar
        <div className="space-y-2">
          <p className="text-sm text-gray-500">เริ่มการวิเคราะห์…</p>
          <div className="h-2 w-full rounded-full bg-gray-100 overflow-hidden">
            <div className="h-full w-1/3 rounded-full bg-blue-400 animate-pulse" />
          </div>
        </div>
      ) : (
        <ol className="space-y-3">
          {stages.map((s) => (
            <li key={s.key} className="flex items-center gap-3">
              {s.status === "done" ? (
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500 text-[10px] font-bold text-white">
                  ✓
                </span>
              ) : s.status === "active" ? (
                <span className="flex h-5 w-5 items-center justify-center">
                  <span className="h-3 w-3 rounded-full bg-blue-500 animate-ping" />
                </span>
              ) : (
                <span className="h-5 w-5 rounded-full border-2 border-gray-200" />
              )}
              <span
                className={`text-sm ${
                  s.status === "active"
                    ? "font-semibold text-gray-900"
                    : s.status === "done"
                      ? "text-gray-500"
                      : "text-gray-300"
                }`}
              >
                {s.label_th}
              </span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
