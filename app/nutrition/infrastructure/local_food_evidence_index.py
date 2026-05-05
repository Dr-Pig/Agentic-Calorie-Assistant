from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.nutrition.application.fooddb_retrieval_policy import (
    IndexedFoodRecord,
    build_runtime_retrieval_records_from_small_anchor_payload,
)
from app.shared.infra.json_artifacts import read_json_artifact


@dataclass(frozen=True)
class LocalSmallAnchorFoodEvidenceIndex:
    """Local JSON adapter for FoodEvidenceIndexPort.

    This adapter is infrastructure-owned. It keeps file loading outside the
    retrieval policy so SQLite FTS or Supabase can later supply the same records.
    """

    payload: dict[str, Any]
    source_label: str = "small_anchor_store_tw"

    @classmethod
    def from_path(cls, path: Path) -> "LocalSmallAnchorFoodEvidenceIndex":
        return cls(payload=read_json_artifact(path), source_label=path.name)

    def load_records(self) -> tuple[IndexedFoodRecord, ...]:
        return build_runtime_retrieval_records_from_small_anchor_payload(self.payload)

    def describe_index(self) -> dict[str, Any]:
        records = self.load_records()
        runtime_records = [
            record for record in records if record.runtime_role == "common_serving_anchor"
        ]
        semantic_records = [
            record for record in records if record.runtime_role == "basket_family_semantic_only"
        ]
        return {
            "adapter_type": "local_small_anchor_json",
            "source_label": self.source_label,
            "record_contract": "IndexedFoodRecord",
            "runtime_truth_boundary": "adapter_returns_indexed_records_not_truth_decisions",
            "runtime_record_count": len(runtime_records),
            "semantic_record_count": len(semantic_records),
            "future_backends": ["sqlite_fts", "supabase"],
            "forbidden_policy_dependencies": [
                "sqlite_file_path",
                "supabase_client",
                "webshell",
                "manager_context_packet",
            ],
        }


__all__ = ["LocalSmallAnchorFoodEvidenceIndex"]
