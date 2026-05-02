import httpx
import json
import os
import re
from dotenv import load_dotenv

load_dotenv()

STOPWORDS = {
    'more', 'and', 'also', 'the', 'need', 'some', 'our', 'all',
    'maybe', 'just', 'now', 'left', 'low', 'up', 'down', 'delay',
    'delivery', 'supplier', 'call', 'order', 'stock', 'stok',
    'finish', 'already', 'tomorrow', 'boss', 'only', 'packet',
    'we', 'have', 'price', 'say', 'coming', 'next', 'week',
    'still', 'ok', 'today', 'day', 'per', 'liter', 'litre',
    'rm', 'to', 'at', 'in', 'is', 'it', 'of', 'or', 'as',
    'current', 'fast', 'soon', 'can', 'deliver',
}


def clean_name(name: str) -> str:
    words = name.strip().lower().split()
    while words and words[-1] in STOPWORDS:
        words.pop()
    while words and words[0] in STOPWORDS:
        words.pop(0)
    words = [w for w in words if w not in STOPWORDS]
    return ' '.join(words)


def is_valid_name(name: str) -> bool:
    name = name.strip().lower()
    if len(name) <= 2:
        return False
    words = name.split()
    if all(w in STOPWORDS for w in words):
        return False
    if words[0] in STOPWORDS:
        return False
    return True


def apply_numeric_defaults(items: list[dict]) -> list[dict]:
    for item in items:
        if item.get("usage_value") is None or item.get("usage_value") == 0:
            item["usage_value"] = 1
        if item.get("lead_time_days") is None or item.get("lead_time_days") == 0:
            item["lead_time_days"] = 1
        if item.get("price_per_unit") is None or item.get("price_per_unit") == 0:
            item["price_per_unit"] = 1
        if item.get("current_stock") is None:
            item["current_stock"] = 0
        if item.get("recent_waste_percentage") is None:
            item["recent_waste_percentage"] = 0
        if item.get("seasonal_factor") is None:
            item["seasonal_factor"] = 1.0
        if not item.get("usage_period"):
            item["usage_period"] = "daily"
        if not item.get("unit"):
            item["unit"] = "unit"
    return items


def simple_extract_fallback(text: str) -> list[dict]:
    """Regex fallback when AI model fails."""
    print("=== USING REGEX FALLBACK ===")

    items = []
    found_names = set()

    blank = lambda: {k: None for k in [
        "item_name", "current_stock", "unit", "usage_value", "usage_period",
        "lead_time_days", "price_per_unit", "category", "seasonal_factor",
        "perishability_level", "recent_waste_percentage"
    ]}

    patterns = [
        (r'have\s+(\d+(?:\.\d+)?)\s*(kg|g|l|ml|liter|litre)?\s*(\w+(?:\s+\w+)?)\s+left', 3, 1, 2),
        (r'(\w+(?:\s+\w+)?)\s+(\d+(?:\.\d+)?)\s*(kg|g|l|ml|dozen|loaf|bottle|piece|pcs|pack|packet|liter)\s+left', 1, 2, 3),
        (r'finish\s+(?:the\s+)?(\d+(?:\.\d+)?)\s*(kg|g|l|ml|pack|packet|pcs)?\s+(\w+(?:\s+\w+)?)', 3, 1, 2),
        (r'(\w+(?:\s+\w+)?)\s+(\d+(?:\.\d+)?)\s*(kg|g|l|ml|dozen|loaf|bottle|piece|pcs|pack|packet|liter)', 1, 2, 3),
        (r'(\d+(?:\.\d+)?)\s*(kg|g|l|ml|liter|litre|dozen|loaf|bottle|piece|packet)\s+(\w+(?:\s+\w+)?)', 3, 1, 2),
        (r'(\w+(?:\s+\w+)?)\s+(?:also\s+)?(?:stock\s+)?low\s+(?:only\s+)?(\d+(?:\.\d+)?)', 1, 2, None),
        (r'need\s+(?:more\s+)?(?:order\s+)?(\w+(?:\s+\w+)?)(?:\s+\d|\s*[.,]|\s*$)', 1, None, None),
        (r'(\w+(?:\s+\w+)?)\s+price\s+up.*?per\s+(kg|g|l|ml|liter|litre|unit|pack)', 1, None, 2),
        (r'\b(\w+(?:\s+\w+)?)\s+(\d+(?:\.\d+)?)\s*(bottle|piece|pcs|box|can|jar|bag|sachet|tin)\b', 1, 2, 3),
    ]

    for pattern, name_group, stock_group, unit_group in patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            try:
                name = clean_name(match.group(name_group))
            except IndexError:
                continue

            if not is_valid_name(name) or name.lower() in found_names:
                continue

            found_names.add(name.lower())
            item = blank()
            item["item_name"] = name.title()

            if stock_group:
                try:
                    val = match.group(stock_group)
                    if val:
                        item["current_stock"] = float(val)
                except (IndexError, TypeError, ValueError):
                    pass

            if unit_group:
                try:
                    val = match.group(unit_group)
                    if val:
                        item["unit"] = val.lower()
                except (IndexError, TypeError):
                    pass

            if 'finish' in match.group(0).lower():
                item["current_stock"] = 0

            items.append(item)

    # Attach orphaned stock statements to last item without stock
    orphan_stock = re.search(
        r'(?:current\s+)?stock[:\s]+(\d+(?:\.\d+)?)\s*(kg|g|l|ml|liter|litre|bottle|piece|pack|packet|dozen)?',
        text, re.IGNORECASE
    )
    if orphan_stock and items:
        for item in reversed(items):
            if not item.get("current_stock"):
                item["current_stock"] = float(orphan_stock.group(1))
                if orphan_stock.group(2):
                    item["unit"] = orphan_stock.group(2).lower()
                break

    print(f"Regex extracted {len(items)} items: {[i['item_name'] for i in items]}")
    return items


async def extract_from_unstructured_text(raw_text: str) -> list[dict]:
    print("=== UNSTRUCTURED EXTRACTION START ===")
    print(f"Raw text: {raw_text}")

    api_key = os.getenv("ZAI_API_KEY")
    glm_mode = os.getenv("GLM_MODE", "mock")
    model = os.getenv("ZAI_MODEL", "glm-5.1")

    extracted = []

    if glm_mode == "live" and api_key:
        url = "https://api.z.ai/api/paas/v4/chat/completions"

        prompt = f"""You are an inventory data extractor for a Malaysian F&B/retail business.
Extract ALL inventory items mentioned in the text. Return ONLY a valid JSON array, no markdown, no explanation.

For each item return this exact structure:
{{"item_name": "string (required)", "current_stock": number or null, "unit": "string or null (kg/g/l/ml/pcs/dozen/bottle/packet/loaf/box etc)", "usage_value": number or null, "usage_period": "daily/weekly/monthly or null", "lead_time_days": number or null, "price_per_unit": number or null, "category": "string or null", "seasonal_factor": number or null, "perishability_level": "low/medium/high or null", "recent_waste_percentage": number or null}}

Rules:
- Extract every physical inventory item mentioned
- If stock quantity is mentioned, put it in current_stock
- If item is finished/habis, set current_stock to 0
- If price is mentioned, put it in price_per_unit
- If delivery delay is mentioned, put days in lead_time_days
- Use null for any field not mentioned
- Handle Malay, English, and Manglish naturally
- "habis" = finished/out of stock
- "stok sikit/low" = low stock
- "naik harga" = price increase

Text:
{raw_text}

Return ONLY the JSON array:"""

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    url,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": model,
                        "messages": [
                            {
                                "role": "system",
                                "content": "You are a JSON extraction API for inventory management. Output ONLY valid JSON arrays. No explanation, no markdown, no reasoning."
                            },
                            {"role": "user", "content": prompt}
                        ],
                        "max_tokens": 2000,
                        "temperature": 0.1,
                    }
                )

                print("HTTP status:", response.status_code)
                print("Raw response:", response.text[:500])

                response.raise_for_status()
                data = response.json()

                choices = data.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "").strip()
                    print("AI content:", repr(content))

                    if content:
                        content = re.sub(r'```json|```', '', content).strip()
                        json_match = re.search(r'\[.*\]', content, re.DOTALL)
                        if json_match:
                            content = json_match.group(0)
                        parsed = json.loads(content)
                        extracted = parsed if isinstance(parsed, list) else [parsed]
                        print(f"AI extracted {len(extracted)} items")
                    else:
                        print("WARNING: Empty AI response, falling back to regex")
                else:
                    print("WARNING: No choices in response")

        except json.JSONDecodeError as e:
            print("JSON parse error:", e, "— falling back to regex")
        except Exception as e:
            print("ERROR:", type(e).__name__, str(e), "— falling back to regex")

    if not extracted:
        extracted = simple_extract_fallback(raw_text)

    # Schema enforcement
    required_keys = [
        "item_name", "current_stock", "unit", "usage_value",
        "usage_period", "lead_time_days", "price_per_unit",
        "category", "seasonal_factor", "perishability_level",
        "recent_waste_percentage"
    ]
    for item in extracted:
        for key in required_keys:
            if key not in item:
                item[key] = None

    extracted = apply_numeric_defaults(extracted)

    try:
        from stockwise_api.services.manual_input import normalize_manual_items
        normalized = normalize_manual_items(extracted)
    except Exception as e:
        print("Normalize failed:", str(e))
        normalized = extracted

    print(f"✅ Returned {len(normalized)} items")
    print("=== EXTRACTION COMPLETE ===")
    return normalized