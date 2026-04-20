from fastapi.testclient import TestClient
import pytest

from stockwise_api.api.app import create_app
from stockwise_api.services.glm import MockZAIProvider


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
    client = TestClient(create_app())
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
    assert body["recommended_action"] == "BUY_LESS"


def test_create_app_fails_fast_when_live_mode_has_no_api_key(monkeypatch):
    monkeypatch.setenv("GLM_MODE", "live")
    monkeypatch.delenv("ZAI_API_KEY", raising=False)

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
