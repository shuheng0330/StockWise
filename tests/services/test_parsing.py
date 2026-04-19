import pytest

from stockwise_api.services.parsing import (
    ExplanationValidationError,
    build_fallback_explanation,
    parse_explanation_response,
)


def _context():
    return {
        "item_name": "Paneer",
        "recommended_action": "BUY_LESS",
        "days_of_cover": 5.5982,
        "lead_time_demand": 11.648,
        "inventory_value": 5643.0,
        "avg_usage_7d": 2.94,
        "trend_direction": "down",
        "waste_risk_score": 87,
        "reorder_urgency_score": 22,
    }


def test_parse_explanation_response_accepts_valid_json():
    payload = """
    {
      "item_name": "Paneer",
      "recommended_action": "BUY_LESS",
      "priority_level": "MEDIUM",
      "short_reason": "Paneer has high waste-cost exposure.",
      "decision_explanation": "Paneer does not need a large top-up right now because waste risk is high.",
      "tradeoff_summary": "Buying less lowers waste and cash risk while keeping the item under review.",
      "suggested_next_step": "Place only a small top-up order if needed.",
      "confidence_note": "Confidence is moderate based on recent usage.",
      "warning_flag": "High-value item."
    }
    """

    parsed = parse_explanation_response(payload, _context())
    assert parsed["item_name"] == "Paneer"
    assert parsed["recommended_action"] == "BUY_LESS"


def test_parse_explanation_response_rejects_bad_enum():
    payload = """
    {
      "item_name": "Paneer",
      "recommended_action": "PANIC",
      "priority_level": "MEDIUM",
      "short_reason": "bad",
      "decision_explanation": "bad",
      "tradeoff_summary": "bad",
      "suggested_next_step": "bad",
      "confidence_note": "bad",
      "warning_flag": "bad"
    }
    """

    with pytest.raises(ExplanationValidationError, match="recommended_action"):
        parse_explanation_response(payload, _context())


def test_parse_explanation_response_rejects_item_mismatch():
    payload = """
    {
      "item_name": "Tomato",
      "recommended_action": "BUY_LESS",
      "priority_level": "MEDIUM",
      "short_reason": "bad",
      "decision_explanation": "bad",
      "tradeoff_summary": "bad",
      "suggested_next_step": "bad",
      "confidence_note": "bad",
      "warning_flag": "bad"
    }
    """

    with pytest.raises(ExplanationValidationError, match="item_name"):
        parse_explanation_response(payload, _context())


def test_parse_explanation_response_rejects_unsupported_revenue_claims():
    payload = """
    {
      "item_name": "Paneer",
      "recommended_action": "BUY_LESS",
      "priority_level": "MEDIUM",
      "short_reason": "This will raise revenue immediately.",
      "decision_explanation": "This decision increases profit next week.",
      "tradeoff_summary": "Revenue goes up and profit improves.",
      "suggested_next_step": "bad",
      "confidence_note": "bad",
      "warning_flag": "bad"
    }
    """

    with pytest.raises(ExplanationValidationError, match="unsupported"):
        parse_explanation_response(payload, _context())


def test_build_fallback_explanation_returns_safe_payload():
    fallback = build_fallback_explanation(_context())

    assert fallback["source"] == "fallback"
    assert fallback["item_name"] == "Paneer"
    assert fallback["recommended_action"] == "BUY_LESS"
    assert fallback["decision_explanation"]
