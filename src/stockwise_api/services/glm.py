import json
import os
from abc import ABC, abstractmethod

import httpx


SYSTEM_PROMPT = (
    "You are StockWise, an inventory decision copilot for small cafe operators. "
    "Use only the provided inventory metrics and structured findings. Explain the recommended action clearly and briefly. "
    "Do not invent sales, profit, or supplier facts that are not in the input. Return valid JSON only."
)


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


class BaseZAIProvider(ABC):
    source = "mock"

    @abstractmethod
    def generate_explanation(self, context: dict) -> str:
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


class LiveZAIProvider(BaseZAIProvider):
    source = "live"

    def __init__(self, api_key: str, base_url: str | None = None, model: str | None = None) -> None:
        self.api_key = api_key
        self.base_url = base_url or os.getenv("ZAI_BASE_URL", "https://api.z.ai/v1/chat/completions")
        self.model = model or os.getenv("ZAI_MODEL", "glm-4.5")

    def generate_explanation(self, context: dict) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "task": "Explain the recommended inventory action for a small cafe operator.",
                            "context": context,
                        }
                    ),
                },
            ],
        }
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                self.base_url,
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            )
            response.raise_for_status()
            body = response.json()
        choices = body.get("choices", [])
        if not choices:
            raise RuntimeError("Z.AI response did not include choices.")
        message = choices[0].get("message", {})
        content = message.get("content")
        if not content:
            raise RuntimeError("Z.AI response did not include content.")
        return content


def provider_from_env() -> BaseZAIProvider:
    mode = os.getenv("GLM_MODE", "mock").lower()
    if mode == "live":
        api_key = os.getenv("ZAI_API_KEY")
        if not api_key:
            raise RuntimeError("GLM_MODE is 'live' but ZAI_API_KEY is not set.")
        return LiveZAIProvider(api_key=api_key)
    return MockZAIProvider()
