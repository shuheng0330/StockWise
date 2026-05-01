from fastapi import HTTPException
import httpx
import json
import os
from dotenv import load_dotenv

load_dotenv()

async def extract_from_unstructured_text(raw_text: str) -> list[dict]:
    """
    Direct call to Groq using httpx (no extra dependencies)
    """
    print("=== UNSTRUCTURED EXTRACTION START ===")
    print(f"Raw text: {raw_text}")

    api_key = os.getenv("ZAI_API_KEY")
    model = os.getenv("ZAI_MODEL", "llama-3.3-70b-versatile")
    base_url = os.getenv("ZAI_BASE_URL", "https://api.groq.com/openai/v1")

    print(f"Using model: {model}")
    print(f"Base URL: {base_url}")

    if not api_key:
        raise HTTPException(status_code=500, detail="ZAI_API_KEY is not set in .env")

    prompt = f"""
You are an expert inventory assistant for Malaysian SME cafes/kiosks.
Extract every item from the messy text below.
Return ONLY a valid JSON array of objects.

Each object MUST have these exact keys:
- item_name (string)
- current_stock (number)
- unit (string)
- usage_value (number > 0)
- usage_period ("daily" or "weekly")
- lead_time_days (number >= 1)
- price_per_unit (number > 0)
- category (string)
- seasonal_factor (number 0.8-1.5)
- perishability_level ("low", "medium", or "high")
- recent_waste_percentage (number 0-100)

Rules:
- usage_value must be > 0 (estimate if unknown)
- lead_time_days at least 1 (usually 2-4 in Malaysia)
- perishability_level: "medium" if unsure
- recent_waste_percentage: 5-15 if unsure

Text:
{raw_text}

Return only the JSON array, no explanation.
"""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.1,
                    "max_tokens": 900
                }
            )

            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"].strip()

            print("✅ Groq response received")

            extracted = json.loads(content)
            if not isinstance(extracted, list):
                extracted = [extracted]

            # Safety fixes
            for item in extracted:
                if item.get("usage_value", 0) <= 0:
                    item["usage_value"] = 5.0
                    item["usage_period"] = "daily"
                if item.get("lead_time_days", 0) < 1:
                    item["lead_time_days"] = 3
                if item.get("perishability_level") not in ["low", "medium", "high"]:
                    item["perishability_level"] = "medium"
                if item.get("recent_waste_percentage") is None:
                    item["recent_waste_percentage"] = 8

            from stockwise_api.services.manual_input import normalize_manual_items
            normalized = normalize_manual_items(extracted)

            print(f"✅ Successfully extracted {len(normalized)} items")
            print("=== EXTRACTION SUCCESS ===")
            return normalized

    except Exception as e:
        print("ERROR during extraction:")
        print(str(e))
        print("=== EXTRACTION FAILED ===")
        raise HTTPException(status_code=400, detail=f"Extraction failed: {str(e)}")