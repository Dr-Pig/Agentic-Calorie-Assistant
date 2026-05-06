from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping

from app.nutrition.application.food_evidence_index_port import FoodEvidenceIndexPort
from app.nutrition.application.food_evidence_retriever_router import (
    RetrieverBackendAvailability,
)
from app.nutrition.application.fooddb_retrieval_policy import IndexedFoodRecord
from app.nutrition.infrastructure.local_food_evidence_index import (
    LocalSmallAnchorFoodEvidenceIndex,
)
from app.nutrition.infrastructure.sqlite_food_evidence_index import (
    SQLiteFtsFoodEvidenceIndex,
)
from app.nutrition.infrastructure.supabase_food_evidence_index import (
    SupabaseRowsFoodEvidenceIndex,
)

FoodEvidenceIndexBackend = Literal["local_json", "sqlite_fts", "supabase_rows"]


@dataclass(frozen=True)
class FoodEvidenceIndexCompositionConfig:
    backend: FoodEvidenceIndexBackend
    small_anchor_store_path: Path
    sqlite_db_path: Path | None = None
    websearch_candidate_lane: bool = False
    supabase_rows: tuple[Mapping[str, Any], ...] = ()


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
    if config.backend == "supabase_rows":
        return SupabaseRowsFoodEvidenceIndex.from_rows(config.supabase_rows)
    raise ValueError(f"Unsupported food evidence index backend: {config.backend!r}")


def build_retriever_backend_availability(
    config: FoodEvidenceIndexCompositionConfig,
) -> RetrieverBackendAvailability:
    return RetrieverBackendAvailability(
        local_fooddb_index=True,
        sqlite_fts_index=config.backend == "sqlite_fts",
        websearch_candidate_lane=config.websearch_candidate_lane,
        supabase_index=_supabase_rows_available(config),
    )


def _supabase_rows_available(config: FoodEvidenceIndexCompositionConfig) -> bool:
    if config.backend != "supabase_rows" or not config.supabase_rows:
        return False
    index = SupabaseRowsFoodEvidenceIndex.from_rows(config.supabase_rows)
    metadata = index.describe_index()
    return metadata.get("mapping_status") == "pass" and int(
        metadata.get("mapped_record_count") or 0
    ) > 0 and _records_runtime_boundary_passed(index.load_records())


def _records_runtime_boundary_passed(records: tuple[IndexedFoodRecord, ...]) -> bool:
    valid_runtime_records = 0
    for record in records:
        if record.runtime_truth_allowed and record.runtime_role != "common_serving_anchor":
            return False
        if record.runtime_role != "common_serving_anchor":
            continue
        if not _common_serving_anchor_ready(record):
            return False
        valid_runtime_records += 1
    return valid_runtime_records > 0


def _common_serving_anchor_ready(record: IndexedFoodRecord) -> bool:
    return (
        record.runtime_truth_allowed is True
        and record.kcal_point is not None
        and record.kcal_range is not None
        and len(record.kcal_range) == 2
        and bool(str(record.serving_basis or "").strip())
        and record.portion_basis not in (None, "", {}, [])
        and bool(record.source_provenance)
        and bool(record.approval_metadata)
        and bool(str(record.runtime_usage_boundary or "").strip())
    )


__all__ = [
    "FoodEvidenceIndexBackend",
    "FoodEvidenceIndexCompositionConfig",
    "build_food_evidence_index",
    "build_retriever_backend_availability",
]
