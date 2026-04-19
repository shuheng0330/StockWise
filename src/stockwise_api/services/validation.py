from dataclasses import dataclass
from io import BytesIO

import pandas as pd


REQUIRED_COLUMNS = [
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

STRING_COLUMNS = ["Item_Name", "Category", "Subcategory", "Unit", "Supplier_Name"]
NUMERIC_COLUMNS = [
    "Current_Stock",
    "Reorder_Level",
    "Daily_Usage",
    "Lead_Time",
    "Price_per_Unit",
    "Seasonal_Factor",
    "Waste_Percentage",
]


class ValidationError(ValueError):
    pass


@dataclass
class DateRangeSummary:
    start: str
    end: str


@dataclass
class DatasetSummary:
    row_count: int
    item_count: int
    date_range: DateRangeSummary


def validate_inventory_csv(raw_bytes: bytes) -> tuple[pd.DataFrame, DatasetSummary]:
    if not raw_bytes or not raw_bytes.strip():
        raise ValidationError("Uploaded file is empty.")

    try:
        dataframe = pd.read_csv(BytesIO(raw_bytes))
    except Exception as exc:  # pragma: no cover - defensive parsing error path
        raise ValidationError("Unable to parse CSV file.") from exc

    if dataframe.empty:
        raise ValidationError("Uploaded file is empty.")

    duplicate_headers = dataframe.columns[dataframe.columns.duplicated()].tolist()
    if duplicate_headers:
        raise ValidationError(f"CSV contains duplicate headers: {duplicate_headers}")

    missing = [column for column in REQUIRED_COLUMNS if column not in dataframe.columns]
    if missing:
        raise ValidationError(f"CSV is missing required columns: {', '.join(missing)}")

    normalized = dataframe[REQUIRED_COLUMNS].copy()

    for column in STRING_COLUMNS:
        normalized[column] = normalized[column].astype(str).str.strip()

    normalized["Date"] = pd.to_datetime(normalized["Date"], errors="coerce")
    if normalized["Date"].isna().any():
        raise ValidationError("CSV contains invalid Date values.")

    for column in NUMERIC_COLUMNS:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")
        if normalized[column].isna().any():
            raise ValidationError(f"CSV contains non-numeric values in {column}.")
        if (normalized[column] < 0).any():
            raise ValidationError(f"CSV contains negative values in {column}.")

    if (normalized["Daily_Usage"] <= 0).any():
        raise ValidationError("CSV contains Daily_Usage values that are zero or negative.")

    normalized["Item_ID"] = pd.to_numeric(normalized["Item_ID"], errors="coerce")
    if normalized["Item_ID"].isna().any():
        raise ValidationError("CSV contains invalid Item_ID values.")
    normalized["Item_ID"] = normalized["Item_ID"].astype(int)
    normalized["Lead_Time"] = normalized["Lead_Time"].astype(int)

    summary = DatasetSummary(
        row_count=int(len(normalized)),
        item_count=int(normalized["Item_ID"].nunique()),
        date_range=DateRangeSummary(
            start=normalized["Date"].min().strftime("%Y-%m-%d"),
            end=normalized["Date"].max().strftime("%Y-%m-%d"),
        ),
    )
    return normalized, summary
