from __future__ import annotations

from app.nutrition.application.approved_packet_ready_fooddb_artifact import (
    build_approved_packet_ready_fooddb_artifact,
)
from app.nutrition.infrastructure.small_anchor_store_loader import (
    load_small_anchor_seed_records,
)


BATCH_IDS = {
    "listed_item_chinese_cabbage_100g",
    "listed_item_celery_100g",
    "listed_item_mustard_greens_100g",
    "listed_item_loose_leaf_lettuce_100g",
    "listed_item_pumpkin_100g",
    "listed_item_gourd_100g",
    "listed_item_purple_onion_100g",
    "listed_item_scallion_30g",
    "listed_item_burdock_100g",
    "listed_item_beef_tripe_100g",
    "listed_item_pork_large_intestine_100g",
    "listed_item_pork_ear_100g",
    "listed_item_chicken_wing_one",
    "listed_item_chicken_feet_one",
    "listed_item_chicken_gizzard_100g",
    "listed_item_bacon_slice_30g",
    "listed_item_hot_dog_one",
    "listed_item_spring_roll_one",
    "listed_item_croquette_cream_one",
    "listed_item_taiwanese_kimchi_100g",
}


def test_listed_component_batch_023_loads_component_only_tfda_records() -> None:
    records = load_small_anchor_seed_records()
    by_id = {str(record.get("anchor_id") or ""): record for record in records}

    assert BATCH_IDS <= set(by_id)
    for anchor_id in BATCH_IDS:
        record = by_id[anchor_id]
        assert record["runtime_role"] == "common_serving_anchor"
        assert record["runtime_truth_allowed"] is True
        assert record["composition_posture"] == "listed_item_component"
        assert record["source_refs"][0]["runtime_role"] == "source_evidence_only"
        assert record["source_refs"][0]["external_source_role"] == "source_evidence_only"
        assert record["source_provenance"]["source_class"] == "taiwan_tfda_open_data"
        assert record["approval_metadata"]["runtime_truth_allowed"] is True
        assert record["runtime_usage_boundary"] == "listed_component_only"


def test_listed_component_batch_023_enters_full_current_shell_with_hidden_macros() -> None:
    artifact = build_approved_packet_ready_fooddb_artifact(
        artifact_path="artifacts/approved_packet_ready_fooddb_full.json",
        selection_profile="full_current_shell",
    )
    by_id = {str(item["item_id"]): item for item in artifact["packet_ready_items"]}

    assert artifact["summary"]["packet_ready_lane_counts"]["listed_component"] == 332
    expected = {
        "listed_item_pumpkin_100g": (69, [45, 100]),
        "listed_item_pork_large_intestine_100g": (198, [150, 280]),
        "listed_item_hot_dog_one": (128, [90, 180]),
        "listed_item_taiwanese_kimchi_100g": (57, [35, 90]),
    }
    for item_id, (kcal_point, kcal_range) in expected.items():
        item = by_id[item_id]
        assert item["kcal_point"] == kcal_point
        assert item["kcal_range"] == kcal_range
        assert item["macro_visibility_status"] == "hidden_missing_source"
        assert item["macro_source_basis"] == "unknown"
        assert item["macro_confidence"] == "unknown"
