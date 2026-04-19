from fastapi.testclient import TestClient
import pytest

from stockwise_api.api.app import create_app
from stockwise_api.services.glm import MockZAIProvider
from tests.fixtures import DATASET_PATH


def test_upload_endpoint_returns_analysis_and_ranked_items():
    client = TestClient(create_app())
    with DATASET_PATH.open("rb") as f:
        response = client.post(
            "/api/v1/analyses",
            files={"file": ("restaurant_inventory_100days.csv", f, "text/csv")},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["dataset_summary"]["row_count"] == 1000
    assert body["dataset_summary"]["item_count"] == 10
    assert len(body["items"]) == 10
    assert any(item["recommended_action"] == "BUY_LESS" for item in body["items"])


def test_simulation_endpoint_returns_updated_scenario_metrics():
    client = TestClient(create_app())
    with DATASET_PATH.open("rb") as f:
        analysis = client.post(
            "/api/v1/analyses",
            files={"file": ("restaurant_inventory_100days.csv", f, "text/csv")},
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
    with DATASET_PATH.open("rb") as f:
        analysis = client.post(
            "/api/v1/analyses",
            files={"file": ("restaurant_inventory_100days.csv", f, "text/csv")},
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
    with DATASET_PATH.open("rb") as f:
        analysis = client.post(
            "/api/v1/analyses",
            files={"file": ("restaurant_inventory_100days.csv", f, "text/csv")},
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
