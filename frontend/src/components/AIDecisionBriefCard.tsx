import React from 'react';
import Link from 'next/link';
import { AlertTriangle, CheckCircle2, Clock3, DollarSign, RefreshCw, ShieldAlert, Sparkles, Trash2 } from 'lucide-react';

import { Button, Card } from '@/components/common';
import { DecisionBriefItem, DecisionBriefResponse, RecommendedAction } from '@/types';

interface AIDecisionBriefCardProps {
  analysisId: string;
  isLoading: boolean;
  brief: DecisionBriefResponse | null;
  error: string;
  onRetry?: () => void;
  isRetrying?: boolean;
}

function sourceClass(source: DecisionBriefResponse['source']) {
  switch (source) {
    case 'live':
      return 'border-emerald-200 bg-emerald-50 text-emerald-800';
    case 'mock':
      return 'border-blue-200 bg-blue-50 text-blue-800';
    case 'fallback':
      return 'border-amber-200 bg-amber-50 text-amber-800';
  }
}

function actionClass(action: RecommendedAction) {
  switch (action) {
    case 'RESTOCK_NOW':
      return 'border-red-200 bg-red-50 text-red-800';
    case 'BUY_LESS':
      return 'border-amber-200 bg-amber-50 text-amber-800';
    case 'DELAY_PURCHASE':
      return 'border-sky-200 bg-sky-50 text-sky-800';
    case 'MONITOR_CLOSELY':
      return 'border-emerald-200 bg-emerald-50 text-emerald-800';
  }
}

function safetyLabel(status: DecisionBriefResponse['safety_status']) {
  return status.replace('_', ' ');
}

function ActionList({ analysisId, title, items }: { analysisId: string; title: string; items: DecisionBriefItem[] }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <h3 className="text-sm font-semibold uppercase tracking-[0.14em] text-slate-500">{title}</h3>
      <div className="mt-3 space-y-3">
        {items.length === 0 ? (
          <p className="text-sm text-slate-500">No items in this group.</p>
        ) : (
          items.map((item) => (
            <Link
              key={`${title}-${item.item_id}`}
              href={`/simulation/${analysisId}/${item.item_id}`}
              className="block rounded-lg border border-slate-200 px-3 py-3 transition hover:border-sky-300 hover:bg-sky-50"
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-semibold text-slate-950">{item.item_name}</p>
                <span className={`rounded-full border px-2.5 py-1 text-xs font-medium ${actionClass(item.recommended_action)}`}>
                  {item.recommended_action.replace('_', ' ')}
                </span>
              </div>
              <p className="mt-2 text-sm text-slate-600">{item.reason}</p>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}

export function AIDecisionBriefCard({
  analysisId,
  isLoading,
  brief,
  error,
  onRetry,
  isRetrying = false,
}: AIDecisionBriefCardProps) {
  if (isLoading) {
    return (
      <Card className="overflow-hidden border border-slate-200 shadow-sm">
        <div className="border-b border-slate-200 bg-white p-6">
          <div className="flex items-center gap-2 text-blue-700">
            <Sparkles className="h-4 w-4" />
            <span className="text-xs font-semibold uppercase tracking-[0.18em]">AI Decision Brief</span>
          </div>
          <h2 className="mt-2 text-2xl font-bold text-slate-950">Preparing decision brief</h2>
          <p className="mt-2 text-slate-600">Your dashboard is ready while Z.AI reviews the trade-offs.</p>
        </div>
        <div className="grid gap-4 p-6 md:grid-cols-3">
          {[0, 1, 2].map((item) => (
            <div key={item} className="h-36 animate-pulse rounded-lg bg-slate-100" />
          ))}
        </div>
      </Card>
    );
  }

  if (error || !brief) {
    return (
      <Card className="border border-amber-200 bg-amber-50 p-6 shadow-sm">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <div className="flex items-center gap-2 text-amber-800">
              <ShieldAlert className="h-5 w-5" />
              <h2 className="text-xl font-bold">AI Decision Brief unavailable</h2>
            </div>
            <p className="mt-2 text-amber-900">
              {error || 'The brief could not be generated. The deterministic dashboard below is still available.'}
            </p>
          </div>
          <Link href={`/records/${analysisId}`}>
            <Button variant="outline">Review Records</Button>
          </Link>
        </div>
      </Card>
    );
  }

  const fallbackUsed = brief.source === 'fallback' || brief.safety_status === 'fallback_used';

  return (
    <Card className="overflow-hidden border border-slate-200 shadow-sm">
      <div className="bg-slate-950 p-6 text-white">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
          <div>
            <div className="flex items-center gap-2 text-sky-300">
              <Sparkles className="h-4 w-4" />
              <span className="text-xs font-semibold uppercase tracking-[0.18em]">AI Decision Brief</span>
            </div>
            <h2 className="mt-2 text-2xl font-bold">Today&apos;s operating plan</h2>
            <p className="mt-3 max-w-4xl text-lg text-slate-100">{brief.summary}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <span className={`rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] ${sourceClass(brief.source)}`}>
              {brief.source}
            </span>
            <span className="rounded-full border border-slate-700 bg-slate-900 px-3 py-1 text-xs font-semibold uppercase tracking-[0.14em] text-slate-200">
              {safetyLabel(brief.safety_status)}
            </span>
          </div>
        </div>
      </div>

      <div className="space-y-6 p-6">
        {fallbackUsed && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-amber-900">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div className="flex items-start gap-2">
                <AlertTriangle className="mt-0.5 h-5 w-5 flex-shrink-0" />
                <p>{brief.warning_flag || 'The AI output was unusable, so StockWise used a deterministic fallback brief.'}</p>
              </div>
              <Link href={`/records/${analysisId}`}>
                <Button variant="outline" size="sm">Review Records</Button>
              </Link>
              {onRetry && (
                <Button
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={onRetry}
                  loading={isRetrying}
                  className="inline-flex items-center gap-2"
                >
                  <RefreshCw className="h-4 w-4" />
                  <span>Retry AI</span>
                </Button>
              )}
            </div>
          </div>
        )}

        <div className="grid gap-4 lg:grid-cols-3">
          <ActionList analysisId={analysisId} title="Buy Today" items={brief.buy_today} />
          <ActionList analysisId={analysisId} title="Buy Less" items={brief.buy_less} />
          <ActionList analysisId={analysisId} title="Delay" items={brief.delay} />
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <div className="flex items-center gap-2 text-slate-500">
              <DollarSign className="h-4 w-4" />
              <h3 className="text-sm font-semibold uppercase tracking-[0.14em]">Cash</h3>
            </div>
            <p className="mt-3 text-sm text-slate-800">{brief.estimated_impact.cash}</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <div className="flex items-center gap-2 text-slate-500">
              <Trash2 className="h-4 w-4" />
              <h3 className="text-sm font-semibold uppercase tracking-[0.14em]">Waste</h3>
            </div>
            <p className="mt-3 text-sm text-slate-800">{brief.estimated_impact.waste}</p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 p-4">
            <div className="flex items-center gap-2 text-slate-500">
              <Clock3 className="h-4 w-4" />
              <h3 className="text-sm font-semibold uppercase tracking-[0.14em]">Shortage</h3>
            </div>
            <p className="mt-3 text-sm text-slate-800">{brief.estimated_impact.shortage}</p>
          </div>
        </div>

        <div className="grid gap-5 lg:grid-cols-2">
          <div>
            <h3 className="text-sm font-semibold uppercase tracking-[0.14em] text-slate-500">Top Trade-Offs</h3>
            <ul className="mt-3 space-y-2 text-sm text-slate-700">
              {brief.top_tradeoffs.map((tradeoff) => (
                <li key={tradeoff} className="rounded-lg bg-slate-50 px-3 py-2">{tradeoff}</li>
              ))}
            </ul>
          </div>
          <div>
            <h3 className="text-sm font-semibold uppercase tracking-[0.14em] text-slate-500">Recommended Order</h3>
            <ol className="mt-3 space-y-2 text-sm text-slate-700">
              {brief.recommended_order.map((step, index) => (
                <li key={step} className="flex gap-3 rounded-lg bg-slate-50 px-3 py-2">
                  <span className="font-semibold text-slate-950">{index + 1}</span>
                  <span>{step}</span>
                </li>
              ))}
            </ol>
          </div>
        </div>

        <div className="flex items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-900">
          <CheckCircle2 className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <p>{brief.confidence_note}</p>
        </div>
      </div>
    </Card>
  );
}
