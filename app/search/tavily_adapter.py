from __future__ import annotations

import os
from typing import Any

import httpx


PLACEHOLDER_API_KEYS = {"", "replace-me"}


class TavilyAdapter:
    def __init__(self) -> None:
        self.api_key = os.getenv("TAVILY_API_KEY", "")

    def readiness(self) -> dict[str, Any]:
        return {"provider": "tavily", "configured": self._is_configured()}

    async def search(self, query: str, *, max_results: int = 5) -> list[dict[str, Any]]:
        if not self._is_configured():
            raise RuntimeError("Tavily is not configured.")
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": max_results,
                },
            )
            response.raise_for_status()
            data = response.json()
        results = []
        for item in data.get("results", []):
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("content", "")[:400],
                }
            )
        return results

    def _is_configured(self) -> bool:
        return self.api_key.strip() not in PLACEHOLDER_API_KEYS
