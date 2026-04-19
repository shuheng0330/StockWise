import pandas as pd


def _trend_direction(first_value: float, last_value: float) -> str:
    if last_value > first_value * 1.05:
        return "up"
    if last_value < first_value * 0.95:
        return "down"
    return "stable"


def build_item_metrics(dataframe: pd.DataFrame) -> list[dict]:
    sorted_df = dataframe.sort_values(["Item_ID", "Date"])
    latest_snapshot = sorted_df.groupby("Item_ID", as_index=False).tail(1).copy()
    result: list[dict] = []

    for _, latest in latest_snapshot.sort_values("Item_ID").iterrows():
        item_history = sorted_df[sorted_df["Item_ID"] == latest["Item_ID"]].sort_values("Date").tail(7)
        avg_usage_7d = float(item_history["Daily_Usage"].mean())
        trend_direction = _trend_direction(
            float(item_history.iloc[0]["Daily_Usage"]),
            float(item_history.iloc[-1]["Daily_Usage"]),
        )

        current_stock = float(latest["Current_Stock"])
        daily_usage = float(latest["Daily_Usage"])
        price_per_unit = float(latest["Price_per_Unit"])
        waste_percentage = float(latest["Waste_Percentage"])
        lead_time = int(latest["Lead_Time"])
        seasonal_factor = float(latest["Seasonal_Factor"])

        days_of_cover = current_stock / daily_usage
        inventory_value = current_stock * price_per_unit
        estimated_waste_cost = inventory_value * (waste_percentage / 100.0)
        lead_time_demand = daily_usage * lead_time * seasonal_factor
        stock_gap_to_lead_demand = current_stock - lead_time_demand

        result.append(
            {
                "item_id": int(latest["Item_ID"]),
                "date": latest["Date"].strftime("%Y-%m-%d"),
                "item_name": latest["Item_Name"],
                "category": latest["Category"],
                "subcategory": latest["Subcategory"],
                "unit": latest["Unit"],
                "supplier_name": latest["Supplier_Name"],
                "current_stock": current_stock,
                "reorder_level": float(latest["Reorder_Level"]),
                "daily_usage": daily_usage,
                "lead_time": lead_time,
                "price_per_unit": price_per_unit,
                "seasonal_factor": seasonal_factor,
                "waste_percentage": waste_percentage,
                "avg_usage_7d": round(avg_usage_7d, 6),
                "trend_direction": trend_direction,
                "days_of_cover": days_of_cover,
                "inventory_value": inventory_value,
                "estimated_waste_cost": estimated_waste_cost,
                "lead_time_demand": lead_time_demand,
                "stock_gap_to_lead_demand": stock_gap_to_lead_demand,
            }
        )

    return result
