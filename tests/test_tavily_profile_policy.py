from __future__ import annotations

from typing import Any

import pytest

from app.nutrition.infrastructure.web_search.tavily_adapter import TavilyAdapter


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self._payload


class _FakeAsyncClient:
    def __init__(self, *, timeout: int, captured: list[dict[str, Any]], response_payload: dict[str, Any]) -> None:
        self.timeout = timeout
        self._captured = captured
        self._response_payload = response_payload

    async def __aenter__(self) -> _FakeAsyncClient:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None

    async def post(self, url: str, *, json: dict[str, Any]) -> _FakeResponse:
        self._captured.append({"url": url, "json": dict(json), "timeout": self.timeout})
        return _FakeResponse(self._response_payload)


@pytest.mark.asyncio
async def test_runtime_search_profile_owns_basic_search_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []
    monkeypatch.setattr(
        "app.nutrition.infrastructure.web_search.tavily_adapter.httpx.AsyncClient",
        lambda timeout: _FakeAsyncClient(timeout=timeout, captured=captured, response_payload={"results": []}),
    )

    adapter = TavilyAdapter()
    monkeypatch.setattr(adapter, "_is_configured", lambda: True)

    await adapter.search_candidates("milk tea", max_results=4)

    assert len(captured) == 1
    request = captured[0]
    assert request["url"] == "https://api.tavily.com/search"
    assert request["json"]["query"] == "milk tea"
    assert request["json"]["max_results"] == 4
    assert request["json"]["search_depth"] == "basic"
    assert request["json"]["include_raw_content"] is False


@pytest.mark.asyncio
async def test_selected_extract_profile_owns_advanced_extract_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[dict[str, Any]] = []
    monkeypatch.setattr(
        "app.nutrition.infrastructure.web_search.tavily_adapter.httpx.AsyncClient",
        lambda timeout: _FakeAsyncClient(timeout=timeout, captured=captured, response_payload={"results": []}),
    )

    adapter = TavilyAdapter()
    monkeypatch.setattr(adapter, "_is_configured", lambda: True)

    await adapter.extract_structured_page_data(urls=["https://example.com/menu"], query="milk tea")

    assert len(captured) == 1
    request = captured[0]
    assert request["url"] == "https://api.tavily.com/extract"
    assert request["json"]["urls"] == ["https://example.com/menu"]
    assert request["json"]["query"] == "milk tea"
    assert request["json"]["extract_depth"] == "advanced"
    assert request["json"]["chunks_per_source"] == 3


def test_readiness_remains_operational_only() -> None:
    adapter = TavilyAdapter()

    readiness = adapter.readiness()

    assert readiness["provider"] == "tavily"
    assert "configured" in readiness
    assert "timeout_seconds" in readiness
    assert "search_depth" not in readiness
    assert "extract_depth" not in readiness
    assert "chunks_per_source" not in readiness
    assert "include_raw_content" not in readiness
