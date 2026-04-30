from __future__ import annotations

from typing import Any

import pytest

from app.providers.tavily_extract_port import TavilyExtractPort


class _FakeTavilyAdapter:
    def __init__(self, rows: list[dict[str, Any]]) -> None:
        self._rows = rows
        self.extract_calls: list[dict[str, Any]] = []
        self.search_called = False

    async def extract_structured_page_data(
        self,
        *,
        urls: list[str],
        query: str,
    ) -> list[dict[str, Any]]:
        self.extract_calls.append({"urls": list(urls), "query": query})
        return self._rows

    async def search_candidates(self, *_: Any, **__: Any) -> list[dict[str, Any]]:
        self.search_called = True
        raise AssertionError("TavilyExtractPort must not call search_candidates().")

    def readiness(self) -> dict[str, Any]:
        return {"provider": "tavily", "configured": True, "status": "ok"}


@pytest.mark.asyncio
async def test_extract_rows_forwards_raw_provider_rows_without_semantic_changes() -> None:
    raw_rows = [
        {
            "url": "https://milksha.example/menu/pearl-black-tea-latte",
            "title": "迷客夏 珍珠紅茶拿鐵",
            "source_type": "official",
            "officialness": "official",
            "serving_basis": "per_cup",
            "raw_content": "每杯 400 kcal",
        }
    ]
    adapter = _FakeTavilyAdapter(raw_rows)
    port = TavilyExtractPort(adapter=adapter)

    rows = await port.extract_rows(
        urls=["https://milksha.example/menu/pearl-black-tea-latte"],
        query="迷客夏珍珠紅茶拿鐵",
    )

    assert rows == raw_rows
    assert adapter.extract_calls == [
        {
            "urls": ["https://milksha.example/menu/pearl-black-tea-latte"],
            "query": "迷客夏珍珠紅茶拿鐵",
        }
    ]
    assert adapter.search_called is False


def test_readiness_forwards_operational_health_without_claiming_semantics() -> None:
    port = TavilyExtractPort(adapter=_FakeTavilyAdapter([]))

    assert port.readiness() == {"provider": "tavily", "configured": True, "status": "ok"}
