import csv
from dataclasses import dataclass
from io import StringIO

import pandas as pd
from pydantic import ValidationError as PydanticValidationError

from stockwise_api.contracts import (
    CANONICAL_ITEM_FIELDS,
    CANONICAL_REQUIRED_FIELDS,
    CSV_HEADER_ALIASES,
    WASTE_SIGNAL_FIELDS,
    CanonicalItemInput,
)


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


def _format_contract_validation_error(exc: PydanticValidationError) -> str:
    errors = exc.errors()
    missing = [err["loc"][-1] for err in errors if err["type"] == "missing"]
    if missing:
        ordered_missing = [field for field in CANONICAL_REQUIRED_FIELDS if field in missing]
        return f"Manual item is missing required fields: {', '.join(ordered_missing)}"

    err = errors[0]
    field = err["loc"][-1] if err["loc"] else ""
    error_type = err["type"]

    if field == "" and error_type == "value_error":
        if "perishability_level" in err["msg"] or "recent_waste_percentage" in err["msg"]:
            return "Manual item must include either perishability_level or recent_waste_percentage."
        return err["msg"]

    if field == "usage_period":
        return "Manual item usage_period must be 'daily' or 'weekly'."

    if field == "perishability_level":
        return "Manual item perishability_level must be 'low', 'medium', or 'high'."

    if field in {
        "current_stock",
        "usage_value",
        "lead_time_days",
        "price_per_unit",
        "manual_reorder_level",
        "seasonal_factor",
        "recent_waste_percentage",
        "item_id",
    } and error_type in {"float_parsing", "int_parsing", "int_from_float", "float_type", "int_type"}:
        return f"Manual item field '{field}' must be numeric."

    if field == "usage_value" and error_type == "greater_than":
        return "Manual item usage_value must be greater than zero."

    if field == "lead_time_days" and error_type == "greater_than":
        return "Manual item lead_time_days must be greater than zero."

    if field in {
        "current_stock",
        "price_per_unit",
        "manual_reorder_level",
        "seasonal_factor",
        "recent_waste_percentage",
        "item_id",
    } and error_type == "greater_than_equal":
        return f"Manual item field '{field}' cannot be negative."

    if field in {"item_name", "unit"} and error_type == "value_error":
        return f"Manual item field '{field}' cannot be blank."

    return err["msg"]


def _clean_csv_value(value):
    if isinstance(value, str):
        value = value.strip()
    return None if value == "" else value


def _canonicalize_csv_row(row: dict) -> dict:
    payload = {}
    for key, value in row.items():
        header = key.strip() if isinstance(key, str) else key
        canonical_key = CSV_HEADER_ALIASES.get(header, header)
        cleaned_value = _clean_csv_value(value)
        if canonical_key in payload and cleaned_value is not None and payload[canonical_key] not in (None, cleaned_value):
            raise ValidationError(f"CSV maps multiple columns to the same field: {canonical_key}")
        payload[canonical_key] = cleaned_value

    if payload.get("usage_value") is not None and payload.get("usage_period") is None:
        payload["usage_period"] = "daily"

    return {key: value for key, value in payload.items() if key in CANONICAL_ITEM_FIELDS}


def _summarize_date_range(rows: list[dict]) -> DateRangeSummary:
    dates = [row["date"] for row in rows if row.get("date")]
    if dates:
        try:
            parsed = pd.to_datetime(dates)
        except Exception as exc:
            raise ValidationError("CSV field 'date' must be a valid date.") from exc
        return DateRangeSummary(
            start=parsed.min().strftime("%Y-%m-%d"),
            end=parsed.max().strftime("%Y-%m-%d"),
        )

    today = pd.Timestamp.today().strftime("%Y-%m-%d")
    return DateRangeSummary(start=today, end=today)


def validate_manual_item_payload(item: dict) -> dict:
    try:
        return CanonicalItemInput.model_validate(item).model_dump(exclude_none=True)
    except PydanticValidationError as exc:
        raise ValidationError(_format_contract_validation_error(exc)) from exc


def validate_inventory_csv(raw_bytes: bytes) -> tuple[list[dict], DatasetSummary]:
    if not raw_bytes or not raw_bytes.strip():
        raise ValidationError("Uploaded file is empty.")

    try:
        text = raw_bytes.decode("utf-8-sig")
        reader = csv.DictReader(StringIO(text))
        rows = list(reader)
    except Exception as exc:  # pragma: no cover - defensive parsing error path
        raise ValidationError("Unable to parse CSV file.") from exc

    if not rows:
        raise ValidationError("Uploaded file is empty.")

    fieldnames = reader.fieldnames or []
    seen = set()
    duplicate_headers = []
    for header in fieldnames:
        if header in seen:
            duplicate_headers.append(header)
        seen.add(header)
    if duplicate_headers:
        raise ValidationError(f"CSV contains duplicate headers: {duplicate_headers}")

    canonical_headers = [CSV_HEADER_ALIASES.get(header.strip(), header.strip()) for header in fieldnames]
    if "Daily_Usage" in fieldnames and "usage_period" not in canonical_headers:
        canonical_headers.append("usage_period")
    canonical_duplicates = [header for index, header in enumerate(canonical_headers) if header in canonical_headers[:index]]
    if canonical_duplicates:
        raise ValidationError(f"CSV contains duplicate mapped headers: {canonical_duplicates}")

    missing = [column for column in CANONICAL_REQUIRED_FIELDS if column not in canonical_headers]
    if missing:
        raise ValidationError(f"CSV is missing required columns: {', '.join(missing)}")
    if not any(column in canonical_headers for column in WASTE_SIGNAL_FIELDS):
        raise ValidationError("CSV is missing required waste-signal column: provide perishability_level or recent_waste_percentage.")

    validated_rows = []
    for row in rows:
        payload = _canonicalize_csv_row(row)
        validated_rows.append(validate_manual_item_payload(payload))

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
        raise ValidationError(
            "CSV contains Daily_Usage values that are zero or negative."
        )

    normalized["Item_ID"] = pd.to_numeric(normalized["Item_ID"], errors="coerce")
    if normalized["Item_ID"].isna().any():
        raise ValidationError("CSV contains invalid Item_ID values.")
    normalized["Item_ID"] = normalized["Item_ID"].astype(int)
    normalized["Lead_Time"] = normalized["Lead_Time"].astype(int)

    summary = DatasetSummary(
        row_count=int(len(validated_rows)),
        item_count=int(len(validated_rows)),
        date_range=_summarize_date_range(validated_rows),
    )
    return validated_rows, summary


def validate_manual_items(items: list[dict]) -> tuple[pd.DataFrame, DatasetSummary]:
    if not items:
        raise ValidationError("No items provided.")

    today = datetime.now().strftime("%Y-%m-%d")
    rows = []
    for idx, item in enumerate(items, start=1):
        daily_usage = (
            item["usage_value"]
            if item["usage_period"] == "daily"
            else item["usage_value"] / 7
        )
        if daily_usage <= 0:
            raise ValidationError(f"Invalid usage value for item {item['item_name']}.")

        row = {
            "Date": today,
            "Item_ID": idx,
            "Item_Name": item["item_name"],
            "Category": item.get("category") or "",
            "Subcategory": "",
            "Unit": item["unit"],
            "Current_Stock": item["current_stock"],
            "Reorder_Level": 0,  # Assume 0 for manual
            "Daily_Usage": daily_usage,
            "Lead_Time": item["lead_time_days"],
            "Price_per_Unit": item["price_per_unit"],
            "Supplier_Name": "",
            "Seasonal_Factor": item["seasonal_factor"],
            "Waste_Percentage": 0,  # Assume 0 for manual
        }
        rows.append(row)

    dataframe = pd.DataFrame(rows)
    dataframe["Date"] = pd.to_datetime(dataframe["Date"])

    summary = DatasetSummary(
        row_count=len(dataframe),
        item_count=len(dataframe),
        date_range=DateRangeSummary(start=today, end=today),
    )
    return dataframe, summary
