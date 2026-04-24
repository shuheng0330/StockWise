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
ALLOWED_CHAT_SCOPES = {"analysis", "simulation"}
CHAT_REQUIRED_FIELDS = {
    "scope",
    "answer",
    "supporting_points",
    "related_items",
    "suggested_follow_ups",
    "warning_flag",
}
CHAT_ACTION_ALIASES = {
    "DELAY_REORDER": "DELAY_PURCHASE",
    "DELAY_RESTOCK": "DELAY_PURCHASE",
    "DELAY_ORDER": "DELAY_PURCHASE",
}


class ExplanationValidationError(ValueError):
    pass


class ChatValidationError(ValueError):
    pass


def _normalize_chat_related_items(raw_related_items: list, context: dict) -> list:
    candidate_items = context.get("related_items", [])
    candidates_by_id = {}
    candidates_by_name = {}
    for item in candidate_items:
        if not isinstance(item, dict):
            continue
        item_id = item.get("item_id")
        item_name = item.get("item_name")
        if item_id is not None:
            candidates_by_id[int(item_id)] = item
        if item_name:
            candidates_by_name[str(item_name).strip().lower()] = item

    normalized = []
    for item in raw_related_items:
        if isinstance(item, dict):
            normalized.append(item)
            continue
        if isinstance(item, int):
            resolved = candidates_by_id.get(int(item))
            normalized.append(resolved if resolved is not None else item)
            continue
        if isinstance(item, str):
            stripped = item.strip()
            resolved = None
            if stripped.isdigit():
                resolved = candidates_by_id.get(int(stripped))
            if resolved is None:
                resolved = candidates_by_name.get(stripped.lower())
            normalized.append(resolved if resolved is not None else item)
            continue
        normalized.append(item)
    return normalized


def _normalize_chat_action(action: object) -> object:
    if not isinstance(action, str):
        return action
    return CHAT_ACTION_ALIASES.get(action.strip().upper(), action)


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


def parse_chat_response(payload: str, context: dict) -> dict:
    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ChatValidationError("Chat response is not valid JSON.") from exc

    missing = CHAT_REQUIRED_FIELDS - parsed.keys()
    if missing:
        raise ChatValidationError(f"Chat response is missing fields: {sorted(missing)}")
    if parsed["scope"] not in ALLOWED_CHAT_SCOPES:
        raise ChatValidationError("Chat response contains invalid scope.")
    if parsed["scope"] != context["scope"]:
        raise ChatValidationError("Chat response scope does not match the request scope.")

    answer = str(parsed["answer"])
    if not answer:
        raise ChatValidationError("Chat response answer must not be empty.")
    if len(answer) > 500:
        raise ChatValidationError("Chat response answer exceeds allowed length.")
    if UNSUPPORTED_PATTERN.search(answer):
        raise ChatValidationError("Chat response contains unsupported revenue/profit/sales claims.")

    supporting_points = parsed["supporting_points"]
    if not isinstance(supporting_points, list) or not supporting_points:
        raise ChatValidationError("Chat response supporting_points must contain at least one entry.")
    for point in supporting_points:
        value = str(point)
        if len(value) > MAX_FIELD_LENGTH:
            raise ChatValidationError("Chat response supporting_points entry exceeds allowed length.")
        if UNSUPPORTED_PATTERN.search(value):
            raise ChatValidationError("Chat response contains unsupported revenue/profit/sales claims.")

    related_items = parsed["related_items"]
    if not isinstance(related_items, list):
        raise ChatValidationError("Chat response related_items must be a list.")
    related_items = _normalize_chat_related_items(related_items, context)
    for item in related_items:
        if not isinstance(item, dict):
            raise ChatValidationError("Chat response related_items entry must be an object.")
        item["recommended_action"] = _normalize_chat_action(item.get("recommended_action"))
        required_item_fields = {"item_id", "item_name", "recommended_action", "reason"}
        missing_item_fields = required_item_fields - item.keys()
        if missing_item_fields:
            raise ChatValidationError(
                f"Chat response related_items entry is missing fields: {sorted(missing_item_fields)}"
            )
        if item["recommended_action"] not in ALLOWED_ACTIONS:
            raise ChatValidationError("Chat response related_items entry contains invalid recommended_action.")
        if int(item["item_id"]) not in context.get("allowed_item_ids", set()):
            raise ChatValidationError("Chat response related_items entry references an unknown item_id.")
        reason = str(item["reason"])
        if len(reason) > MAX_FIELD_LENGTH:
            raise ChatValidationError("Chat response related_items reason exceeds allowed length.")
        if UNSUPPORTED_PATTERN.search(reason):
            raise ChatValidationError("Chat response contains unsupported revenue/profit/sales claims.")
    parsed["related_items"] = related_items

    follow_ups = parsed["suggested_follow_ups"]
    if not isinstance(follow_ups, list) or not follow_ups:
        raise ChatValidationError("Chat response suggested_follow_ups must contain at least one entry.")
    for follow_up in follow_ups:
        value = str(follow_up)
        if len(value) > MAX_FIELD_LENGTH:
            raise ChatValidationError("Chat response suggested_follow_ups entry exceeds allowed length.")
        if UNSUPPORTED_PATTERN.search(value):
            raise ChatValidationError("Chat response contains unsupported revenue/profit/sales claims.")

    warning_flag = parsed["warning_flag"]
    if warning_flag is False:
        warning_flag = None
        parsed["warning_flag"] = None
    elif warning_flag is True:
        warning_flag = "Review the highlighted inventory risks before ordering."
        parsed["warning_flag"] = warning_flag
    if warning_flag is not None:
        warning_value = str(warning_flag)
        if len(warning_value) > MAX_FIELD_LENGTH:
            raise ChatValidationError("Chat response warning_flag exceeds allowed length.")
        if UNSUPPORTED_PATTERN.search(warning_value):
            raise ChatValidationError("Chat response contains unsupported revenue/profit/sales claims.")

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


def build_fallback_chat_response(context: dict) -> dict:
    starter_follow_ups = [
        "What should I buy today?",
        "Which items can I delay to save cash?",
        "Why is dairy risky this week?",
    ]
    if context.get("off_topic"):
        return {
            "source": "fallback",
            "scope": context["scope"],
            "answer": "I can help with inventory questions about this analysis, such as restocking, waste risk, delay candidates, or simulation changes.",
            "supporting_points": [
                "Ask about items to restock, buy less, or delay.",
                "You can also ask what changed after a simulation.",
            ],
            "related_items": context.get("related_items", [])[:2],
            "suggested_follow_ups": starter_follow_ups,
            "warning_flag": None,
        }

    related_items = context.get("related_items", [])[:3]
    if context["scope"] == "simulation" and context.get("simulation"):
        simulation = context["simulation"]
        current_action = simulation["current_recommended_action"]
        simulated_action = simulation["simulated_recommended_action"]
        answer = (
            f"For {simulation['item_name']}, the simulated order of {simulation['simulated_order_qty']} keeps the recommendation at "
            f"{simulated_action.replace('_', ' ')}."
            if simulated_action == current_action
            else f"For {simulation['item_name']}, the simulation changes the recommendation from "
            f"{current_action.replace('_', ' ')} to {simulated_action.replace('_', ' ')}."
        )
        supporting_points = [
            f"Simulated coverage becomes {simulation['simulated_coverage_days']:.1f} days.",
            f"Cash outlay for the simulated order is {simulation['simulated_cash_outlay']:.2f}.",
            f"Risk change is {simulation['simulated_risk_change'].replace('_', ' ')}.",
        ]
        warning_flag = (
            "The simulated scenario increases waste exposure."
            if simulation["simulated_risk_change"] == "higher_waste_risk"
            else None
        )
        follow_ups = [
            "Should I still order today?",
            "How does this affect waste risk?",
            "What should I buy today?",
        ]
        return {
            "source": "fallback",
            "scope": "simulation",
            "answer": answer,
            "supporting_points": supporting_points,
            "related_items": related_items,
            "suggested_follow_ups": follow_ups,
            "warning_flag": warning_flag,
        }

    answer = "Use today’s urgent restock items first, buy less where waste risk is high, and delay purchases where coverage is already strong."
    supporting_points = []
    kpi_summary = context.get("analysis", {}).get("kpi_summary", {})
    if kpi_summary:
        supporting_points.append(
            f"{kpi_summary.get('restock_now_count', 0)} item(s) currently need immediate restocking."
        )
        supporting_points.append(
            f"{kpi_summary.get('buy_less_count', 0)} item(s) are currently flagged to buy less."
        )
    supporting_points.extend(
        item["reason"] for item in related_items[:2]
    )
    if not supporting_points:
        supporting_points = [
            "The answer is based on the current analysis only.",
            "You can ask follow-ups about restocking, waste, or simulation changes.",
        ]
    warning_flag = (
        "You have both shortage risk and waste risk items to manage today."
        if kpi_summary.get("restock_now_count", 0) and kpi_summary.get("buy_less_count", 0)
        else None
    )
    return {
        "source": "fallback",
        "scope": "analysis",
        "answer": answer,
        "supporting_points": supporting_points[:4],
        "related_items": related_items,
        "suggested_follow_ups": starter_follow_ups,
        "warning_flag": warning_flag,
    }
