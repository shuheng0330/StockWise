import json

import httpx

from stockwise_api.services.glm import LiveZAIProvider


class FakeResponse:
    def json(self):
        return {
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
    assert "thinking" not in request["json"]
    assert request["json"]["max_tokens"] == 1600
    assert "priority_level" in request["json"]["messages"][0]["content"]
    user_payload = json.loads(request["json"]["messages"][1]["content"])
    assert user_payload["item_name"] == "Paneer"
    assert user_payload["recommended_action"] == "BUY_LESS"
    assert "metrics" in user_payload
    assert "waste_risk_score" in user_payload["metrics"]
    assert "supplier_name" not in user_payload["metrics"]


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
