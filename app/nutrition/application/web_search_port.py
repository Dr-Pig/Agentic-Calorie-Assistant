from __future__ import annotations

from typing import Any, Protocol


class WebSearchPort(Protocol):
    async def search_hits(
        self,
        *,
        query: str,
        max_results: int = 5,
    ) -> list[dict[str, Any]]:
        """Return provider-agnostic web search hits for later B2 normalization."""


__all__ = ["WebSearchPort"]
