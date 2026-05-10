from __future__ import annotations

from pathlib import Path

from app.nutrition.application.food_evidence_index_port import FoodEvidenceIndexPort
from app.nutrition.application.fooddb_retrieval_policy import (
    build_runtime_retrieval_records_from_small_anchor_payload,
    retrieve_fooddb_candidates,
)
from app.nutrition.infrastructure.local_food_evidence_index import (
    LocalSmallAnchorFoodEvidenceIndex,
)
from app.shared.infra.json_artifacts import read_json_artifact


SMALL_ANCHOR_STORE = Path("app/knowledge/small_anchor_store_tw.json")


def test_local_small_anchor_index_implements_port_and_preserves_existing_records() -> None:
    payload = read_json_artifact(SMALL_ANCHOR_STORE)
    expected = build_runtime_retrieval_records_from_small_anchor_payload(payload)
    index = LocalSmallAnchorFoodEvidenceIndex.from_path(SMALL_ANCHOR_STORE)

    assert isinstance(index, FoodEvidenceIndexPort)
    assert index.load_records() == expected


def test_local_small_anchor_index_reports_adapter_metadata_without_policy_leakage() -> None:
    index = LocalSmallAnchorFoodEvidenceIndex.from_path(SMALL_ANCHOR_STORE)

    metadata = index.describe_index()

    assert metadata["adapter_type"] == "local_small_anchor_json"
    assert metadata["record_contract"] == "IndexedFoodRecord"
    assert metadata["runtime_record_count"] == 55
    assert metadata["semantic_record_count"] >= 1
    assert metadata["future_backends"] == ["sqlite_fts", "supabase"]
    assert metadata["forbidden_policy_dependencies"] == [
        "sqlite_file_path",
        "supabase_client",
        "webshell",
        "manager_context_packet",
    ]


def test_retrieval_can_depend_on_port_supplied_records() -> None:
    index = LocalSmallAnchorFoodEvidenceIndex.from_path(SMALL_ANCHOR_STORE)

    result = retrieve_fooddb_candidates(
        "boba",
        retrieval_records=index.load_records(),
    )

    assert result["retrieval_scope"] == "candidate_recall_only"
    assert result["truth_selection_forbidden"] is True
    assert result["runtime_mutation_allowed"] is False
    assert result["accepted_candidates"][0]["anchor_id"] == "custom_drink_boba_milk_tea"
