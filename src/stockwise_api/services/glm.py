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

SYSTEM_PROMPT = (
    "You are StockWise. Use only the provided inventory metrics. "
    f"Return one JSON object with exactly these fields: {EXPLANATION_FIELDS}. "
    "Use the provided item_name and recommended_action exactly. "
    "priority_level must be HIGH, MEDIUM, or LOW in uppercase. "
    "Keep each text field concise. Do not add markdown or code fences."
)
CHAT_SYSTEM_PROMPT = (
    "You are StockWise AI Copilot for small cafe operators. "
    "Answer only from the provided analysis and optional simulation context. "
    "If the user asks for anything outside the current inventory analysis, respond with a brief refusal that redirects them back to inventory questions. "
    "Do not invent sales, revenue, profit, supplier, or outside market facts. "
    f"Return one JSON object with exactly these fields: {CHAT_FIELDS}. "
    "scope must be either analysis or simulation. "
    "related_items must be a list of objects, and each object must contain item_id, item_name, recommended_action, and reason. "
    "Each related_items item_id must come from the provided item list. "
    "Keep the answer concise, operational, and owner-friendly. Do not add markdown or code fences."
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


def _compact_chat_context(context: dict) -> dict:
    compact = {
        "scope": context["scope"],
        "message": context["message"],
        "recent_messages": context.get("recent_messages", []),
        "dataset_summary": context["analysis"]["dataset_summary"],
        "kpi_summary": context["analysis"]["kpi_summary"],
        "items": [
            {
                "item_id": item["item_id"],
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
                "reason_hint": item.get("reason_hint"),
            }
            for item in context["analysis"]["items"]
        ],
    }
    if context.get("simulation"):
        compact["simulation"] = context["simulation"]
    return compact


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
            "items": compact_items,
        },
        "simulation": simulation_context,
        "allowed_item_ids": {int(item["item_id"]) for item in items},
    }


class BaseZAIProvider(ABC):
    source = "mock"

    @abstractmethod
    def generate_explanation(self, context: dict) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate_inventory_chat(self, context: dict) -> str:
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
        return self._generate_json_response(SYSTEM_PROMPT, model_context)

    def generate_inventory_chat(self, context: dict) -> str:
        model_context = _compact_chat_context(context)
        return self._generate_json_response(CHAT_SYSTEM_PROMPT, model_context)

    def _generate_json_response(self, system_prompt: str, model_context: dict) -> str:
        payload = {
            "model": self.model,
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
            "max_tokens": self.max_tokens,
            "reasoning_effort": "low",
            "stream": True,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(model_context),
                },
            ],
        }
        started_at = time.monotonic()
        try:
            with httpx.Client(timeout=self.timeout) as client:
                with client.stream(
                    "POST",
                    self.base_url,
                    json=payload,
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                ) as response:
                    response.raise_for_status()
                    content = self._collect_streamed_content(response)
        except Exception as exc:
            elapsed = time.monotonic() - started_at
            print(
                f"Live explanation request failed after {elapsed:.2f}s "
                f"(model={self.model}, max_tokens={self.max_tokens}): {type(exc).__name__}: {exc}"
            )
            raise
        elapsed = time.monotonic() - started_at
        print(
            f"Live explanation request completed in {elapsed:.2f}s "
            f"(model={self.model}, max_tokens={self.max_tokens})"
        )
        return content

    def _collect_streamed_content(self, response) -> str:
        chunks: list[str] = []
        for line in response.iter_lines():
            if not line or not line.startswith("data: "):
                continue
            payload = line[6:]
            if payload == "[DONE]":
                break
            try:
                event = json.loads(payload)
            except json.JSONDecodeError:
                continue
            choices = event.get("choices")
            if not choices:
                continue
            delta = choices[0].get("delta", {})
            content = delta.get("content")
            if content:
                chunks.append(content)
        combined = _strip_json_fences("".join(chunks))
        if not combined:
            raise RuntimeError("Z.AI stream completed without visible content.")
        return combined


def provider_from_env() -> BaseZAIProvider:
    mode = os.getenv("GLM_MODE", "mock").lower()
    if mode == "live":
        api_key = os.getenv("ZAI_API_KEY")
        if not api_key:
            raise RuntimeError("GLM_MODE is 'live' but ZAI_API_KEY is not set.")
        return LiveZAIProvider(api_key=api_key)
    return MockZAIProvider()
