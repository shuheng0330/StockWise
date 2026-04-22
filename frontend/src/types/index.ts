// Type definitions for StockWise frontend

export type RecommendedAction = 'RESTOCK_NOW' | 'BUY_LESS' | 'DELAY_PURCHASE' | 'MONITOR_CLOSELY';
export type UsagePeriod = 'daily' | 'weekly';
export type PerishabilityLevel = 'low' | 'medium' | 'high';

export interface InventoryItem {
  item_id: string;
  item_name: string;
  category?: string;
  subcategory?: string;
  unit: string;
  supplier_name?: string;
  current_stock: number;
  reorder_level: number;
  daily_usage: number;
  lead_time: number;
  price_per_unit: number;
  seasonal_factor: number;
  waste_percentage: number;
  days_of_cover: number;
  inventory_value: number;
  estimated_waste_cost: number;
  lead_time_demand: number;
  stock_gap_to_lead_demand: number;
  reorder_urgency_score: number;
  waste_risk_score: number;
  recommended_action: RecommendedAction;
}

export interface KPISummary {
  item_count: number;
  restock_now_count: number;
  buy_less_count: number;
  high_waste_risk_count: number;
  inventory_value_at_risk: number;
  top_urgent_items: string[];
  top_waste_cost_items: string[];
}

export interface DatasetSummary {
  total_items: number;
  total_inventory_value: number;
  avg_days_of_cover: number;
}

export interface AnalysisResponse {
  analysis_id: string;
  dataset_summary: DatasetSummary;
  kpi_summary: KPISummary;
  items: InventoryItem[];
}

export interface SimulationRequest {
  simulated_order_qty: number;
}

export interface SimulationResponse {
  item_id: string;
  simulated_order_qty: number;
  simulated_cash_outlay: number;
  simulated_coverage_days: number;
  simulated_inventory_value: number;
  simulated_estimated_waste_cost: number;
  simulated_risk_change: number;
  reorder_urgency_score: number;
  waste_risk_score: number;
  recommended_action: RecommendedAction;
}

export interface ExplanationRequest {
  simulated_order_qty?: number;
  simulated_cash_outlay?: number;
  simulated_coverage_days?: number;
  simulated_risk_change?: number;
}

export interface ExplanationResponse {
  source: 'mock' | 'live' | 'fallback';
  item_name: string;
  recommended_action: RecommendedAction;
  priority_level: 'high' | 'medium' | 'low';
  short_reason: string;
  decision_explanation: string;
  tradeoff_summary: string;
  suggested_next_step: string;
  confidence_note: string;
  warning_flag: boolean;
}

export interface ManualItemInput {
  item_name: string;
  current_stock: number;
  unit: string;
  usage_value: number;
  usage_period: UsagePeriod;
  lead_time_days: number;
  price_per_unit: number;
  seasonal_factor: number;
  category?: string;
  subcategory?: string;
  supplier_name?: string;
  perishability_level?: PerishabilityLevel;
  manual_reorder_level?: number;
  recent_waste_percentage?: number;
}

export interface ApiError {
  error_code: string;
  message: string;
  details?: Record<string, any>;
}

export interface FilterOptions {
  search: string;
  actions: RecommendedAction[];
  categories: string[];
}
