import json
import re


ALLOWED_ACTIONS = {"RESTOCK_NOW", "BUY_LESS", "DELAY_PURCHASE", "MONITOR_CLOSELY"}
ALLOWED_PRIORITIES = {"HIGH", "MEDIUM", "LOW"}
REQUIRED_FIELDS = {
    "item_name",
    "recommended_action",
    "priority_level",
    "short_reason",
    "decision_explanation",
    "tradeoff_summary",
    "suggested_next_step",
    "confidence_note",
    "warning_flag",
}
MAX_FIELD_LENGTH = 280
UNSUPPORTED_PATTERN = re.compile(r"\b(sales|revenue|profit)\b", re.IGNORECASE)


class ExplanationValidationError(ValueError):
    pass


def parse_explanation_response(payload: str, context: dict) -> dict:
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ExplanationValidationError("Explanation response is not valid JSON.") from exc

    missing = REQUIRED_FIELDS - parsed.keys()
    if missing:
        raise ExplanationValidationError(f"Explanation response is missing fields: {sorted(missing)}")
    if parsed["recommended_action"] not in ALLOWED_ACTIONS:
        raise ExplanationValidationError("Explanation response contains invalid recommended_action.")
    if parsed["priority_level"] not in ALLOWED_PRIORITIES:
        raise ExplanationValidationError("Explanation response contains invalid priority_level.")
    if parsed["item_name"] != context["item_name"]:
        raise ExplanationValidationError("Explanation response item_name does not match request item_name.")

    for field in REQUIRED_FIELDS - {"item_name", "recommended_action", "priority_level"}:
        value = str(parsed[field])
        if len(value) > MAX_FIELD_LENGTH:
            raise ExplanationValidationError(f"Explanation field '{field}' exceeds allowed length.")
        if UNSUPPORTED_PATTERN.search(value):
            raise ExplanationValidationError("Explanation response contains unsupported revenue/profit/sales claims.")

    return parsed


def build_fallback_explanation(context: dict) -> dict:
    priority = "HIGH" if context["reorder_urgency_score"] >= 70 else "MEDIUM" if context["waste_risk_score"] >= 70 else "LOW"
    action = context["recommended_action"]
    if action == "RESTOCK_NOW":
        short_reason = "Stock is not covering projected lead-time demand."
        decision_explanation = (
            f"Restock {context['item_name']} now because current stock is below projected lead-time demand."
        )
        tradeoff_summary = "Buying now reduces shortage risk even though it may increase near-term cash outlay."
        suggested_next_step = "Place a replenishment order for the next cycle."
    elif action == "BUY_LESS":
        short_reason = "Waste-cost exposure is high for the current stock position."
        decision_explanation = (
            f"Buy less of {context['item_name']} because waste risk is high relative to urgency and the item ties up significant inventory value."
        )
        tradeoff_summary = "A smaller order lowers waste and cash exposure while keeping the item available."
        suggested_next_step = "Place only a small top-up order if needed."
    elif action == "DELAY_PURCHASE":
        short_reason = "Current coverage is strong enough to wait."
        decision_explanation = (
            f"Delay purchasing {context['item_name']} because current stock already covers the near-term need."
        )
        tradeoff_summary = "Waiting preserves cash without meaningfully increasing shortage risk."
        suggested_next_step = "Recheck after the next usage cycle."
    else:
        short_reason = "Signals are mixed and should be monitored."
        decision_explanation = (
            f"Monitor {context['item_name']} closely because urgency is rising but does not yet justify a large replenishment."
        )
        tradeoff_summary = "Monitoring avoids premature overbuying while keeping the item under review."
        suggested_next_step = "Review this item again after the next daily update."

    return {
        "source": "fallback",
        "item_name": context["item_name"],
        "recommended_action": action,
        "priority_level": priority,
        "short_reason": short_reason,
        "decision_explanation": decision_explanation,
        "tradeoff_summary": tradeoff_summary,
        "suggested_next_step": suggested_next_step,
        "confidence_note": "Fallback explanation generated from deterministic rules.",
        "warning_flag": f"Trend direction: {context.get('trend_direction', 'stable')}.",
    }
