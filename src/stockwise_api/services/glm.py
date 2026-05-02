import json
import os
import time
from abc import ABC, abstractmethod

import httpx


EXPLANATION_FIELDS = (
    "item_name, recommended_action, priority_level, short_reason, "
    "decision_explanation, tradeoff_summary, suggested_next_step, "
    "confidence_note, warning_flag"
)
CHAT_FIELDS = (
    "scope, answer, supporting_points, related_items, suggested_follow_ups, warning_flag"
)
CHAT_NARRATIVE_FIELDS = (
    "answer, supporting_points, suggested_follow_ups, warning_flag"
)
CHAT_NARRATIVE_TOKENS = 900
DECISION_BRIEF_FIELDS = (
    "summary, buy_today, buy_less, delay, estimated_impact, top_tradeoffs, "
    "recommended_order, confidence_note, warning_flag"
)
DECISION_BRIEF_NARRATIVE_FIELDS = (
    "summary, top_tradeoffs, confidence_note, warning_flag"
)
DECISION_BRIEF_NARRATIVE_TOKENS = 1600
TRADEOFF_VERDICT_FIELDS = "verdict, reason, confidence_note"
TRADEOFF_VERDICT_TOKENS = 450

SYSTEM_PROMPT = (
    "You are StockWise. Use only the provided inventory metrics. "
    f"Return one JSON object with exactly these fields: {EXPLANATION_FIELDS}. "
    "Use the provided item_name and recommended_action exactly. "
    "priority_level must be HIGH, MEDIUM, or LOW in uppercase. "
    "Keep each text field concise. Do not add markdown or code fences."
)
STRICT_EXPLANATION_PROMPT_SUFFIX = (
    " Return compact valid JSON only. "
    "Do not use the words sales, revenue, or profit. "
    "Keep every text field under 220 characters. "
    "Use only stock, usage, lead-time, waste, cover, and cash language."
)
CHAT_SYSTEM_PROMPT = (
    "You are StockWise AI Advisor for small cafe operators. "
    "Answer only from the provided analysis and optional simulation context. "
    "If the user asks for anything outside the current inventory analysis, respond with a brief refusal that redirects them back to inventory questions. "
    "Do not invent sales, revenue, profit, supplier, or outside market facts. "
    f"Return one JSON object with exactly these fields: {CHAT_NARRATIVE_FIELDS}. "
    "supporting_points and suggested_follow_ups must be lists with one to three strings. "
    "Keep the answer concise, operational, and owner-friendly. Do not add markdown or code fences."
)
STRICT_CHAT_PROMPT_SUFFIX = (
    " Return compact valid JSON only. "
    "Do not use the words sales, revenue, or profit. "
    "Keep answer and warning_flag under 220 characters. "
    "Keep each supporting point and follow-up under 140 characters."
)
DECISION_BRIEF_SYSTEM_PROMPT = (
    "You are StockWise AI Decision Brief for small cafe operators. "
    "Use only the provided analysis, item list, and deterministic impact notes. "
    "Do not invent item names, item IDs, actions, sales, revenue, profit, supplier facts, or outside market facts. "
    f"Return one JSON object with exactly these fields: {DECISION_BRIEF_NARRATIVE_FIELDS}. "
    "top_tradeoffs must be a list with one or two strings. "
    "Keep every string under 18 words. "
    "Return compact valid JSON only. Do not add markdown or code fences."
)
STRICT_DECISION_BRIEF_PROMPT_SUFFIX = (
    " Keep summary, confidence_note, and warning_flag under 220 characters. "
    "Keep each tradeoff under 140 characters. "
    "Do not use the words sales, revenue, or profit."
)
TRADEOFF_VERDICT_SYSTEM_PROMPT = (
    "You are StockWise AI Trade-off Verdict for small cafe operators. "
    "Use only the provided current item metrics and server-computed simulation metrics. "
    "Choose exactly one verdict from: Worth it, Too much stock, Cash-heavy but safe, Try smaller quantity, Good emergency reorder. "
    f"Return one JSON object with exactly these fields: {TRADEOFF_VERDICT_FIELDS}. "
    "Do not invent sales, revenue, profit, supplier facts, or outside market facts. "
    "Keep reason under 24 words and confidence_note under 18 words. "
    "Return compact valid JSON only. Do not add markdown or code fences."
)
STRICT_TRADEOFF_VERDICT_PROMPT_SUFFIX = (
    " Do not use the words sales, revenue, or profit. "
    "Use only stock, cover, waste, urgency, and cash language."
)


def _env_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return float(raw_value)
    except ValueError:
        print(f"Ignoring invalid {name} value: {raw_value!r}")
        return default


def _env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError:
        print(f"Ignoring invalid {name} value: {raw_value!r}")
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    normalized = raw_value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    print(f"Ignoring invalid {name} value: {raw_value!r}")
    return default


def _is_gemini_endpoint(base_url: str) -> bool:
    return "generativelanguage.googleapis.com" in base_url.lower()


def _strip_json_fences(text: str) -> str:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    return cleaned


def _content_to_text(content) -> str:
    if isinstance(content, list):
        return "".join(
            part.get("text", "") if isinstance(part, dict) else str(part)
            for part in content
        )
    if isinstance(content, dict):
        return str(content.get("text") or content.get("content") or "")
    return str(content or "")


def _tool_calls_to_text(tool_calls) -> str:
    if not isinstance(tool_calls, list):
        return ""
    chunks: list[str] = []
    for tool_call in tool_calls:
        if not isinstance(tool_call, dict):
            continue
        function = tool_call.get("function") or {}
        if not isinstance(function, dict):
            continue
        arguments = _content_to_text(function.get("arguments"))
        if arguments:
            chunks.append(arguments)
    return "".join(chunks)


def _extract_choice_content(choice: dict) -> str:
    message = choice.get("message") or {}
    delta = choice.get("delta") or {}
    candidates = (
        message.get("content"),
        message.get("reasoning_content"),
        message.get("reasoning"),
        delta.get("content"),
        delta.get("reasoning_content"),
        _tool_calls_to_text(message.get("tool_calls")),
        _tool_calls_to_text(delta.get("tool_calls")),
        choice.get("text"),
    )
    for candidate in candidates:
        content = _strip_json_fences(_content_to_text(candidate))
        if content:
            return content
    return ""


def _response_debug_hint(event: dict) -> str:
    choices = event.get("choices") or []
    if not choices:
        return "choices=0"
    choice = choices[0]
    message = choice.get("message") or {}
    return (
        f"finish_reason={choice.get('finish_reason')!r}, "
        f"message_keys={sorted(message.keys())}, "
        f"choice_keys={sorted(choice.keys())}"
    )


def _loads_model_json(payload: str) -> dict:
    cleaned = _strip_json_fences(payload)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        start = cleaned.find("{")
        while start != -1:
            try:
                parsed, _end = decoder.raw_decode(cleaned[start:])
                break
            except json.JSONDecodeError:
                start = cleaned.find("{", start + 1)
        else:
            raise
    if not isinstance(parsed, dict):
        raise ValueError("Model JSON payload must be an object.")
    return parsed


def _compact_model_context(context: dict) -> dict:
    metrics = {
        "current_stock": context.get("current_stock"),
        "reorder_level": context.get("reorder_level"),
        "daily_usage": context.get("daily_usage"),
        "lead_time": context.get("lead_time"),
        "days_of_cover": context.get("days_of_cover"),
        "lead_time_demand": context.get("lead_time_demand"),
        "stock_gap_to_lead_demand": context.get("stock_gap_to_lead_demand"),
        "reorder_urgency_score": context.get("reorder_urgency_score"),
        "waste_risk_score": context.get("waste_risk_score"),
        "waste_percentage": context.get("waste_percentage"),
        "estimated_waste_cost": context.get("estimated_waste_cost"),
        "inventory_value": context.get("inventory_value"),
        "avg_usage_7d": context.get("avg_usage_7d"),
        "trend_direction": context.get("trend_direction"),
    }
    compact = {
        "item_name": context.get("item_name"),
        "recommended_action": context.get("recommended_action"),
        "category": context.get("category"),
        "subcategory": context.get("subcategory"),
        "unit": context.get("unit"),
        "metrics": {key: value for key, value in metrics.items() if value is not None},
    }
    if "simulated_order_qty" in context:
        compact["simulation"] = {
            key: context.get(key)
            for key in (
                "simulated_order_qty",
                "simulated_cash_outlay",
                "simulated_coverage_days",
                "simulated_risk_change",
            )
            if context.get(key) is not None
        }
    return compact


def _system_prompt(base_prompt: str, context: dict, strict_suffix: str = "") -> str:
    if context.get("_strict_json") and strict_suffix:
        return f"{base_prompt}{strict_suffix}"
    return base_prompt


def _compact_chat_context(context: dict) -> dict:
    related_items = _chat_related_items(context) if "analysis" in context else []
    compact = {
        "scope": context["scope"],
        "message": context["message"],
        "recent_messages": context.get("recent_messages", []),
        "kpi_summary": context["analysis"]["kpi_summary"],
        "related_items": related_items,
    }
    if context.get("simulation"):
        compact["simulation"] = context["simulation"]
    return compact


def _compact_decision_brief_context(context: dict) -> dict:
    return {
        "dataset_summary": context["analysis"]["dataset_summary"],
        "kpi_summary": context["analysis"]["kpi_summary"],
        "deterministic_impact": context["deterministic_impact"],
        "items": [
            {
                "item_id": item["item_id"],
                "item_name": item["item_name"],
                "category": item.get("category"),
                "current_stock": item["current_stock"],
                "daily_usage": item["daily_usage"],
                "days_of_cover": item["days_of_cover"],
                "inventory_value": item["inventory_value"],
                "estimated_waste_cost": item["estimated_waste_cost"],
                "lead_time_demand": item["lead_time_demand"],
                "stock_gap_to_lead_demand": item["stock_gap_to_lead_demand"],
                "reorder_urgency_score": item["reorder_urgency_score"],
                "waste_risk_score": item["waste_risk_score"],
                "recommended_action": item["recommended_action"],
            }
            for item in context["analysis"]["items"]
        ],
    }


def _compact_tradeoff_verdict_context(context: dict) -> dict:
    return {
        "item_name": context["item_name"],
        "current": {
            "recommended_action": context["recommended_action"],
            "days_of_cover": context["days_of_cover"],
            "estimated_waste_cost": context["estimated_waste_cost"],
            "reorder_urgency_score": context["reorder_urgency_score"],
            "waste_risk_score": context["waste_risk_score"],
            "stock_gap_to_lead_demand": context["stock_gap_to_lead_demand"],
        },
        "simulation": {
            "simulated_order_qty": context["simulated_order_qty"],
            "simulated_cash_outlay": context["simulated_cash_outlay"],
            "simulated_coverage_days": context["simulated_coverage_days"],
            "simulated_estimated_waste_cost": context["simulated_estimated_waste_cost"],
            "simulated_risk_change": context["simulated_risk_change"],
            "simulated_reorder_urgency_score": context["simulated_reorder_urgency_score"],
            "simulated_waste_risk_score": context["simulated_waste_risk_score"],
            "simulated_recommended_action": context["simulated_recommended_action"],
        },
    }


def build_explanation_context(item: dict, simulation_context: dict | None = None) -> dict:
    context = {
        "item_name": item["item_name"],
        "category": item["category"],
        "subcategory": item["subcategory"],
        "unit": item["unit"],
        "supplier_name": item["supplier_name"],
        "current_stock": item["current_stock"],
        "reorder_level": item["reorder_level"],
        "daily_usage": item["daily_usage"],
        "lead_time": item["lead_time"],
        "seasonal_factor": item["seasonal_factor"],
        "price_per_unit": item["price_per_unit"],
        "waste_percentage": item["waste_percentage"],
        "days_of_cover": item["days_of_cover"],
        "inventory_value": item["inventory_value"],
        "estimated_waste_cost": item["estimated_waste_cost"],
        "lead_time_demand": item["lead_time_demand"],
        "stock_gap_to_lead_demand": item["stock_gap_to_lead_demand"],
        "reorder_urgency_score": item["reorder_urgency_score"],
        "waste_risk_score": item["waste_risk_score"],
        "recommended_action": item["recommended_action"],
        "avg_usage_7d": item["avg_usage_7d"],
        "trend_direction": item["trend_direction"],
    }
    if simulation_context:
        context.update(simulation_context)
    return context


def build_tradeoff_verdict_context(item: dict, simulation: dict) -> dict:
    context = build_explanation_context(item)
    context.update(
        {
            "simulated_order_qty": simulation["simulated_order_qty"],
            "simulated_cash_outlay": simulation["simulated_cash_outlay"],
            "simulated_coverage_days": simulation["simulated_coverage_days"],
            "simulated_inventory_value": simulation["simulated_inventory_value"],
            "simulated_estimated_waste_cost": simulation["simulated_estimated_waste_cost"],
            "simulated_risk_change": simulation["simulated_risk_change"],
            "simulated_reorder_urgency_score": simulation["reorder_urgency_score"],
            "simulated_waste_risk_score": simulation["waste_risk_score"],
            "simulated_recommended_action": simulation["recommended_action"],
        }
    )
    return context


def build_inventory_chat_context(
    *,
    message: str,
    recent_messages: list[dict],
    dataset_summary: dict,
    kpi_summary: dict,
    items: list[dict],
    simulation_context: dict | None = None,
) -> dict:
    top_items = sorted(
        items,
        key=lambda item: (
            int(item.get("reorder_urgency_score", 0)) + int(item.get("waste_risk_score", 0)),
            float(item.get("estimated_waste_cost", 0.0)),
        ),
        reverse=True,
    )[:6]
    compact_items = []
    for item in top_items:
        compact_items.append(
            {
                "item_id": int(item["item_id"]),
                "item_name": item["item_name"],
                "category": item.get("category"),
                "subcategory": item.get("subcategory"),
                "current_stock": item["current_stock"],
                "daily_usage": item["daily_usage"],
                "days_of_cover": item["days_of_cover"],
                "estimated_waste_cost": item["estimated_waste_cost"],
                "reorder_urgency_score": item["reorder_urgency_score"],
                "waste_risk_score": item["waste_risk_score"],
                "recommended_action": item["recommended_action"],
                "history": _compact_item_history(item),
                "reason_hint": (
                    "Urgent restock needed."
                    if item["recommended_action"] == "RESTOCK_NOW"
                    else "Waste risk is elevated."
                    if item["recommended_action"] == "BUY_LESS"
                    else "Coverage is strong enough to wait."
                    if item["recommended_action"] == "DELAY_PURCHASE"
                    else "Monitor this item closely."
                ),
            }
        )
    return {
        "scope": "simulation" if simulation_context else "analysis",
        "message": message,
        "recent_messages": recent_messages[-4:],
        "analysis": {
            "dataset_summary": dataset_summary,
            "kpi_summary": kpi_summary,
            "history_summary": _analysis_history_summary(dataset_summary),
            "items": compact_items,
        },
        "simulation": simulation_context,
        "allowed_item_ids": {int(item["item_id"]) for item in items},
    }


def _brief_item_reason(item: dict) -> str:
    action = item["recommended_action"]
    if action == "RESTOCK_NOW":
        return "Current stock does not comfortably cover lead-time demand."
    if action == "BUY_LESS":
        return "Waste risk is high relative to the current stock position."
    if action == "DELAY_PURCHASE":
        return "Coverage is strong enough to preserve cash for now."
    return "Signals are mixed, so this item should stay under review."


def _brief_item_payload(item: dict) -> dict:
    return {
        "item_id": item["item_id"],
        "item_name": item["item_name"],
        "recommended_action": item["recommended_action"],
        "reason": item.get("reason_hint") or _brief_item_reason(item),
    }


def _analysis_history_summary(dataset_summary: dict) -> dict:
    date_range = dataset_summary.get("date_range", {}) or {}
    return {
        "date_range": {
            "start": date_range.get("start"),
            "end": date_range.get("end"),
        },
        "source_observation_count": int(dataset_summary.get("row_count", 0)),
        "current_item_count": int(dataset_summary.get("item_count", 0)),
        "latest_observation_date": date_range.get("end"),
    }


def _compact_item_history(item: dict) -> dict:
    return {
        "observation_count": int(item.get("_observation_count", 1)),
        "latest_observation_date": item.get("date"),
        "avg_usage_7d": item.get("avg_usage_7d"),
        "trend_direction": item.get("trend_direction"),
    }


def _narrative_text(value, fallback: str) -> str:
    text = "" if value is None else str(value).strip()
    return text or fallback


def _narrative_text_list(value, fallback: list[str]) -> list[str]:
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        return items[:2] or fallback
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return fallback


def _chat_related_items(context: dict) -> list[dict]:
    related_items = context.get("related_items") or []
    if not related_items:
        related_items = [
            {
                "item_id": item["item_id"],
                "item_name": item["item_name"],
                "recommended_action": item["recommended_action"],
                "reason": item.get("reason_hint") or "This item is relevant to the current question.",
            }
            for item in context.get("analysis", {}).get("items", [])[:3]
        ]
    return [
        {
            "item_id": int(item["item_id"]),
            "item_name": item["item_name"],
            "recommended_action": item["recommended_action"],
            "reason": item.get("reason") or item.get("reason_hint") or "This item is relevant to the current question.",
        }
        for item in related_items[:3]
    ]


def _assemble_live_chat_response(context: dict, narrative: dict) -> str:
    related_items = _chat_related_items(context)
    starter_follow_ups = [
        "What's the biggest risk in today's plan?",
        "Which items can I delay to save cash?",
        "Why is dairy risky this week?",
    ]
    kpi_summary = context.get("analysis", {}).get("kpi_summary", {})
    fallback_points = []
    if kpi_summary:
        fallback_points.extend(
            [
                f"{kpi_summary.get('restock_now_count', 0)} item(s) need immediate restocking.",
                f"{kpi_summary.get('buy_less_count', 0)} item(s) are flagged to buy less.",
            ]
        )
    fallback_points.extend(item["reason"] for item in related_items[:2])
    if not fallback_points:
        fallback_points = ["This answer is grounded in the current StockWise analysis."]
    response = {
        "scope": context["scope"],
        "answer": _narrative_text(
            narrative.get("answer"),
            "Focus on urgent restocks first, buy less for high waste-risk items, and delay items with enough cover.",
        ),
        "supporting_points": _narrative_text_list(
            narrative.get("supporting_points"),
            fallback_points[:3],
        )[:3],
        "related_items": related_items,
        "suggested_follow_ups": _narrative_text_list(
            narrative.get("suggested_follow_ups"),
            starter_follow_ups,
        )[:3],
        "warning_flag": narrative.get("warning_flag"),
    }
    return json.dumps(response)


def _assemble_live_decision_brief(context: dict, narrative: dict) -> str:
    items = context["analysis"]["items"]
    buy_today = [_brief_item_payload(item) for item in items if item["recommended_action"] == "RESTOCK_NOW"][:3]
    buy_less = [_brief_item_payload(item) for item in items if item["recommended_action"] == "BUY_LESS"][:3]
    delay = [_brief_item_payload(item) for item in items if item["recommended_action"] == "DELAY_PURCHASE"][:3]
    recommended_order = [
        f"{item['recommended_action'].replace('_', ' ').title()}: {item['item_name']}"
        for item in [*buy_today, *buy_less, *delay]
    ][:5]
    if not recommended_order:
        recommended_order = ["Review the ranked item table before placing orders."]
    response = {
        "summary": _narrative_text(
            narrative.get("summary"),
            "Review urgent restocks, waste-risk items, and purchases that can wait.",
        ),
        "buy_today": buy_today,
        "buy_less": buy_less,
        "delay": delay,
        "estimated_impact": context["deterministic_impact"],
        "top_tradeoffs": _narrative_text_list(
            narrative.get("top_tradeoffs"),
            [
                "Urgent restocks reduce shortage risk but use cash now.",
                "Buying less lowers waste exposure but needs monitoring.",
            ],
        ),
        "recommended_order": recommended_order,
        "confidence_note": _narrative_text(
            narrative.get("confidence_note"),
            "Live brief grounded in deterministic StockWise metrics.",
        ),
        "warning_flag": _narrative_text(
            narrative.get("warning_flag"),
            "Review records before placing orders.",
        ),
    }
    return json.dumps(response)


def build_decision_brief_context(
    *,
    dataset_summary: dict,
    kpi_summary: dict,
    items: list[dict],
) -> dict:
    sorted_items = sorted(
        items,
        key=lambda item: (
            int(item.get("recommended_action") == "RESTOCK_NOW") * 300
            + int(item.get("recommended_action") == "BUY_LESS") * 220
            + int(item.get("recommended_action") == "DELAY_PURCHASE") * 120
            + int(item.get("reorder_urgency_score", 0))
            + int(item.get("waste_risk_score", 0)),
            float(item.get("estimated_waste_cost", 0.0)),
        ),
        reverse=True,
    )[:8]
    impact = {
        "cash": (
            f"{kpi_summary.get('buy_less_count', 0)} buy-less item(s) and delay candidates can reduce immediate purchase pressure."
        ),
        "waste": (
            f"{kpi_summary.get('high_waste_risk_count', 0)} high waste-risk item(s) represent "
            f"{float(kpi_summary.get('inventory_value_at_risk', 0.0)):.2f} in inventory value at risk."
        ),
        "shortage": (
            f"{kpi_summary.get('restock_now_count', 0)} item(s) need immediate restocking to reduce shortage risk."
        ),
    }
    return {
        "analysis": {
            "dataset_summary": dataset_summary,
            "kpi_summary": kpi_summary,
            "history_summary": _analysis_history_summary(dataset_summary),
            "items": [
                {
                    **item,
                    "history": _compact_item_history(item),
                    "reason_hint": _brief_item_reason(item),
                }
                for item in sorted_items
            ],
        },
        "deterministic_impact": impact,
        "allowed_item_ids": {int(item["item_id"]) for item in items},
        "items_by_id": {
            int(item["item_id"]): {
                "item_name": item["item_name"],
                "recommended_action": item["recommended_action"],
            }
            for item in items
        },
    }


class BaseZAIProvider(ABC):
    source = "mock"

    @abstractmethod
    def generate_explanation(self, context: dict) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate_inventory_chat(self, context: dict) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate_decision_brief(self, context: dict) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate_tradeoff_verdict(self, context: dict) -> str:
        raise NotImplementedError


class MockZAIProvider(BaseZAIProvider):
    source = "mock"

    def generate_explanation(self, context: dict) -> str:
        action = context["recommended_action"]
        priority = "HIGH" if action == "RESTOCK_NOW" else "MEDIUM" if action in {"BUY_LESS", "MONITOR_CLOSELY"} else "LOW"
        response = {
            "item_name": context["item_name"],
            "recommended_action": action,
            "priority_level": priority,
            "short_reason": f"{context['item_name']} is being evaluated from structured stock and waste metrics.",
            "decision_explanation": (
                f"{context['item_name']} is recommended as {action} based on current coverage, lead-time demand, and waste-cost exposure."
            ),
            "tradeoff_summary": "The decision balances shortage risk, waste risk, and cash usage.",
            "suggested_next_step": "Review the recommendation and place the corresponding order decision.",
            "confidence_note": "Mock provider response generated from deterministic context.",
            "warning_flag": f"Trend direction: {context['trend_direction']}.",
        }
        return json.dumps(response)

    def generate_inventory_chat(self, context: dict) -> str:
        simulation = context.get("simulation")
        related_items = [
            {
                "item_id": item["item_id"],
                "item_name": item["item_name"],
                "recommended_action": item["recommended_action"],
                "reason": item.get("reason_hint", "This item is relevant to the current question."),
            }
            for item in context["analysis"]["items"][:3]
        ]
        if simulation:
            response = {
                "scope": "simulation",
                "answer": f"The simulated order for {simulation['item_name']} should be reviewed against waste and coverage together.",
                "supporting_points": [
                    f"Simulated coverage is {simulation['simulated_coverage_days']:.1f} days.",
                    f"Simulated cash outlay is {simulation['simulated_cash_outlay']:.2f}.",
                    f"Risk change is {simulation['simulated_risk_change'].replace('_', ' ')}.",
                ],
                "related_items": related_items[:1],
                "suggested_follow_ups": [
                    "Should I still order today?",
                    "How does this affect waste risk?",
                ],
                "warning_flag": None,
            }
        else:
            response = {
                "scope": "analysis",
                "answer": "Focus first on urgent restocks and buy less for items with elevated waste risk.",
                "supporting_points": [
                    f"{context['analysis']['kpi_summary'].get('restock_now_count', 0)} item(s) need immediate restocking.",
                    f"{context['analysis']['kpi_summary'].get('buy_less_count', 0)} item(s) are flagged to buy less.",
                ],
                "related_items": related_items,
                "suggested_follow_ups": [
                    "Which items can I delay to save cash?",
                    "Why is dairy risky this week?",
                ],
                "warning_flag": None,
            }
        return json.dumps(response)

    def generate_decision_brief(self, context: dict) -> str:
        items = context["analysis"]["items"]
        buy_today = [
            {
                "item_id": item["item_id"],
                "item_name": item["item_name"],
                "recommended_action": item["recommended_action"],
                "reason": item.get("reason_hint", "This item should be prioritized today."),
            }
            for item in items
            if item["recommended_action"] == "RESTOCK_NOW"
        ][:3]
        buy_less = [
            {
                "item_id": item["item_id"],
                "item_name": item["item_name"],
                "recommended_action": item["recommended_action"],
                "reason": item.get("reason_hint", "This item has elevated waste risk."),
            }
            for item in items
            if item["recommended_action"] == "BUY_LESS"
        ][:3]
        delay = [
            {
                "item_id": item["item_id"],
                "item_name": item["item_name"],
                "recommended_action": item["recommended_action"],
                "reason": item.get("reason_hint", "This item can wait."),
            }
            for item in items
            if item["recommended_action"] == "DELAY_PURCHASE"
        ][:3]
        response = {
            "summary": "Start with urgent restocks, reduce high waste-risk buys, and delay items with healthy cover.",
            "buy_today": buy_today,
            "buy_less": buy_less,
            "delay": delay,
            "estimated_impact": context["deterministic_impact"],
            "top_tradeoffs": [
                "Restocking urgent items uses cash but reduces shortage risk.",
                "Buying less for risky items lowers waste exposure but needs closer monitoring.",
            ],
            "recommended_order": [
                item["item_name"]
                for item in [*buy_today, *buy_less, *delay]
            ][:5],
            "confidence_note": "Mock decision brief generated from grounded StockWise metrics.",
            "warning_flag": "Review records before placing orders.",
        }
        return json.dumps(response)

    def generate_tradeoff_verdict(self, context: dict) -> str:
        risk_change = context["simulated_risk_change"]
        simulated_action = context["simulated_recommended_action"]
        if risk_change == "higher_waste_risk":
            verdict = "Cash-heavy but safe"
        elif simulated_action == "RESTOCK_NOW":
            verdict = "Good emergency reorder"
        elif simulated_action == "DELAY_PURCHASE":
            verdict = "Worth it"
        else:
            verdict = "Try smaller quantity"
        response = {
            "verdict": verdict,
            "reason": (
                f"The simulation changes {context['item_name']} to "
                f"{simulated_action.replace('_', ' ').lower()} with {risk_change.replace('_', ' ')}."
            ),
            "confidence_note": "Mock verdict generated from grounded simulation metrics.",
        }
        return json.dumps(response)


class LiveZAIProvider(BaseZAIProvider):
    source = "live"

    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float | None = None,
        max_tokens: int | None = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url or os.getenv("ZAI_BASE_URL", "https://api.z.ai/api/paas/v4/chat/completions")
        self.model = model or os.getenv("ZAI_MODEL", "glm-4.5")
        self.timeout = self._build_timeout(timeout_seconds)
        self.max_tokens = max_tokens if max_tokens is not None else _env_int("ZAI_MAX_TOKENS", 1600)
        self.is_gemini = _is_gemini_endpoint(self.base_url)
        self.stream = _env_bool(
            "ZAI_STREAM",
            default=("api.ilmu.ai" not in self.base_url.lower() and not self.is_gemini),
        )

    def _build_timeout(self, timeout_seconds: float | None) -> httpx.Timeout:
        if timeout_seconds is not None:
            return httpx.Timeout(timeout_seconds)
        return httpx.Timeout(
            connect=_env_float("ZAI_CONNECT_TIMEOUT_SECONDS", 10.0),
            read=_env_float("ZAI_READ_TIMEOUT_SECONDS", _env_float("ZAI_TIMEOUT_SECONDS", 180.0)),
            write=_env_float("ZAI_WRITE_TIMEOUT_SECONDS", 10.0),
            pool=_env_float("ZAI_POOL_TIMEOUT_SECONDS", 10.0),
        )

    def generate_explanation(self, context: dict) -> str:
        model_context = _compact_model_context(context)
        return self._generate_json_response(
            _system_prompt(SYSTEM_PROMPT, context, STRICT_EXPLANATION_PROMPT_SUFFIX),
            model_context,
        )

    def generate_inventory_chat(self, context: dict) -> str:
        model_context = _compact_chat_context(context)
        narrative = self._generate_narrative_json(
            context=context,
            model_context=model_context,
            base_prompt=CHAT_SYSTEM_PROMPT,
            strict_suffix=STRICT_CHAT_PROMPT_SUFFIX,
            max_tokens=CHAT_NARRATIVE_TOKENS,
        )
        return _assemble_live_chat_response(context, narrative)

    def generate_decision_brief(self, context: dict) -> str:
        model_context = _compact_decision_brief_context(context)
        narrative = self._generate_narrative_json(
            context=context,
            model_context=model_context,
            base_prompt=DECISION_BRIEF_SYSTEM_PROMPT,
            strict_suffix=STRICT_DECISION_BRIEF_PROMPT_SUFFIX,
            max_tokens=DECISION_BRIEF_NARRATIVE_TOKENS,
        )
        return _assemble_live_decision_brief(context, narrative)

    def generate_tradeoff_verdict(self, context: dict) -> str:
        model_context = _compact_tradeoff_verdict_context(context)
        return self._generate_json_response(
            _system_prompt(
                TRADEOFF_VERDICT_SYSTEM_PROMPT,
                context,
                STRICT_TRADEOFF_VERDICT_PROMPT_SUFFIX,
            ),
            model_context,
            max_tokens=TRADEOFF_VERDICT_TOKENS,
        )

    def _generate_narrative_json(
        self,
        *,
        context: dict,
        model_context: dict,
        base_prompt: str,
        strict_suffix: str,
        max_tokens: int,
    ) -> dict:
        raw = self._generate_json_response(
            _system_prompt(base_prompt, context, strict_suffix),
            model_context,
            max_tokens=max_tokens,
        )
        try:
            return _loads_model_json(raw)
        except Exception:
            if context.get("_strict_json"):
                raise
            retry_context = {**context, "_strict_json": True}
            retry_raw = self._generate_json_response(
                _system_prompt(base_prompt, retry_context, strict_suffix),
                model_context,
                max_tokens=max_tokens,
            )
            return _loads_model_json(retry_raw)

    def _generate_json_response(self, system_prompt: str, model_context: dict, max_tokens: int | None = None) -> str:
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "max_tokens": max_tokens if max_tokens is not None else self.max_tokens,
            "reasoning_effort": "low",
            "stream": self.stream,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(model_context),
                },
            ],
        }
        if not self.is_gemini:
            payload["response_format"] = {"type": "json_object"}
            payload["thinking"] = {"type": "disabled"}
        started_at = time.monotonic()
        try:
            with httpx.Client(timeout=self.timeout) as client:
                if self.stream:
                    with client.stream(
                        "POST",
                        self.base_url,
                        json=payload,
                        headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    ) as response:
                        response.raise_for_status()
                        try:
                            content = self._collect_streamed_content(response)
                        except RuntimeError as stream_exc:
                            if "without visible content" not in str(stream_exc):
                                raise
                            print(
                                "Live streamed response had no visible content; "
                                f"retrying without streaming: {stream_exc}"
                            )
                            non_stream_payload = {**payload, "stream": False}
                            non_stream_response = client.post(
                                self.base_url,
                                json=non_stream_payload,
                                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                            )
                            non_stream_response.raise_for_status()
                            content = self._collect_non_stream_content(
                                non_stream_response,
                                lambda: self._retry_non_stream_without_strict_json(client, payload),
                            )
                else:
                    response = client.post(
                        self.base_url,
                        json=payload,
                        headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    )
                    response.raise_for_status()
                    content = self._collect_non_stream_content(
                        response,
                        lambda: self._retry_non_stream_without_strict_json(client, payload),
                    )
        except Exception as exc:
            elapsed = time.monotonic() - started_at
            print(
                f"Live explanation request failed after {elapsed:.2f}s "
                f"(model={self.model}, max_tokens={payload['max_tokens']}): {type(exc).__name__}: {exc}"
            )
            raise
        elapsed = time.monotonic() - started_at
        print(
            f"Live explanation request completed in {elapsed:.2f}s "
            f"(model={self.model}, max_tokens={payload['max_tokens']})"
        )
        return content

    def _retry_non_stream_without_strict_json(self, client, payload: dict) -> str:
        compatibility_payload = {
            key: value
            for key, value in {**payload, "stream": False}.items()
            if key not in {"response_format", "reasoning_effort"}
        }
        response = client.post(
            self.base_url,
            json=compatibility_payload,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        response.raise_for_status()
        return self._collect_non_stream_content(response)

    def _collect_non_stream_content(self, response, empty_retry=None) -> str:
        event = response.json()
        choices = event.get("choices") or []
        if not choices:
            raise RuntimeError("Z.AI non-stream response completed without choices.")
        choice = choices[0]
        combined = _extract_choice_content(choice)
        if not combined:
            if empty_retry is not None:
                try:
                    return empty_retry()
                except Exception as retry_exc:
                    print(f"Z.AI compatibility retry failed after empty content: {type(retry_exc).__name__}: {retry_exc}")
            raise RuntimeError(
                "Z.AI non-stream response completed without visible content "
                f"({_response_debug_hint(event)})."
            )
        return combined

    def _collect_streamed_content(self, response) -> str:
        chunks: list[str] = []
        observed_events: list[str] = []
        for line in response.iter_lines():
            if not line:
                continue
            if isinstance(line, bytes):
                line = line.decode("utf-8", errors="replace")
            if not line.startswith("data:"):
                continue
            payload = line[len("data:"):].strip()
            if payload == "[DONE]":
                break
            if len(observed_events) < 3:
                observed_events.append(payload[:240])
            try:
                event = json.loads(payload)
            except json.JSONDecodeError:
                continue
            choices = event.get("choices")
            if not choices:
                continue
            choice = choices[0]
            content = _extract_choice_content(choice)
            if content:
                chunks.append(content)
        combined = _strip_json_fences("".join(chunks))
        if not combined:
            event_hint = f" Observed events: {observed_events}" if observed_events else ""
            raise RuntimeError(f"Z.AI stream completed without visible content.{event_hint}")
        return combined


def provider_from_env() -> BaseZAIProvider:
    mode = os.getenv("GLM_MODE", "mock").lower()
    if mode == "live":
        api_key = os.getenv("ZAI_API_KEY")
        if not api_key:
            raise RuntimeError("GLM_MODE is 'live' but ZAI_API_KEY is not set.")
        return LiveZAIProvider(api_key=api_key)
    return MockZAIProvider()
