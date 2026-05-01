from fastapi import HTTPException
from groq import Groq
import json
import os
from dotenv import load_dotenv

load_dotenv()

async def extract_from_unstructured_text(raw_text: str) -> list[dict]:
    """
    FINAL VERSION - very strict prompt + full safety defaults
    """
    print("=== UNSTRUCTURED EXTRACTION START ===")
    print(f"Raw text: {raw_text}")

    api_key = os.getenv("ZAI_API_KEY")
    model = os.getenv("ZAI_MODEL", "llama-3.3-70b-versatile")

    print(f"Using model: {model}")

    client = Groq(api_key=api_key)

    prompt = f"""
You are an inventory extraction assistant for Malaysian SME cafes/kiosks.
Extract every item from the messy text below.
Return ONLY a valid JSON array of objects.

Each object MUST have these exact keys with valid values:

- item_name (string)
- current_stock (number >= 0)
- unit (string)
- usage_value (number > 0)
- usage_period ("daily" or "weekly")
- lead_time_days (number >= 1)                  ← MUST be at least 1
- price_per_unit (number > 0)
- category (string)
- seasonal_factor (number 0.8-1.5)
- perishability_level (string: "low", "medium", or "high")
- recent_waste_percentage (number 0-100)

Rules (very important):
- If usage_value unknown → use 5
- If lead_time_days unknown → use 3
- If perishability_level unknown → use "medium"
- If recent_waste_percentage unknown → use 5

Text:
{raw_text}

Return only the JSON array, no explanation, no extra text.
"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=800,
        )

        content = response.choices[0].message.content.strip()
        print("Groq raw response received")

        extracted = json.loads(content)
        if not isinstance(extracted, list):
            extracted = [extracted]

        print("Raw extracted JSON before safety fix:")
        print(json.dumps(extracted, indent=2))

        # Strong safety fixes
        for item in extracted:
            if item.get("usage_value", 0) <= 0:
                item["usage_value"] = 5.0
                item["usage_period"] = "daily"
            if item.get("lead_time_days", 0) < 1:
                item["lead_time_days"] = 3
            if item.get("perishability_level") not in ["low", "medium", "high"]:
                item["perishability_level"] = "medium"
            if item.get("recent_waste_percentage") is None:
                item["recent_waste_percentage"] = 5

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