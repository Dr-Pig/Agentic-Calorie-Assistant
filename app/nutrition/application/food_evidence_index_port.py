from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.nutrition.application.fooddb_retrieval_policy import IndexedFoodRecord


@runtime_checkable
class FoodEvidenceIndexPort(Protocol):
    """Adapter boundary for runtime FoodDB retrieval records.

    Implementations may load from local JSON, SQLite FTS, Supabase, or another index,
    but application retrieval policy should only depend on indexed records.
    """

    def load_records(self) -> tuple[IndexedFoodRecord, ...]:
        """Return normalized records consumable by FoodDB retrieval policy."""

    def describe_index(self) -> dict[str, Any]:
        """Return diagnostic metadata without granting semantic truth authority."""


__all__ = ["FoodEvidenceIndexPort"]
