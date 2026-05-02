import {
  buildSimulatedChatHref,
  buildSimulatedExplanationHref,
  runSimulationAndStore,
  runSimulationWithVerdict,
} from './simulationFlow';
import { SimulationResponse, TradeoffVerdictResponse } from '@/types';

const simulationResult: SimulationResponse = {
  item_id: 10,
  simulated_order_qty: 12,
  simulated_cash_outlay: 240,
  simulated_coverage_days: 6,
  simulated_inventory_value: 500,
  simulated_estimated_waste_cost: 25,
  simulated_risk_change: 'minimal_change',
  reorder_urgency_score: 40,
  waste_risk_score: 30,
  recommended_action: 'MONITOR_CLOSELY',
};

const verdictResult: TradeoffVerdictResponse = {
  source: 'mock',
  verdict: 'Cash-heavy but safe',
  reason: 'This reduces urgency but commits cash and raises waste exposure.',
  confidence_note: 'Based on simulated metrics.',
  safety_status: 'validated',
};

describe('simulation flow', () => {
  it('returns the stored simulation result so the page can render result details', async () => {
    const storeResult = jest.fn();
    const simulate = jest.fn(async () => simulationResult);

    const result = await runSimulationAndStore(12, simulate, storeResult);

    expect(result).toBe(simulationResult);
    expect(storeResult).toHaveBeenCalledWith(simulationResult);
  });

  it('runs the AI verdict after a successful simulation and stores both results', async () => {
    const storeResult = jest.fn();
    const storeVerdict = jest.fn();
    const simulate = jest.fn(async () => simulationResult);
    const fetchVerdict = jest.fn(async () => verdictResult);

    const result = await runSimulationWithVerdict(12, simulate, fetchVerdict, storeResult, storeVerdict);

    expect(result).toBe(simulationResult);
    expect(fetchVerdict).toHaveBeenCalledWith(simulationResult.simulated_order_qty);
    expect(storeResult).toHaveBeenCalledWith(simulationResult);
    expect(storeVerdict).toHaveBeenCalledWith(verdictResult);
  });

  it('builds a simulated explanation route for the same item', () => {
    expect(buildSimulatedExplanationHref('analysis-1', '10', 12)).toBe(
      '/explanation/analysis-1/10?simulated=12'
    );
  });

  it('builds a simulated chat handoff route back to the dashboard', () => {
    expect(buildSimulatedChatHref('analysis-1', '10', 12)).toBe(
      '/dashboard/analysis-1?chatItemId=10&simulated=12&chatPrompt=What%20changed%20after%20my%20simulation%3F'
    );
  });
});
