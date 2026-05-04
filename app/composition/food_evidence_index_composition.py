from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from app.nutrition.application.food_evidence_index_port import FoodEvidenceIndexPort
from app.nutrition.application.food_evidence_retriever_router import (
    RetrieverBackendAvailability,
)
from app.nutrition.infrastructure.local_food_evidence_index import (
    LocalSmallAnchorFoodEvidenceIndex,
)
from app.nutrition.infrastructure.sqlite_food_evidence_index import (
    SQLiteFtsFoodEvidenceIndex,
)

FoodEvidenceIndexBackend = Literal["local_json", "sqlite_fts"]


@dataclass(frozen=True)
class FoodEvidenceIndexCompositionConfig:
    backend: FoodEvidenceIndexBackend
    small_anchor_store_path: Path
    sqlite_db_path: Path | None = None
    websearch_candidate_lane: bool = False


def build_food_evidence_index(config: FoodEvidenceIndexCompositionConfig) -> FoodEvidenceIndexPort:
    if config.backend == "local_json":
        return LocalSmallAnchorFoodEvidenceIndex.from_path(config.small_anchor_store_path)
    if config.backend == "sqlite_fts":
        if config.sqlite_db_path is None:
            raise ValueError("sqlite_db_path is required for sqlite_fts backend")
        source = LocalSmallAnchorFoodEvidenceIndex.from_path(config.small_anchor_store_path)
        return SQLiteFtsFoodEvidenceIndex.rebuild_from_records(
            config.sqlite_db_path,
            source.load_records(),
        )
    raise ValueError(f"Unsupported food evidence index backend: {config.backend!r}")


def build_retriever_backend_availability(
    config: FoodEvidenceIndexCompositionConfig,
) -> RetrieverBackendAvailability:
    return RetrieverBackendAvailability(
        local_fooddb_index=True,
        sqlite_fts_index=config.backend == "sqlite_fts",
        websearch_candidate_lane=config.websearch_candidate_lane,
    )


__all__ = [
    "FoodEvidenceIndexBackend",
    "FoodEvidenceIndexCompositionConfig",
    "build_food_evidence_index",
    "build_retriever_backend_availability",
]
