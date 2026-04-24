import pytest

from stockwise_api.services.parsing import (
    ChatValidationError,
    ExplanationValidationError,
    build_fallback_chat_response,
    build_fallback_explanation,
    parse_chat_response,
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


def _chat_context():
    return {
        "message": "What should I buy today?",
        "scope": "analysis",
        "allowed_item_ids": {1},
        "analysis": {
            "kpi_summary": {
                "restock_now_count": 1,
                "buy_less_count": 1,
            }
        },
        "related_items": [
            {
                "item_id": 1,
                "item_name": "Paneer",
                "recommended_action": "BUY_LESS",
                "reason": "Waste risk is high.",
            }
        ],
    }


def test_parse_chat_response_accepts_valid_json():
    payload = """
    {
      "scope": "analysis",
      "answer": "Buy eggs today and hold off on paneer.",
      "supporting_points": [
        "Eggs have the highest urgency score.",
        "Paneer has elevated waste risk."
      ],
      "related_items": [
        {
          "item_id": 1,
          "item_name": "Paneer",
          "recommended_action": "BUY_LESS",
          "reason": "Waste risk is high."
        }
      ],
      "suggested_follow_ups": [
        "Which items can I delay?",
        "Why is dairy risky this week?"
      ],
      "warning_flag": "Watch dairy spoilage closely."
    }
    """

    parsed = parse_chat_response(payload, _chat_context())
    assert parsed["scope"] == "analysis"
    assert parsed["related_items"][0]["item_name"] == "Paneer"


def test_parse_chat_response_resolves_related_item_ids_from_context():
    payload = """
    {
      "scope": "analysis",
      "answer": "Delay paneer and restock eggs first.",
      "supporting_points": [
        "Paneer still has cover remaining.",
        "Urgent items should be handled first."
      ],
      "related_items": [1],
      "suggested_follow_ups": [
        "Which items can I delay?",
        "What should I buy today?"
      ],
      "warning_flag": null
    }
    """

    parsed = parse_chat_response(payload, _chat_context())
    assert parsed["related_items"] == _chat_context()["related_items"]


def test_parse_chat_response_normalizes_live_model_action_aliases_and_false_warning():
    payload = """
    {
      "scope": "analysis",
      "answer": "Delay paneer for now and reorder eggs first.",
      "supporting_points": [
        "Paneer still has enough cover.",
        "Eggs are close to stocking out."
      ],
      "related_items": [
        {
          "item_id": 1,
          "item_name": "Paneer",
          "recommended_action": "DELAY_REORDER",
          "reason": "Current cover is still acceptable."
        }
      ],
      "suggested_follow_ups": [
        "Which items can I delay?",
        "What should I buy today?"
      ],
      "warning_flag": false
    }
    """

    parsed = parse_chat_response(payload, _chat_context())
    assert parsed["related_items"][0]["recommended_action"] == "DELAY_PURCHASE"
    assert parsed["warning_flag"] is None


def test_parse_chat_response_normalizes_true_warning_flag_to_string():
    payload = """
    {
      "scope": "analysis",
      "answer": "Delay paneer for now and reorder eggs first.",
      "supporting_points": [
        "Paneer still has enough cover.",
        "Eggs are close to stocking out."
      ],
      "related_items": [
        {
          "item_id": 1,
          "item_name": "Paneer",
          "recommended_action": "BUY_LESS",
          "reason": "Current cover is still acceptable."
        }
      ],
      "suggested_follow_ups": [
        "Which items can I delay?",
        "What should I buy today?"
      ],
      "warning_flag": true
    }
    """

    parsed = parse_chat_response(payload, _chat_context())
    assert isinstance(parsed["warning_flag"], str)
    assert parsed["warning_flag"]


def test_parse_chat_response_normalizes_delay_restock_alias():
    payload = """
    {
      "scope": "analysis",
      "answer": "Delay paneer for now.",
      "supporting_points": [
        "Paneer still has enough cover."
      ],
      "related_items": [
        {
          "item_id": 1,
          "item_name": "Paneer",
          "recommended_action": "DELAY_RESTOCK",
          "reason": "Current cover is still acceptable."
        }
      ],
      "suggested_follow_ups": [
        "Which items can I delay?"
      ],
      "warning_flag": "none"
    }
    """

    parsed = parse_chat_response(payload, _chat_context())
    assert parsed["related_items"][0]["recommended_action"] == "DELAY_PURCHASE"


def test_parse_chat_response_rejects_bad_scope():
    payload = """
    {
      "scope": "global",
      "answer": "bad",
      "supporting_points": ["bad"],
      "related_items": [],
      "suggested_follow_ups": ["bad"],
      "warning_flag": null
    }
    """

    with pytest.raises(ChatValidationError, match="scope"):
        parse_chat_response(payload, _chat_context())


def test_parse_chat_response_rejects_unsupported_claims():
    payload = """
    {
      "scope": "analysis",
      "answer": "This will improve profit immediately.",
      "supporting_points": ["Revenue will go up."],
      "related_items": [],
      "suggested_follow_ups": ["What should I buy today?"],
      "warning_flag": null
    }
    """

    with pytest.raises(ChatValidationError, match="unsupported"):
        parse_chat_response(payload, _chat_context())


def test_build_fallback_chat_response_returns_safe_payload():
    fallback = build_fallback_chat_response(_chat_context())

    assert fallback["source"] == "fallback"
    assert fallback["scope"] == "analysis"
    assert fallback["answer"]
    assert fallback["related_items"][0]["item_name"] == "Paneer"
