from typing import Any, Literal

from pydantic import BaseModel, Field

from stockwise_api.contracts import CanonicalItemInput


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
    recommended_action: Literal[
        "RESTOCK_NOW", "BUY_LESS", "DELAY_PURCHASE", "MONITOR_CLOSELY"
    ]


class AnalysisResponse(BaseModel):
    analysis_id: str
    dataset_summary: DatasetSummary
    kpi_summary: KpiSummary
    items: list[ItemAnalysis]


class DecisionBriefItem(BaseModel):
    item_id: int
    item_name: str
    recommended_action: Literal[
        "RESTOCK_NOW", "BUY_LESS", "DELAY_PURCHASE", "MONITOR_CLOSELY"
    ]
    reason: str


class DecisionBriefImpact(BaseModel):
    cash: str
    waste: str
    shortage: str


class DecisionBriefResponse(BaseModel):
    source: Literal["live", "mock", "fallback"]
    summary: str
    buy_today: list[DecisionBriefItem]
    buy_less: list[DecisionBriefItem]
    delay: list[DecisionBriefItem]
    estimated_impact: DecisionBriefImpact
    top_tradeoffs: list[str]
    recommended_order: list[str]
    confidence_note: str
    warning_flag: str | None = None
    safety_status: Literal["validated", "retried", "fallback_used"]


class ManualItemInput(CanonicalItemInput):
    pass


class ManualAnalysisRequest(BaseModel):
    items: list[ManualItemInput]
    base_analysis_id: str | None = None


class RecordItem(BaseModel):
    item_id: int
    last_updated: str
    item_name: str
    current_stock: float
    unit: str
    usage_value: float
    usage_period: Literal["daily", "weekly"]
    daily_usage: float
    lead_time_days: int
    price_per_unit: float
    category: str | None = None
    subcategory: str | None = None
    supplier_name: str | None = None
    perishability_level: Literal["low", "medium", "high"] | None = None
    manual_reorder_level: float | None = None
    seasonal_factor: float
    recent_waste_percentage: float | None = None
    recommended_action: Literal[
        "RESTOCK_NOW", "BUY_LESS", "DELAY_PURCHASE", "MONITOR_CLOSELY"
    ]


class SourceObservation(BaseModel):
    date: str | None = None
    item_id: int | None = None
    item_name: str
    current_stock: float
    unit: str
    usage_value: float
    usage_period: Literal["daily", "weekly"]
    lead_time_days: int
    price_per_unit: float
    category: str | None = None
    subcategory: str | None = None
    supplier_name: str | None = None
    perishability_level: Literal["low", "medium", "high"] | None = None
    manual_reorder_level: float | None = None
    seasonal_factor: float
    recent_waste_percentage: float | None = None


class RecordsResponse(BaseModel):
    analysis_id: str
    dataset_summary: DatasetSummary
    kpi_summary: KpiSummary
    items: list[RecordItem]
    source_observations: list[SourceObservation] = Field(default_factory=list)


class RecordUpdateRequest(BaseModel):
    date: str | None = None
    item_name: str | None = None
    current_stock: float | None = Field(default=None, ge=0)
    unit: str | None = None
    usage_value: float | None = Field(default=None, gt=0)
    usage_period: Literal["daily", "weekly"] | None = None
    lead_time_days: int | None = Field(default=None, gt=0)
    price_per_unit: float | None = Field(default=None, ge=0)
    category: str | None = None
    subcategory: str | None = None
    supplier_name: str | None = None
    perishability_level: Literal["low", "medium", "high"] | None = None
    manual_reorder_level: float | None = Field(default=None, ge=0)
    seasonal_factor: float | None = Field(default=None, ge=0)
    recent_waste_percentage: float | None = Field(default=None, ge=0)


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
    recommended_action: Literal[
        "RESTOCK_NOW", "BUY_LESS", "DELAY_PURCHASE", "MONITOR_CLOSELY"
    ]


class TradeoffVerdictRequest(BaseModel):
    simulated_order_qty: float = Field(ge=0)


class TradeoffVerdictResponse(BaseModel):
    source: Literal["live", "mock", "fallback"]
    verdict: Literal[
        "Worth it",
        "Too much stock",
        "Cash-heavy but safe",
        "Try smaller quantity",
        "Good emergency reorder",
    ]
    reason: str
    confidence_note: str
    safety_status: Literal["validated", "retried", "fallback_used"]


class ExplanationRequest(BaseModel):
    simulated_order_qty: float | None = Field(default=None, ge=0)
    simulated_cash_outlay: float | None = None
    simulated_coverage_days: float | None = None
    simulated_risk_change: str | None = None


class ExplanationResponse(BaseModel):
    source: Literal["live", "mock", "fallback"]
    item_name: str
    recommended_action: Literal[
        "RESTOCK_NOW", "BUY_LESS", "DELAY_PURCHASE", "MONITOR_CLOSELY"
    ]
    priority_level: Literal["HIGH", "MEDIUM", "LOW"]
    short_reason: str
    decision_explanation: str
    tradeoff_summary: str
    suggested_next_step: str
    confidence_note: str
    warning_flag: str


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=500)


class SimulationChatContext(BaseModel):
    item_id: int
    simulated_order_qty: float = Field(ge=0)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    recent_messages: list[ChatMessage] = Field(default_factory=list, max_length=6)
    simulation_context: SimulationChatContext | None = None


class ChatRelatedItem(BaseModel):
    item_id: int
    item_name: str
    recommended_action: Literal[
        "RESTOCK_NOW", "BUY_LESS", "DELAY_PURCHASE", "MONITOR_CLOSELY"
    ]
    reason: str


class ChatResponse(BaseModel):
    source: Literal["live", "mock", "fallback"]
    scope: Literal["analysis", "simulation"]
    answer: str
    supporting_points: list[str]
    related_items: list[ChatRelatedItem]
    suggested_follow_ups: list[str]
    warning_flag: str | None = None


class ManualItemInput(BaseModel):
    item_name: str
    current_stock: float = Field(ge=0)
    unit: str
    usage_value: float = Field(ge=0)
    usage_period: Literal["daily", "weekly"]
    lead_time_days: int = Field(ge=0)
    price_per_unit: float = Field(ge=0)
    seasonal_factor: float = Field(ge=0, le=2.0)
    category: str = ""
    perishability_level: str | None = None
    recent_waste_percentage: float | None = Field(default=None, ge=0)
