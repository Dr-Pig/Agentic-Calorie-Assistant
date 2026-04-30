from __future__ import annotations

from app.providers.tavily_adapter import TavilyAdapter


def test_tavily_timeout_is_capped_by_foreground_ceiling(monkeypatch) -> None:
    monkeypatch.setenv("TAVILY_TIMEOUT_SECONDS", "90")

    adapter = TavilyAdapter()
    readiness = adapter.readiness()

    assert adapter.timeout_seconds <= 15
    assert readiness["timeout_seconds"] == adapter.timeout_seconds
