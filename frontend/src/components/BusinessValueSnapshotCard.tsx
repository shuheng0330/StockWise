import React from 'react';
import { Clock3, PiggyBank, ShieldAlert, Target, WalletCards } from 'lucide-react';

import { Card } from '@/components/common';
import { BusinessValueSnapshot } from '@/lib/businessValue';

interface BusinessValueSnapshotCardProps {
  snapshot: BusinessValueSnapshot;
}

function formatRM(value: number) {
  return `RM${value.toFixed(2)}`;
}

function Metric({
  icon: Icon,
  label,
  value,
  helper,
  className = '',
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string;
  helper: string;
  className?: string;
}) {
  return (
    <div className={`min-w-0 rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 ${className}`.trim()}>
      <div className="flex items-center gap-2 text-slate-500">
        <Icon className="h-4 w-4 flex-shrink-0" />
        <span className="text-xs font-semibold uppercase tracking-[0.12em]">{label}</span>
      </div>
      <p className="mt-2 text-2xl font-bold leading-tight text-slate-950">{value}</p>
      <p className="mt-1 text-xs leading-snug text-slate-500">{helper}</p>
    </div>
  );
}

export function BusinessValueSnapshotCard({ snapshot }: BusinessValueSnapshotCardProps) {
  const ratioText =
    snapshot.valueToCostRatio === null
      ? 'No paid plan needed yet'
      : `${snapshot.valueToCostRatio.toFixed(1)}x`;

  return (
    <Card className="mb-6 overflow-hidden border border-emerald-200 shadow-sm">
      <div className="grid gap-5 p-5 xl:grid-cols-[280px_minmax(0,1fr)]">
        <div className="flex flex-col gap-4">
          <div>
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-emerald-800">
              <Target className="h-3.5 w-3.5" />
              Estimated opportunity
            </div>
            <h2 className="mt-3 text-xl font-bold text-slate-950">Business Value Snapshot</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              A planning estimate from current inventory risk, shown as potential monthly value if StockWise recommendations are followed.
            </p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="text-sm font-semibold text-slate-500">Suggested StockWise plan</p>
            <div className="mt-2 flex flex-wrap items-end gap-x-3 gap-y-1">
              <span className="text-2xl font-bold text-slate-950">{snapshot.suggestedPlan.name}</span>
              <span className="pb-1 text-sm text-slate-600">
                {snapshot.suggestedPlan.monthlyPrice > 0
                  ? `${formatRM(snapshot.suggestedPlan.monthlyPrice)}/month`
                  : 'RM0/month'}
              </span>
            </div>
            <p className="mt-2 text-sm text-slate-600">{snapshot.suggestedPlan.rationale}</p>
          </div>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          <Metric
            icon={PiggyBank}
            label="Waste avoided"
            value={formatRM(snapshot.monthlyWasteAvoided)}
            helper="High-waste items"
          />
          <Metric
            icon={ShieldAlert}
            label="Stockout loss"
            value={formatRM(snapshot.monthlyStockoutLossAvoided)}
            helper="Current shortfall value"
          />
          <Metric
            icon={Clock3}
            label="Time saved"
            value={`${snapshot.monthlyTimeSavedHours.toFixed(1)}h`}
            helper="Versus spreadsheet review"
          />
          <Metric
            icon={WalletCards}
            label="Value created"
            value={formatRM(snapshot.monthlyOpportunityValue)}
            helper="Waste plus stockout exposure"
            className="lg:col-span-2"
          />
          <Metric
            icon={Target}
            label="Value vs cost"
            value={ratioText}
            helper={
              snapshot.valueToCostRatio === null
                ? 'No subscription cost applied'
                : 'Value-to-price ratio, not realized ROI'
            }
          />
        </div>
      </div>
      <div className="border-t border-emerald-100 bg-emerald-50 px-5 py-3">
        <p className="text-xs leading-5 text-emerald-900">
          {snapshot.assumptions.join(' ')} Estimates are directional and require owner follow-through before they become realized business value.
        </p>
      </div>
    </Card>
  );
}
