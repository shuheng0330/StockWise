import json
import pytest

from stockwise_api.services.manual_input import normalize_manual_items
from stockwise_api.services.recommendations import build_ranked_analysis
from stockwise_api.services.simulation import simulate_item_quantity
from stockwise_api.services.parsing import parse_explanation_response, ExplanationValidationError


def _two_items():
    return normalize_manual_items([
        {
            "item_name": "Eggs",
            "current_stock": 5.0,
            "unit": "pieces",
            "usage_value": 7.0,
            "usage_period": "daily",
            "lead_time_days": 2,
            "price_per_unit": 6.0,
            "seasonal_factor": 1.2,
            "perishability_level": "medium",
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
    ])


# UT-01: build_ranked_analysis()


def test_ut01_build_ranked_analysis_produces_correct_scores_and_ranked_actions():
    ranked = build_ranked_analysis(_two_items())

    assert len(ranked) == 2
    for item in ranked:
        assert "reorder_urgency_score" in item
        assert "waste_risk_score" in item
        assert item["recommended_action"] in {"RESTOCK_NOW", "BUY_LESS", "DELAY_PURCHASE", "MONITOR_CLOSELY"}

    eggs = next(i for i in ranked if i["item_name"] == "Eggs")
    tomato = next(i for i in ranked if i["item_name"] == "Tomato")

    assert eggs["recommended_action"] == "RESTOCK_NOW"
    assert eggs["reorder_urgency_score"] > tomato["reorder_urgency_score"]
    assert ranked[0]["item_name"] == "Eggs"


# UT-02: simulate_item_quantity()


def test_ut02_simulate_item_quantity_computes_accurate_projections():
    ranked = build_ranked_analysis(_two_items())
    eggs = next(i for i in ranked if i["item_name"] == "Eggs")

    result = simulate_item_quantity(eggs, simulated_order_qty=10.0)

    assert result["item_id"] == eggs["item_id"]
    assert result["simulated_order_qty"] == 10.0
    assert result["simulated_cash_outlay"] == round(10.0 * eggs["price_per_unit"], 2)
    assert result["simulated_coverage_days"] > eggs["days_of_cover"]
    assert result["recommended_action"] in {"RESTOCK_NOW", "BUY_LESS", "DELAY_PURCHASE", "MONITOR_CLOSELY"}
    assert result["simulated_risk_change"] in {
        "higher_waste_risk", "lower_shortage_risk", "lower_waste_risk", "minimal_change"
    }


# UT-03: parse_explanation_response()


_VALID_PAYLOAD = {
    "item_name": "Eggs",
    "recommended_action": "RESTOCK_NOW",
    "priority_level": "HIGH",
    "short_reason": "Stock is critically low.",
    "decision_explanation": "Reorder immediately to avoid stockout.",
    "tradeoff_summary": "Risk of stockout outweighs holding cost.",
    "suggested_next_step": "Order 10 units from supplier.",
    "confidence_note": "High confidence based on usage trend.",
    "warning_flag": False,
}


def test_ut03_parse_explanation_response_validates_schema_and_triggers_fallback():
    context = {"item_name": "Eggs"}

    # Valid JSON accepted and warning_flag normalised
    result = parse_explanation_response(json.dumps(_VALID_PAYLOAD), context)
    assert result["recommended_action"] == "RESTOCK_NOW"
    assert result["warning_flag"] == ""

    # Invalid JSON triggers ExplanationValidationError (fallback path)
    with pytest.raises(ExplanationValidationError, match="not valid JSON"):
        parse_explanation_response("{not-json}", context)

    # Invalid enum triggers ExplanationValidationError
    bad_action = {**_VALID_PAYLOAD, "recommended_action": "SELL_NOW"}
    with pytest.raises(ExplanationValidationError, match="invalid recommended_action"):
        parse_explanation_response(json.dumps(bad_action), context)
