from __future__ import annotations

from functools import lru_cache
from typing import Any, Protocol, Sequence


class NutritionEvidenceStorePort(Protocol):
    """Application-owned read port for B2 nutrition evidence records.

    Implementations may read local JSON seeds, SQLite/FTS, Postgres, or
    Supabase-backed tables. The port returns evidence records only; it must not
    decide logged/draft/mutation semantics.
    """

    def load_small_anchor_records(self) -> Sequence[dict[str, Any]]:
        """Return generic anchor and semantic-only support records."""

    def load_exact_item_card_records(self) -> Sequence[dict[str, Any]]:
        """Return exact item card records."""


@lru_cache(maxsize=1)
def default_nutrition_evidence_store() -> NutritionEvidenceStorePort:
    from ..infrastructure.local_seed_evidence_store import LocalSeedNutritionEvidenceStore

    return LocalSeedNutritionEvidenceStore()


__all__ = [
    "NutritionEvidenceStorePort",
    "default_nutrition_evidence_store",
]
