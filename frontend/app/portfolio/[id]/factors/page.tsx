"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { getFactorExposure } from "@/lib/api";
import type { FactorExposureResult } from "@/lib/api";
import BackBreadcrumb from "@/components/BackBreadcrumb";
import PortfolioTabs from "@/components/PortfolioTabs";
import PortfolioDNASummaryCard from "@/components/factor/PortfolioDNASummaryCard";
import FactorExposureBars      from "@/components/factor/FactorExposureBars";
import SectorConcentrationPanel from "@/components/factor/SectorConcentrationPanel";
import PortfolioDriftInsight   from "@/components/factor/PortfolioDriftInsight";
import PerStockScoreTable      from "@/components/factor/PerStockScoreTable";

const FactorRadarChart = dynamic(
  () => import("@/components/factor/FactorRadarChart"),
  { ssr: false, loading: () => <SkeletonBox height={300} /> }
);

// ─── Skeletons ────────────────────────────────────────────────────────────────

function SkeletonBox({ height }: { height: number }) {
  return <div className="animate-pulse bg-gray-100 rounded-2xl" style={{ height }} />;
}

function PageSkeleton() {
  return (
    <div className="space-y-4">
      <SkeletonBox height={220} />
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <div className="lg:col-span-2"><SkeletonBox height={350} /></div>
        <div className="lg:col-span-3"><SkeletonBox height={350} /></div>
      </div>
      <SkeletonBox height={300} />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <SkeletonBox height={280} />
        <SkeletonBox height={280} />
      </div>
      <SkeletonBox height={400} />
    </div>
  );
}

// ─── Empty portfolio state ────────────────────────────────────────────────────

function EmptyState({ portfolioId }: { portfolioId: number }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="w-16 h-16 rounded-2xl bg-blue-50 flex items-center justify-center text-3xl mb-4">◈</div>
      <h3 className="text-lg font-bold text-gray-800 mb-2">No Holdings Found</h3>
      <p className="text-sm text-gray-500 max-w-xs mb-6">
        Add stocks to your portfolio to generate the factor DNA analysis.
      </p>
      <Link
        href="/portfolio"
        className="text-sm font-semibold text-blue-600 hover:text-blue-700 border border-blue-200 rounded-xl px-4 py-2 hover:bg-blue-50 transition-colors"
      >
        ← Go to Portfolio
      </Link>
    </div>
  );
}

// ─── Error state ──────────────────────────────────────────────────────────────

function ErrorState({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center py-24 text-center">
      <div className="w-16 h-16 rounded-2xl bg-red-50 flex items-center justify-center text-3xl mb-4">⚠</div>
      <h3 className="text-lg font-bold text-gray-800 mb-2">Failed to Load Factor Data</h3>
      <p className="text-sm text-gray-500 max-w-sm mb-6">{message}</p>
      <button
        onClick={onRetry}
        className="text-sm font-semibold text-blue-600 hover:text-blue-700 border border-blue-200 rounded-xl px-4 py-2 hover:bg-blue-50 transition-colors"
      >
        Try again
      </button>
    </div>
  );
}

// ─── Header ───────────────────────────────────────────────────────────────────

function PageHeader({
  name,
  portfolioId,
  loading,
  onRefresh,
}: {
  name: string;
  portfolioId: number;
  loading: boolean;
  onRefresh: () => void;
}) {
  return (
    <div className="space-y-1 mb-6">
      <PortfolioTabs />
      <BackBreadcrumb parent="ภาพรวม" current="DNA Analysis" href="/portfolio" />
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl font-black text-gray-900">Portfolio DNA</h1>
          <p className="text-sm text-gray-500 mt-0.5">Institutional factor exposure analysis · {name}</p>
        </div>
        <button
          onClick={onRefresh}
          disabled={loading}
          className="flex items-center gap-1.5 text-xs font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg px-3 py-1.5 transition-colors self-start sm:self-auto"
        >
          {loading ? (
            <span className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin" />
          ) : (
            <span>↻</span>
          )}
          Refresh
        </button>
      </div>
    </div>
  );
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function FactorsPage({ params }: { params: { id: string } }) {
  const portfolioId = parseInt(params.id, 10);
  const [data, setData]     = useState<FactorExposureResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState<string | null>(null);

  // M36.1 WP4B F04 — this page is anchored to the URL's Portfolio Identity
  // (validated deep-entry), not Current Selection, but a request identity
  // guard still prevents a stale response for a previous [id] from
  // repopulating the page if the route param changes without a full remount.
  const requestIdRef = useRef<number | null>(null);

  const load = useCallback(async () => {
    const pid = portfolioId;
    setLoading(true);
    setError(null);
    try {
      const result = await getFactorExposure(pid);
      if (requestIdRef.current !== pid) return;
      if (result.error) {
        setError(result.error === "portfolio_not_found"
          ? "Portfolio not found. Check the URL or select a portfolio from the portfolio page."
          : result.error
        );
      } else {
        setData(result);
      }
    } catch (e: unknown) {
      if (requestIdRef.current !== pid) return;
      setError(e instanceof Error ? e.message : "Unexpected error loading factor data.");
    } finally {
      if (requestIdRef.current === pid) setLoading(false);
    }
  }, [portfolioId]);

  useEffect(() => {
    requestIdRef.current = portfolioId;
    setData(null);
    setError(null);
    load();
  }, [portfolioId, load]);

  const isEmpty = data && data.per_stock_scores.length === 0;

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
      {/* Header always visible */}
      <PageHeader
        name={data?.portfolio_name ?? "Loading…"}
        portfolioId={portfolioId}
        loading={loading}
        onRefresh={load}
      />

      {/* Loading state */}
      {loading && <PageSkeleton />}

      {/* Error state */}
      {!loading && error && <ErrorState message={error} onRetry={load} />}

      {/* Empty portfolio */}
      {!loading && !error && isEmpty && <EmptyState portfolioId={portfolioId} />}

      {/* Main dashboard */}
      {!loading && !error && data && !isEmpty && (
        <div className="space-y-5">

          {/* Row 1: DNA Summary Card (full width) */}
          <PortfolioDNASummaryCard
            portfolioName={data.portfolio_name}
            generatedAt={data.generated_at}
            style={data.style_classification}
            sector={data.sector_concentration}
            metadata={data.metadata}
          />

          {/* Row 2: Radar (left) + Factor bars (right) */}
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
            <div className="lg:col-span-2">
              <FactorRadarChart factorExposures={data.factor_exposures} />
            </div>
            <div className="lg:col-span-3">
              <FactorExposureBars factorExposures={data.factor_exposures} />
            </div>
          </div>

          {/* Row 3: Drift Insight (full width) */}
          <PortfolioDriftInsight
            style={data.style_classification}
            sector={data.sector_concentration}
            factorExposures={data.factor_exposures}
            rawMetrics={data.raw_metrics_summary}
          />

          {/* Row 4: Sector Concentration */}
          <SectorConcentrationPanel sector={data.sector_concentration} />

          {/* Row 5: Per-stock table */}
          <PerStockScoreTable stocks={data.per_stock_scores} />

          {/* Footer: metadata */}
          <div className="text-center py-4">
            <p className="text-xs text-gray-400">
              Factor scores are percentile-ranked within this portfolio universe ({data.metadata.universe_size} holdings).
              Normalization method: <span className="font-medium text-gray-500">{data.metadata.normalization_method.replace(/_/g, " ")}</span>.
              {" "}15-minute cache · scores not investment advice.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
