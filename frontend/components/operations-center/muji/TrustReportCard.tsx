"use client";

// AI Evaluation M7 — MUJI Trust Report (UX S9): "one calm card, not the
// hub." Renders GET /analytics/evaluation/trust-report verbatim — up to
// three plain Thai sentences, no letter grades, no jargon, at most two
// numbers total. Same verdict source as the Quant Scorecard (S1); this is
// the MUJI-register view of the identical underlying evaluation.

import { useEffect, useState } from "react";
import Link from "next/link";
import { getTrustReport, type TrustReport } from "@/lib/api";

export default function TrustReportCard({ portfolioId }: { portfolioId: number }) {
  const [data, setData] = useState<TrustReport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getTrustReport(portfolioId, 90)
      .then((r) => {
        if (!cancelled) setData(r);
      })
      .catch(() => {
        if (!cancelled) setData(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [portfolioId]);

  return (
    <div className="rounded-2xl border-2 border-gray-200 bg-white p-5 space-y-3 shadow-sm">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-widest">
        รายงานความน่าเชื่อถือของ AI
      </p>

      {loading && (
        <div className="space-y-2 animate-pulse">
          <div className="h-4 bg-gray-100 rounded w-5/6" />
          <div className="h-4 bg-gray-100 rounded w-4/6" />
        </div>
      )}

      {!loading && !data && (
        <p className="text-sm text-gray-400">ยังไม่สามารถโหลดรายงานความน่าเชื่อถือได้ในขณะนี้</p>
      )}

      {!loading && data && (
        <ul className="space-y-2">
          {data.sentences.map((s, i) => (
            <li key={i} className="text-sm text-gray-700 leading-relaxed">
              {s.th}
            </li>
          ))}
        </ul>
      )}

      <Link
        href={data?.link ?? "/ai-analytics"}
        className="inline-block text-sm font-semibold text-blue-600 hover:underline pt-1"
      >
        ดูรายละเอียดทั้งหมด →
      </Link>
    </div>
  );
}
