import pytest

from stockwise_api.services.manual_input import (
    ManualInputValidationError,
    normalize_item_history,
    normalize_manual_items,
)


def test_normalize_manual_items_converts_weekly_usage_and_preserves_required_score_inputs():
    items = [
        {
            "item_name": "Paneer",
            "current_stock": 14.0,
            "unit": "kg",
            "usage_value": 14.0,
            "usage_period": "weekly",
            "lead_time_days": 3,
            "price_per_unit": 450.0,
            "seasonal_factor": 1.0,
            "category": "Dairy",
            "supplier_name": "Supplier A",
            "perishability_level": "high",
        }
    ]

    normalized = normalize_manual_items(items)
    paneer = normalized[0]

    assert paneer["item_id"] == 1
    assert paneer["daily_usage"] == 2.0
    assert paneer["seasonal_factor"] == 1.0
    assert paneer["reorder_level"] > 0
    assert paneer["waste_percentage"] == 4.5


def test_normalize_manual_items_uses_optional_overrides_when_present():
    items = [
        {
            "item_name": "Milk",
            "current_stock": 8.0,
            "unit": "litre",
            "usage_value": 4.0,
            "usage_period": "daily",
            "lead_time_days": 2,
            "price_per_unit": 8.0,
            "manual_reorder_level": 9.5,
            "seasonal_factor": 1.2,
            "recent_waste_percentage": 6.0,
        }
    ]

    normalized = normalize_manual_items(items)
    milk = normalized[0]

    assert milk["reorder_level"] == 9.5
    assert milk["seasonal_factor"] == 1.2
    assert milk["waste_percentage"] == 6.0


def test_normalize_item_history_keeps_latest_snapshot_and_computes_trend():
    items = [
        {
            "date": "2025-06-10",
            "item_name": "Milk",
            "current_stock": 10.0,
            "unit": "litre",
            "usage_value": 2.0,
            "usage_period": "daily",
            "lead_time_days": 2,
            "price_per_unit": 8.0,
            "seasonal_factor": 1.0,
            "perishability_level": "medium",
        },
        {
            "date": "2025-06-11",
            "item_name": "Milk",
            "current_stock": 8.0,
            "unit": "litre",
            "usage_value": 3.0,
            "usage_period": "daily",
            "lead_time_days": 2,
            "price_per_unit": 8.0,
            "seasonal_factor": 1.0,
            "perishability_level": "medium",
        },
        {
            "date": "2025-06-12",
            "item_name": "Milk",
            "current_stock": 5.0,
            "unit": "litre",
            "usage_value": 4.0,
            "usage_period": "daily",
            "lead_time_days": 2,
            "price_per_unit": 8.0,
            "seasonal_factor": 1.0,
            "perishability_level": "medium",
        },
    ]

    history = normalize_item_history(items)

    assert len(history) == 1
    milk = history[0]
    assert milk["date"] == "2025-06-12"
    assert milk["item_id"] == 1
    assert milk["current_stock"] == 5.0
    assert milk["daily_usage"] == 4.0
    assert milk["avg_usage_7d"] == 3.0
    assert milk["trend_direction"] == "up"


def test_normalize_manual_items_rejects_missing_required_fields():
    items = [
        {
            "item_name": "Eggs",
            "current_stock": 10.0,
            "unit": "pieces",
            "usage_value": 5.0,
        }
    ]

    with pytest.raises(ManualInputValidationError, match="lead_time_days"):
        normalize_manual_items(items)


def test_normalize_manual_items_rejects_invalid_usage_period():
    items = [
        {
            "item_name": "Eggs",
            "current_stock": 10.0,
            "unit": "pieces",
            "usage_value": 5.0,
            "usage_period": "monthly",
            "lead_time_days": 2,
            "price_per_unit": 0.6,
            "seasonal_factor": 1.0,
            "perishability_level": "medium",
        }
    ]

    with pytest.raises(ManualInputValidationError, match="usage_period"):
        normalize_manual_items(items)
