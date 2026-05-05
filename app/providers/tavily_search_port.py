from __future__ import annotations

from typing import Any
from typing import TYPE_CHECKING

from .tavily_adapter import TavilyAdapter

if TYPE_CHECKING:
    from .tavily_extract_port import TavilyExtractPort


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

    def extract_port(self) -> "TavilyExtractPort":
        from .tavily_extract_port import TavilyExtractPort

        return TavilyExtractPort(adapter=self._adapter)

    async def aclose(self) -> None:
        close = getattr(self._adapter, "aclose", None)
        if close is not None:
            await close()


__all__ = ["TavilySearchPort"]
