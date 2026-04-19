from io import BytesIO

import pytest

from stockwise_api.services.validation import ValidationError, validate_inventory_csv
from tests.fixtures import DATASET_PATH


def test_validate_inventory_csv_returns_normalized_dataframe_and_summary():
    with DATASET_PATH.open("rb") as f:
        normalized, summary = validate_inventory_csv(f.read())

    assert list(normalized.columns) == [
        "Date",
        "Item_ID",
        "Item_Name",
        "Category",
        "Subcategory",
        "Unit",
        "Current_Stock",
        "Reorder_Level",
        "Daily_Usage",
        "Lead_Time",
        "Price_per_Unit",
        "Supplier_Name",
        "Seasonal_Factor",
        "Waste_Percentage",
    ]
    assert summary.row_count == 1000
    assert summary.item_count == 10
    assert summary.date_range.start == "2025-06-10"
    assert summary.date_range.end == "2025-09-17"


def test_validate_inventory_csv_rejects_missing_required_column():
    raw = (
        "Date,Item_ID,Item_Name,Category,Subcategory,Unit,Current_Stock,Reorder_Level,Daily_Usage,"
        "Lead_Time,Price_per_Unit,Supplier_Name,Seasonal_Factor\n"
        "2025-01-01,1,Paneer,Veg,Dairy,kg,10,5,2,3,450,Supplier A,1.1\n"
    ).encode()

    with pytest.raises(ValidationError, match="Waste_Percentage"):
        validate_inventory_csv(raw)


def test_validate_inventory_csv_rejects_empty_file():
    with pytest.raises(ValidationError, match="empty"):
        validate_inventory_csv(b"")


def test_validate_inventory_csv_rejects_negative_numeric_value():
    raw = (
        "Date,Item_ID,Item_Name,Category,Subcategory,Unit,Current_Stock,Reorder_Level,Daily_Usage,"
        "Lead_Time,Price_per_Unit,Supplier_Name,Seasonal_Factor,Waste_Percentage\n"
        "2025-01-01,1,Paneer,Veg,Dairy,kg,-10,5,2,3,450,Supplier A,1.1,2.5\n"
    ).encode()

    with pytest.raises(ValidationError, match="negative"):
        validate_inventory_csv(raw)
