import React, { useState } from 'react';
import { InventoryItem, SimulationResponse, TradeoffVerdictResponse } from '@/types';
import { Button, Input } from './common';
import { Sparkles } from 'lucide-react';
import { runSimulationWithVerdict } from '@/lib/simulationFlow';

interface ItemSimulationProps {
  item: InventoryItem;
  analysisId: string;
  onSimulate: (qty: number) => Promise<any>;
  onGenerateTradeoffVerdict?: (qty: number) => Promise<TradeoffVerdictResponse>;
  isLoading?: boolean;
}

interface TradeoffVerdictCardProps {
  verdict: TradeoffVerdictResponse | null;
  isLoading: boolean;
  error: string;
  onRetry?: () => void;
}

function sourceLabel(source: TradeoffVerdictResponse['source']) {
  return source === 'live' ? 'live' : source === 'mock' ? 'mock' : 'fallback';
}

export function TradeoffVerdictCard({ verdict, isLoading, error, onRetry }: TradeoffVerdictCardProps) {
  if (isLoading) {
    return (
      <div className="rounded-lg border border-indigo-200 bg-indigo-50 p-4">
        <div className="flex items-center gap-2 text-indigo-900">
          <Sparkles className="h-4 w-4 animate-pulse" />
          <p className="font-semibold">Generating AI trade-off verdict...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p>{error}</p>
          {onRetry && (
            <Button variant="outline" size="sm" onClick={onRetry}>
              Retry AI
            </Button>
          )}
        </div>
      </div>
    );
  }

  if (!verdict) {
    return null;
  }

  return (
    <div className="rounded-lg border border-indigo-200 bg-white p-4 shadow-sm">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2 text-indigo-700">
            <Sparkles className="h-4 w-4" />
            <span className="text-xs font-semibold uppercase tracking-wide">AI Trade-off Verdict</span>
          </div>
          <p className="mt-2 text-xl font-bold text-gray-950">{verdict.verdict}</p>
          <p className="mt-1 text-sm leading-6 text-gray-700">{verdict.reason}</p>
        </div>
        <span className="w-fit rounded-full bg-indigo-50 px-3 py-1 text-xs font-semibold uppercase text-indigo-700">
          {sourceLabel(verdict.source)}
        </span>
      </div>
      <p className="mt-3 text-xs text-gray-500">{verdict.confidence_note}</p>
    </div>
  );
}

export function ItemSimulation({
  item,
  onSimulate,
  onGenerateTradeoffVerdict,
  isLoading = false,
}: ItemSimulationProps) {
  const [simQty, setSimQty] = useState<number>(item.reorder_level);
  const [simulationResult, setSimulationResult] = useState<SimulationResponse | null>(null);
  const [tradeoffVerdict, setTradeoffVerdict] = useState<TradeoffVerdictResponse | null>(null);
  const [isVerdictLoading, setIsVerdictLoading] = useState(false);
  const [verdictError, setVerdictError] = useState<string>('');
  const [error, setError] = useState<string>('');

  const handleSimulate = async () => {
    setError('');
    setVerdictError('');
    setTradeoffVerdict(null);
    try {
      if (!onGenerateTradeoffVerdict) {
        const result = await onSimulate(simQty);
        setSimulationResult(result);
        return;
      }

      setIsVerdictLoading(true);
      await runSimulationWithVerdict(
        simQty,
        onSimulate,
        onGenerateTradeoffVerdict,
        setSimulationResult,
        setTradeoffVerdict,
        () => setVerdictError('AI trade-off verdict is unavailable right now. The simulation result is still usable.')
      );
    } catch (err: any) {
      setError(err.message || 'Simulation failed');
    } finally {
      setIsVerdictLoading(false);
    }
  };

  const getActionColor = (action: string) => {
    switch (action) {
      case 'RESTOCK_NOW':
        return 'text-red-600 bg-red-50';
      case 'BUY_LESS':
        return 'text-amber-600 bg-amber-50';
      case 'DELAY_PURCHASE':
        return 'text-blue-600 bg-blue-50';
      case 'MONITOR_CLOSELY':
        return 'text-green-600 bg-green-50';
      default:
        return 'text-gray-600 bg-gray-50';
    }
  };

  const getRiskChangeLabel = (riskChange: SimulationResponse['simulated_risk_change']) => {
    switch (riskChange) {
      case 'lower_shortage_risk':
        return 'Lower shortage risk';
      case 'lower_waste_risk':
        return 'Lower waste risk';
      case 'higher_waste_risk':
        return 'Higher waste risk';
      case 'minimal_change':
        return 'Minimal change';
    }
  };

  return (
    <div className="space-y-6">
      {/* Current State */}
      <div className="bg-gray-50 rounded-lg p-4">
        <h4 className="font-semibold text-gray-900 mb-3">Current State</h4>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div>
            <p className="text-gray-600 text-sm">Current Stock</p>
            <p className="font-semibold text-lg">{item.current_stock} {item.unit}</p>
          </div>
          <div>
            <p className="text-gray-600 text-sm">Days of Cover</p>
            <p className="font-semibold text-lg">{item.days_of_cover.toFixed(1)}</p>
          </div>
          <div>
            <p className="text-gray-600 text-sm">Inventory Value</p>
            <p className="font-semibold text-lg">${item.inventory_value.toFixed(2)}</p>
          </div>
          <div>
            <p className="text-gray-600 text-sm">Waste Cost</p>
            <p className="font-semibold text-lg">${item.estimated_waste_cost.toFixed(2)}</p>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-4">
          <div>
            <p className="text-gray-600 text-sm">Urgency Score</p>
            <div className="flex items-center gap-2">
              <div className="flex-1 bg-white rounded border border-gray-300 h-2">
                <div
                  className="bg-red-500 h-full rounded"
                  style={{ width: `${Math.min(item.reorder_urgency_score, 100)}%` }}
                />
              </div>
              <span className="font-semibold">{item.reorder_urgency_score.toFixed(0)}</span>
            </div>
          </div>
          <div>
            <p className="text-gray-600 text-sm">Waste Risk Score</p>
            <div className="flex items-center gap-2">
              <div className="flex-1 bg-white rounded border border-gray-300 h-2">
                <div
                  className="bg-yellow-500 h-full rounded"
                  style={{ width: `${Math.min(item.waste_risk_score, 100)}%` }}
                />
              </div>
              <span className="font-semibold">{item.waste_risk_score.toFixed(0)}</span>
            </div>
          </div>
        </div>
        <div className={`mt-3 p-2 rounded text-sm ${getActionColor(item.recommended_action)}`}>
          <strong>Recommendation:</strong> {item.recommended_action.replace('_', ' ')}
        </div>
      </div>

      {/* Simulation Input */}
      <div className="border rounded-lg p-4">
        <h4 className="font-semibold text-gray-900 mb-3">Test a Reorder Quantity</h4>
        <div className="flex flex-col sm:flex-row sm:items-end gap-3">
          <div className="flex-1 min-w-0">
            <Input
              label={`Proposed Reorder Quantity (${item.unit})`}
              type="number"
              min="0"
              step={item.unit === 'pieces' ? '1' : '0.01'}
              data-testid="reorder-qty-input"
              value={simQty}
              onChange={(e) => setSimQty(parseFloat(e.target.value) || 0)}
            />
          </div>
          <Button
            variant="primary"
            data-testid="run-simulation-btn"
            onClick={handleSimulate}
            loading={isLoading}
            className="w-full sm:w-auto"
          >
            Simulate
          </Button>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-900 text-sm">
          {error}
        </div>
      )}

      {/* Simulation Results */}
      {simulationResult && (
        <div data-testid="simulation-result" className="bg-blue-50 rounded-lg p-4 border border-blue-200">
          <h4 className="font-semibold text-gray-900 mb-3">Simulated Results</h4>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
            <div>
              <p className="text-gray-600 text-sm">Reorder Qty</p>
              <p className="font-semibold text-lg">{simulationResult.simulated_order_qty} {item.unit}</p>
            </div>
            <div>
              <p className="text-gray-600 text-sm">Cash Outlay</p>
              <p className="font-semibold text-lg">${simulationResult.simulated_cash_outlay.toFixed(2)}</p>
            </div>
            <div>
              <p className="text-gray-600 text-sm">Coverage Days</p>
              <p className="font-semibold text-lg">{simulationResult.simulated_coverage_days.toFixed(1)}</p>
            </div>
            <div>
              <p className="text-gray-600 text-sm">Waste Cost</p>
              <p className="font-semibold text-lg">${simulationResult.simulated_estimated_waste_cost.toFixed(2)}</p>
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 mb-4">
            <div>
              <p className="text-gray-600 text-sm">Urgency Score</p>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-white rounded border border-gray-300 h-2">
                  <div
                    className="bg-red-500 h-full rounded"
                    style={{ width: `${Math.min(simulationResult.reorder_urgency_score, 100)}%` }}
                  />
                </div>
                <span className="font-semibold">{simulationResult.reorder_urgency_score.toFixed(0)}</span>
              </div>
            </div>
            <div>
              <p className="text-gray-600 text-sm">Waste Risk Score</p>
              <div className="flex items-center gap-2">
                <div className="flex-1 bg-white rounded border border-gray-300 h-2">
                  <div
                    className="bg-yellow-500 h-full rounded"
                    style={{ width: `${Math.min(simulationResult.waste_risk_score, 100)}%` }}
                  />
                </div>
                <span className="font-semibold">{simulationResult.waste_risk_score.toFixed(0)}</span>
              </div>
            </div>
          </div>
          <div className={`p-2 rounded text-sm ${getActionColor(simulationResult.recommended_action)}`}>
            <strong>New Recommendation:</strong> {simulationResult.recommended_action}
          </div>
          <div className="mt-3 text-sm text-gray-600">
            <strong>Risk Change:</strong> {getRiskChangeLabel(simulationResult.simulated_risk_change)}
          </div>
        </div>
      )}

      {simulationResult && (
        <TradeoffVerdictCard
          verdict={tradeoffVerdict}
          isLoading={isVerdictLoading}
          error={verdictError}
          onRetry={
            onGenerateTradeoffVerdict
              ? async () => {
                  setVerdictError('');
                  setIsVerdictLoading(true);
                  try {
                    const verdict = await onGenerateTradeoffVerdict(simulationResult.simulated_order_qty);
                    setTradeoffVerdict(verdict);
                  } catch {
                    setVerdictError('AI trade-off verdict is unavailable right now. The simulation result is still usable.');
                  } finally {
                    setIsVerdictLoading(false);
                  }
                }
              : undefined
          }
        />
      )}
    </div>
  );
}
