from __future__ import annotations

from typing import Any

from .tavily_adapter import TavilyAdapter


class TavilySearchPort:
    """Infrastructure adapter wrapper only.

    This wrapper forwards Tavily candidate-search behavior into the app-owned
    WebSearchPort seam. It must not decide source quality, exactness, candidate
    acceptance, or nutrition semantics.
    """

    def __init__(self, *, adapter: TavilyAdapter | None = None) -> None:
        self._adapter = adapter or TavilyAdapter()

    async def search_hits(
        self,
        *,
        query: str,
        max_results: int = 5,
    ) -> list[dict[str, Any]]:
        return await self._adapter.search_candidates(query, max_results=max_results)

    def readiness(self) -> dict[str, Any]:
        """Operational health only; not a capability or evidence-quality claim."""
        return dict(self._adapter.readiness())


__all__ = ["TavilySearchPort"]
