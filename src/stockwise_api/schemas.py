from typing import Any, Literal

from pydantic import BaseModel, Field


class ErrorEnvelope(BaseModel):
    error_code: str
    message: str
    details: Any | None = None


class DateRange(BaseModel):
    start: str
    end: str


class DatasetSummary(BaseModel):
    row_count: int
    item_count: int
    date_range: DateRange


class KpiSummary(BaseModel):
    item_count: int
    restock_now_count: int
    buy_less_count: int
    high_waste_risk_count: int
    inventory_value_at_risk: float
    top_urgent_items: list[str]
    top_waste_cost_items: list[str]


class ItemAnalysis(BaseModel):
    item_id: int
    date: str
    item_name: str
    category: str
    subcategory: str
    unit: str
    supplier_name: str
    current_stock: float
    reorder_level: float
    daily_usage: float
    lead_time: int
    price_per_unit: float
    seasonal_factor: float
    waste_percentage: float
    avg_usage_7d: float
    trend_direction: Literal["up", "down", "stable"]
    days_of_cover: float
    inventory_value: float
    estimated_waste_cost: float
    lead_time_demand: float
    stock_gap_to_lead_demand: float
    reorder_urgency_score: int
    waste_risk_score: int
    recommended_action: Literal["RESTOCK_NOW", "BUY_LESS", "DELAY_PURCHASE", "MONITOR_CLOSELY"]


class AnalysisResponse(BaseModel):
    analysis_id: str
    dataset_summary: DatasetSummary
    kpi_summary: KpiSummary
    items: list[ItemAnalysis]


class SimulationRequest(BaseModel):
    simulated_order_qty: float = Field(ge=0)


class SimulationResponse(BaseModel):
    item_id: int
    simulated_order_qty: float
    simulated_cash_outlay: float
    simulated_coverage_days: float
    simulated_inventory_value: float
    simulated_estimated_waste_cost: float
    simulated_risk_change: Literal[
        "lower_shortage_risk",
        "lower_waste_risk",
        "higher_waste_risk",
        "minimal_change",
    ]
    reorder_urgency_score: int
    waste_risk_score: int
    recommended_action: Literal["RESTOCK_NOW", "BUY_LESS", "DELAY_PURCHASE", "MONITOR_CLOSELY"]


class ExplanationRequest(BaseModel):
    simulated_order_qty: float | None = Field(default=None, ge=0)
    simulated_cash_outlay: float | None = None
    simulated_coverage_days: float | None = None
    simulated_risk_change: str | None = None


class ExplanationResponse(BaseModel):
    source: Literal["live", "mock", "fallback"]
    item_name: str
    recommended_action: Literal["RESTOCK_NOW", "BUY_LESS", "DELAY_PURCHASE", "MONITOR_CLOSELY"]
    priority_level: Literal["HIGH", "MEDIUM", "LOW"]
    short_reason: str
    decision_explanation: str
    tradeoff_summary: str
    suggested_next_step: str
    confidence_note: str
    warning_flag: str
