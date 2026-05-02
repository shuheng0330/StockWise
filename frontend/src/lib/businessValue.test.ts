import { AnalysisResponse, InventoryItem } from '@/types';

import { buildBusinessValueSnapshot } from './businessValue';

function item(overrides: Partial<InventoryItem>): InventoryItem {
  return {
    item_id: 1,
    item_name: 'Item',
    unit: 'unit',
    current_stock: 0,
    reorder_level: 0,
    daily_usage: 0,
    lead_time: 0,
    price_per_unit: 0,
    seasonal_factor: 1,
    waste_percentage: 0,
    days_of_cover: 0,
    inventory_value: 0,
    estimated_waste_cost: 0,
    lead_time_demand: 0,
    stock_gap_to_lead_demand: 0,
    reorder_urgency_score: 0,
    waste_risk_score: 0,
    recommended_action: 'MONITOR_CLOSELY',
    ...overrides,
  };
}

function analysis(items: InventoryItem[]): AnalysisResponse {
  return {
    analysis_id: 'analysis-1',
    dataset_summary: {
      row_count: items.length,
      item_count: items.length,
      date_range: { start: '2025-06-12', end: '2025-06-12' },
    },
    kpi_summary: {
      item_count: items.length,
      restock_now_count: 0,
      buy_less_count: 0,
      high_waste_risk_count: 0,
      inventory_value_at_risk: 0,
      top_urgent_items: [],
      top_waste_cost_items: [],
    },
    items,
  };
}

describe('business value snapshot', () => {
  it('estimates monthly value opportunity from current waste and stockout exposure', () => {
    const snapshot = buildBusinessValueSnapshot(analysis([
      item({
        item_id: 1,
        item_name: 'Paneer',
        recommended_action: 'BUY_LESS',
        estimated_waste_cost: 10,
      }),
      item({
        item_id: 2,
        item_name: 'Milk',
        recommended_action: 'RESTOCK_NOW',
        stock_gap_to_lead_demand: -5,
        price_per_unit: 4,
      }),
    ]));

    expect(snapshot.monthlyWasteAvoided).toBe(40);
    expect(snapshot.monthlyStockoutLossAvoided).toBe(80);
    expect(snapshot.monthlyOpportunityValue).toBe(120);
    expect(snapshot.monthlyTimeSavedHours).toBe(1);
    expect(snapshot.suggestedPlan.name).toBe('Starter');
    expect(snapshot.suggestedPlan.monthlyPrice).toBe(39);
    expect(snapshot.valueToCostRatio).toBe(3.1);
  });

  it('recommends a paid plan only when there is measurable opportunity', () => {
    const snapshot = buildBusinessValueSnapshot(analysis([
      item({
        item_id: 1,
        item_name: 'Rice',
        current_stock: 12,
        recommended_action: 'MONITOR_CLOSELY',
      }),
    ]));

    expect(snapshot.monthlyOpportunityValue).toBe(0);
    expect(snapshot.suggestedPlan.name).toBe('Free');
    expect(snapshot.valueToCostRatio).toBeNull();
  });
});
