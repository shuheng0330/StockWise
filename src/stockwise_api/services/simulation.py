from stockwise_api.services.recommendations import _classify_action, _compute_scores


def _risk_change(current_item: dict, simulated_item: dict) -> str:
    current_urgency = current_item["reorder_urgency_score"]
    current_waste = current_item["waste_risk_score"]
    urgency_delta = simulated_item["reorder_urgency_score"] - current_urgency
    waste_delta = simulated_item["waste_risk_score"] - current_waste

    if waste_delta >= 5:
        return "higher_waste_risk"
    if urgency_delta <= -5 and waste_delta <= 2:
        return "lower_shortage_risk"
    if waste_delta <= -5:
        return "lower_waste_risk"
    return "minimal_change"


def simulate_item_quantity(item: dict, simulated_order_qty: float) -> dict:
    if simulated_order_qty < 0:
        raise ValueError("simulated_order_qty cannot be negative.")

    simulated_stock = item["current_stock"] + simulated_order_qty
    simulated_coverage_days = simulated_stock / item["daily_usage"]
    simulated_inventory_value = simulated_stock * item["price_per_unit"]
    simulated_estimated_waste_cost = simulated_inventory_value * (item["waste_percentage"] / 100.0)
    simulated_stock_gap_to_lead_demand = simulated_stock - item["lead_time_demand"]

    simulated_item = {
        **item,
        "current_stock": simulated_stock,
        "days_of_cover": simulated_coverage_days,
        "inventory_value": simulated_inventory_value,
        "estimated_waste_cost": simulated_estimated_waste_cost,
        "stock_gap_to_lead_demand": simulated_stock_gap_to_lead_demand,
    }
    score_context = item["_score_context"]
    reorder_urgency_score, waste_risk_score = _compute_scores(simulated_item, score_context)
    recommended_action = _classify_action(simulated_item, reorder_urgency_score, waste_risk_score)

    payload = {
        "item_id": item["item_id"],
        "simulated_order_qty": simulated_order_qty,
        "simulated_cash_outlay": round(simulated_order_qty * item["price_per_unit"], 2),
        "simulated_coverage_days": simulated_coverage_days,
        "simulated_inventory_value": simulated_inventory_value,
        "simulated_estimated_waste_cost": simulated_estimated_waste_cost,
        "reorder_urgency_score": reorder_urgency_score,
        "waste_risk_score": waste_risk_score,
        "recommended_action": recommended_action,
    }
    payload["simulated_risk_change"] = _risk_change(item, payload)
    return payload
