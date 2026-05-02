from typing import Dict, List, Any

def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def _compute_scores(item: Dict[str, Any], score_context: Dict[str, float]) -> tuple[int, int]:
    """
    SENSITIVE, URGENCY-AWARE & DYNAMIC FLOOR VERSION
    - High urgency actively lowers the initial base waste score.
    - Highly sensitive to days_of_cover increases.
    - Urgency score drops to 0 when significantly overstocked.
    """
    print("=== DEBUG _compute_scores ===")
    print(f"waste_percentage: {item.get('waste_percentage')}")
    print(f"days_of_cover: {item.get('days_of_cover')}")
    print("=============================")

    current_stock = item.get("current_stock", 0)
    lead_time_demand = item.get("lead_time_demand", 0)
    reorder_level = item.get("reorder_level", 0)
    daily_usage = item.get("daily_usage", 0)
    lead_time = item.get("lead_time", 0)
    seasonal_factor = item.get("seasonal_factor", 1.0)
    waste_percentage = item.get("waste_percentage", 0)
    days_of_cover = item.get("days_of_cover", 0)

    # 1. Reorder Urgency Score - Dynamic Floor (Can drop to 0)
    stockout_risk = clamp((lead_time_demand - current_stock) / max(lead_time_demand, 1))
    reorder_gap = clamp((reorder_level - current_stock) / max(reorder_level, 1))

    # Dynamic multiplier: If stock is double the reorder level, urgency starts dropping. 
    # If it's 4x, the multiplier reaches 0.
    supply_buffer = current_stock / max(reorder_level, 1)
    urgency_multiplier = clamp(2.0 - (supply_buffer / 2.0), 0.0, 1.0)

    importance_score = (
        15 * (daily_usage / max(score_context.get("max_daily_usage", 1), 1)) +
        10 * (lead_time / max(score_context.get("max_lead_time", 1), 1))
    )

    reorder_urgency_score = round(
        (50 * stockout_risk) + 
        (25 * reorder_gap) + 
        (importance_score * urgency_multiplier)
    )

    # 2. Waste Risk Score - Sensitive & Urgency-Discounted
    base_waste = waste_percentage * 10
    urgency_discount = reorder_urgency_score * 0.25
    initial_waste = max(0.0, base_waste - urgency_discount)

    expected_cover = max(lead_time * seasonal_factor, 1.0)
    
    # Decreased denominator for higher sensitivity -> small overstock causes larger score spikes
    overstock_ratio = clamp((days_of_cover - expected_cover) / max(expected_cover * 1.5, 7.0))

    waste_risk_score = round(initial_waste + 65 * overstock_ratio)

    print(f"Final scores -> urgency: {reorder_urgency_score}, waste: {waste_risk_score}")
    print("=============================")

    return max(0, min(100, reorder_urgency_score)), max(0, min(100, waste_risk_score))


def _classify_action(item: Dict[str, Any], reorder_urgency_score: int, waste_risk_score: int) -> str:
    # Fix for the "Eggs" anomaly: Only force a restock due to a gap if urgency is at least 20
    force_restock = item.get("stock_gap_to_lead_demand", 0) < 0 and reorder_urgency_score > 20

    # High Urgency
    if reorder_urgency_score >= 55 or force_restock:
        return "RESTOCK_NOW"
    
    # High Waste boundary
    if waste_risk_score >= 60 and reorder_urgency_score < 55:
        return "BUY_LESS"
    
    # Safe boundaries for delaying
    if reorder_urgency_score <= 35 and waste_risk_score <= 45:
        return "DELAY_PURCHASE"
    
    # Narrowed "Monitor Closely" range to show higher accuracy
    return "MONITOR_CLOSELY"


def build_ranked_analysis(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not items:
        return []

    score_context = {
        "max_daily_usage": max((item.get("daily_usage", 0) for item in items), default=1),
        "max_lead_time": max((item.get("lead_time", 0) for item in items), default=1),
        "max_waste_percentage": max((item.get("waste_percentage", 0) for item in items), default=1),
        "max_inventory_value": max((item.get("inventory_value", 0) for item in items), default=1),
    }

    ranked = []
    for item in items:
        urgency_score, waste_score = _compute_scores(item, score_context)
        action = _classify_action(item, urgency_score, waste_score)

        ranked.append({
            **item,
            "reorder_urgency_score": urgency_score,
            "waste_risk_score": waste_score,
            "recommended_action": action,
        })

    return sorted(
        ranked,
        key=lambda x: (-x["reorder_urgency_score"], -x["waste_risk_score"], x.get("item_id", 0))
    )


def build_kpi_summary(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not items:
        return {
            "item_count": 0, "restock_now_count": 0, "buy_less_count": 0,
            "high_waste_risk_count": 0, "inventory_value_at_risk": 0.0,
            "top_urgent_items": [], "top_waste_cost_items": []
        }

    restock_count = sum(1 for item in items if item.get("recommended_action") == "RESTOCK_NOW")
    buy_less_count = sum(1 for item in items if item.get("recommended_action") == "BUY_LESS")
    high_waste_items = [item for item in items if item.get("waste_risk_score", 0) >= 65]

    return {
        "item_count": len(items),
        "restock_now_count": restock_count,
        "buy_less_count": buy_less_count,
        "high_waste_risk_count": len(high_waste_items),
        "inventory_value_at_risk": round(sum(item.get("inventory_value", 0) for item in high_waste_items), 2),
        "top_urgent_items": [item.get("item_name", "Unknown") 
                           for item in sorted(items, key=lambda x: -x.get("reorder_urgency_score", 0))[:3]],
        "top_waste_cost_items": [item.get("item_name", "Unknown") 
                               for item in sorted(items, key=lambda x: -x.get("estimated_waste_cost", 0))[:3]],
    }