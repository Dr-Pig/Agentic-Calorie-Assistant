from __future__ import annotations

from typing import Any

from .tavily_adapter import TavilyAdapter


class TavilyExtractPort:
    """Infrastructure adapter wrapper only.

    This wrapper forwards Tavily extract behavior into the app-owned
    WebExtractPort seam. It must not normalize rows, decide exactness,
    candidate acceptance, or nutrition semantics.
    """

    def __init__(self, *, adapter: TavilyAdapter | None = None) -> None:
        self._adapter = adapter or TavilyAdapter()

    async def extract_rows(
        self,
        *,
        urls: list[str],
        query: str,
    ) -> list[dict[str, Any]]:
        return await self._adapter.extract_structured_page_data(urls=urls, query=query)

    def readiness(self) -> dict[str, Any]:
        return dict(self._adapter.readiness())


__all__ = ["TavilyExtractPort"]
