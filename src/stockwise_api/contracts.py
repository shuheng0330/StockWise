from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


CANONICAL_REQUIRED_FIELDS = [
    "item_name",
    "current_stock",
    "unit",
    "usage_value",
    "usage_period",
    "lead_time_days",
    "price_per_unit",
    "seasonal_factor",
]

CANONICAL_OPTIONAL_FIELDS = [
    "category",
    "supplier_name",
]

CANONICAL_ADVANCED_OPTIONAL_FIELDS = [
    "manual_reorder_level",
    "perishability_level",
    "recent_waste_percentage",
]

WASTE_SIGNAL_FIELDS = [
    "perishability_level",
    "recent_waste_percentage",
]

CANONICAL_METADATA_FIELDS = [
    "date",
    "item_id",
    "subcategory",
]

CANONICAL_ITEM_FIELDS = (
    CANONICAL_METADATA_FIELDS
    + CANONICAL_REQUIRED_FIELDS
    + CANONICAL_OPTIONAL_FIELDS
    + CANONICAL_ADVANCED_OPTIONAL_FIELDS
)

CSV_HEADER_ALIASES = {
    "date": "date",
    "Date": "date",
    "item_id": "item_id",
    "Item_ID": "item_id",
    "item_name": "item_name",
    "Item_Name": "item_name",
    "current_stock": "current_stock",
    "Current_Stock": "current_stock",
    "unit": "unit",
    "Unit": "unit",
    "usage_value": "usage_value",
    "Daily_Usage": "usage_value",
    "usage_period": "usage_period",
    "lead_time_days": "lead_time_days",
    "Lead_Time": "lead_time_days",
    "price_per_unit": "price_per_unit",
    "Price_per_Unit": "price_per_unit",
    "category": "category",
    "Category": "category",
    "subcategory": "subcategory",
    "Subcategory": "subcategory",
    "supplier_name": "supplier_name",
    "Supplier_Name": "supplier_name",
    "perishability_level": "perishability_level",
    "manual_reorder_level": "manual_reorder_level",
    "Reorder_Level": "manual_reorder_level",
    "seasonal_factor": "seasonal_factor",
    "Seasonal_Factor": "seasonal_factor",
    "recent_waste_percentage": "recent_waste_percentage",
    "Waste_Percentage": "recent_waste_percentage",
}

ALLOWED_USAGE_PERIODS = {"daily", "weekly"}
ALLOWED_PERISHABILITY_LEVELS = {"low", "medium", "high"}


def _normalize_string(value):
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


class CanonicalItemBase(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    date: str | None = None
    item_id: int | None = Field(default=None, ge=1)
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

    @field_validator("date", "category", "subcategory", "supplier_name", mode="before")
    @classmethod
    def _normalize_optional_text(cls, value):
        return _normalize_string(value)

    @field_validator("item_name", "unit", mode="before")
    @classmethod
    def _normalize_required_text(cls, value):
        return _normalize_string(value)

    @field_validator("usage_period", "perishability_level", mode="before")
    @classmethod
    def _normalize_enums(cls, value):
        normalized = _normalize_string(value)
        return normalized.lower() if normalized is not None else None

    @field_validator("item_name", "unit")
    @classmethod
    def _validate_non_blank_required_text(cls, value, info):
        if value is None:
            return value
        if not value:
            raise ValueError(f"{info.field_name} cannot be blank.")
        return value


class CanonicalItemInput(CanonicalItemBase):
    item_name: str
    current_stock: float = Field(ge=0)
    unit: str
    usage_value: float = Field(gt=0)
    usage_period: Literal["daily", "weekly"]
    lead_time_days: int = Field(gt=0)
    price_per_unit: float = Field(ge=0)
    seasonal_factor: float = Field(ge=0)

    @model_validator(mode="after")
    def _validate_waste_signal(self):
        if self.perishability_level is None and self.recent_waste_percentage is None:
            raise ValueError("Manual item must include either perishability_level or recent_waste_percentage.")
        return self


class PartialCanonicalItemInput(CanonicalItemBase):
    pass
