interface AnalyticsFiltersProps {
  portfolioName: string;
  snapshotCount?: number;
  dateFrom?: string;
  dateTo?: string;
}

export default function AnalyticsFilters({
  portfolioName,
  snapshotCount,
  dateFrom,
  dateTo,
}: AnalyticsFiltersProps) {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center gap-3 flex-wrap">
      {/* Portfolio context */}
      <div className="flex items-center gap-2 mr-auto">
        <span className="text-xs text-gray-500 font-medium uppercase tracking-wider">Portfolio</span>
        <span className="text-sm font-semibold text-gray-800">{portfolioName}</span>
        {snapshotCount != null && (
          <span className="text-xs text-gray-400">
            ({snapshotCount} snapshot{snapshotCount !== 1 ? "s" : ""}
            {dateFrom && dateTo ? `, ${dateFrom} – ${dateTo}` : ""})
          </span>
        )}
      </div>
    </div>
  );
}
