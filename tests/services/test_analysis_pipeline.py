import math

from stockwise_api.services.metrics import build_item_metrics
from stockwise_api.services.recommendations import build_ranked_analysis
from stockwise_api.services.simulation import simulate_item_quantity
from stockwise_api.services.validation import validate_inventory_csv
from tests.fixtures import DATASET_PATH


def _load_ranked_items():
    with DATASET_PATH.open("rb") as f:
        normalized, _ = validate_inventory_csv(f.read())
    metrics = build_item_metrics(normalized)
    return build_ranked_analysis(metrics)


def test_build_item_metrics_picks_latest_snapshot_and_recent_context():
    with DATASET_PATH.open("rb") as f:
        normalized, _ = validate_inventory_csv(f.read())

    items = build_item_metrics(normalized)
    paneer = next(item for item in items if item["item_id"] == 1)

    assert paneer["date"] == "2025-09-17"
    assert math.isclose(paneer["avg_usage_7d"], 2.94, abs_tol=0.01)
    assert paneer["trend_direction"] == "down"
    assert math.isclose(paneer["days_of_cover"], 5.5982, abs_tol=0.001)
    assert math.isclose(paneer["estimated_waste_cost"], 267.4782, abs_tol=0.01)


def test_build_ranked_analysis_scores_and_labels_representative_items():
    ranked = _load_ranked_items()

    paneer = next(item for item in ranked if item["item_id"] == 1)
    eggs = next(item for item in ranked if item["item_id"] == 7)
    tomato = next(item for item in ranked if item["item_id"] == 2)
    mutton = next(item for item in ranked if item["item_id"] == 5)

    assert paneer["reorder_urgency_score"] == 22
    assert paneer["waste_risk_score"] == 87
    assert paneer["recommended_action"] == "BUY_LESS"

    assert eggs["recommended_action"] == "RESTOCK_NOW"
    assert eggs["trend_direction"] == "up"

    assert tomato["recommended_action"] == "DELAY_PURCHASE"
    assert mutton["recommended_action"] == "RESTOCK_NOW"


def test_simulation_recomputes_metrics_and_keeps_action_payload():
    ranked = _load_ranked_items()
    paneer = next(item for item in ranked if item["item_id"] == 1)

    simulated = simulate_item_quantity(paneer, simulated_order_qty=3.0)

    assert simulated["item_id"] == 1
    assert simulated["simulated_order_qty"] == 3.0
    assert math.isclose(simulated["simulated_cash_outlay"], 1350.0, abs_tol=0.001)
    assert math.isclose(simulated["simulated_coverage_days"], 6.9375, abs_tol=0.001)
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


def test_smaller_simulated_order_reduces_cash_exposure_for_risky_item():
    ranked = _load_ranked_items()
    paneer = next(item for item in ranked if item["item_id"] == 1)

    small = simulate_item_quantity(paneer, simulated_order_qty=1.0)
    large = simulate_item_quantity(paneer, simulated_order_qty=5.0)

    assert small["simulated_cash_outlay"] < large["simulated_cash_outlay"]
    assert small["simulated_estimated_waste_cost"] < large["simulated_estimated_waste_cost"]
