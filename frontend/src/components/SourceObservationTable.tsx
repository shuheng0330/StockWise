import { History } from 'lucide-react';

import { SourceObservation } from '@/types';

interface SourceObservationTableProps {
  observations: SourceObservation[];
  className?: string;
}

function formatNumber(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(2).replace(/\.?0+$/, '');
}

export function SourceObservationTable({
  observations,
  className = '',
}: SourceObservationTableProps) {
  if (observations.length === 0) {
    return null;
  }

  return (
    <section className={`rounded-lg border border-slate-200 bg-white shadow-sm ${className}`.trim()}>
      <div className="flex flex-col gap-1 border-b border-slate-200 px-4 py-4 sm:px-6">
        <div className="flex items-center gap-2">
          <History className="h-5 w-5 text-cyan-700" />
          <h2 className="text-lg font-semibold text-slate-950">Source Upload History</h2>
        </div>
        <p className="text-sm text-slate-600">
          Every row below is kept for month-to-month trend analysis and AI recommendations.
        </p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-500 sm:px-6">Date</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-500 sm:px-6">Item</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-500 sm:px-6">Stock</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-500 sm:px-6">Usage</th>
              <th className="px-4 py-3 text-left text-xs font-semibold uppercase text-slate-500 sm:px-6">Supplier</th>
            </tr>
          </thead>
          <tbody>
            {observations.map((observation, index) => (
              <tr
                key={`${observation.item_id ?? observation.item_name}-${observation.date ?? 'undated'}-${index}`}
                className="border-t border-slate-100 hover:bg-slate-50"
              >
                <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-600 sm:px-6">
                  {observation.date || '-'}
                </td>
                <td className="px-4 py-3 sm:px-6">
                  <p className="font-medium text-slate-950">{observation.item_name}</p>
                  {(observation.category || observation.subcategory) && (
                    <p className="text-xs text-slate-500">
                      {[observation.category, observation.subcategory].filter(Boolean).join(' / ')}
                    </p>
                  )}
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-900 sm:px-6">
                  {formatNumber(observation.current_stock)} {observation.unit}
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-900 sm:px-6">
                  {formatNumber(observation.usage_value)} {observation.usage_period}
                </td>
                <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-600 sm:px-6">
                  {observation.supplier_name || 'Unknown'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
