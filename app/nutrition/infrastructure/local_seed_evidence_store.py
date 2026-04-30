from __future__ import annotations

from typing import Any

from .exact_item_card_loader import load_exact_item_card_seed_records
from .small_anchor_store_loader import load_small_anchor_seed_records


class LocalSeedNutritionEvidenceStore:
    """Local app-owned seed adapter for the B2 evidence store port."""

    def load_small_anchor_records(self) -> list[dict[str, Any]]:
        return list(load_small_anchor_seed_records())

    def load_exact_item_card_records(self) -> list[dict[str, Any]]:
        return list(load_exact_item_card_seed_records())


__all__ = ["LocalSeedNutritionEvidenceStore"]
