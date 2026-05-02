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


def test_health_reports_history_snapshot_write_mode():
    client = TestClient(create_app(supabase_store=object()))

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["supabase_store_ready"] is True
    assert body["history_snapshot_table"] == "analysis_source_observations"
    assert body["snapshot_write_mode"] == "required"


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


def test_upload_endpoint_persists_snapshot_when_observation_persistence_times_out(monkeypatch):
    class SlowSupabaseStore:
        def __init__(self):
            self.snapshot_kwargs = None

        def persist_observations(self, observations, **kwargs):
            time.sleep(1)
            return {"import_batch_id": "slow-import", "successful_rows": len(observations), "failed_rows": 0}

        def create_analysis_snapshot(self, **kwargs):
            self.snapshot_kwargs = kwargs
            return "33333333-3333-3333-3333-333333333333"

    monkeypatch.setenv("STOCKWISE_SUPABASE_OPERATION_TIMEOUT_SECONDS", "0.01")
    supabase_store = SlowSupabaseStore()
    client = TestClient(create_app(supabase_store=supabase_store))

    start = time.perf_counter()
    response = client.post(
        "/api/v1/analyses",
        files={"file": ("owner_inventory.csv", OWNER_CSV, "text/csv")},
    )
    elapsed = time.perf_counter() - start

    assert response.status_code == 200
    assert elapsed < 0.5
    body = response.json()
    assert body["analysis_id"] == "33333333-3333-3333-3333-333333333333"
    assert len(body["items"]) == 2
    assert supabase_store.snapshot_kwargs["import_batch_id"] is None
    assert len(supabase_store.snapshot_kwargs["source_observations"]) == 2


def test_upload_endpoint_waits_for_analysis_snapshot_even_when_supabase_timeout_is_short(monkeypatch):
    class SlowSnapshotSupabaseStore:
        def persist_observations(self, observations, **kwargs):
            return {"import_batch_id": "import-batch-1", "successful_rows": len(observations), "failed_rows": 0}

        def create_analysis_snapshot(self, **kwargs):
            time.sleep(0.05)
            return "44444444-4444-4444-4444-444444444444"

    monkeypatch.setenv("STOCKWISE_SUPABASE_OPERATION_TIMEOUT_SECONDS", "0.01")
    client = TestClient(create_app(supabase_store=SlowSnapshotSupabaseStore()))

    response = client.post(
        "/api/v1/analyses",
        files={"file": ("owner_inventory.csv", OWNER_CSV, "text/csv")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["analysis_id"] == "44444444-4444-4444-4444-444444444444"


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


def test_tradeoff_verdict_endpoint_returns_structured_mock_response():
    class VerdictProvider(MockZAIProvider):
        def generate_tradeoff_verdict(self, context):
            return json.dumps(
                {
                    "verdict": "Cash-heavy but safe",
                    "reason": "The simulation lowers shortage pressure but commits cash today.",
                    "confidence_note": "Based on server-computed simulation metrics.",
                }
            )

    client = TestClient(create_app(glm_provider=VerdictProvider()))
    analysis = client.post(
        "/api/v1/analyses",
        files={"file": ("owner_inventory.csv", OWNER_CSV, "text/csv")},
    ).json()

    response = client.post(
        f"/api/v1/analyses/{analysis['analysis_id']}/items/1/tradeoff-verdict",
        json={"simulated_order_qty": 3.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "mock"
    assert body["verdict"] == "Cash-heavy but safe"
    assert body["safety_status"] == "validated"


def test_tradeoff_verdict_endpoint_falls_back_on_malformed_provider_response():
    class BrokenVerdictProvider(MockZAIProvider):
        def generate_tradeoff_verdict(self, context):
            return "{not-json"

    client = TestClient(create_app(glm_provider=BrokenVerdictProvider()))
    analysis = client.post(
        "/api/v1/analyses",
        files={"file": ("owner_inventory.csv", OWNER_CSV, "text/csv")},
    ).json()

    response = client.post(
        f"/api/v1/analyses/{analysis['analysis_id']}/items/1/tradeoff-verdict",
        json={"simulated_order_qty": 3.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "fallback"
    assert body["verdict"] in {
        "Worth it",
        "Too much stock",
        "Cash-heavy but safe",
        "Try smaller quantity",
        "Good emergency reorder",
    }


def test_tradeoff_verdict_endpoint_falls_back_when_live_verdict_conflicts_with_simulation():
    class ConflictingVerdictProvider(MockZAIProvider):
        def generate_tradeoff_verdict(self, context):
            return json.dumps(
                {
                    "verdict": "Try smaller quantity",
                    "reason": "Ordering this amount extends coverage beyond the best level.",
                    "confidence_note": "Based on simulated metrics.",
                }
            )

    low_stock_csv = (
        "item_name,current_stock,unit,usage_value,usage_period,lead_time_days,price_per_unit,"
        "category,supplier_name,perishability_level,manual_reorder_level,seasonal_factor,recent_waste_percentage\n"
        "Milk,1,liter,10,daily,3,5,Dairy,Supplier A,low,30,1.0,1.0\n"
    )
    client = TestClient(create_app(glm_provider=ConflictingVerdictProvider()))
    analysis = client.post(
        "/api/v1/analyses",
        files={"file": ("low_stock.csv", low_stock_csv, "text/csv")},
    ).json()

    response = client.post(
        f"/api/v1/analyses/{analysis['analysis_id']}/items/1/tradeoff-verdict",
        json={"simulated_order_qty": 2.0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "fallback"
    assert body["verdict"] == "Good emergency reorder"
    assert "still needs restocking" in body["reason"]


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


def test_repeated_csv_uploads_without_supabase_append_to_session_history():
    next_month_csv = (
        "Date,Item_ID,Item_Name,Category,Subcategory,Unit,Current_Stock,Reorder_Level,Daily_Usage,Lead_Time,Price_per_Unit,Supplier_Name,Seasonal_Factor,Waste_Percentage\n"
        "2025-07-10,1,Paneer,Dairy,Cheese,kg,4,8,5,3,450,Supplier A,1.1,4.0\n"
        "2025-07-10,2,Rice,Grain,Staple,kg,18,6,3,2,70,Supplier B,1.0,1.5\n"
    ).encode()
    client = TestClient(create_app())

    first_response = client.post(
        "/api/v1/analyses",
        files={"file": ("june_inventory.csv", LEGACY_CSV, "text/csv")},
    )
    second_response = client.post(
        "/api/v1/analyses",
        files={"file": ("july_inventory.csv", next_month_csv, "text/csv")},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    body = second_response.json()
    assert body["dataset_summary"]["row_count"] == 4
    assert body["dataset_summary"]["item_count"] == 2
    assert body["dataset_summary"]["date_range"] == {
        "start": "2025-06-10",
        "end": "2025-07-10",
    }
    paneer = next(item for item in body["items"] if item["item_id"] == 1)
    assert paneer["date"] == "2025-07-10"
    assert paneer["current_stock"] == 4.0
    assert paneer["avg_usage_7d"] == 3.5


def test_csv_upload_keeps_previous_snapshot_history_when_supabase_history_is_partial():
    next_month_csv = (
        "Date,Item_ID,Item_Name,Category,Subcategory,Unit,Current_Stock,Reorder_Level,Daily_Usage,Lead_Time,Price_per_Unit,Supplier_Name,Seasonal_Factor,Waste_Percentage\n"
        "2025-07-10,1,Paneer,Dairy,Cheese,kg,4,8,5,3,450,Supplier A,1.1,4.0\n"
        "2025-07-10,2,Rice,Grain,Staple,kg,18,6,3,2,70,Supplier B,1.0,1.5\n"
    ).encode()

    class PartialHistorySupabaseStore:
        def __init__(self):
            self.persisted = []
            self.new_only = False
            self.snapshot_count = 0

        def persist_observations(self, observations, **kwargs):
            self.persisted.extend(dict(row) for row in observations)
            return {
                "import_batch_id": f"batch-{self.snapshot_count + 1}",
                "successful_rows": len(observations),
                "failed_rows": 0,
            }

        def list_user_observations(self, user_id):
            if self.new_only:
                return [row for row in self.persisted if row.get("date") == "2025-07-10"]
            return list(self.persisted)

        def create_analysis_snapshot(self, **kwargs):
            self.snapshot_count += 1
            return f"snapshot-{self.snapshot_count}"

    supabase_store = PartialHistorySupabaseStore()
    app = create_app(supabase_store=supabase_store, auth_user_resolver=_test_user_resolver)
    client = TestClient(app)

    first_response = client.post(
        "/api/v1/analyses",
        files={"file": ("june_inventory.csv", LEGACY_CSV, "text/csv")},
        headers=_auth_headers(),
    )
    supabase_store.new_only = True
    app.state.observation_history = {}
    second_response = client.post(
        "/api/v1/analyses",
        files={"file": ("july_inventory.csv", next_month_csv, "text/csv")},
        headers=_auth_headers(),
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    body = second_response.json()
    assert body["dataset_summary"]["row_count"] == 4
    assert body["dataset_summary"]["date_range"] == {
        "start": "2025-06-10",
        "end": "2025-07-10",
    }


def test_records_endpoint_includes_all_uploaded_source_observations():
    next_month_csv = (
        "Date,Item_ID,Item_Name,Category,Subcategory,Unit,Current_Stock,Reorder_Level,Daily_Usage,Lead_Time,Price_per_Unit,Supplier_Name,Seasonal_Factor,Waste_Percentage\n"
        "2025-07-10,1,Paneer,Dairy,Cheese,kg,4,8,5,3,450,Supplier A,1.1,4.0\n"
        "2025-07-10,2,Rice,Grain,Staple,kg,18,6,3,2,70,Supplier B,1.0,1.5\n"
    ).encode()
    client = TestClient(create_app())

    client.post(
        "/api/v1/analyses",
        files={"file": ("june_inventory.csv", LEGACY_CSV, "text/csv")},
    )
    analysis = client.post(
        "/api/v1/analyses",
        files={"file": ("july_inventory.csv", next_month_csv, "text/csv")},
    ).json()

    response = client.get(f"/api/v1/analyses/{analysis['analysis_id']}/records")

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    assert len(body["source_observations"]) == 4
    assert [row["date"] for row in body["source_observations"]] == [
        "2025-06-10",
        "2025-06-11",
        "2025-07-10",
        "2025-07-10",
    ]
    assert [row["current_stock"] for row in body["source_observations"]] == [
        12.0,
        20.0,
        4.0,
        18.0,
    ]


def test_csv_upload_merges_arbitrary_date_ranges_and_sorts_by_observation_date():
    october_csv = (
        "Date,Item_ID,Item_Name,Category,Subcategory,Unit,Current_Stock,Reorder_Level,Daily_Usage,Lead_Time,Price_per_Unit,Supplier_Name,Seasonal_Factor,Waste_Percentage\n"
        "2025-10-01,1,Paneer,Dairy,Cheese,kg,9,8,4,3,450,Supplier A,1.1,4.0\n"
        "2025-10-31,1,Paneer,Dairy,Cheese,kg,3,8,7,3,450,Supplier A,1.1,4.0\n"
        "2025-10-31,2,Rice,Grain,Staple,kg,18,6,3,2,70,Supplier B,1.0,1.5\n"
    ).encode()
    june_to_september_csv = (
        "Date,Item_ID,Item_Name,Category,Subcategory,Unit,Current_Stock,Reorder_Level,Daily_Usage,Lead_Time,Price_per_Unit,Supplier_Name,Seasonal_Factor,Waste_Percentage\n"
        "2025-06-10,1,Paneer,Dairy,Cheese,kg,12,8,2,3,450,Supplier A,1.1,4.0\n"
        "2025-09-17,1,Paneer,Dairy,Cheese,kg,7,8,5,3,450,Supplier A,1.1,4.0\n"
        "2025-09-17,2,Rice,Grain,Staple,kg,20,6,2,2,70,Supplier B,1.0,1.5\n"
    ).encode()
    client = TestClient(create_app())

    october_response = client.post(
        "/api/v1/analyses",
        files={"file": ("october_inventory.csv", october_csv, "text/csv")},
    )
    combined_response = client.post(
        "/api/v1/analyses",
        files={"file": ("june_to_september_inventory.csv", june_to_september_csv, "text/csv")},
    )

    assert october_response.status_code == 200
    assert combined_response.status_code == 200
    body = combined_response.json()
    assert body["dataset_summary"]["row_count"] == 6
    assert body["dataset_summary"]["item_count"] == 2
    assert body["dataset_summary"]["date_range"] == {
        "start": "2025-06-10",
        "end": "2025-10-31",
    }
    paneer = next(item for item in body["items"] if item["item_id"] == 1)
    assert paneer["date"] == "2025-10-31"
    assert paneer["current_stock"] == 3.0
    assert paneer["avg_usage_7d"] == 4.5
    assert paneer["trend_direction"] == "up"


def test_reuploading_same_csv_does_not_duplicate_identical_source_rows():
    client = TestClient(create_app())

    first_response = client.post(
        "/api/v1/analyses",
        files={"file": ("june_inventory.csv", LEGACY_CSV, "text/csv")},
    )
    second_response = client.post(
        "/api/v1/analyses",
        files={"file": ("june_inventory_again.csv", LEGACY_CSV, "text/csv")},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    body = second_response.json()
    assert body["dataset_summary"]["row_count"] == 2
    assert body["dataset_summary"]["item_count"] == 2
    assert body["dataset_summary"]["date_range"] == {
        "start": "2025-06-10",
        "end": "2025-06-11",
    }
    records = client.get(f"/api/v1/analyses/{body['analysis_id']}/records").json()
    assert len(records["source_observations"]) == 2


def test_csv_upload_uses_previous_item_snapshot_as_history_fallback_when_raw_rows_are_missing():
    october_csv = (
        "Date,Item_ID,Item_Name,Category,Subcategory,Unit,Current_Stock,Reorder_Level,Daily_Usage,Lead_Time,Price_per_Unit,Supplier_Name,Seasonal_Factor,Waste_Percentage\n"
        "2025-10-31,1,Paneer,Dairy,Cheese,kg,3,8,7,3,450,Supplier A,1.1,4.0\n"
        "2025-10-31,2,Rice,Grain,Staple,kg,18,6,3,2,70,Supplier B,1.0,1.5\n"
    ).encode()

    previous_item = {
        "item_id": 1,
        "date": "2025-09-17",
        "item_name": "Paneer",
        "category": "Dairy",
        "subcategory": "Cheese",
        "unit": "kg",
        "supplier_name": "Supplier A",
        "current_stock": 7.0,
        "reorder_level": 8.0,
        "daily_usage": 5.0,
        "lead_time": 3,
        "price_per_unit": 450.0,
        "seasonal_factor": 1.1,
        "waste_percentage": 4.0,
        "avg_usage_7d": 3.0,
        "trend_direction": "up",
        "days_of_cover": 1.4,
        "inventory_value": 3150.0,
        "estimated_waste_cost": 126.0,
        "lead_time_demand": 16.5,
        "stock_gap_to_lead_demand": -9.5,
        "reorder_urgency_score": 70,
        "waste_risk_score": 20,
        "recommended_action": "RESTOCK_NOW",
    }

    class SnapshotOnlyHistoryStore:
        def __init__(self):
            self.snapshot_calls = []

        def get_latest_analysis_id(self, user_id):
            return "previous-analysis"

        def get(self, analysis_id, user_id=None):
            if analysis_id != "previous-analysis":
                raise KeyError(analysis_id)
            return AnalysisRecord(
                dataset_summary={
                    "row_count": 1000,
                    "item_count": 10,
                    "date_range": {"start": "2025-06-10", "end": "2025-09-17"},
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
                items=[previous_item],
                source_observations=[],
            )

        def persist_observations(self, observations, **kwargs):
            return {
                "import_batch_id": "october-batch",
                "successful_rows": len(observations),
                "failed_rows": 0,
            }

        def list_user_observations(self, user_id):
            return []

        def create_analysis_snapshot(self, **kwargs):
            self.snapshot_calls.append(kwargs)
            return "new-analysis"

    app = create_app(
        supabase_store=SnapshotOnlyHistoryStore(),
        auth_user_resolver=_test_user_resolver,
    )
    client = TestClient(app)

    response = client.post(
        "/api/v1/analyses",
        files={"file": ("october_inventory.csv", october_csv, "text/csv")},
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["dataset_summary"]["row_count"] == 3
    assert body["dataset_summary"]["item_count"] == 2
    assert body["dataset_summary"]["date_range"] == {
        "start": "2025-09-17",
        "end": "2025-10-31",
    }
    paneer = next(item for item in body["items"] if item["item_id"] == 1)
    assert paneer["date"] == "2025-10-31"
    assert paneer["avg_usage_7d"] == 6.0
    assert paneer["trend_direction"] == "up"


def test_csv_upload_uses_explicit_base_analysis_instead_of_guessing_latest_snapshot():
    october_csv = (
        "Date,Item_ID,Item_Name,Category,Subcategory,Unit,Current_Stock,Reorder_Level,Daily_Usage,Lead_Time,Price_per_Unit,Supplier_Name,Seasonal_Factor,Waste_Percentage\n"
        "2025-10-31,1,Paneer,Dairy,Cheese,kg,3,8,7,3,450,Supplier A,1.1,4.0\n"
    ).encode()

    historical_record = AnalysisRecord(
        dataset_summary={
            "row_count": 1000,
            "item_count": 10,
            "date_range": {"start": "2025-06-10", "end": "2025-09-17"},
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
        items=[],
        source_observations=[
            {
                "date": "2025-06-10",
                "item_id": 1,
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
                "date": "2025-09-17",
                "item_id": 1,
                "item_name": "Paneer",
                "current_stock": 7.0,
                "unit": "kg",
                "usage_value": 5.0,
                "usage_period": "daily",
                "lead_time_days": 3,
                "price_per_unit": 450.0,
                "seasonal_factor": 1.1,
                "category": "Dairy",
                "subcategory": "Cheese",
                "supplier_name": "Supplier A",
                "recent_waste_percentage": 4.0,
            },
        ],
    )
    latest_record = AnalysisRecord(
        dataset_summary={
            "row_count": 310,
            "item_count": 10,
            "date_range": {"start": "2025-10-01", "end": "2025-10-31"},
        },
        kpi_summary=historical_record.kpi_summary,
        items=[],
        source_observations=[],
    )

    class ExplicitBaseStore:
        def get_latest_analysis_id(self, user_id):
            return "october-only"

        def get(self, analysis_id, user_id=None):
            if analysis_id == "june-september":
                return historical_record
            if analysis_id == "october-only":
                return latest_record
            raise KeyError(analysis_id)

        def persist_observations(self, observations, **kwargs):
            return {
                "import_batch_id": "october-batch",
                "successful_rows": len(observations),
                "failed_rows": 0,
            }

        def list_user_observations(self, user_id):
            return []

        def create_analysis_snapshot(self, **kwargs):
            return "merged-analysis"

    client = TestClient(
        create_app(supabase_store=ExplicitBaseStore(), auth_user_resolver=_test_user_resolver)
    )

    response = client.post(
        "/api/v1/analyses",
        data={"base_analysis_id": "june-september"},
        files={"file": ("october_inventory.csv", october_csv, "text/csv")},
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["dataset_summary"]["row_count"] == 3
    assert body["dataset_summary"]["date_range"] == {
        "start": "2025-06-10",
        "end": "2025-10-31",
    }
    paneer = body["items"][0]
    assert paneer["date"] == "2025-10-31"
    assert paneer["avg_usage_7d"] == pytest.approx(14 / 3)


def test_loaded_supabase_analysis_keeps_source_observations_for_followup_upload():
    historical_record = AnalysisRecord(
        dataset_summary={
            "row_count": 1,
            "item_count": 1,
            "date_range": {"start": "2025-06-10", "end": "2025-06-10"},
        },
        kpi_summary={
            "item_count": 1,
            "restock_now_count": 0,
            "buy_less_count": 0,
            "high_waste_risk_count": 0,
            "inventory_value_at_risk": 0.0,
            "top_urgent_items": [],
            "top_waste_cost_items": [],
        },
        items=[],
        source_observations=[
            {
                "date": "2025-06-10",
                "item_id": 1,
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
            }
        ],
    )

    class SupabaseHistoryStore:
        def __init__(self):
            self.snapshot_kwargs = None

        def get(self, analysis_id, user_id=None):
            if analysis_id != "historical-analysis":
                raise KeyError(analysis_id)
            return historical_record

        def persist_observations(self, observations, **kwargs):
            return {"import_batch_id": "october-batch", "successful_rows": len(observations), "failed_rows": 0}

        def list_user_observations(self, user_id):
            return []

        def create_analysis_snapshot(self, **kwargs):
            self.snapshot_kwargs = kwargs
            return "merged-analysis"

    october_csv = (
        "Date,Item_ID,Item_Name,Category,Subcategory,Unit,Current_Stock,Reorder_Level,Daily_Usage,Lead_Time,Price_per_Unit,Supplier_Name,Seasonal_Factor,Waste_Percentage\n"
        "2025-10-31,1,Paneer,Dairy,Cheese,kg,3,8,7,3,450,Supplier A,1.1,4.0\n"
    ).encode()
    supabase_store = SupabaseHistoryStore()
    app = create_app(supabase_store=supabase_store, auth_user_resolver=_test_user_resolver)
    client = TestClient(app)

    loaded = client.get(
        "/api/v1/analyses/historical-analysis",
        headers=_auth_headers(),
    )
    assert loaded.status_code == 200

    response = client.post(
        "/api/v1/analyses",
        data={"base_analysis_id": "historical-analysis"},
        files={"file": ("october_inventory.csv", october_csv, "text/csv")},
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["dataset_summary"]["row_count"] == 2
    assert body["dataset_summary"]["date_range"] == {
        "start": "2025-06-10",
        "end": "2025-10-31",
    }
    assert len(supabase_store.snapshot_kwargs["source_observations"]) == 2


def test_decision_brief_context_includes_summarized_history_not_raw_rows():
    class CapturingDecisionProvider(MockZAIProvider):
        def __init__(self):
            self.context = None

        def generate_decision_brief(self, context):
            self.context = context
            return super().generate_decision_brief(context)

    provider = CapturingDecisionProvider()
    client = TestClient(create_app(glm_provider=provider))
    client.post(
        "/api/v1/analyses",
        files={"file": ("june_inventory.csv", LEGACY_CSV, "text/csv")},
    )
    analysis = client.post(
        "/api/v1/analyses",
        files={
            "file": (
                "october_inventory.csv",
                (
                    "Date,Item_ID,Item_Name,Category,Subcategory,Unit,Current_Stock,Reorder_Level,Daily_Usage,Lead_Time,Price_per_Unit,Supplier_Name,Seasonal_Factor,Waste_Percentage\n"
                    "2025-10-31,1,Paneer,Dairy,Cheese,kg,3,8,7,3,450,Supplier A,1.1,4.0\n"
                ).encode(),
                "text/csv",
            )
        },
    ).json()

    response = client.get(f"/api/v1/analyses/{analysis['analysis_id']}/decision-brief")

    assert response.status_code == 200
    history_summary = provider.context["analysis"]["history_summary"]
    assert history_summary == {
        "date_range": {"start": "2025-06-10", "end": "2025-10-31"},
        "source_observation_count": 3,
        "current_item_count": 2,
        "latest_observation_date": "2025-10-31",
    }
    paneer_context = next(
        item for item in provider.context["analysis"]["items"] if item["item_name"] == "Paneer"
    )
    assert paneer_context["history"] == {
        "observation_count": 2,
        "latest_observation_date": "2025-10-31",
        "avg_usage_7d": 4.5,
        "trend_direction": "up",
    }
    assert "source_observations" not in provider.context["analysis"]


def test_records_endpoint_backfills_source_observations_when_memory_snapshot_is_stale():
    class ReadOnlySupabaseStore:
        def get(self, analysis_id, user_id=None):
            assert analysis_id == "stale-analysis-id"
            assert user_id == TEST_USER_ID
            return AnalysisRecord(
                dataset_summary={
                    "row_count": 2,
                    "item_count": 1,
                    "date_range": {"start": "2025-06-10", "end": "2025-07-10"},
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
                        "date": "2025-07-10",
                        "item_name": "Paneer",
                        "category": "Dairy",
                        "subcategory": "Cheese",
                        "unit": "kg",
                        "supplier_name": "Supplier A",
                        "current_stock": 4.0,
                        "reorder_level": 8.0,
                        "daily_usage": 5.0,
                        "lead_time": 3,
                        "price_per_unit": 450.0,
                        "seasonal_factor": 1.1,
                        "waste_percentage": 4.0,
                        "avg_usage_7d": 3.5,
                        "trend_direction": "up",
                        "days_of_cover": 0.8,
                        "inventory_value": 1800.0,
                        "estimated_waste_cost": 72.0,
                        "lead_time_demand": 16.5,
                        "stock_gap_to_lead_demand": -12.5,
                        "reorder_urgency_score": 75,
                        "waste_risk_score": 21,
                        "recommended_action": "RESTOCK_NOW",
                    }
                ],
                source_observations=[
                    {
                        "date": "2025-06-10",
                        "item_id": 1,
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
                        "date": "2025-07-10",
                        "item_id": 1,
                        "item_name": "Paneer",
                        "current_stock": 4.0,
                        "unit": "kg",
                        "usage_value": 5.0,
                        "usage_period": "daily",
                        "lead_time_days": 3,
                        "price_per_unit": 450.0,
                        "seasonal_factor": 1.1,
                        "category": "Dairy",
                        "subcategory": "Cheese",
                        "supplier_name": "Supplier A",
                        "recent_waste_percentage": 4.0,
                    },
                ],
            )

    app = create_app(supabase_store=ReadOnlySupabaseStore(), auth_user_resolver=_test_user_resolver)
    stale_snapshot = ReadOnlySupabaseStore().get("stale-analysis-id", TEST_USER_ID)
    app.state.store.create(
        analysis_id="stale-analysis-id",
        owner_id=TEST_USER_ID,
        dataset_summary=stale_snapshot.dataset_summary,
        kpi_summary=stale_snapshot.kpi_summary,
        items=stale_snapshot.items,
        source_observations=[],
    )
    client = TestClient(app)

    response = client.get(
        "/api/v1/analyses/stale-analysis-id/records",
        headers=_auth_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert len(body["source_observations"]) == 2
    assert body["source_observations"][0]["date"] == "2025-06-10"


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
