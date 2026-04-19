def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _compute_scores(item: dict, score_context: dict) -> tuple[int, int]:
    current_stock = item["current_stock"]
    lead_time_demand = item["lead_time_demand"]
    reorder_level = item["reorder_level"]
    daily_usage = item["daily_usage"]
    lead_time = item["lead_time"]
    seasonal_factor = item["seasonal_factor"]
    waste_percentage = item["waste_percentage"]
    inventory_value = item["inventory_value"]
    days_of_cover = item["days_of_cover"]

    lead_time_gap_ratio = clamp((lead_time_demand - current_stock) / max(lead_time_demand, 1))
    reorder_gap_ratio = clamp((reorder_level - current_stock) / max(reorder_level, 1))
    usage_pressure = daily_usage / max(score_context["max_daily_usage"], 1)
    lead_time_pressure = lead_time / max(score_context["max_lead_time"], 1)
    seasonal_pressure = clamp((seasonal_factor - 1.0) / 0.5)

    reorder_urgency_score = round(
        40 * lead_time_gap_ratio
        + 20 * reorder_gap_ratio
        + 20 * usage_pressure
        + 10 * lead_time_pressure
        + 10 * seasonal_pressure
    )

    waste_pressure = waste_percentage / max(score_context["max_waste_percentage"], 1)
    value_pressure = inventory_value / max(score_context["max_inventory_value"], 1)
    over_coverage_ratio = clamp((days_of_cover - lead_time) / max(lead_time, 1))

    waste_risk_score = round(
        45 * waste_pressure
        + 35 * value_pressure
        + 20 * over_coverage_ratio
    )
    return reorder_urgency_score, waste_risk_score


def _classify_action(item: dict, reorder_urgency_score: int, waste_risk_score: int) -> str:
    if item["stock_gap_to_lead_demand"] < 0 or reorder_urgency_score >= 70:
        return "RESTOCK_NOW"
    if waste_risk_score >= 70 and reorder_urgency_score < 70:
        return "BUY_LESS"
    if (
        reorder_urgency_score < 40
        and waste_risk_score < 60
        and item["days_of_cover"] > item["lead_time"] * item["seasonal_factor"]
    ):
        return "DELAY_PURCHASE"
    return "MONITOR_CLOSELY"


def build_ranked_analysis(items: list[dict]) -> list[dict]:
    score_context = {
        "max_daily_usage": max(item["daily_usage"] for item in items),
        "max_lead_time": max(item["lead_time"] for item in items),
        "max_waste_percentage": max(item["waste_percentage"] for item in items),
        "max_inventory_value": max(item["inventory_value"] for item in items),
    }

    ranked = []
    for item in items:
        reorder_urgency_score, waste_risk_score = _compute_scores(item, score_context)
        recommended_action = _classify_action(item, reorder_urgency_score, waste_risk_score)
        ranked.append(
            {
                **item,
                "reorder_urgency_score": reorder_urgency_score,
                "waste_risk_score": waste_risk_score,
                "recommended_action": recommended_action,
                "_score_context": score_context,
            }
        )

    return sorted(
        ranked,
        key=lambda item: (
            -item["reorder_urgency_score"],
            -item["waste_risk_score"],
            item["item_id"],
        ),
    )


def build_kpi_summary(items: list[dict]) -> dict:
    high_waste_items = [item for item in items if item["waste_risk_score"] >= 70]
    return {
        "item_count": len(items),
        "restock_now_count": sum(item["recommended_action"] == "RESTOCK_NOW" for item in items),
        "buy_less_count": sum(item["recommended_action"] == "BUY_LESS" for item in items),
        "high_waste_risk_count": len(high_waste_items),
        "inventory_value_at_risk": round(sum(item["inventory_value"] for item in high_waste_items), 2),
        "top_urgent_items": [item["item_name"] for item in sorted(items, key=lambda x: -x["reorder_urgency_score"])[:3]],
        "top_waste_cost_items": [
            item["item_name"] for item in sorted(items, key=lambda x: -x["estimated_waste_cost"])[:3]
        ],
    }
