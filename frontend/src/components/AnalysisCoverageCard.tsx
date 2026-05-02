import { CalendarDays, Database, Layers3 } from 'lucide-react';

interface AnalysisCoverageCardProps {
  rowCount?: number;
  itemCount?: number;
  dateRange?: {
    start?: string | null;
    end?: string | null;
  } | null;
  className?: string;
}

function formatCount(value: number | undefined): string {
  return typeof value === 'number' && Number.isFinite(value)
    ? value.toLocaleString()
    : '-';
}

function formatDateRange(dateRange: AnalysisCoverageCardProps['dateRange']): string {
  const start = dateRange?.start || '-';
  const end = dateRange?.end || '-';
  return `${start} to ${end}`;
}

export function AnalysisCoverageCard({
  rowCount,
  itemCount,
  dateRange,
  className = '',
}: AnalysisCoverageCardProps) {
  return (
    <section
      className={`rounded-lg border border-slate-200 bg-white p-4 shadow-sm ${className}`.trim()}
      aria-label="Analysis coverage"
    >
      <div className="grid gap-3 sm:grid-cols-3">
        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-cyan-50 text-cyan-700">
            <Database className="h-4 w-4" />
          </span>
          <div>
            <p className="text-xs font-medium text-slate-500">Source observations</p>
            <p className="text-lg font-semibold text-slate-950">{formatCount(rowCount)}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-emerald-50 text-emerald-700">
            <Layers3 className="h-4 w-4" />
          </span>
          <div>
            <p className="text-xs font-medium text-slate-500">Current item snapshots</p>
            <p className="text-lg font-semibold text-slate-950">{formatCount(itemCount)}</p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-lg bg-amber-50 text-amber-700">
            <CalendarDays className="h-4 w-4" />
          </span>
          <div>
            <p className="text-xs font-medium text-slate-500">Date range</p>
            <p className="text-sm font-semibold text-slate-950">{formatDateRange(dateRange)}</p>
          </div>
        </div>
      </div>

      <p className="mt-3 border-t border-slate-100 pt-3 text-sm text-slate-600">
        StockWise keeps every uploaded source observation for trend-aware scoring, then shows the latest row for each item in this table.
      </p>
    </section>
  );
}
