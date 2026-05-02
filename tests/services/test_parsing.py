import pytest

from stockwise_api.services.parsing import (
    ChatValidationError,
    DecisionBriefValidationError,
    ExplanationValidationError,
    TradeoffVerdictValidationError,
    build_fallback_decision_brief,
    build_fallback_chat_response,
    build_fallback_explanation,
    build_fallback_tradeoff_verdict,
    parse_decision_brief_response,
    parse_chat_response,
    parse_explanation_response,
    parse_tradeoff_verdict_response,
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


def _tradeoff_context():
    context = _context()
    context.update(
        {
            "simulated_order_qty": 3.0,
            "simulated_cash_outlay": 1350.0,
            "simulated_coverage_days": 7.1,
            "simulated_estimated_waste_cost": 11.5,
            "simulated_risk_change": "lower_shortage_risk",
            "simulated_recommended_action": "MONITOR_CLOSELY",
        }
    )
    return context


def test_parse_tradeoff_verdict_response_accepts_allowed_verdict():
    payload = """
    {
      "verdict": "Cash-heavy but safe",
      "reason": "This order lowers shortage pressure, but it commits cash and raises waste exposure.",
      "confidence_note": "Based on simulated cover, cash outlay, urgency, and waste risk."
    }
    """

    parsed = parse_tradeoff_verdict_response(payload, _tradeoff_context())

    assert parsed["verdict"] == "Cash-heavy but safe"
    assert parsed["reason"].startswith("This order lowers")


def test_parse_tradeoff_verdict_response_rejects_invalid_label():
    payload = """
    {
      "verdict": "Guaranteed profit",
      "reason": "bad",
      "confidence_note": "bad"
    }
    """

    with pytest.raises(TradeoffVerdictValidationError, match="verdict"):
        parse_tradeoff_verdict_response(payload, _tradeoff_context())


def test_parse_tradeoff_verdict_response_rejects_unsupported_revenue_claims():
    payload = """
    {
      "verdict": "Worth it",
      "reason": "This will increase revenue immediately.",
      "confidence_note": "Profit should improve."
    }
    """

    with pytest.raises(TradeoffVerdictValidationError, match="unsupported"):
        parse_tradeoff_verdict_response(payload, _tradeoff_context())


def test_build_fallback_tradeoff_verdict_returns_safe_payload():
    fallback = build_fallback_tradeoff_verdict(_tradeoff_context())

    assert fallback["source"] == "fallback"
    assert fallback["verdict"] in {
        "Worth it",
        "Too much stock",
        "Cash-heavy but safe",
        "Try smaller quantity",
        "Good emergency reorder",
    }
    assert fallback["reason"]
    assert fallback["safety_status"] == "fallback_used"


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


def _decision_brief_context():
    return {
        "allowed_item_ids": {1, 2, 3},
        "items_by_id": {
            1: {"item_name": "Paneer", "recommended_action": "BUY_LESS"},
            2: {"item_name": "Eggs", "recommended_action": "RESTOCK_NOW"},
            3: {"item_name": "Rice", "recommended_action": "DELAY_PURCHASE"},
        },
        "analysis": {
            "kpi_summary": {
                "restock_now_count": 1,
                "buy_less_count": 1,
                "inventory_value_at_risk": 120.0,
            }
        },
        "deterministic_impact": {
            "cash": "Delay low-risk purchases to preserve cash.",
            "waste": "Buy less for high waste-risk items.",
            "shortage": "Restock urgent items first.",
        },
    }


def test_parse_decision_brief_response_accepts_valid_grounded_json():
    payload = """
    {
      "summary": "Handle eggs first, reduce paneer purchases, and delay rice.",
      "buy_today": [
        {"item_id": 2, "item_name": "Eggs", "recommended_action": "RESTOCK_NOW", "reason": "Shortage risk is highest."}
      ],
      "buy_less": [
        {"item_id": 1, "item_name": "Paneer", "recommended_action": "BUY_LESS", "reason": "Waste risk is elevated."}
      ],
      "delay": [
        {"item_id": 3, "item_name": "Rice", "recommended_action": "DELAY_PURCHASE", "reason": "Coverage is healthy."}
      ],
      "estimated_impact": {
        "cash": "Delay low-risk purchases to preserve cash.",
        "waste": "Smaller paneer order lowers waste exposure.",
        "shortage": "Restocking eggs lowers shortage risk."
      },
      "top_tradeoffs": [
        "Restocking eggs uses cash but protects availability.",
        "Buying less paneer lowers waste but needs monitoring."
      ],
      "recommended_order": [
        "Restock eggs.",
        "Buy less paneer.",
        "Delay rice."
      ],
      "confidence_note": "Grounded in current StockWise metrics.",
      "warning_flag": "Review records before ordering."
    }
    """

    parsed = parse_decision_brief_response(payload, _decision_brief_context())

    assert parsed["buy_today"][0]["item_id"] == 2
    assert parsed["buy_less"][0]["recommended_action"] == "BUY_LESS"
    assert parsed["safety_status"] == "validated"


def test_parse_decision_brief_response_fills_empty_text_lists_from_context():
    payload = """
    {
      "summary": "Handle eggs first, reduce paneer purchases, and delay rice.",
      "buy_today": [
        {"item_id": 2, "item_name": "Eggs", "recommended_action": "RESTOCK_NOW", "reason": "Shortage risk is highest."}
      ],
      "buy_less": [
        {"item_id": 1, "item_name": "Paneer", "recommended_action": "BUY_LESS", "reason": "Waste risk is elevated."}
      ],
      "delay": [
        {"item_id": 3, "item_name": "Rice", "recommended_action": "DELAY_PURCHASE", "reason": "Coverage is healthy."}
      ],
      "estimated_impact": {
        "cash": "Delay low-risk purchases to preserve cash.",
        "waste": "Smaller paneer order lowers waste exposure.",
        "shortage": "Restocking eggs lowers shortage risk."
      },
      "top_tradeoffs": [],
      "recommended_order": [],
      "confidence_note": "Grounded in current StockWise metrics.",
      "warning_flag": "Review records before ordering."
    }
    """

    parsed = parse_decision_brief_response(payload, _decision_brief_context())

    assert parsed["top_tradeoffs"]
    assert parsed["recommended_order"]


def test_parse_decision_brief_response_fills_null_text_lists_from_context():
    payload = """
    {
      "summary": "Handle eggs first.",
      "buy_today": [
        {"item_id": 2, "item_name": "Eggs", "recommended_action": "RESTOCK_NOW", "reason": "Shortage risk is highest."}
      ],
      "buy_less": [],
      "delay": [],
      "estimated_impact": {
        "cash": "Delay low-risk purchases to preserve cash.",
        "waste": "Smaller paneer order lowers waste exposure.",
        "shortage": "Restocking eggs lowers shortage risk."
      },
      "top_tradeoffs": null,
      "recommended_order": "",
      "confidence_note": "Grounded in current StockWise metrics.",
      "warning_flag": "Review records before ordering."
    }
    """

    parsed = parse_decision_brief_response(payload, _decision_brief_context())

    assert parsed["top_tradeoffs"]
    assert parsed["recommended_order"]


def test_parse_decision_brief_response_accepts_single_text_list_value():
    payload = """
    {
      "summary": "Handle eggs first.",
      "buy_today": [
        {"item_id": 2, "item_name": "Eggs", "recommended_action": "RESTOCK_NOW", "reason": "Shortage risk is highest."}
      ],
      "buy_less": [],
      "delay": [],
      "estimated_impact": {
        "cash": "Delay low-risk purchases to preserve cash.",
        "waste": "Smaller paneer order lowers waste exposure.",
        "shortage": "Restocking eggs lowers shortage risk."
      },
      "top_tradeoffs": "Restocking eggs uses cash but protects availability.",
      "recommended_order": "Restock Now: Eggs",
      "confidence_note": "Grounded in current StockWise metrics.",
      "warning_flag": "Review records before ordering."
    }
    """

    parsed = parse_decision_brief_response(payload, _decision_brief_context())

    assert parsed["top_tradeoffs"] == ["Restocking eggs uses cash but protects availability."]
    assert parsed["recommended_order"] == ["Restock Now: Eggs"]


def test_parse_decision_brief_response_rejects_hallucinated_item_id():
    payload = """
    {
      "summary": "Buy coffee beans too.",
      "buy_today": [
        {"item_id": 99, "item_name": "Coffee Beans", "recommended_action": "RESTOCK_NOW", "reason": "Made up item."}
      ],
      "buy_less": [],
      "delay": [],
      "estimated_impact": {"cash": "cash", "waste": "waste", "shortage": "shortage"},
      "top_tradeoffs": ["tradeoff"],
      "recommended_order": ["order"],
      "confidence_note": "note",
      "warning_flag": null
    }
    """

    with pytest.raises(DecisionBriefValidationError, match="unknown item_id"):
        parse_decision_brief_response(payload, _decision_brief_context())


def test_parse_decision_brief_response_rejects_unsupported_profit_claims():
    payload = """
    {
      "summary": "This will increase profit immediately.",
      "buy_today": [],
      "buy_less": [],
      "delay": [],
      "estimated_impact": {"cash": "cash", "waste": "waste", "shortage": "shortage"},
      "top_tradeoffs": ["Revenue will grow."],
      "recommended_order": ["order"],
      "confidence_note": "note",
      "warning_flag": null
    }
    """

    with pytest.raises(DecisionBriefValidationError, match="unsupported"):
        parse_decision_brief_response(payload, _decision_brief_context())


def test_build_fallback_decision_brief_returns_safe_payload():
    fallback = build_fallback_decision_brief(_decision_brief_context())

    assert fallback["source"] == "fallback"
    assert fallback["safety_status"] == "fallback_used"
    assert fallback["buy_today"][0]["item_name"] == "Eggs"
    assert fallback["estimated_impact"]["shortage"]
