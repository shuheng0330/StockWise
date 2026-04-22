import { buildSimulatedExplanationHref, runSimulationAndStore } from './simulationFlow';
import { SimulationResponse } from '@/types';

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

describe('simulation flow', () => {
  it('returns the stored simulation result so the page can render result details', async () => {
    const storeResult = jest.fn();
    const simulate = jest.fn(async () => simulationResult);

    const result = await runSimulationAndStore(12, simulate, storeResult);

    expect(result).toBe(simulationResult);
    expect(storeResult).toHaveBeenCalledWith(simulationResult);
  });

  it('builds a simulated explanation route for the same item', () => {
    expect(buildSimulatedExplanationHref('analysis-1', '10', 12)).toBe(
      '/explanation/analysis-1/10?simulated=12'
    );
  });
});
