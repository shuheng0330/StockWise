from fastapi.testclient import TestClient
import json
import pytest
import time

from stockwise_api.api.app import create_app
from stockwise_api.services.glm import MockZAIProvider
from stockwise_api.store import AnalysisRecord


OWNER_CSV = (
    "item_name,current_stock,unit,usage_value,usage_period,lead_time_days,price_per_unit,category,supplier_name,perishability_level,manual_reorder_level,seasonal_factor,recent_waste_percentage\n"
    "Paneer,12,kg,14,weekly,3,450,Dairy,Supplier A,high,8,1.1,4.0\n"
    "Rice,20,kg,2,daily,2,70,Grain,Supplier B,low,,1.0, \n"
).encode()

LEGACY_CSV = (
    "Date,Item_ID,Item_Name,Category,Subcategory,Unit,Current_Stock,Reorder_Level,Daily_Usage,Lead_Time,Price_per_Unit,Supplier_Name,Seasonal_Factor,Waste_Percentage\n"
    "2025-06-10,1,Paneer,Dairy,Cheese,kg,12,8,2,3,450,Supplier A,1.1,4.0\n"
    "2025-06-11,2,Rice,Grain,Staple,kg,20,6,2,2,70,Supplier B,1.0,1.5\n"
).encode()

TEST_USER_ID = "user-1"
OTHER_TEST_USER_ID = "user-2"


def _auth_headers(user_id: str = TEST_USER_ID) -> dict[str, str]:
    return {"Authorization": f"Bearer {user_id}"}


def _test_user_resolver(token: str) -> str | None:
    return token or None


def test_upload_endpoint_returns_analysis_and_ranked_items():
    client = TestClient(create_app())
    response = client.post(
        "/api/v1/analyses",
        files={"file": ("owner_inventory.csv", OWNER_CSV, "text/csv")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["dataset_summary"]["row_count"] == 2
    assert body["dataset_summary"]["item_count"] == 2
    assert len(body["items"]) == 2
    assert any(item["recommended_action"] == "BUY_LESS" for item in body["items"])


def test_cors_allows_deployed_frontend_origin_from_env(monkeypatch):
    monkeypatch.setenv("STOCKWISE_CORS_ORIGINS", "https://stockwise.vercel.app")
    client = TestClient(create_app())

    response = client.options(
        "/api/v1/analyses",
        headers={
            "Origin": "https://stockwise.vercel.app",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://stockwise.vercel.app"


def test_upload_endpoint_accepts_legacy_dataset_csv_headers():
    client = TestClient(create_app())
    response = client.post(
        "/api/v1/analyses",
        files={"file": ("legacy_inventory.csv", LEGACY_CSV, "text/csv")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["dataset_summary"]["date_range"]["start"] == "2025-06-10"
    assert body["dataset_summary"]["date_range"]["end"] == "2025-06-11"
    assert len(body["items"]) == 2
    assert body["items"][0]["subcategory"] in {"Cheese", "Staple"}


def test_upload_endpoint_collapses_historical_csv_to_latest_item_metrics():
    historical_csv = (
        "Date,Item_ID,Item_Name,Category,Subcategory,Unit,Current_Stock,Reorder_Level,Daily_Usage,Lead_Time,Price_per_Unit,Supplier_Name,Seasonal_Factor,Waste_Percentage\n"
        "2025-06-10,1,Paneer,Dairy,Cheese,kg,12,8,2,3,450,Supplier A,1.1,4.0\n"
        "2025-06-11,1,Paneer,Dairy,Cheese,kg,9,8,3,3,450,Supplier A,1.1,4.0\n"
        "2025-06-12,1,Paneer,Dairy,Cheese,kg,5,8,4,3,450,Supplier A,1.1,4.0\n"
        "2025-06-12,2,Rice,Grain,Staple,kg,20,6,2,2,70,Supplier B,1.0,1.5\n"
    ).encode()
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/analyses",
        files={"file": ("historical_inventory.csv", historical_csv, "text/csv")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["dataset_summary"]["row_count"] == 4
    assert body["dataset_summary"]["item_count"] == 2
    assert len(body["items"]) == 2
    assert {item["item_id"] for item in body["items"]} == {1, 2}
    paneer = next(item for item in body["items"] if item["item_id"] == 1)
    assert paneer["date"] == "2025-06-12"
    assert paneer["current_stock"] == 5.0
    assert paneer["daily_usage"] == 4.0
    assert paneer["avg_usage_7d"] == 3.0
    assert paneer["trend_direction"] == "up"


def test_upload_endpoint_persists_historical_source_rows_to_supabase_store():
    class CapturingSupabaseStore:
        def __init__(self):
            self.calls = []

        def persist_observations(self, observations, **kwargs):
            self.calls.append((observations, kwargs))
            return {"import_batch_id": "import-batch-1", "successful_rows": len(observations), "failed_rows": 0}

        def create_analysis_snapshot(self, **kwargs):
            return "11111111-1111-1111-1111-111111111111"

    historical_csv = (
        "Date,Item_ID,Item_Name,Category,Subcategory,Unit,Current_Stock,Reorder_Level,Daily_Usage,Lead_Time,Price_per_Unit,Supplier_Name,Seasonal_Factor,Waste_Percentage\n"
        "2025-06-10,1,Paneer,Dairy,Cheese,kg,12,8,2,3,450,Supplier A,1.1,4.0\n"
        "2025-06-11,1,Paneer,Dairy,Cheese,kg,9,8,3,3,450,Supplier A,1.1,4.0\n"
        "2025-06-12,1,Paneer,Dairy,Cheese,kg,5,8,4,3,450,Supplier A,1.1,4.0\n"
        "2025-06-12,2,Rice,Grain,Staple,kg,20,6,2,2,70,Supplier B,1.0,1.5\n"
    ).encode()
    supabase_store = CapturingSupabaseStore()
    client = TestClient(create_app(supabase_store=supabase_store))

    response = client.post(
        "/api/v1/analyses",
        files={"file": ("historical_inventory.csv", historical_csv, "text/csv")},
    )

    assert response.status_code == 200
    observations, kwargs = supabase_store.calls[0]
    assert len(observations) == 4
    assert kwargs["source_type"] == "import"
    assert kwargs["file_name"] == "historical_inventory.csv"
    assert observations[0]["date"] == "2025-06-10"
    assert observations[2]["date"] == "2025-06-12"


def test_upload_endpoint_returns_supabase_analysis_snapshot_id_when_available():
    class SnapshotSupabaseStore:
        def persist_observations(self, observations, **kwargs):
            return {
                "import_batch_id": "import-batch-1",
                "successful_rows": len(observations),
                "failed_rows": 0,
                "latest_records_by_history_identity": {
                    "item:paneer|kg|dairy|": {
                        "item_id": "supabase-paneer",
                        "record_id": "record-paneer",
                    }
                },
            }

        def create_analysis_snapshot(self, **kwargs):
            self.snapshot_kwargs = kwargs
            return "22222222-2222-2222-2222-222222222222"

    supabase_store = SnapshotSupabaseStore()
    client = TestClient(create_app(supabase_store=supabase_store))

    response = client.post(
        "/api/v1/analyses",
        files={"file": ("owner_inventory.csv", OWNER_CSV, "text/csv")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["analysis_id"] == "22222222-2222-2222-2222-222222222222"
    assert supabase_store.snapshot_kwargs["source_type"] == "import"
    assert supabase_store.snapshot_kwargs["import_batch_id"] == "import-batch-1"
    paneer = next(
        item for item in supabase_store.snapshot_kwargs["ranked_items"]
        if item["item_name"] == "Paneer"
    )
    assert paneer["_supabase_item_id"] == "supabase-paneer"
    assert paneer["_latest_record_id"] == "record-paneer"


def test_upload_endpoint_does_not_wait_forever_for_slow_supabase_persistence(monkeypatch):
    class SlowSupabaseStore:
        def persist_observations(self, observations, **kwargs):
            time.sleep(1)
            return {"import_batch_id": "slow-import", "successful_rows": len(observations), "failed_rows": 0}

        def create_analysis_snapshot(self, **kwargs):
            pytest.fail("snapshot persistence should be skipped after observation persistence times out")

    monkeypatch.setenv("STOCKWISE_SUPABASE_OPERATION_TIMEOUT_SECONDS", "0.01")
    client = TestClient(create_app(supabase_store=SlowSupabaseStore()))

    start = time.perf_counter()
    response = client.post(
        "/api/v1/analyses",
        files={"file": ("owner_inventory.csv", OWNER_CSV, "text/csv")},
    )
    elapsed = time.perf_counter() - start

    assert response.status_code == 200
    assert elapsed < 0.5
    body = response.json()
    assert body["analysis_id"] != "slow-import"
    assert len(body["items"]) == 2


def test_simulation_endpoint_returns_updated_scenario_metrics():
    client = TestClient(create_app())
    analysis = client.post(
        "/api/v1/analyses",
        files={"file": ("owner_inventory.csv", OWNER_CSV, "text/csv")},
    ).json()

    response = client.post(
        f"/api/v1/analyses/{analysis['analysis_id']}/items/1/simulate",
        json={"simulated_order_qty": 3.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["item_id"] == 1
    assert body["simulated_order_qty"] == 3.0
    assert body["simulated_cash_outlay"] == 1350.0


def test_explanation_endpoint_returns_mock_source_by_default():
    client = TestClient(create_app(glm_provider=MockZAIProvider()))
    analysis = client.post(
        "/api/v1/analyses",
        files={"file": ("owner_inventory.csv", OWNER_CSV, "text/csv")},
    ).json()

    response = client.post(
        f"/api/v1/analyses/{analysis['analysis_id']}/items/1/explanation",
        json={},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "mock"
    assert body["item_name"] == "Paneer"


def test_explanation_endpoint_falls_back_on_malformed_provider_response():
    class BrokenMockProvider(MockZAIProvider):
        def generate_explanation(self, context):
            return "{not-json"

    app = create_app(glm_provider=BrokenMockProvider())
    client = TestClient(app)
    analysis = client.post(
        "/api/v1/analyses",
        files={"file": ("owner_inventory.csv", OWNER_CSV, "text/csv")},
    ).json()

    response = client.post(
        f"/api/v1/analyses/{analysis['analysis_id']}/items/1/explanation",
        json={},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "fallback"
    expected_action = next(
        item["recommended_action"]
        for item in analysis["items"]
        if int(item["item_id"]) == 1
    )
    assert body["recommended_action"] == expected_action


def test_explanation_endpoint_reuses_cached_response_until_refresh_is_requested():
    class CountingExplanationProvider(MockZAIProvider):
        def __init__(self):
            self.calls = 0

        def generate_explanation(self, context):
            self.calls += 1
            payload = json.loads(super().generate_explanation(context))
            payload["short_reason"] = f"Cached explanation {self.calls}."
            return json.dumps(payload)

    provider = CountingExplanationProvider()
    client = TestClient(create_app(glm_provider=provider))
    analysis = client.post(
        "/api/v1/analyses",
        files={"file": ("owner_inventory.csv", OWNER_CSV, "text/csv")},
    ).json()

    first = client.post(f"/api/v1/analyses/{analysis['analysis_id']}/items/1/explanation", json={})
    second = client.post(f"/api/v1/analyses/{analysis['analysis_id']}/items/1/explanation", json={})
    refreshed = client.post(
        f"/api/v1/analyses/{analysis['analysis_id']}/items/1/explanation?refresh=true",
        json={},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert refreshed.status_code == 200
    assert provider.calls == 2
    assert second.json()["short_reason"] == "Cached explanation 1."
    assert refreshed.json()["short_reason"] == "Cached explanation 2."


def test_explanation_endpoint_uses_in_memory_item_when_supabase_store_is_unavailable():
    class ExplodingSupabaseStore:
        def persist_observations(self, observations, **kwargs):
            pass

        def get_item(self, analysis_id, item_id):
            raise RuntimeError("network unavailable")

    client = TestClient(create_app(supabase_store=ExplodingSupabaseStore()))
    analysis = client.post(
        "/api/v1/analyses",
        files={"file": ("owner_inventory.csv", OWNER_CSV, "text/csv")},
    ).json()

    response = client.post(
        f"/api/v1/analyses/{analysis['analysis_id']}/items/1/explanation",
        json={},
    )

    assert response.status_code == 200
    assert response.json()["item_name"] == "Paneer"


def test_ai_chat_endpoint_returns_structured_mock_response():
    class MockChatProvider(MockZAIProvider):
        def generate_inventory_chat(self, context):
            return """
            {
              "scope": "analysis",
              "answer": "Restock urgent items first and buy less paneer.",
              "supporting_points": [
                "One item requires immediate restocking.",
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
                "Which items can I delay to save cash?",
                "Why is dairy risky this week?"
              ],
              "warning_flag": "Watch dairy waste closely."
            }
            """

    client = TestClient(create_app(glm_provider=MockChatProvider()))
    analysis = client.post(
        "/api/v1/analyses",
        files={"file": ("owner_inventory.csv", OWNER_CSV, "text/csv")},
    ).json()

    response = client.post(
        f"/api/v1/analyses/{analysis['analysis_id']}/ai-chat",
        json={"message": "What should I buy today?", "recent_messages": []},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "mock"
    assert body["scope"] == "analysis"
    assert body["related_items"][0]["item_name"] == "Paneer"


def test_ai_chat_endpoint_uses_simulation_scope_when_simulation_context_is_present():
    class MockChatProvider(MockZAIProvider):
        def generate_inventory_chat(self, context):
            assert context["scope"] == "simulation"
            assert context["simulation"]["item_id"] == 1
            return """
            {
              "scope": "simulation",
              "answer": "The smaller top-up reduces waste risk.",
              "supporting_points": [
                "Coverage remains above lead-time demand.",
                "Waste exposure is lower after the simulation."
              ],
              "related_items": [
                {
                  "item_id": 1,
                  "item_name": "Paneer",
                  "recommended_action": "BUY_LESS",
                  "reason": "The simulated order lowers waste exposure."
                }
              ],
              "suggested_follow_ups": [
                "Should I still order today?",
                "What changed after my simulation?"
              ],
              "warning_flag": null
            }
            """

    client = TestClient(create_app(glm_provider=MockChatProvider()))
    analysis = client.post(
        "/api/v1/analyses",
        files={"file": ("owner_inventory.csv", OWNER_CSV, "text/csv")},
    ).json()

    response = client.post(
        f"/api/v1/analyses/{analysis['analysis_id']}/ai-chat",
        json={
            "message": "What changed after my simulation?",
            "recent_messages": [],
            "simulation_context": {"item_id": 1, "simulated_order_qty": 3.0},
        },
    )

    assert response.status_code == 200
    assert response.json()["scope"] == "simulation"


def test_ai_chat_endpoint_falls_back_on_invalid_provider_response():
    class BrokenChatProvider(MockZAIProvider):
        def generate_inventory_chat(self, context):
            return "{not-json"

    client = TestClient(create_app(glm_provider=BrokenChatProvider()))
    analysis = client.post(
        "/api/v1/analyses",
        files={"file": ("owner_inventory.csv", OWNER_CSV, "text/csv")},
    ).json()

    response = client.post(
        f"/api/v1/analyses/{analysis['analysis_id']}/ai-chat",
        json={"message": "Which items can I delay to save cash?", "recent_messages": []},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "fallback"
    assert body["answer"]


def test_ai_chat_endpoint_reuses_cached_response_until_refresh_is_requested():
    class CountingChatProvider(MockZAIProvider):
        def __init__(self):
            self.calls = 0

        def generate_inventory_chat(self, context):
            self.calls += 1
            return f"""
            {{
              "scope": "analysis",
              "answer": "Cached answer {self.calls}.",
              "supporting_points": ["Call {self.calls}."],
              "related_items": [
                {{
                  "item_id": 1,
                  "item_name": "Paneer",
                  "recommended_action": "BUY_LESS",
                  "reason": "Waste risk is high."
                }}
              ],
              "suggested_follow_ups": ["Which items can I delay?"],
              "warning_flag": null
            }}
            """

    provider = CountingChatProvider()
    client = TestClient(create_app(glm_provider=provider))
    analysis = client.post(
        "/api/v1/analyses",
        files={"file": ("owner_inventory.csv", OWNER_CSV, "text/csv")},
    ).json()
    payload = {"message": "What should I buy today?", "recent_messages": []}

    first = client.post(f"/api/v1/analyses/{analysis['analysis_id']}/ai-chat", json=payload)
    second = client.post(f"/api/v1/analyses/{analysis['analysis_id']}/ai-chat", json=payload)
    refreshed = client.post(
        f"/api/v1/analyses/{analysis['analysis_id']}/ai-chat?refresh=true",
        json=payload,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert refreshed.status_code == 200
    assert provider.calls == 2
    assert second.json()["answer"] == "Cached answer 1."
    assert refreshed.json()["answer"] == "Cached answer 2."


def test_ai_chat_endpoint_politely_refuses_off_topic_questions():
    client = TestClient(create_app(glm_provider=MockZAIProvider()))
    analysis = client.post(
        "/api/v1/analyses",
        files={"file": ("owner_inventory.csv", OWNER_CSV, "text/csv")},
    ).json()

    response = client.post(
        f"/api/v1/analyses/{analysis['analysis_id']}/ai-chat",
        json={"message": "Tell me a joke about football.", "recent_messages": []},
    )

    assert response.status_code == 200
    body = response.json()
    assert "inventory" in body["answer"].lower()
    assert body["source"] == "fallback"


def test_decision_brief_endpoint_returns_structured_mock_response():
    client = TestClient(create_app(glm_provider=MockZAIProvider(), enable_supabase=False))
    analysis = client.post(
        "/api/v1/analyses",
        files={"file": ("owner_inventory.csv", OWNER_CSV, "text/csv")},
    ).json()

    response = client.get(f"/api/v1/analyses/{analysis['analysis_id']}/decision-brief")

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "mock"
    assert body["safety_status"] == "validated"
    assert body["summary"]
    assert set(body["estimated_impact"].keys()) == {"cash", "waste", "shortage"}


def test_decision_brief_endpoint_retries_then_falls_back_on_hallucinated_response():
    class HallucinatingBriefProvider(MockZAIProvider):
        def __init__(self):
            self.calls = 0

        def generate_decision_brief(self, context):
            self.calls += 1
            return """
            {
              "summary": "Buy invented coffee beans for higher profit.",
              "buy_today": [
                {
                  "item_id": 999,
                  "item_name": "Coffee Beans",
                  "recommended_action": "RESTOCK_NOW",
                  "reason": "This invented item will increase profit."
                }
              ],
              "buy_less": [],
              "delay": [],
              "estimated_impact": {"cash": "cash", "waste": "waste", "shortage": "shortage"},
              "top_tradeoffs": ["Revenue improves."],
              "recommended_order": ["Buy invented item."],
              "confidence_note": "note",
              "warning_flag": null
            }
            """

    provider = HallucinatingBriefProvider()
    client = TestClient(create_app(glm_provider=provider, enable_supabase=False))
    analysis = client.post(
        "/api/v1/analyses",
        files={"file": ("owner_inventory.csv", OWNER_CSV, "text/csv")},
    ).json()

    response = client.get(f"/api/v1/analyses/{analysis['analysis_id']}/decision-brief")

    assert response.status_code == 200
    body = response.json()
    assert provider.calls == 2
    assert body["source"] == "fallback"
    assert body["safety_status"] == "fallback_used"
    assert all(item["item_id"] != 999 for item in body["buy_today"])


def test_decision_brief_endpoint_reuses_cached_response_until_refresh_is_requested():
    class CountingBriefProvider(MockZAIProvider):
        def __init__(self):
            self.calls = 0

        def generate_decision_brief(self, context):
            self.calls += 1
            response = super().generate_decision_brief(context)
            payload = json.loads(response)
            payload["summary"] = f"Cached decision brief {self.calls}."
            return json.dumps(payload)

    provider = CountingBriefProvider()
    client = TestClient(create_app(glm_provider=provider, enable_supabase=False))
    analysis = client.post(
        "/api/v1/analyses",
        files={"file": ("owner_inventory.csv", OWNER_CSV, "text/csv")},
    ).json()

    first = client.get(f"/api/v1/analyses/{analysis['analysis_id']}/decision-brief")
    second = client.get(f"/api/v1/analyses/{analysis['analysis_id']}/decision-brief")
    refreshed = client.get(f"/api/v1/analyses/{analysis['analysis_id']}/decision-brief?refresh=true")

    assert first.status_code == 200
    assert second.status_code == 200
    assert refreshed.status_code == 200
    assert provider.calls == 2
    assert second.json()["summary"] == "Cached decision brief 1."
    assert refreshed.json()["summary"] == "Cached decision brief 2."


def test_decision_brief_endpoint_requires_authenticated_user():
    client = TestClient(create_app(auth_user_resolver=_test_user_resolver))

    response = client.get("/api/v1/analyses/some-analysis/decision-brief")

    assert response.status_code == 401


def test_ai_chat_endpoint_rejects_unauthenticated_requests():
    client = TestClient(create_app(auth_user_resolver=_test_user_resolver))

    response = client.post(
        "/api/v1/analyses/some-analysis/ai-chat",
        json={"message": "What should I buy today?", "recent_messages": []},
    )

    assert response.status_code == 401


def test_create_app_fails_fast_when_live_mode_has_no_api_key(monkeypatch):
    monkeypatch.setenv("GLM_MODE", "live")
    monkeypatch.setenv("ZAI_API_KEY", "")

    with pytest.raises(RuntimeError, match="ZAI_API_KEY"):
        create_app()


def test_manual_analysis_endpoint_accepts_owner_friendly_input():
    client = TestClient(create_app())
    payload = {
        "items": [
            {
                "item_name": "Paneer",
                "current_stock": 12.0,
                "unit": "kg",
                "usage_value": 14.0,
                "usage_period": "weekly",
                "lead_time_days": 3,
                "price_per_unit": 450.0,
                "seasonal_factor": 1.1,
                "category": "Dairy",
                "supplier_name": "Supplier A",
                "perishability_level": "high",
            },
            {
                "item_name": "Rice",
                "current_stock": 20.0,
                "unit": "kg",
                "usage_value": 2.0,
                "usage_period": "daily",
                "lead_time_days": 2,
                "price_per_unit": 70.0,
                "seasonal_factor": 1.0,
                "perishability_level": "low",
            },
        ]
    }

    response = client.post("/api/v1/manual-analyses", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["dataset_summary"]["row_count"] == 2
    assert body["dataset_summary"]["item_count"] == 2
    assert len(body["items"]) == 2
    paneer = next(item for item in body["items"] if item["item_name"] == "Paneer")
    assert paneer["daily_usage"] == 2.0
    assert paneer["waste_percentage"] > 0


def test_manual_analysis_endpoint_collapses_repeated_daily_entries_into_history():
    client = TestClient(create_app())
    payload = {
        "items": [
            {
                "date": "2025-06-10",
                "item_name": "Paneer",
                "current_stock": 12.0,
                "unit": "kg",
                "usage_value": 2.0,
                "usage_period": "daily",
                "lead_time_days": 3,
                "price_per_unit": 450.0,
                "seasonal_factor": 1.1,
                "category": "Dairy",
                "subcategory": "Cheese",
                "supplier_name": "Supplier A",
                "recent_waste_percentage": 4.0,
            },
            {
                "date": "2025-06-11",
                "item_name": "Paneer",
                "current_stock": 9.0,
                "unit": "kg",
                "usage_value": 3.0,
                "usage_period": "daily",
                "lead_time_days": 3,
                "price_per_unit": 450.0,
                "seasonal_factor": 1.1,
                "category": "Dairy",
                "subcategory": "Cheese",
                "supplier_name": "Supplier A",
                "recent_waste_percentage": 4.0,
            },
            {
                "date": "2025-06-12",
                "item_name": "Paneer",
                "current_stock": 5.0,
                "unit": "kg",
                "usage_value": 4.0,
                "usage_period": "daily",
                "lead_time_days": 3,
                "price_per_unit": 450.0,
                "seasonal_factor": 1.1,
                "category": "Dairy",
                "subcategory": "Cheese",
                "supplier_name": "Supplier A",
                "recent_waste_percentage": 4.0,
            },
        ]
    }

    response = client.post("/api/v1/manual-analyses", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["dataset_summary"]["row_count"] == 3
    assert body["dataset_summary"]["item_count"] == 1
    assert len(body["items"]) == 1
    paneer = body["items"][0]
    assert paneer["date"] == "2025-06-12"
    assert paneer["current_stock"] == 5.0
    assert paneer["daily_usage"] == 4.0
    assert paneer["avg_usage_7d"] == 3.0
    assert paneer["trend_direction"] == "up"


def test_manual_analysis_endpoint_persists_manual_source_rows_to_supabase_store():
    class CapturingSupabaseStore:
        def __init__(self):
            self.calls = []

        def persist_observations(self, observations, **kwargs):
            self.calls.append((observations, kwargs))
            return {"import_batch_id": None, "successful_rows": len(observations), "failed_rows": 0}

        def create_analysis_snapshot(self, **kwargs):
            return "33333333-3333-3333-3333-333333333333"

    supabase_store = CapturingSupabaseStore()
    client = TestClient(create_app(supabase_store=supabase_store))
    payload = {
        "items": [
            {
                "date": "2025-06-10",
                "item_name": "Paneer",
                "current_stock": 12.0,
                "unit": "kg",
                "usage_value": 2.0,
                "usage_period": "daily",
                "lead_time_days": 3,
                "price_per_unit": 450.0,
                "seasonal_factor": 1.1,
                "recent_waste_percentage": 4.0,
            },
            {
                "date": "2025-06-11",
                "item_name": "Paneer",
                "current_stock": 9.0,
                "unit": "kg",
                "usage_value": 3.0,
                "usage_period": "daily",
                "lead_time_days": 3,
                "price_per_unit": 450.0,
                "seasonal_factor": 1.1,
                "recent_waste_percentage": 4.0,
            },
        ]
    }

    response = client.post("/api/v1/manual-analyses", json=payload)

    assert response.status_code == 200
    observations, kwargs = supabase_store.calls[0]
    assert len(observations) == 2
    assert kwargs["source_type"] == "manual"
    assert kwargs["file_name"] is None
    assert observations[1]["date"] == "2025-06-11"


def test_manual_analysis_endpoint_returns_supabase_analysis_snapshot_id_when_available():
    class SnapshotSupabaseStore:
        def persist_observations(self, observations, **kwargs):
            return {"import_batch_id": None, "successful_rows": len(observations), "failed_rows": 0}

        def create_analysis_snapshot(self, **kwargs):
            self.snapshot_kwargs = kwargs
            return "44444444-4444-4444-4444-444444444444"

    supabase_store = SnapshotSupabaseStore()
    client = TestClient(create_app(supabase_store=supabase_store))
    payload = {
        "items": [
            {
                "item_name": "Paneer",
                "current_stock": 12.0,
                "unit": "kg",
                "usage_value": 14.0,
                "usage_period": "weekly",
                "lead_time_days": 3,
                "price_per_unit": 450.0,
                "seasonal_factor": 1.1,
                "perishability_level": "high",
            }
        ]
    }

    response = client.post("/api/v1/manual-analyses", json=payload)

    assert response.status_code == 200
    assert response.json()["analysis_id"] == "44444444-4444-4444-4444-444444444444"
    assert supabase_store.snapshot_kwargs["source_type"] == "manual"
    assert supabase_store.snapshot_kwargs["import_batch_id"] is None


def test_get_analysis_falls_back_to_supabase_snapshot_when_memory_is_empty():
    class ReadOnlySupabaseStore:
        def get(self, analysis_id):
            if analysis_id != "55555555-5555-5555-5555-555555555555":
                raise KeyError(analysis_id)
            return AnalysisRecord(
                dataset_summary={
                    "row_count": 1,
                    "item_count": 1,
                    "date_range": {"start": "2025-06-12", "end": "2025-06-12"},
                },
                kpi_summary={
                    "item_count": 1,
                    "restock_now_count": 1,
                    "buy_less_count": 0,
                    "high_waste_risk_count": 0,
                    "inventory_value_at_risk": 0.0,
                    "top_urgent_items": ["Paneer"],
                    "top_waste_cost_items": ["Paneer"],
                },
                items=[
                    {
                        "item_id": 1,
                        "date": "2025-06-12",
                        "item_name": "Paneer",
                        "category": "Dairy",
                        "subcategory": "Cheese",
                        "unit": "kg",
                        "supplier_name": "Supplier A",
                        "current_stock": 5.0,
                        "reorder_level": 8.0,
                        "daily_usage": 4.0,
                        "lead_time": 3,
                        "price_per_unit": 450.0,
                        "seasonal_factor": 1.1,
                        "waste_percentage": 4.0,
                        "avg_usage_7d": 3.0,
                        "trend_direction": "up",
                        "days_of_cover": 1.25,
                        "inventory_value": 2250.0,
                        "estimated_waste_cost": 90.0,
                        "lead_time_demand": 13.2,
                        "stock_gap_to_lead_demand": -8.2,
                        "reorder_urgency_score": 88,
                        "waste_risk_score": 42,
                        "recommended_action": "RESTOCK_NOW",
                    }
                ],
            )

    client = TestClient(create_app(supabase_store=ReadOnlySupabaseStore()))

    response = client.get("/api/v1/analyses/55555555-5555-5555-5555-555555555555")

    assert response.status_code == 200
    body = response.json()
    assert body["analysis_id"] == "55555555-5555-5555-5555-555555555555"
    assert body["items"][0]["item_name"] == "Paneer"


def test_get_latest_analysis_falls_back_to_latest_supabase_snapshot_when_memory_is_empty():
    class ReadOnlySupabaseStore:
        def get_latest_analysis_id(self):
            return "66666666-6666-6666-6666-666666666666"

        def get(self, analysis_id):
            if analysis_id != "66666666-6666-6666-6666-666666666666":
                raise KeyError(analysis_id)
            return AnalysisRecord(
                dataset_summary={
                    "row_count": 1,
                    "item_count": 1,
                    "date_range": {"start": "2025-06-12", "end": "2025-06-12"},
                },
                kpi_summary={
                    "item_count": 1,
                    "restock_now_count": 1,
                    "buy_less_count": 0,
                    "high_waste_risk_count": 0,
                    "inventory_value_at_risk": 0.0,
                    "top_urgent_items": ["Paneer"],
                    "top_waste_cost_items": ["Paneer"],
                },
                items=[
                    {
                        "item_id": 1,
                        "date": "2025-06-12",
                        "item_name": "Paneer",
                        "category": "Dairy",
                        "subcategory": "Cheese",
                        "unit": "kg",
                        "supplier_name": "Supplier A",
                        "current_stock": 5.0,
                        "reorder_level": 8.0,
                        "daily_usage": 4.0,
                        "lead_time": 3,
                        "price_per_unit": 450.0,
                        "seasonal_factor": 1.1,
                        "waste_percentage": 4.0,
                        "avg_usage_7d": 3.0,
                        "trend_direction": "up",
                        "days_of_cover": 1.25,
                        "inventory_value": 2250.0,
                        "estimated_waste_cost": 90.0,
                        "lead_time_demand": 13.2,
                        "stock_gap_to_lead_demand": -8.2,
                        "reorder_urgency_score": 88,
                        "waste_risk_score": 42,
                        "recommended_action": "RESTOCK_NOW",
                    }
                ],
            )

    client = TestClient(create_app(supabase_store=ReadOnlySupabaseStore()))

    response = client.get("/api/v1/analyses/latest")

    assert response.status_code == 200
    body = response.json()
    assert body["analysis_id"] == "66666666-6666-6666-6666-666666666666"
    assert body["items"][0]["item_name"] == "Paneer"


def test_simulation_endpoint_falls_back_to_supabase_snapshot_when_memory_is_empty():
    class ReadOnlySupabaseStore:
        def get(self, analysis_id):
            if analysis_id != "77777777-7777-7777-7777-777777777777":
                raise KeyError(analysis_id)
            return AnalysisRecord(
                dataset_summary={
                    "row_count": 1,
                    "item_count": 1,
                    "date_range": {"start": "2025-06-12", "end": "2025-06-12"},
                },
                kpi_summary={
                    "item_count": 1,
                    "restock_now_count": 1,
                    "buy_less_count": 0,
                    "high_waste_risk_count": 0,
                    "inventory_value_at_risk": 0.0,
                    "top_urgent_items": ["Paneer"],
                    "top_waste_cost_items": ["Paneer"],
                },
                items=[
                    {
                        "item_id": 1,
                        "date": "2025-06-12",
                        "item_name": "Paneer",
                        "category": "Dairy",
                        "subcategory": "Cheese",
                        "unit": "kg",
                        "supplier_name": "Supplier A",
                        "current_stock": 5.0,
                        "reorder_level": 8.0,
                        "daily_usage": 4.0,
                        "lead_time": 3,
                        "price_per_unit": 450.0,
                        "seasonal_factor": 1.1,
                        "waste_percentage": 4.0,
                        "avg_usage_7d": 3.0,
                        "trend_direction": "up",
                        "days_of_cover": 1.25,
                        "inventory_value": 2250.0,
                        "estimated_waste_cost": 90.0,
                        "lead_time_demand": 13.2,
                        "stock_gap_to_lead_demand": -8.2,
                        "reorder_urgency_score": 88,
                        "waste_risk_score": 42,
                        "recommended_action": "RESTOCK_NOW",
                        "_score_context": {
                            "max_daily_usage": 4.0,
                            "max_lead_time": 3,
                            "max_waste_percentage": 4.0,
                            "max_inventory_value": 2250.0,
                        },
                    }
                ],
            )

    client = TestClient(create_app(supabase_store=ReadOnlySupabaseStore()))

    response = client.post(
        "/api/v1/analyses/77777777-7777-7777-7777-777777777777/items/1/simulate",
        json={"simulated_order_qty": 3.0},
    )

    assert response.status_code == 200
    assert response.json()["item_id"] == 1


def test_explanation_endpoint_falls_back_to_supabase_snapshot_when_memory_is_empty():
    class ReadOnlySupabaseStore:
        def get(self, analysis_id):
            if analysis_id != "88888888-8888-8888-8888-888888888888":
                raise KeyError(analysis_id)
            return AnalysisRecord(
                dataset_summary={
                    "row_count": 1,
                    "item_count": 1,
                    "date_range": {"start": "2025-06-12", "end": "2025-06-12"},
                },
                kpi_summary={
                    "item_count": 1,
                    "restock_now_count": 1,
                    "buy_less_count": 0,
                    "high_waste_risk_count": 0,
                    "inventory_value_at_risk": 0.0,
                    "top_urgent_items": ["Paneer"],
                    "top_waste_cost_items": ["Paneer"],
                },
                items=[
                    {
                        "item_id": 1,
                        "date": "2025-06-12",
                        "item_name": "Paneer",
                        "category": "Dairy",
                        "subcategory": "Cheese",
                        "unit": "kg",
                        "supplier_name": "Supplier A",
                        "current_stock": 5.0,
                        "reorder_level": 8.0,
                        "daily_usage": 4.0,
                        "lead_time": 3,
                        "price_per_unit": 450.0,
                        "seasonal_factor": 1.1,
                        "waste_percentage": 4.0,
                        "avg_usage_7d": 3.0,
                        "trend_direction": "up",
                        "days_of_cover": 1.25,
                        "inventory_value": 2250.0,
                        "estimated_waste_cost": 90.0,
                        "lead_time_demand": 13.2,
                        "stock_gap_to_lead_demand": -8.2,
                        "reorder_urgency_score": 88,
                        "waste_risk_score": 42,
                        "recommended_action": "RESTOCK_NOW",
                        "_score_context": {
                            "max_daily_usage": 4.0,
                            "max_lead_time": 3,
                            "max_waste_percentage": 4.0,
                            "max_inventory_value": 2250.0,
                        },
                    }
                ],
            )

    client = TestClient(create_app(supabase_store=ReadOnlySupabaseStore()))

    response = client.post(
        "/api/v1/analyses/88888888-8888-8888-8888-888888888888/items/1/explanation",
        json={},
    )

    assert response.status_code == 200
    assert response.json()["item_name"] == "Paneer"


def test_records_endpoint_returns_current_analysis_items():
    client = TestClient(create_app())
    payload = {
        "items": [
            {
                "item_name": "Eggs",
                "current_stock": 30.0,
                "unit": "pieces",
                "usage_value": 7.0,
                "usage_period": "daily",
                "lead_time_days": 2,
                "price_per_unit": 0.6,
                "seasonal_factor": 1.0,
                "perishability_level": "medium",
            }
        ]
    }
    analysis = client.post("/api/v1/manual-analyses", json=payload).json()

    response = client.get(f"/api/v1/analyses/{analysis['analysis_id']}/records")

    assert response.status_code == 200
    body = response.json()
    assert body["analysis_id"] == analysis["analysis_id"]
    assert len(body["items"]) == 1
    assert body["items"][0]["item_name"] == "Eggs"


def test_update_record_endpoint_recomputes_item_and_kpis():
    client = TestClient(create_app())
    payload = {
        "items": [
            {
                "item_name": "Milk",
                "current_stock": 8.0,
                "unit": "litre",
                "usage_value": 4.0,
                "usage_period": "daily",
                "lead_time_days": 3,
                "price_per_unit": 8.0,
                "seasonal_factor": 1.1,
                "perishability_level": "high",
            }
        ]
    }
    analysis = client.post("/api/v1/manual-analyses", json=payload).json()

    response = client.patch(
        f"/api/v1/analyses/{analysis['analysis_id']}/items/1",
        json={"current_stock": 20.0, "usage_value": 2.0, "usage_period": "daily"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["item_name"] == "Milk"
    assert body["current_stock"] == 20.0
    assert body["daily_usage"] == 2.0
    assert body["recommended_action"] in {
        "RESTOCK_NOW",
        "BUY_LESS",
        "DELAY_PURCHASE",
        "MONITOR_CLOSELY",
    }


def test_update_record_endpoint_allows_date_edit():
    client = TestClient(create_app())
    payload = {
        "items": [
            {
                "item_name": "Milk",
                "current_stock": 8.0,
                "unit": "litre",
                "usage_value": 4.0,
                "usage_period": "daily",
                "lead_time_days": 3,
                "price_per_unit": 8.0,
                "seasonal_factor": 1.1,
                "perishability_level": "high",
            }
        ]
    }
    analysis = client.post("/api/v1/manual-analyses", json=payload).json()

    response = client.patch(
        f"/api/v1/analyses/{analysis['analysis_id']}/items/1",
        json={"date": "2026-04-24"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["last_updated"] == "2026-04-24"


def test_delete_record_endpoint_removes_item_and_updates_analysis():
    client = TestClient(create_app())
    payload = {
        "items": [
            {
                "item_name": "Tomato",
                "current_stock": 10.0,
                "unit": "kg",
                "usage_value": 2.0,
                "usage_period": "daily",
                "lead_time_days": 2,
                "price_per_unit": 40.0,
                "seasonal_factor": 1.0,
                "perishability_level": "medium",
            },
            {
                "item_name": "Onion",
                "current_stock": 9.0,
                "unit": "kg",
                "usage_value": 1.0,
                "usage_period": "daily",
                "lead_time_days": 2,
                "price_per_unit": 10.0,
                "seasonal_factor": 1.0,
                "perishability_level": "low",
            },
        ]
    }
    analysis = client.post("/api/v1/manual-analyses", json=payload).json()

    response = client.delete(f"/api/v1/analyses/{analysis['analysis_id']}/items/1")

    assert response.status_code == 200
    body = response.json()
    assert body["analysis_id"] == analysis["analysis_id"]
    assert len(body["items"]) == 1
    assert body["items"][0]["item_name"] == "Onion"


def test_update_historical_record_preserves_source_observation_count():
    historical_csv = (
        "Date,Item_ID,Item_Name,Category,Subcategory,Unit,Current_Stock,Reorder_Level,Daily_Usage,Lead_Time,Price_per_Unit,Supplier_Name,Seasonal_Factor,Waste_Percentage\n"
        "2025-06-10,1,Paneer,Dairy,Cheese,kg,12,8,2,3,450,Supplier A,1.1,4.0\n"
        "2025-06-11,1,Paneer,Dairy,Cheese,kg,9,8,3,3,450,Supplier A,1.1,4.0\n"
        "2025-06-12,1,Paneer,Dairy,Cheese,kg,5,8,4,3,450,Supplier A,1.1,4.0\n"
        "2025-06-12,2,Rice,Grain,Staple,kg,20,6,2,2,70,Supplier B,1.0,1.5\n"
    ).encode()
    client = TestClient(create_app())
    analysis = client.post(
        "/api/v1/analyses",
        files={"file": ("historical_inventory.csv", historical_csv, "text/csv")},
    ).json()

    response = client.patch(
        f"/api/v1/analyses/{analysis['analysis_id']}/items/1",
        json={"current_stock": 6.0},
    )
    records = client.get(f"/api/v1/analyses/{analysis['analysis_id']}/records").json()

    assert response.status_code == 200
    assert records["dataset_summary"]["row_count"] == 4
    assert records["dataset_summary"]["item_count"] == 2


def test_delete_historical_record_removes_source_observations_for_group():
    historical_csv = (
        "Date,Item_ID,Item_Name,Category,Subcategory,Unit,Current_Stock,Reorder_Level,Daily_Usage,Lead_Time,Price_per_Unit,Supplier_Name,Seasonal_Factor,Waste_Percentage\n"
        "2025-06-10,1,Paneer,Dairy,Cheese,kg,12,8,2,3,450,Supplier A,1.1,4.0\n"
        "2025-06-11,1,Paneer,Dairy,Cheese,kg,9,8,3,3,450,Supplier A,1.1,4.0\n"
        "2025-06-12,1,Paneer,Dairy,Cheese,kg,5,8,4,3,450,Supplier A,1.1,4.0\n"
        "2025-06-12,2,Rice,Grain,Staple,kg,20,6,2,2,70,Supplier B,1.0,1.5\n"
    ).encode()
    client = TestClient(create_app())
    analysis = client.post(
        "/api/v1/analyses",
        files={"file": ("historical_inventory.csv", historical_csv, "text/csv")},
    ).json()

    response = client.delete(f"/api/v1/analyses/{analysis['analysis_id']}/items/2")

    assert response.status_code == 200
    body = response.json()
    assert body["dataset_summary"]["row_count"] == 3
    assert body["dataset_summary"]["item_count"] == 1


def test_manual_analysis_endpoint_rejects_missing_required_score_inputs():
    client = TestClient(create_app())
    payload = {
        "items": [
            {
                "item_name": "Paneer",
                "current_stock": 12.0,
                "unit": "kg",
                "usage_value": 14.0,
                "usage_period": "weekly",
                "lead_time_days": 3,
            }
        ]
    }

    response = client.post("/api/v1/manual-analyses", json=payload)

    assert response.status_code == 422


def test_upload_endpoint_requires_authenticated_user():
    client = TestClient(create_app(auth_user_resolver=_test_user_resolver))

    response = client.post(
        "/api/v1/analyses",
        files={"file": ("owner_inventory.csv", OWNER_CSV, "text/csv")},
    )

    assert response.status_code == 401


def test_manual_analysis_after_csv_returns_merged_user_history_snapshot():
    class MemorySupabaseStore:
        def __init__(self):
            self.persisted = []
            self.snapshot_calls = []

        def persist_observations(self, observations, **kwargs):
            self.persisted.extend([{**row, "_created_by": kwargs["created_by"]} for row in observations])
            return {
                "import_batch_id": None if kwargs["source_type"] == "manual" else "import-batch-1",
                "successful_rows": len(observations),
                "failed_rows": 0,
            }

        def list_user_observations(self, user_id):
            return [
                {
                    key: value
                    for key, value in row.items()
                    if not key.startswith("_") and key != "item_id"
                }
                for row in self.persisted
                if row["_created_by"] == user_id
            ]

        def create_analysis_snapshot(self, **kwargs):
            self.snapshot_calls.append(kwargs)
            return f"snapshot-{len(self.snapshot_calls)}"

        def get(self, analysis_id, user_id=None):
            call_index = int(str(analysis_id).split("-")[-1]) - 1
            ranked_items = self.snapshot_calls[call_index]["ranked_items"]
            return AnalysisRecord(
                dataset_summary=self.snapshot_calls[call_index]["dataset_summary"],
                kpi_summary={
                    "item_count": len(ranked_items),
                    "restock_now_count": sum(
                        1 for item in ranked_items if item["recommended_action"] == "RESTOCK_NOW"
                    ),
                    "buy_less_count": sum(
                        1 for item in ranked_items if item["recommended_action"] == "BUY_LESS"
                    ),
                    "high_waste_risk_count": sum(
                        1 for item in ranked_items if item["waste_risk_score"] >= 70
                    ),
                    "inventory_value_at_risk": sum(
                        item["estimated_waste_cost"] for item in ranked_items
                    ),
                    "top_urgent_items": [item["item_name"] for item in ranked_items[:3]],
                    "top_waste_cost_items": [item["item_name"] for item in ranked_items[:3]],
                },
                items=ranked_items,
            )

    supabase_store = MemorySupabaseStore()
    client = TestClient(
        create_app(supabase_store=supabase_store, auth_user_resolver=_test_user_resolver)
    )

    upload_response = client.post(
        "/api/v1/analyses",
        files={"file": ("legacy_inventory.csv", LEGACY_CSV, "text/csv")},
        headers=_auth_headers(),
    )
    manual_response = client.post(
        "/api/v1/manual-analyses",
        json={
            "items": [
                {
                    "date": "2025-06-12",
                    "item_name": "Paneer",
                    "current_stock": 5.0,
                    "unit": "kg",
                    "usage_value": 4.0,
                    "usage_period": "daily",
                    "lead_time_days": 3,
                    "price_per_unit": 450.0,
                    "seasonal_factor": 1.1,
                    "category": "Dairy",
                    "subcategory": "Cheese",
                    "supplier_name": "Supplier A",
                    "recent_waste_percentage": 4.0,
                }
            ]
        },
        headers=_auth_headers(),
    )

    assert upload_response.status_code == 200
    assert manual_response.status_code == 200
    assert manual_response.json()["dataset_summary"]["row_count"] == 3
    assert manual_response.json()["dataset_summary"]["item_count"] == 2
    assert {item["item_name"] for item in manual_response.json()["items"]} == {"Paneer", "Rice"}


def test_get_latest_analysis_is_scoped_to_authenticated_user():
    class ReadOnlySupabaseStore:
        def get_latest_analysis_id(self, user_id):
            assert user_id == TEST_USER_ID
            return "latest-for-user-1"

        def get(self, analysis_id, user_id=None):
            assert analysis_id == "latest-for-user-1"
            assert user_id == TEST_USER_ID
            return AnalysisRecord(
                dataset_summary={
                    "row_count": 1,
                    "item_count": 1,
                    "date_range": {"start": "2025-06-12", "end": "2025-06-12"},
                },
                kpi_summary={
                    "item_count": 1,
                    "restock_now_count": 1,
                    "buy_less_count": 0,
                    "high_waste_risk_count": 0,
                    "inventory_value_at_risk": 0.0,
                    "top_urgent_items": ["Paneer"],
                    "top_waste_cost_items": ["Paneer"],
                },
                items=[
                    {
                        "item_id": 1,
                        "date": "2025-06-12",
                        "item_name": "Paneer",
                        "category": "Dairy",
                        "subcategory": "Cheese",
                        "unit": "kg",
                        "supplier_name": "Supplier A",
                        "current_stock": 5.0,
                        "reorder_level": 8.0,
                        "daily_usage": 4.0,
                        "lead_time": 3,
                        "price_per_unit": 450.0,
                        "seasonal_factor": 1.1,
                        "waste_percentage": 4.0,
                        "avg_usage_7d": 3.0,
                        "trend_direction": "up",
                        "days_of_cover": 1.25,
                        "inventory_value": 2250.0,
                        "estimated_waste_cost": 90.0,
                        "lead_time_demand": 13.2,
                        "stock_gap_to_lead_demand": -8.2,
                        "reorder_urgency_score": 88,
                        "waste_risk_score": 42,
                        "recommended_action": "RESTOCK_NOW",
                    }
                ],
            )

    client = TestClient(
        create_app(supabase_store=ReadOnlySupabaseStore(), auth_user_resolver=_test_user_resolver)
    )

    response = client.get("/api/v1/analyses/latest", headers=_auth_headers())

    assert response.status_code == 200
    assert response.json()["analysis_id"] == "latest-for-user-1"


def test_get_latest_analysis_falls_back_to_in_memory_when_supabase_latest_is_deleted():
    class ReadOnlySupabaseStore:
        def get_latest_analysis_id(self, user_id=None):
            return "deleted-analysis-id"

        def get(self, analysis_id, user_id=None):
            raise KeyError(analysis_id)

    app = create_app(supabase_store=ReadOnlySupabaseStore(), auth_user_resolver=_test_user_resolver)
    app.state.store.create(
        analysis_id="memory-analysis-id",
        owner_id=TEST_USER_ID,
        dataset_summary={
            "row_count": 1,
            "item_count": 1,
            "date_range": {"start": "2025-06-12", "end": "2025-06-12"},
        },
        kpi_summary={
            "item_count": 1,
            "restock_now_count": 1,
            "buy_less_count": 0,
            "high_waste_risk_count": 0,
            "inventory_value_at_risk": 0.0,
            "top_urgent_items": ["Paneer"],
            "top_waste_cost_items": ["Paneer"],
        },
        items=[
            {
                "item_id": 1,
                "date": "2025-06-12",
                "item_name": "Paneer",
                "category": "Dairy",
                "subcategory": "Cheese",
                "unit": "kg",
                "supplier_name": "Supplier A",
                "current_stock": 5.0,
                "reorder_level": 8.0,
                "daily_usage": 4.0,
                "lead_time": 3,
                "price_per_unit": 450.0,
                "seasonal_factor": 1.1,
                "waste_percentage": 4.0,
                "avg_usage_7d": 3.0,
                "trend_direction": "up",
                "days_of_cover": 1.25,
                "inventory_value": 2250.0,
                "estimated_waste_cost": 90.0,
                "lead_time_demand": 13.2,
                "stock_gap_to_lead_demand": -8.2,
                "reorder_urgency_score": 88,
                "waste_risk_score": 42,
                "recommended_action": "RESTOCK_NOW",
            }
        ],
    )

    client = TestClient(app)
    response = client.get("/api/v1/analyses/latest", headers=_auth_headers())

    assert response.status_code == 200
    assert response.json()["analysis_id"] == "memory-analysis-id"


def test_user_cannot_load_another_users_analysis():
    class ReadOnlySupabaseStore:
        def get(self, analysis_id, user_id=None):
            raise KeyError(f"{analysis_id}:{user_id}")

    client = TestClient(
        create_app(supabase_store=ReadOnlySupabaseStore(), auth_user_resolver=_test_user_resolver)
    )

    response = client.get(
        "/api/v1/analyses/55555555-5555-5555-5555-555555555555",
        headers=_auth_headers(OTHER_TEST_USER_ID),
    )

    assert response.status_code == 404
