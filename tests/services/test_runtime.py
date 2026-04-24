import asyncio
import sys

from stockwise_api.runtime import configure_windows_event_loop_policy


def test_configure_windows_event_loop_policy_uses_selector_policy_on_windows(monkeypatch):
    calls = []

    class FakeSelectorPolicy:
        pass

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(asyncio, "WindowsSelectorEventLoopPolicy", FakeSelectorPolicy, raising=False)
    monkeypatch.setattr(asyncio, "set_event_loop_policy", lambda policy: calls.append(policy))

    assert configure_windows_event_loop_policy() is True
    assert isinstance(calls[0], FakeSelectorPolicy)


def test_configure_windows_event_loop_policy_is_noop_off_windows(monkeypatch):
    calls = []

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setattr(asyncio, "set_event_loop_policy", lambda policy: calls.append(policy))

    assert configure_windows_event_loop_policy() is False
    assert calls == []
