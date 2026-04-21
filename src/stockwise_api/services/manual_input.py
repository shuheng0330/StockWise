from collections import OrderedDict
from datetime import date, datetime

from stockwise_api.services.validation import validate_manual_item_payload


PERISHABILITY_TO_WASTE = {
    "low": 1.5,
    "medium": 3.0,
    "high": 4.5,
}


class ManualInputValidationError(ValueError):
    pass


def _infer_perishability_from_waste(waste_percentage: float | None) -> str:
    if waste_percentage is None:
        return "medium"
    if waste_percentage >= 4:
        return "high"
    if waste_percentage <= 2:
        return "low"
    return "medium"


def _trend_direction(first_value: float, last_value: float) -> str:
    if last_value > first_value * 1.05:
        return "up"
    if last_value < first_value * 0.95:
        return "down"
    return "stable"


def _date_sort_key(value: str) -> date:
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except ValueError:
        return date.min


def _history_identity(item: dict) -> str:
    source_item_id = item.get("item_id")
    if source_item_id is not None:
        return f"id:{int(source_item_id)}"

    identity_parts = [
        str(item["item_name"]).strip().lower(),
        str(item["unit"]).strip().lower(),
        str(item.get("category") or "").strip().lower(),
        str(item.get("subcategory") or "").strip().lower(),
    ]
    return "item:" + "|".join(identity_parts)


def normalize_manual_items(items: list[dict], *, preserve_item_ids: bool = False) -> list[dict]:
    if not items:
        raise ManualInputValidationError("Manual entry requires at least one item.")

    normalized: list[dict] = []
    today = date.today().isoformat()
    for index, raw_item in enumerate(items, start=1):
        try:
            item = validate_manual_item_payload(dict(raw_item))
        except Exception as exc:
            raise ManualInputValidationError(str(exc)) from exc

        usage_value = float(item["usage_value"])
        usage_period = item["usage_period"]
        daily_usage = usage_value if usage_period == "daily" else usage_value / 7.0
        current_stock = float(item["current_stock"])
        lead_time_days = int(item["lead_time_days"])
        seasonal_factor = float(item["seasonal_factor"])
        waste_percentage = (
            float(item["recent_waste_percentage"])
            if item.get("recent_waste_percentage") is not None
            else PERISHABILITY_TO_WASTE.get(item.get("perishability_level") or "medium", 3.0)
        )
        reorder_level = (
            float(item["manual_reorder_level"])
            if item.get("manual_reorder_level") is not None
            else round(max(daily_usage * lead_time_days, daily_usage), 2)
        )
        price_per_unit = float(item["price_per_unit"])
        inventory_value = current_stock * price_per_unit
        days_of_cover = current_stock / daily_usage
        lead_time_demand = daily_usage * lead_time_days * seasonal_factor
        stock_gap_to_lead_demand = current_stock - lead_time_demand
        estimated_waste_cost = inventory_value * (waste_percentage / 100.0)

        normalized.append(
            {
                "item_id": int(item["item_id"]) if preserve_item_ids and item.get("item_id") is not None else index,
                "date": item.get("date", today),
                "item_name": str(item["item_name"]).strip(),
                "category": str(item.get("category") or "Uncategorized").strip(),
                "subcategory": str(item.get("subcategory") or item.get("category") or "General").strip(),
                "unit": str(item["unit"]).strip(),
                "supplier_name": str(item.get("supplier_name") or "Unknown").strip(),
                "current_stock": current_stock,
                "reorder_level": reorder_level,
                "daily_usage": daily_usage,
                "lead_time": lead_time_days,
                "price_per_unit": price_per_unit,
                "seasonal_factor": seasonal_factor,
                "waste_percentage": waste_percentage,
                "avg_usage_7d": round(daily_usage, 6),
                "trend_direction": "stable",
                "days_of_cover": days_of_cover,
                "inventory_value": inventory_value,
                "estimated_waste_cost": estimated_waste_cost,
                "lead_time_demand": lead_time_demand,
                "stock_gap_to_lead_demand": stock_gap_to_lead_demand,
                "usage_value": usage_value,
                "usage_period": usage_period,
                "lead_time_days": lead_time_days,
                "perishability_level": item.get("perishability_level") or _infer_perishability_from_waste(
                    item.get("recent_waste_percentage")
                ),
                "manual_reorder_level": item.get("manual_reorder_level"),
                "recent_waste_percentage": item.get("recent_waste_percentage"),
                "_history_identity": _history_identity(item),
                "_observation_count": 1,
                "_observation_index": index,
            }
        )
    return normalized


def normalize_item_history(items: list[dict], *, preserve_item_ids: bool = False) -> list[dict]:
    observations = normalize_manual_items(items, preserve_item_ids=preserve_item_ids)
    grouped_observations: OrderedDict[str, list[dict]] = OrderedDict()

    for observation in observations:
        grouped_observations.setdefault(observation["_history_identity"], []).append(observation)

    latest_items: list[dict] = []
    for history in grouped_observations.values():
        sorted_history = sorted(
            history,
            key=lambda item: (_date_sort_key(item["date"]), int(item.get("_observation_index", 0))),
        )
        latest_item = dict(sorted_history[-1])
        latest_item["item_id"] = int(sorted_history[0]["item_id"])
        latest_item["_observation_count"] = len(sorted_history)

        recent_history = sorted_history[-7:]
        latest_item["avg_usage_7d"] = round(
            sum(float(item["daily_usage"]) for item in recent_history) / len(recent_history),
            6,
        )
        latest_item["trend_direction"] = _trend_direction(
            float(recent_history[0]["daily_usage"]),
            float(recent_history[-1]["daily_usage"]),
        )
        latest_items.append(latest_item)

    return latest_items


def item_to_record_view(item: dict) -> dict:
    usage_value = item.get("usage_value")
    usage_period = item.get("usage_period")
    if usage_value is None or usage_period is None:
        usage_value = item["daily_usage"]
        usage_period = "daily"

    return {
        "item_id": int(item["item_id"]),
        "last_updated": item["date"],
        "item_name": item["item_name"],
        "current_stock": item["current_stock"],
        "unit": item["unit"],
        "usage_value": usage_value,
        "usage_period": usage_period,
        "daily_usage": item["daily_usage"],
        "lead_time_days": item.get("lead_time_days", item["lead_time"]),
        "price_per_unit": item.get("price_per_unit"),
        "category": item.get("category"),
        "subcategory": item.get("subcategory"),
        "supplier_name": item.get("supplier_name"),
        "perishability_level": item.get("perishability_level") or _infer_perishability_from_waste(
            item.get("recent_waste_percentage", item.get("waste_percentage"))
        ),
        "manual_reorder_level": item.get("manual_reorder_level"),
        "seasonal_factor": item.get("seasonal_factor"),
        "recent_waste_percentage": item.get("recent_waste_percentage"),
        "recommended_action": item["recommended_action"],
    }
