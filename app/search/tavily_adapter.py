from __future__ import annotations

import os
from typing import Any

import httpx


class TavilyAdapter:
    def __init__(self) -> None:
        self.api_key = os.getenv("TAVILY_API_KEY", "")

    def readiness(self) -> dict[str, Any]:
        return {"provider": "tavily", "configured": bool(self.api_key)}

    async def search(self, query: str, *, max_results: int = 3) -> list[dict[str, Any]]:
        if not self.api_key:
            raise RuntimeError("Tavily is not configured.")
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": self.api_key,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": max_results,
                    "topic": "general",
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
