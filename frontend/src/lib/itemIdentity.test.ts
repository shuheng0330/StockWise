import { findInventoryItemByRouteId } from './itemIdentity';
import { InventoryItem } from '@/types';

const baseItem: InventoryItem = {
  item_id: 1,
  item_name: 'Paneer',
  category: 'Dairy',
  subcategory: 'Cheese',
  unit: 'kg',
  supplier_name: 'Supplier A',
  current_stock: 5,
  reorder_level: 8,
  daily_usage: 4,
  lead_time: 3,
  price_per_unit: 450,
  seasonal_factor: 1.1,
  waste_percentage: 4,
  days_of_cover: 1.25,
  inventory_value: 2250,
  estimated_waste_cost: 90,
  lead_time_demand: 13.2,
  stock_gap_to_lead_demand: -8.2,
  reorder_urgency_score: 88,
  waste_risk_score: 42,
  recommended_action: 'RESTOCK_NOW',
};

describe('item route identity', () => {
  it('matches numeric API item ids to string route params', () => {
    expect(findInventoryItemByRouteId([baseItem], '1')).toBe(baseItem);
  });
});
