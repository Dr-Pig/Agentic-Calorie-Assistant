from __future__ import annotations

from typing import Any, Protocol


class WebExtractPort(Protocol):
    async def extract_rows(
        self,
        *,
        urls: list[str],
        query: str,
    ) -> list[dict[str, Any]]:
        """Return provider-agnostic extract rows for later B2 normalization."""


__all__ = ["WebExtractPort"]
