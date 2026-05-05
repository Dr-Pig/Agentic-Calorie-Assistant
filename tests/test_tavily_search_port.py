from __future__ import annotations

from typing import Any

import pytest

from app.providers.tavily_search_port import TavilySearchPort


class _FakeTavilyAdapter:
    def __init__(self, hits: list[dict[str, Any]]) -> None:
        self._hits = hits
        self.search_calls: list[dict[str, Any]] = []
        self.extract_called = False

    def readiness(self) -> dict[str, Any]:
        return {"provider": "tavily", "configured": True, "timeout_seconds": 15}

    async def search_candidates(self, query: str, *, max_results: int = 5) -> list[dict[str, Any]]:
        self.search_calls.append({"query": query, "max_results": max_results})
        return self._hits

    async def extract_structured_page_data(self, **_: Any) -> list[dict[str, Any]]:
        self.extract_called = True
        raise AssertionError("TavilySearchPort must not call extract_structured_page_data().")


@pytest.mark.asyncio
async def test_search_hits_forwards_raw_candidate_output_without_semantic_changes() -> None:
    raw_hits = [
        {
            "title": "CoCo pearl milk tea",
            "url": "https://www.coco-tea.com/menu/pearl-milk-tea",
            "snippet": "official menu",
            "score": 0.92,
            "officialness": "official",
            "raw_content": "",
        }
    ]
    adapter = _FakeTavilyAdapter(raw_hits)
    port = TavilySearchPort(adapter=adapter)

    hits = await port.search_hits(query="CoCo pearl milk tea", max_results=3)

    assert hits == raw_hits
    assert adapter.search_calls == [{"query": "CoCo pearl milk tea", "max_results": 3}]
    assert adapter.extract_called is False


def test_readiness_is_forwarded_as_operational_health_only() -> None:
    adapter = _FakeTavilyAdapter([])
    port = TavilySearchPort(adapter=adapter)

    assert port.readiness() == {"provider": "tavily", "configured": True, "timeout_seconds": 15}


def test_search_and_extract_runtime_ports_can_share_adapter() -> None:
    adapter = _FakeTavilyAdapter([])

    search_port = TavilySearchPort(adapter=adapter)
    extract_port = search_port.extract_port()

    assert search_port._adapter is extract_port._adapter
