import json

import httpx

from stockwise_api.services.glm import LiveZAIProvider


class FakeResponse:
    def __init__(self, payload=None):
        self.payload = payload

    def json(self):
        return self.payload or {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "item_name": "Paneer",
                                "recommended_action": "BUY_LESS",
                                "priority_level": "MEDIUM",
                                "short_reason": "Paneer has high waste risk.",
                                "decision_explanation": "Paneer should be bought in a smaller quantity.",
                                "tradeoff_summary": "A smaller order lowers waste exposure.",
                                "suggested_next_step": "Place a small top-up order only if needed.",
                                "confidence_note": "Confidence is based on current StockWise metrics.",
                                "warning_flag": "Trend direction: stable.",
                            }
                        )
                    }
                }
            ]
        }

    def raise_for_status(self):
        return None


class FakeStreamResponse:
    def __init__(self, lines, status_code=200):
        self.lines = lines
        self.status_code = status_code

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def iter_lines(self):
        for line in self.lines:
            yield line

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("stream failed", request=None, response=None)


class FakeClient:
    def __init__(self, *, timeout):
        self.timeout = timeout
        self.requests = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def post(self, url, *, json, headers):
        self.requests.append({"url": url, "json": json, "headers": headers})
        return FakeResponse()

    def stream(self, method, url, *, json, headers):
        self.requests.append({"method": method, "url": url, "json": json, "headers": headers})
        return FakeStreamResponse(
            [
                'data: {"choices":[{"delta":{"role":"assistant","content":"```json\\n"}}]}',
                'data: {"choices":[{"delta":{"content":"{\\"item_name\\": \\"Paneer\\", "}}]}',
                'data: {"choices":[{"delta":{"content":"\\"recommended_action\\": \\"BUY_LESS\\"}"}, "finish_reason":"stop"}]}',
                'data: {"usage":{"prompt_tokens":10,"completion_tokens":20,"total_tokens":30}}',
                "data: [DONE]",
            ]
        )


def test_live_provider_requests_json_contract(monkeypatch):
    fake_client = FakeClient(timeout=20.0)
    monkeypatch.setattr(httpx, "Client", lambda *, timeout: fake_client)
    provider = LiveZAIProvider(api_key="test-key", base_url="https://example.test/chat", model="test-model")

    content = provider.generate_explanation(
        {
            "item_name": "Paneer",
            "recommended_action": "BUY_LESS",
            "waste_risk_score": 100,
        }
    )

    request = fake_client.requests[0]
    assert json.loads(content)["recommended_action"] == "BUY_LESS"
    assert request["url"] == "https://example.test/chat"
    assert request["method"] == "POST"
    assert request["json"]["model"] == "test-model"
    assert request["json"]["stream"] is True
    assert request["json"]["response_format"] == {"type": "json_object"}
    assert request["json"]["reasoning_effort"] == "low"
    assert request["json"]["thinking"] == {"type": "disabled"}
    assert request["json"]["max_tokens"] == 1600
    assert "priority_level" in request["json"]["messages"][0]["content"]
    user_payload = json.loads(request["json"]["messages"][1]["content"])
    assert user_payload["item_name"] == "Paneer"
    assert user_payload["recommended_action"] == "BUY_LESS"
    assert "metrics" in user_payload
    assert "waste_risk_score" in user_payload["metrics"]
    assert "supplier_name" not in user_payload["metrics"]


def test_live_provider_can_disable_streaming_with_env_var(monkeypatch):
    fake_client = FakeClient(timeout=20.0)
    monkeypatch.setattr(httpx, "Client", lambda *, timeout: fake_client)
    monkeypatch.setenv("ZAI_STREAM", "false")
    provider = LiveZAIProvider(api_key="test-key", base_url="https://example.test/chat", model="test-model")

    content = provider.generate_explanation(
        {
            "item_name": "Paneer",
            "recommended_action": "BUY_LESS",
            "waste_risk_score": 100,
        }
    )

    assert json.loads(content)["recommended_action"] == "BUY_LESS"
    assert len(fake_client.requests) == 1
    assert fake_client.requests[0]["json"]["stream"] is False


def test_live_provider_defaults_to_non_streaming_for_ilmu_endpoint(monkeypatch):
    fake_client = FakeClient(timeout=20.0)
    monkeypatch.setattr(httpx, "Client", lambda *, timeout: fake_client)
    provider = LiveZAIProvider(
        api_key="test-key",
        base_url="https://api.ilmu.ai/v1/chat/completions",
        model="ilmu-glm-5.1",
    )

    provider.generate_explanation(
        {
            "item_name": "Paneer",
            "recommended_action": "BUY_LESS",
            "waste_risk_score": 100,
        }
    )

    assert len(fake_client.requests) == 1
    assert fake_client.requests[0]["json"]["stream"] is False


def test_live_provider_uses_configurable_timeout(monkeypatch):
    observed = {}

    class TimeoutCapturingClient(FakeClient):
        def __init__(self, *, timeout):
            super().__init__(timeout=timeout)
            observed["timeout"] = timeout
            observed["client"] = self

    monkeypatch.setattr(httpx, "Client", lambda *, timeout: TimeoutCapturingClient(timeout=timeout))
    provider = LiveZAIProvider(
        api_key="test-key",
        base_url="https://example.test/chat",
        model="test-model",
    )

    provider.generate_explanation(
        {
            "item_name": "Paneer",
            "recommended_action": "BUY_LESS",
            "waste_risk_score": 100,
        }
    )

    assert isinstance(observed["timeout"], httpx.Timeout)
    assert observed["timeout"].connect == 10.0
    assert observed["timeout"].read == 180.0
    assert observed["timeout"].write == 10.0
    assert observed["timeout"].pool == 10.0


def test_live_provider_respects_timeout_and_token_env_vars(monkeypatch):
    observed = {}

    class TimeoutCapturingClient(FakeClient):
        def __init__(self, *, timeout):
            super().__init__(timeout=timeout)
            observed["timeout"] = timeout
            observed["client"] = self

    monkeypatch.setattr(httpx, "Client", lambda *, timeout: TimeoutCapturingClient(timeout=timeout))
    monkeypatch.setenv("ZAI_CONNECT_TIMEOUT_SECONDS", "3")
    monkeypatch.setenv("ZAI_READ_TIMEOUT_SECONDS", "90")
    monkeypatch.setenv("ZAI_WRITE_TIMEOUT_SECONDS", "7")
    monkeypatch.setenv("ZAI_POOL_TIMEOUT_SECONDS", "5")
    monkeypatch.setenv("ZAI_MAX_TOKENS", "250")
    provider = LiveZAIProvider(
        api_key="test-key",
        base_url="https://example.test/chat",
        model="test-model",
    )

    provider.generate_explanation(
        {
            "item_name": "Paneer",
            "recommended_action": "BUY_LESS",
            "waste_risk_score": 100,
        }
    )

    timeout = observed["timeout"]
    assert isinstance(timeout, httpx.Timeout)
    assert timeout.connect == 3.0
    assert timeout.read == 90.0
    assert timeout.write == 7.0
    assert timeout.pool == 5.0
    assert observed["client"].requests[0]["json"]["max_tokens"] == 250


def test_live_provider_uses_compact_decision_brief_narrative(monkeypatch):
    observed = {}
    narrative_payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "summary": "Restock milk first and reduce waste-risk buys.",
                            "top_tradeoffs": ["Restocking uses cash but reduces shortage risk."],
                            "confidence_note": "Grounded in StockWise metrics.",
                            "warning_flag": "Review records before ordering.",
                        }
                    )
                },
                "finish_reason": "stop",
            }
        ]
    }

    class RequestCapturingClient(FakeClient):
        def __init__(self, *, timeout):
            super().__init__(timeout=timeout)
            observed["client"] = self

        def post(self, url, *, json, headers):
            self.requests.append({"method": "POST", "url": url, "json": json, "headers": headers})
            return FakeResponse(narrative_payload)

    monkeypatch.setattr(httpx, "Client", lambda *, timeout: RequestCapturingClient(timeout=timeout))
    monkeypatch.setenv("ZAI_MAX_TOKENS", "250")
    provider = LiveZAIProvider(
        api_key="test-key",
        base_url="https://api.ilmu.ai/v1/chat/completions",
        model="ilmu-glm-5.1",
    )

    content = provider.generate_decision_brief(
        {
            "analysis": {
                "dataset_summary": {"total_items": 3},
                "kpi_summary": {"restock_now_count": 1},
                "items": [
                    {
                        "item_id": 1,
                        "item_name": "Milk",
                        "category": "Dairy",
                        "current_stock": 2,
                        "daily_usage": 5,
                        "days_of_cover": 0.4,
                        "inventory_value": 12,
                        "estimated_waste_cost": 0,
                        "lead_time_demand": 15,
                        "stock_gap_to_lead_demand": -13,
                        "reorder_urgency_score": 95,
                        "waste_risk_score": 10,
                        "recommended_action": "RESTOCK_NOW",
                    }
                ],
            },
            "deterministic_impact": {"cash": "Cash impact.", "waste": "Waste impact.", "shortage": "Shortage impact."},
        }
    )
    parsed = json.loads(content)

    assert observed["client"].requests[0]["json"]["max_tokens"] == 1600
    assert observed["client"].requests[0]["json"]["thinking"] == {"type": "disabled"}
    assert parsed["summary"] == "Restock milk first and reduce waste-risk buys."
    assert parsed["buy_today"][0]["item_name"] == "Milk"
    assert parsed["estimated_impact"]["cash"] == "Cash impact."


def test_live_provider_prefers_split_read_timeout_over_legacy_total_timeout(monkeypatch):
    observed = {}

    class TimeoutCapturingClient(FakeClient):
        def __init__(self, *, timeout):
            super().__init__(timeout=timeout)
            observed["timeout"] = timeout

    monkeypatch.setattr(httpx, "Client", lambda *, timeout: TimeoutCapturingClient(timeout=timeout))
    monkeypatch.setenv("ZAI_TIMEOUT_SECONDS", "60")
    monkeypatch.setenv("ZAI_READ_TIMEOUT_SECONDS", "150")
    provider = LiveZAIProvider(
        api_key="test-key",
        base_url="https://example.test/chat",
        model="test-model",
    )

    provider.generate_explanation(
        {
            "item_name": "Paneer",
            "recommended_action": "BUY_LESS",
            "waste_risk_score": 100,
        }
    )

    timeout = observed["timeout"]
    assert isinstance(timeout, httpx.Timeout)
    assert timeout.read == 150.0


def test_live_provider_raises_when_stream_has_no_visible_content(monkeypatch):
    class EmptyStreamClient(FakeClient):
        def stream(self, method, url, *, json, headers):
            self.requests.append({"method": method, "url": url, "json": json, "headers": headers})
            return FakeStreamResponse(
                [
                    'data: {"choices":[{"delta":{"role":"assistant","content":""}}]}',
                    'data: {"choices":[{"delta":{"content":null},"finish_reason":"length"}]}',
                    "data: [DONE]",
                ]
            )

    monkeypatch.setattr(httpx, "Client", lambda *, timeout: EmptyStreamClient(timeout=timeout))
    provider = LiveZAIProvider(
        api_key="test-key",
        base_url="https://example.test/chat",
        model="test-model",
    )

    try:
        provider.generate_explanation(
            {
                "item_name": "Paneer",
                "recommended_action": "BUY_LESS",
                "waste_risk_score": 100,
            }
        )
    except RuntimeError as exc:
        assert "visible content" in str(exc)
    else:
        raise AssertionError("Expected provider to reject an empty streamed response.")


def test_live_provider_retries_non_stream_when_stream_has_no_visible_content(monkeypatch):
    class EmptyThenNonStreamClient(FakeClient):
        def stream(self, method, url, *, json, headers):
            self.requests.append({"method": method, "url": url, "json": json, "headers": headers})
            return FakeStreamResponse(
                [
                    'data: {"choices":[{"delta":{"role":"assistant","content":""},"finish_reason":null}]}',
                    'data: {"choices":[{"delta":{"content":null},"finish_reason":"stop"}]}',
                    "data: [DONE]",
                ]
            )

        def post(self, url, *, json, headers):
            self.requests.append({"method": "POST", "url": url, "json": json, "headers": headers})
            return FakeResponse()

    fake_client = EmptyThenNonStreamClient(timeout=20.0)
    monkeypatch.setattr(httpx, "Client", lambda *, timeout: fake_client)
    provider = LiveZAIProvider(api_key="test-key", base_url="https://example.test/chat", model="test-model")

    content = provider.generate_explanation(
        {
            "item_name": "Paneer",
            "recommended_action": "BUY_LESS",
            "waste_risk_score": 100,
        }
    )

    assert json.loads(content)["recommended_action"] == "BUY_LESS"
    assert fake_client.requests[0]["json"]["stream"] is True
    assert fake_client.requests[1]["json"]["stream"] is False


def test_live_provider_accepts_message_content_from_stream(monkeypatch):
    class MessageContentStreamClient(FakeClient):
        def stream(self, method, url, *, json, headers):
            self.requests.append({"method": method, "url": url, "json": json, "headers": headers})
            return FakeStreamResponse(
                [
                    'data:{"choices":[{"message":{"content":"{\\"item_name\\":\\"Paneer\\",\\"recommended_action\\":\\"BUY_LESS\\"}"}}]}',
                    "data: [DONE]",
                ]
            )

    monkeypatch.setattr(httpx, "Client", lambda *, timeout: MessageContentStreamClient(timeout=timeout))
    provider = LiveZAIProvider(
        api_key="test-key",
        base_url="https://example.test/chat",
        model="test-model",
    )

    content = provider.generate_explanation(
        {
            "item_name": "Paneer",
            "recommended_action": "BUY_LESS",
            "waste_risk_score": 100,
        }
    )

    assert json.loads(content)["recommended_action"] == "BUY_LESS"


def test_live_provider_accepts_text_content_from_stream(monkeypatch):
    class TextContentStreamClient(FakeClient):
        def stream(self, method, url, *, json, headers):
            self.requests.append({"method": method, "url": url, "json": json, "headers": headers})
            return FakeStreamResponse(
                [
                    'data: {"choices":[{"text":"{\\"item_name\\":\\"Paneer\\",\\"recommended_action\\":\\"BUY_LESS\\"}"}]}',
                    "data: [DONE]",
                ]
            )

    monkeypatch.setattr(httpx, "Client", lambda *, timeout: TextContentStreamClient(timeout=timeout))
    provider = LiveZAIProvider(
        api_key="test-key",
        base_url="https://example.test/chat",
        model="test-model",
    )

    content = provider.generate_explanation(
        {
            "item_name": "Paneer",
            "recommended_action": "BUY_LESS",
            "waste_risk_score": 100,
        }
    )

    assert json.loads(content)["item_name"] == "Paneer"


def test_live_provider_accepts_reasoning_content_when_message_content_is_empty(monkeypatch):
    payload = {
        "choices": [
            {
                "message": {
                    "content": "",
                    "reasoning_content": '{"item_name":"Paneer","recommended_action":"BUY_LESS"}',
                },
                "finish_reason": "stop",
            }
        ]
    }

    class ReasoningContentClient(FakeClient):
        def post(self, url, *, json, headers):
            self.requests.append({"method": "POST", "url": url, "json": json, "headers": headers})
            return FakeResponse(payload)

    monkeypatch.setattr(httpx, "Client", lambda *, timeout: ReasoningContentClient(timeout=timeout))
    provider = LiveZAIProvider(
        api_key="test-key",
        base_url="https://api.ilmu.ai/v1/chat/completions",
        model="ilmu-glm-5.1",
    )

    content = provider.generate_explanation(
        {
            "item_name": "Paneer",
            "recommended_action": "BUY_LESS",
            "waste_risk_score": 100,
        }
    )

    assert json.loads(content)["item_name"] == "Paneer"


def test_live_provider_accepts_tool_call_arguments_when_message_content_is_empty(monkeypatch):
    payload = {
        "choices": [
            {
                "message": {
                    "content": "",
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "type": "function",
                            "function": {
                                "name": "respond",
                                "arguments": '{"item_name":"Paneer","recommended_action":"BUY_LESS"}',
                            },
                        }
                    ],
                },
                "finish_reason": "stop",
            }
        ]
    }

    class ToolCallArgumentsClient(FakeClient):
        def post(self, url, *, json, headers):
            self.requests.append({"method": "POST", "url": url, "json": json, "headers": headers})
            return FakeResponse(payload)

    monkeypatch.setattr(httpx, "Client", lambda *, timeout: ToolCallArgumentsClient(timeout=timeout))
    provider = LiveZAIProvider(
        api_key="test-key",
        base_url="https://api.ilmu.ai/v1/chat/completions",
        model="ilmu-glm-5.1",
    )

    content = provider.generate_explanation(
        {
            "item_name": "Paneer",
            "recommended_action": "BUY_LESS",
            "waste_risk_score": 100,
        }
    )

    assert json.loads(content)["recommended_action"] == "BUY_LESS"


def test_live_provider_retries_without_strict_json_format_when_non_stream_content_is_empty(monkeypatch):
    valid_payload = {
        "choices": [
            {
                "message": {
                    "content": '{"item_name":"Paneer","recommended_action":"BUY_LESS"}',
                },
                "finish_reason": "stop",
            }
        ]
    }

    class EmptyThenCompatibleClient(FakeClient):
        def post(self, url, *, json, headers):
            self.requests.append({"method": "POST", "url": url, "json": json, "headers": headers})
            if len(self.requests) == 1:
                return FakeResponse({"choices": [{"message": {"content": ""}, "finish_reason": "stop"}]})
            return FakeResponse(valid_payload)

    fake_client = EmptyThenCompatibleClient(timeout=20.0)
    monkeypatch.setattr(httpx, "Client", lambda *, timeout: fake_client)
    provider = LiveZAIProvider(
        api_key="test-key",
        base_url="https://api.ilmu.ai/v1/chat/completions",
        model="ilmu-glm-5.1",
    )

    content = provider.generate_explanation(
        {
            "item_name": "Paneer",
            "recommended_action": "BUY_LESS",
            "waste_risk_score": 100,
        }
    )

    assert json.loads(content)["recommended_action"] == "BUY_LESS"
    assert fake_client.requests[0]["json"]["response_format"] == {"type": "json_object"}
    assert "response_format" not in fake_client.requests[1]["json"]
    assert "reasoning_effort" not in fake_client.requests[1]["json"]
