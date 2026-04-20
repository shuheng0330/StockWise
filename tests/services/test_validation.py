import pytest

from stockwise_api.services.validation import (
    ValidationError,
    validate_inventory_csv,
    validate_manual_item_payload,
)


def test_validate_inventory_csv_accepts_owner_friendly_columns():
    raw = (
        "item_name,current_stock,unit,usage_value,usage_period,lead_time_days,price_per_unit,category,supplier_name,perishability_level,manual_reorder_level,seasonal_factor,recent_waste_percentage\n"
        "Paneer,12,kg,14,weekly,3,450,Dairy,Supplier A,high,8,1.1,4.0\n"
        "Rice,20,kg,2,daily,2,70,Grain,Supplier B,low,,1.0, \n"
    ).encode()

    rows, summary = validate_inventory_csv(raw)

    assert len(rows) == 2
    assert rows[0]["item_name"] == "Paneer"
    assert rows[0]["usage_period"] == "weekly"
    assert rows[0]["lead_time_days"] == 3
    assert rows[0]["recent_waste_percentage"] == 4.0
    assert summary.row_count == 2
    assert summary.item_count == 2


def test_validate_inventory_csv_accepts_legacy_dataset_columns_and_maps_to_canonical_fields():
    raw = (
        "Date,Item_ID,Item_Name,Category,Subcategory,Unit,Current_Stock,Reorder_Level,Daily_Usage,Lead_Time,Price_per_Unit,Supplier_Name,Seasonal_Factor,Waste_Percentage\n"
        "2025-06-10,1,Paneer,Dairy,Cheese,kg,12,8,2,3,450,Supplier A,1.1,4.0\n"
        "2025-06-11,2,Rice,Grain,Staple,kg,20,6,2,2,70,Supplier B,1.0,1.5\n"
    ).encode()

    rows, summary = validate_inventory_csv(raw)

    assert len(rows) == 2
    assert rows[0]["date"] == "2025-06-10"
    assert rows[0]["item_id"] == 1
    assert rows[0]["item_name"] == "Paneer"
    assert rows[0]["category"] == "Dairy"
    assert rows[0]["subcategory"] == "Cheese"
    assert rows[0]["usage_value"] == 2.0
    assert rows[0]["usage_period"] == "daily"
    assert rows[0]["lead_time_days"] == 3
    assert rows[0]["manual_reorder_level"] == 8.0
    assert rows[0]["recent_waste_percentage"] == 4.0
    assert summary.date_range.start == "2025-06-10"
    assert summary.date_range.end == "2025-06-11"


def test_validate_inventory_csv_rejects_missing_required_column():
    raw = (
        "item_name,current_stock,unit,usage_value,usage_period,price_per_unit,seasonal_factor,perishability_level\n"
        "Paneer,12,kg,14,weekly,450,1.1,high\n"
    ).encode()

    with pytest.raises(ValidationError, match="lead_time_days"):
        validate_inventory_csv(raw)


def test_validate_inventory_csv_rejects_empty_file():
    with pytest.raises(ValidationError, match="empty"):
        validate_inventory_csv(b"")


def test_validate_inventory_csv_rejects_negative_numeric_value():
    raw = (
        "item_name,current_stock,unit,usage_value,usage_period,lead_time_days,price_per_unit,seasonal_factor,perishability_level\n"
        "Paneer,-10,kg,14,weekly,3,450,1.1,high\n"
    ).encode()

    with pytest.raises(ValidationError, match="negative"):
        validate_inventory_csv(raw)


def test_validate_inventory_csv_rejects_invalid_usage_period():
    raw = (
        "item_name,current_stock,unit,usage_value,usage_period,lead_time_days,price_per_unit,seasonal_factor,perishability_level\n"
        "Paneer,10,kg,14,monthly,3,450,1.1,high\n"
    ).encode()

    with pytest.raises(ValidationError, match="usage_period"):
        validate_inventory_csv(raw)


def test_validate_manual_item_payload_accepts_owner_friendly_required_fields():
    payload = validate_manual_item_payload(
        {
            "item_name": "Paneer",
            "current_stock": 12,
            "unit": "kg",
            "usage_value": 14,
            "usage_period": "weekly",
            "lead_time_days": 3,
            "price_per_unit": 450,
            "seasonal_factor": 1.1,
            "perishability_level": "high",
        }
    )

    assert payload["item_name"] == "Paneer"
    assert payload["usage_period"] == "weekly"
    assert payload["lead_time_days"] == 3


def test_validate_manual_item_payload_rejects_missing_price_per_unit():
    with pytest.raises(ValidationError, match="price_per_unit"):
        validate_manual_item_payload(
            {
                "item_name": "Paneer",
                "current_stock": 12,
                "unit": "kg",
                "usage_value": 14,
                "usage_period": "weekly",
                "lead_time_days": 3,
                "seasonal_factor": 1.1,
                "perishability_level": "high",
            }
        )


def test_validate_manual_item_payload_rejects_missing_seasonal_factor():
    with pytest.raises(ValidationError, match="seasonal_factor"):
        validate_manual_item_payload(
            {
                "item_name": "Paneer",
                "current_stock": 12,
                "unit": "kg",
                "usage_value": 14,
                "usage_period": "weekly",
                "lead_time_days": 3,
                "price_per_unit": 450,
                "perishability_level": "high",
            }
        )


def test_validate_manual_item_payload_rejects_when_waste_signal_is_missing():
    with pytest.raises(ValidationError, match="perishability_level|recent_waste_percentage|waste"):
        validate_manual_item_payload(
            {
                "item_name": "Paneer",
                "current_stock": 12,
                "unit": "kg",
                "usage_value": 14,
                "usage_period": "weekly",
                "lead_time_days": 3,
                "price_per_unit": 450,
                "seasonal_factor": 1.1,
            }
        )


def test_validate_manual_item_payload_accepts_recent_waste_percentage_without_perishability_level():
    payload = validate_manual_item_payload(
        {
            "item_name": "Paneer",
            "current_stock": 12,
            "unit": "kg",
            "usage_value": 14,
            "usage_period": "weekly",
            "lead_time_days": 3,
            "price_per_unit": 450,
            "seasonal_factor": 1.1,
            "recent_waste_percentage": 4.0,
        }
    )

    assert payload["recent_waste_percentage"] == 4.0
    assert "perishability_level" not in payload


def test_validate_manual_item_payload_preserves_optional_fields_used_by_csv_and_records():
    payload = validate_manual_item_payload(
        {
            "date": "2025-06-10",
            "item_id": 7,
            "item_name": "Paneer",
            "current_stock": 12,
            "unit": "kg",
            "usage_value": 14,
            "usage_period": "weekly",
            "lead_time_days": 3,
            "price_per_unit": 450,
            "seasonal_factor": 1.1,
            "subcategory": "Cheese",
            "manual_reorder_level": 8,
            "recent_waste_percentage": 4.0,
        }
    )

    assert payload["date"] == "2025-06-10"
    assert payload["item_id"] == 7
    assert payload["subcategory"] == "Cheese"
    assert payload["manual_reorder_level"] == 8.0
    assert payload["recent_waste_percentage"] == 4.0


def test_validate_manual_item_payload_rejects_invalid_perishability_level():
    with pytest.raises(ValidationError, match="perishability_level"):
        validate_manual_item_payload(
            {
                "item_name": "Paneer",
                "current_stock": 12,
                "unit": "kg",
                "usage_value": 14,
                "usage_period": "weekly",
                "lead_time_days": 3,
                "price_per_unit": 450,
                "seasonal_factor": 1.1,
                "perishability_level": "very_high",
            }
        )
