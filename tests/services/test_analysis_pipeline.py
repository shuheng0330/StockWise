import math

from stockwise_api.services.manual_input import normalize_manual_items
from stockwise_api.services.recommendations import build_ranked_analysis
from stockwise_api.services.validation import validate_inventory_csv
from stockwise_api.services.simulation import simulate_item_quantity


def _normalized_items():
    items = [
        {
            "item_name": "Paneer",
            "current_stock": 12.0,
            "unit": "kg",
            "usage_value": 14.0,
            "usage_period": "weekly",
            "lead_time_days": 3,
            "price_per_unit": 450.0,
            "seasonal_factor": 1.0,
            "category": "Dairy",
            "supplier_name": "Supplier A",
            "perishability_level": "high",
        },
        {
            "item_name": "Eggs",
            "current_stock": 5.0,
            "unit": "pieces",
            "usage_value": 7.0,
            "usage_period": "daily",
            "lead_time_days": 2,
            "price_per_unit": 6.0,
            "perishability_level": "medium",
            "seasonal_factor": 1.2,
        },
        {
            "item_name": "Tomato",
            "current_stock": 16.0,
            "unit": "kg",
            "usage_value": 2.0,
            "usage_period": "daily",
            "lead_time_days": 2,
            "price_per_unit": 40.0,
            "seasonal_factor": 1.0,
            "perishability_level": "low",
        },
    ]
    return normalize_manual_items(items)


def test_normalized_owner_items_include_expected_internal_fields():
    items = _normalized_items()
    paneer = next(item for item in items if item["item_name"] == "Paneer")

    assert paneer["item_id"] == 1
    assert paneer["daily_usage"] == 2.0
    assert paneer["reorder_level"] == 6.0
    assert paneer["waste_percentage"] == 4.5
    assert math.isclose(paneer["days_of_cover"], 6.0, abs_tol=0.001)


def test_build_ranked_analysis_scores_and_labels_representative_manual_items():
    ranked = build_ranked_analysis(_normalized_items())

    paneer = next(item for item in ranked if item["item_name"] == "Paneer")
    eggs = next(item for item in ranked if item["item_name"] == "Eggs")
    tomato = next(item for item in ranked if item["item_name"] == "Tomato")

    assert paneer["recommended_action"] == "BUY_LESS"
    assert paneer["waste_risk_score"] >= 70

    assert eggs["recommended_action"] == "RESTOCK_NOW"
    assert eggs["reorder_urgency_score"] > tomato["reorder_urgency_score"]

    assert tomato["recommended_action"] == "DELAY_PURCHASE"


def test_equivalent_csv_and_manual_inputs_produce_same_normalized_values_and_scores():
    raw = (
        "Date,Item_ID,Item_Name,Category,Subcategory,Unit,Current_Stock,Reorder_Level,Daily_Usage,Lead_Time,Price_per_Unit,Supplier_Name,Seasonal_Factor,Waste_Percentage\n"
        "2025-06-10,1,Paneer,Dairy,Cheese,kg,12,8,2,3,450,Supplier A,1.1,4.0\n"
    ).encode()
    csv_rows, _ = validate_inventory_csv(raw)
    csv_ranked = build_ranked_analysis(normalize_manual_items(csv_rows))

    manual_ranked = build_ranked_analysis(
        normalize_manual_items(
            [
                {
                    "date": "2025-06-10",
                    "item_id": 1,
                    "item_name": "Paneer",
                    "current_stock": 12.0,
                    "unit": "kg",
                    "usage_value": 2.0,
                    "usage_period": "daily",
                    "lead_time_days": 3,
                    "price_per_unit": 450.0,
                    "category": "Dairy",
                    "subcategory": "Cheese",
                    "supplier_name": "Supplier A",
                    "seasonal_factor": 1.1,
                    "manual_reorder_level": 8.0,
                    "recent_waste_percentage": 4.0,
                }
            ],
            preserve_item_ids=True,
        )
    )

    csv_item = csv_ranked[0]
    manual_item = manual_ranked[0]

    for field in [
        "item_name",
        "category",
        "subcategory",
        "daily_usage",
        "reorder_level",
        "waste_percentage",
        "lead_time_demand",
        "reorder_urgency_score",
        "waste_risk_score",
        "recommended_action",
    ]:
        assert csv_item[field] == manual_item[field]


def test_simulation_recomputes_metrics_and_keeps_action_payload():
    ranked = build_ranked_analysis(_normalized_items())
    paneer = next(item for item in ranked if item["item_name"] == "Paneer")

    simulated = simulate_item_quantity(paneer, simulated_order_qty=3.0)

    assert simulated["item_id"] == paneer["item_id"]
    assert simulated["simulated_order_qty"] == 3.0
    assert math.isclose(simulated["simulated_cash_outlay"], 1350.0, abs_tol=0.001)
    assert math.isclose(simulated["simulated_coverage_days"], 7.5, abs_tol=0.001)
    assert simulated["simulated_risk_change"] in {
        "lower_shortage_risk",
        "lower_waste_risk",
        "higher_waste_risk",
        "minimal_change",
    }
    assert simulated["recommended_action"] in {
        "RESTOCK_NOW",
        "BUY_LESS",
        "DELAY_PURCHASE",
        "MONITOR_CLOSELY",
    }


def test_simulation_derives_score_context_when_restored_snapshot_omits_internal_context():
    ranked = build_ranked_analysis(_normalized_items())
    paneer = next(item for item in ranked if item["item_name"] == "Paneer")
    restored_item = {key: value for key, value in paneer.items() if key != "_score_context"}

    simulated = simulate_item_quantity(restored_item, simulated_order_qty=3.0)

    assert simulated["item_id"] == paneer["item_id"]
    assert simulated["simulated_order_qty"] == 3.0
    assert simulated["recommended_action"] in {
        "RESTOCK_NOW",
        "BUY_LESS",
        "DELAY_PURCHASE",
        "MONITOR_CLOSELY",
    }


def test_smaller_simulated_order_reduces_cash_exposure_for_risky_item():
    ranked = build_ranked_analysis(_normalized_items())
    paneer = next(item for item in ranked if item["item_name"] == "Paneer")

    small = simulate_item_quantity(paneer, simulated_order_qty=1.0)
    large = simulate_item_quantity(paneer, simulated_order_qty=5.0)

    assert small["simulated_cash_outlay"] < large["simulated_cash_outlay"]
    assert small["simulated_estimated_waste_cost"] < large["simulated_estimated_waste_cost"]
