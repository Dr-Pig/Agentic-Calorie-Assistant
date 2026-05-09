from __future__ import annotations

from functools import lru_cache
from typing import Any, Protocol, Sequence


class ExactItemLookupPort(Protocol):
    """Application-owned lookup boundary for exact-item candidate retrieval."""

    def resolve_exact_item_fts(self, query: str, *, limit: int) -> Sequence[dict[str, Any]]:
        """Return raw exact-item candidates for the agent lane to validate."""


class DefaultExactItemLookupPort:
    def resolve_exact_item_fts(self, query: str, *, limit: int) -> Sequence[dict[str, Any]]:
        from app.nutrition.infrastructure.web_search.exact_item_lookup import resolve_exact_item_fts

        return resolve_exact_item_fts(query, limit=limit)


@lru_cache(maxsize=1)
def default_exact_item_lookup_port() -> ExactItemLookupPort:
    return DefaultExactItemLookupPort()


__all__ = [
    "DefaultExactItemLookupPort",
    "ExactItemLookupPort",
    "default_exact_item_lookup_port",
]
