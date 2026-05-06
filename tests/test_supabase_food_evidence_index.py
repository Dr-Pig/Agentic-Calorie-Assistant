from __future__ import annotations

import json
from pathlib import Path

from app.nutrition.application.food_evidence_index_port import FoodEvidenceIndexPort
from app.nutrition.application.fooddb_index_adapter_health import (
    build_fooddb_index_adapter_health,
)
from app.nutrition.infrastructure.local_food_evidence_index import (
    LocalSmallAnchorFoodEvidenceIndex,
)
from app.nutrition.infrastructure.sqlite_food_evidence_index import (
    SQLiteFtsFoodEvidenceIndex,
)
from app.nutrition.infrastructure.supabase_food_evidence_index import (
    SupabaseRowsFoodEvidenceIndex,
)


SMALL_ANCHOR_STORE = Path("app/knowledge/small_anchor_store_tw.json")


def _small_anchor_row() -> dict[str, object]:
    return {
        "anchor_id": "single_item_tea_egg",
        "canonical_name": "Tea egg",
        "aliases": ["tea egg", "cha ye dan"],
        "dish_type": "single_item",
        "runtime_truth_allowed": True,
        "runtime_role": "common_serving_anchor",
        "kcal_point": 80,
        "kcal_range": [70, 90],
        "serving_basis": "common_serving",
        "portion_basis": {"portion_unit": "egg", "portion_quantity": 1},
        "followup_hints": [],
        "major_modifiers": [],
        "runtime_usage_boundary": "single_item",
        "source_provenance": {"source_id": "test_supabase_fixture"},
        "approval_metadata": {"approval_mode": "internal_seed_batch_approved"},
    }


def _local_index() -> LocalSmallAnchorFoodEvidenceIndex:
    return LocalSmallAnchorFoodEvidenceIndex.from_path(SMALL_ANCHOR_STORE)


def _sqlite_index(tmp_path: Path) -> SQLiteFtsFoodEvidenceIndex:
    local = _local_index()
    return SQLiteFtsFoodEvidenceIndex.rebuild_from_records(
        tmp_path / "food_evidence.sqlite",
        local.load_records(),
    )


def test_supabase_rows_index_maps_array_and_jsonb_shape_to_indexed_record() -> None:
    index: FoodEvidenceIndexPort = SupabaseRowsFoodEvidenceIndex.from_rows(
        (_small_anchor_row(),)
    )

    records = index.load_records()
    metadata = index.describe_index()

    assert len(records) == 1
    record = records[0]
    assert record.anchor_id == "single_item_tea_egg"
    assert record.aliases == ("tea egg", "cha ye dan")
    assert record.kcal_range == (70, 90)
    assert record.portion_basis == {"portion_unit": "egg", "portion_quantity": 1}
    assert record.source_provenance["source_id"] == "test_supabase_fixture"
    assert metadata["adapter_type"] == "supabase_rows_food_evidence_index"
    assert metadata["mapping_status"] == "pass"
    assert metadata["row_shape_policy"]["network_io_allowed"] is False
    assert metadata["row_shape_policy"]["supabase_client_visible"] is False
    assert "supabase_client" in metadata["forbidden_policy_dependencies"]


def test_supabase_rows_index_supports_payload_json_without_live_supabase() -> None:
    payload = _small_anchor_row()
    index = SupabaseRowsFoodEvidenceIndex.from_rows(
        (
            {
                "payload_json": json.dumps(payload),
            },
        )
    )

    records = index.load_records()

    assert len(records) == 1
    assert records[0].anchor_id == "single_item_tea_egg"
    assert records[0].runtime_truth_allowed is True
    assert index.describe_index()["mapped_record_count"] == 1


def test_supabase_rows_index_fails_closed_on_malformed_rows() -> None:
    index = SupabaseRowsFoodEvidenceIndex.from_rows(
        (
            {
                "anchor_id": "",
                "canonical_name": "Broken",
                "runtime_role": "common_serving_anchor",
            },
            {
                "payload_json": "{not-json",
                "anchor_id": "bad_payload",
                "canonical_name": "Bad payload",
                "runtime_role": "common_serving_anchor",
            },
        )
    )

    metadata = index.describe_index()

    assert index.load_records() == ()
    assert metadata["mapping_status"] == "blocked"
    assert "row_0:missing_anchor_id" in metadata["mapping_blockers"]
    assert "row_1:invalid_payload_json" in metadata["mapping_blockers"]


def test_supabase_rows_index_reports_malformed_numeric_fields_as_blockers() -> None:
    row = {
        **_small_anchor_row(),
        "kcal_point": "not-int",
        "kcal_range": ["low", "high"],
    }

    index = SupabaseRowsFoodEvidenceIndex.from_rows((row,))
    metadata = index.describe_index()

    assert index.load_records() == ()
    assert metadata["mapping_status"] == "blocked"
    assert "row_0:invalid_kcal_point" in metadata["mapping_blockers"]
    assert "row_0:invalid_kcal_range_low" in metadata["mapping_blockers"]


def test_supabase_rows_index_does_not_fix_source_only_runtime_truth_leak(
    tmp_path: Path,
) -> None:
    unsafe = {
        **_small_anchor_row(),
        "anchor_id": "tfda_source_evidence",
        "runtime_role": "source_evidence_only",
        "runtime_truth_allowed": True,
        "serving_basis": "per_100g",
    }
    supabase_index = SupabaseRowsFoodEvidenceIndex.from_rows((unsafe,))

    artifact = build_fooddb_index_adapter_health(
        local_index=_local_index(),
        sqlite_index=_sqlite_index(tmp_path),
        supabase_index=supabase_index,
    )

    assert artifact["status"] == "blocked"
    assert "supabase:tfda_source_evidence:runtime_truth_allowed_forbidden_role:source_evidence_only" in artifact[
        "blockers"
    ]
    assert artifact["future_backend_contracts"]["supabase"]["status"] == (
        "offline_row_adapter_contract_available"
    )
